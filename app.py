from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from models import User, Orden, Cliente, Anticipo, Pasaje
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novafrost_erp.db'
app.config['SECRET_KEY'] = 'cambia_este_secreto_por_algo_muy_largo_y_seguro_2025'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ====================== CREAR DB + USUARIOS INICIALES ======================
with app.app_context():
    db.create_all()

    # Admin principal
    if not User.query.filter_by(email='admin@novafrost.com').first():
        admin = User(
            email='admin@novafrost.com',
            nombre='Admin',
            apellido='NovaFrost',
            role='admin',
            activo=True
        )
        admin.set_password('admin123')  # ¡Cámbiala después!
        db.session.add(admin)
        db.session.commit()
        print("Admin creado → admin@novafrost.com / admin123")

    # Usuarios de prueba (con nombres reales)
    usuarios_prueba = [
        ('coordinador@novafrost.com', 'Carlos', 'Ramírez', 'coordinador', 'pass123'),
        ('juan.perez@novafrost.com', 'Juan', 'Pérez', 'tecnico', 'pass123'),
        ('maria.gomez@novafrost.com', 'María', 'Gómez', 'tecnico', 'pass123'),
        ('contadora@novafrost.com', 'Ana', 'López', 'contadora', 'pass123')
    ]
    for email, nombre, apellido, rol, password in usuarios_prueba:
        if not User.query.filter_by(email=email).first():
            u = User(email=email, nombre=nombre, apellido=apellido, role=rol, activo=True)
            u.set_password(password)
            db.session.add(u)
    db.session.commit()

# ====================== RUTAS PRINCIPALES ======================
@app.route('/')
def index():
    return redirect(url_for('login') if not current_user.is_authenticated else url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']) and user.activo:
            login_user(user)
            flash(f'¡Bienvenido, {user.nombre} {user.apellido}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Email o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'tecnico':
        ordenes = Orden.query.filter_by(tecnico_id=current_user.id).all()
        return render_template('dashboard_tecnico.html', ordenes=ordenes)

    elif current_user.role == 'coordinador':
        estado = request.args.get('estado')
        ordenes = Orden.query.filter_by(estado=estado).all() if estado else Orden.query.all()
        anticipos = Anticipo.query.all()
        tecnicos = User.query.filter_by(role='tecnico').all()

        # Preparar anticipos con datos calculados
        anticipos_data = []
        for a in anticipos:
            validado = db.session.query(db.func.sum(Pasaje.monto))\
                .filter(Pasaje.anticipo_id == a.id, Pasaje.validado == True).scalar() or 0
            anticipos_data.append({
                'id': a.id,
                'fecha': a.fecha,
                'tecnico': f"{a.user.nombre} {a.user.apellido}",
                'monto': a.monto,
                'validado': validado,
                'por_validar': a.monto - validado
            })

        return render_template('dashboard_coordinador.html',
                               ordenes=ordenes,
                               anticipos=anticipos_data,
                               tecnicos=tecnicos)

    elif current_user.role == 'admin':
        return redirect(url_for('admin_tecnicos'))

    return render_template('dashboard.html')

# ====================== ADMIN TÉCNICOS ======================
@app.route('/admin/tecnicos')
@login_required
def admin_tecnicos():
    if current_user.role != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('dashboard'))
    tecnicos = User.query.filter_by(role='tecnico').all()
    return render_template('admin/tecnicos.html', tecnicos=tecnicos)

@app.route('/admin/tecnicos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_tecnico():
    if current_user.role != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'danger')
        else:
            nuevo = User(
                email=email,
                nombre=request.form['nombre'],
                apellido=request.form['apellido'],
                role='tecnico',
                activo=True
            )
            nuevo.set_password(request.form['password'])
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Técnico {nuevo.nombre} {nuevo.apellido} creado con éxito', 'success')
            return redirect(url_for('admin_tecnicos'))

    return render_template('admin/nuevo_tecnico.html')

# ====================== GPS EN TIEMPO REAL ======================
tecnicos_gps = {}

@app.route('/enviar_gps', methods=['POST'])
@login_required
def enviar_gps():
    if current_user.role != 'tecnico':
        return jsonify({"error": "Solo técnicos"}), 403
    data = request.get_json()
    tecnicos_gps[current_user.id] = {
        "lat": data['lat'],
        "lng": data['lng'],
        "timestamp": datetime.utcnow().isoformat()
    }
    return jsonify({"success": True})

@app.route('/get_gps_tecnicos')
def get_gps_tecnicos():
    return jsonify(tecnicos_gps)

# ====================== OTRAS RUTAS (crear orden, dar anticipo, etc.) ======================
# (Tienes estas rutas en tu código original, solo asegúrate de tenerlas)

@app.route('/crear_orden', methods=['GET', 'POST'])
@login_required
def crear_orden():
    if current_user.role != 'coordinador':
        return redirect(url_for('dashboard'))
    # ... tu código existente de crear_orden
    pass  # ← Pega aquí tu ruta completa si ya la tienes

@app.route('/dar_anticipo', methods=['POST'])
@login_required
def dar_anticipo():
    if current_user.role != 'coordinador':
        return redirect(url_for('dashboard'))
    # ... tu código existente
    pass

# ====================== RUN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)