from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from models import User, Orden, Cliente, Anticipo, Pasaje
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novafrost_erp.db'
app.config['SECRET_KEY'] = 'nova_frost_2025_super_secreto_ultra_seguro_1234567890!@#'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# "now" disponible en todos los templates
app.jinja_env.globals['now'] = datetime.utcnow()   # ← CON PARÉNTESIS

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ====================== CREAR DB + USUARIOS ======================
with app.app_context():
    db.create_all()

    # Admin (siempre queda)
    if not User.query.filter_by(email='admin@novafrost.com').first():
        admin = User(email='admin@novafrost.com', nombre='Admin', apellido='NovaFrost',
                     role='admin', activo=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # Usuarios de prueba (siempre en minúsculas)
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

# ====================== RUTAS ======================
@app.route('/')
def index():
    return redirect(url_for('login') if not current_user.is_authenticated else url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form['password']) and user.activo:
            login_user(user, remember=True)
            flash(f'¡Bienvenido, {user.nombre_completo()}!', 'success')
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
        # FIX DEFINITIVO: nunca más 500 - carga el cliente y ordena por fecha
        from sqlalchemy.orm import joinedload
        ordenes = (Orden.query
                   .options(joinedload(Orden.cliente))
                   .filter_by(tecnico_id=current_user.id)
                   .order_by(Orden.fecha.desc())
                   .all())
        return render_template('dashboard_tecnico.html', ordenes=ordenes)

    elif current_user.role == 'coordinador':
        estado = request.args.get('estado')
        query = Orden.query
        if estado:
            query = query.filter_by(estado=estado)
        ordenes = query.all()

        anticipos = Anticipo.query.all()
        anticipos_data = []
        for a in anticipos:
            validado = db.session.query(db.func.sum(Pasaje.monto))\
                .filter(Pasaje.anticipo_id == a.id, Pasaje.validado == True).scalar() or 0
            anticipos_data.append({
                'id': a.id,
                'fecha': a.fecha.strftime('%d/%m/%Y'),
                'tecnico': a.user.nombre_completo() if a.user else 'Sin técnico',
                'monto': float(a.monto),
                'validado': float(validado),
                'por_validar': float(a.monto - validado)
            })

        tecnicos = User.query.filter_by(role='tecnico', activo=True).all()
        return render_template('dashboard_coordinador.html',
                               ordenes=ordenes,
                               anticipos=anticipos_data,
                               tecnicos=tecnicos)

    elif current_user.role == 'admin':
        return redirect(url_for('admin_tecnicos'))

    elif current_user.role == 'contadora':
        return render_template('dashboard_contadora.html')

    return render_template('dashboard.html')

# ====================== ADMIN TÉCNICOS ======================
@app.route('/admin/tecnicos')
@login_required
def admin_tecnicos():
    if current_user.role != 'admin':
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))
    tecnicos = User.query.filter_by(role='tecnico').order_by(User.fecha_registro.desc()).all()
    return render_template('admin/tecnicos.html', tecnicos=tecnicos)

@app.route('/admin/tecnicos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_tecnico():
    if current_user.role != 'admin':
        flash('Solo administradores', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email ya registrado', 'danger')
        else:
            nuevo = User(email=email,
                         nombre=request.form['nombre'].strip(),
                         apellido=request.form['apellido'].strip(),
                         role='tecnico',
                         activo=True)
            nuevo.set_password(request.form['password'])
            db.session.add(nuevo)
            db.session.commit()
            flash('Técnico creado con éxito', 'success')
            return redirect(url_for('admin_tecnicos'))
    return render_template('admin/nuevo_tecnico.html')

# ====================== GPS ======================
tecnicos_gps = {}

@app.route('/enviar_gps', methods=['POST'])
@login_required
def enviar_gps():
    if current_user.role != 'tecnico':
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    tecnicos_gps[current_user.id] = {
        "lat": data.get('lat'),
        "lng": data.get('lng'),
        "nombre": current_user.nombre_completo(),
        "timestamp": datetime.utcnow().strftime("%H:%M:%S")
    }
    return jsonify({"success": True})

@app.route('/get_gps_tecnicos')
def get_gps_tecnicos():
    return jsonify(tecnicos_gps)

# ====================== DEBUG TEMPORAL (BORRAR DESPUÉS) ======================
@app.route('/debug-users')
def debug_users():
    users = User.query.all()
    result = "<h2>Usuarios en la base de datos:</h2><ul>"
    for u in users:
        result += f"<li>ID: {u.id} | Email: <strong>{u.email}</strong> | Nombre: {u.nombre_completo()} | Role: {u.role}</li>"
    result += "</ul><p><a href='/'>Volver al login</a></p>"
    return result

# ====================== RUN ======================
# ====================== RUTAS QUE FALTABAN ======================
# ====================== CREAR ORDEN (CON BUSCADOR PRO DE CLIENTES) ======================
@app.route('/crear_orden', methods=['GET', 'POST'])
@login_required
def crear_orden():
    if current_user.role != 'coordinador':
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))

    tecnicos = User.query.filter_by(role='tecnico', activo=True).all()

    if request.method == 'POST':
        try:
            # --- CLIENTE: ahora OBLIGATORIAMENTE viene por ID del buscador ---
            cliente_id = request.form.get('cliente_id')
            if not cliente_id or not cliente_id.isdigit():
                flash('Debe seleccionar un cliente de la lista', 'danger')
                return redirect(url_for('crear_orden'))
            
            cliente = Cliente.query.get_or_404(int(cliente_id))

            # --- RESTO DE CAMPOS ---
            falla = request.form['falla'].strip()
            tecnico_id = request.form['tecnico_id']
            tipo_aparato = request.form['tipo_aparato']
            total = float(request.form['total'])
            urgente = 'urgente' in request.form

            # --- CREAR LA ORDEN ---
            orden = Orden(
                cliente_id=cliente.id,
                tecnico_id=tecnico_id,
                falla=falla,
                tipo_aparato=tipo_aparato,
                total=total,
                estado='urgente' if urgente else 'pendiente',
                fecha=datetime.utcnow()
            )
            db.session.add(orden)
            db.session.commit()

            flash(f'Orden #{orden.id} creada con éxito para {cliente.nombre}', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la orden: {str(e)}', 'danger')
            return redirect(url_for('crear_orden'))

    return render_template('crear_orden.html', tecnicos=tecnicos)

# ====================== LISTAR CLIENTES (opcional) ======================
@app.route('/listar_clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('listar_clientes.html', clientes=clientes)

# ====================== RUTA ACTUALIZAR ORDEN - ELIMINA EL 500 DEL TÉCNICO ======================
@app.route('/actualizar_orden/<int:orden_id>', methods=['GET', 'POST'])
@login_required
def actualizar_orden(orden_id):
    if current_user.role != 'tecnico':
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))

    orden = Orden.query.get_or_404(orden_id)
    if orden.tecnico_id != current_user.id:
        flash('No puedes editar esta orden', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            orden.falla = request.form['falla']
            orden.tipo_aparato = request.form['tipo_aparato']
            orden.estado = request.form['estado']
            orden.justificacion_demora = request.form.get('justificacion_demora', '')

            # Guardar videos si se subieron
            for campo in ['video_inicial', 'video_falla', 'video_final', 'video_demora']:
                if campo in request.files:
                    file = request.files[campo]
                    if file and file.filename != '':
                        filename = f"{orden.id}_{campo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                        filepath = os.path.join('static', 'videos', filename)
                        file.save(filepath)
                        setattr(orden, campo, f"/static/videos/{filename}")

            db.session.commit()
            flash('Orden actualizada con éxito', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    return render_template('actualizar_orden.html', orden=orden)

# ====================== REGISTRAR PASAJES (FUNCIONA CON TU TEMPLATE ORIGINAL) ======================
@app.route('/registrar_pasajes/<int:orden_id>', methods=['GET', 'POST'])
@login_required
def registrar_pasajes(orden_id):
    if current_user.role != 'tecnico':
        flash('Solo los técnicos pueden registrar pasajes', 'danger')
        return redirect(url_for('dashboard'))

    orden = Orden.query.get_or_404(orden_id)
    if orden.tecnico_id != current_user.id:
        flash('Esta orden no te pertenece', 'danger')
        return redirect(url_for('dashboard'))

    # Cargar anticipos del técnico para el select
    anticipos = Anticipo.query.filter_by(tecnico_id=current_user.id).all()

    if request.method == 'POST':
        try:
            anticipo_id = request.form['anticipo_id']
            origen_destino = request.form['origen_destino'].strip()
            monto = float(request.form['monto'])

            pasaje = Pasaje(
                orden_id=orden.id,
                anticipo_id=anticipo_id,
                tecnico_id=current_user.id,
                origen_destino=origen_destino,
                monto=monto,
                fecha=datetime.utcnow(),
                validado=False
            )
            db.session.add(pasaje)
            db.session.commit()
            flash('Pasaje registrado correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el pasaje', 'danger')

        return redirect(url_for('registrar_pasajes', orden_id=orden.id))

    return render_template('registrar_pasajes.html', orden=orden, anticipos=anticipos)

# ====================== RUN ======================
# ====================== GESTIÓN DE CLIENTES (CON MEDIO DE CONTACTO) ======================
@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def clientes():
    if current_user.role not in ['admin', 'coordinador']:
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            nombre = request.form['nombre'].strip()
            telefono = request.form.get('telefono', '').strip()
            direccion = request.form.get('direccion', '').strip()
            distrito = request.form.get('distrito', '').strip()
            medio_contacto = request.form['medio_contacto']  # ← NUEVO CAMPO

            # Evitar duplicados
            existe = Cliente.query.filter_by(nombre=nombre).first()
            if existe:
                flash('Este cliente ya existe', 'warning')
            else:
                nuevo = Cliente(
                    nombre=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    distrito=distrito,
                    medio_contacto=medio_contacto  # ← GUARDADO
                )
                db.session.add(nuevo)
                db.session.commit()
                flash(f'Cliente {nombre} creado ({medio_contacto})', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al crear cliente', 'danger')

    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('clientes.html', clientes=clientes)

# BUSCADOR DE CLIENTES PARA CREAR ORDEN
@app.route('/buscar_clientes')
@login_required
def buscar_clientes():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    clientes = Cliente.query.filter(
        Cliente.nombre.ilike(f'%{query}%')
    ).order_by(Cliente.nombre).limit(10).all()
    
    resultados = []
    for c in clientes:
        resultados.append({
            'id': c.id,
            'nombre': c.nombre,
            'telefono': c.telefono or '',
            'direccion': c.direccion or '',
            'distrito': c.distrito or '',
            'medio_contacto': c.medio_contacto or ''
        })
    
    return jsonify(resultados)

# =============================================
# CREAR CLIENTE DESDE ORDEN Y VOLVER
# =============================================
@app.route('/crear_cliente_desde_orden', methods=['POST'])
@login_required
def crear_cliente_desde_orden():
    if current_user.role not in ['admin', 'coordinador']:
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))

    try:
        nombre = request.form['nombre'].strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        distrito = request.form.get('distrito', '').strip()
        medio_contacto = request.form['medio_contacto']

        # Evitar duplicados
        existe = Cliente.query.filter_by(nombre=nombre).first()
        if existe:
            flash(f'El cliente "{nombre}" ya existe', 'warning')
            return redirect(url_for('crear_orden'))

        nuevo = Cliente(
            nombre=nombre,
            telefono=telefono,
            direccion=direccion,
            distrito=distrito,
            medio_contacto=medio_contacto
        )
        db.session.add(nuevo)
        db.session.commit()

        flash(f'Cliente {nombre} creado con éxito', 'success')
        # ← VUELVE A CREAR ORDEN CON EL CLIENTE NUEVO SELECCIONADO
        return redirect(url_for('crear_orden', cliente_nuevo_id=nuevo.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear cliente: {str(e)}', 'danger')
        return redirect(url_for('crear_orden'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)