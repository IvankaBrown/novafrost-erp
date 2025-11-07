from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db  # Importa db desde db.py
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novafrost_erp.db'
app.config['SECRET_KEY'] = 'tu_secreto_aqui_cambia_esto_por_algo_muy_largo_y_secreto_123456789'  # ¡CÁMBIALO!

db.init_app(app)  # Inicializa db con la app

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Fix para LegacyAPIWarning

# Registra las clases de modelos
with app.app_context():
    from models import User, Orden, Cliente, Proveedor, Compra, Stock, Gasto, Ingreso, Salario, Anticipo, Pasaje

    # Crea las tablas si no existen
    db.create_all()

    # Crea un usuario de prueba para coordinador si no existe
    if not db.session.get(User, 1):
        nuevo_usuario = User(username='coordinador', password=generate_password_hash('pass123'), role='coordinador')
        db.session.add(nuevo_usuario)
        db.session.commit()

    # Crea un usuario de prueba para técnico si no existe
    if not User.query.filter_by(username='tecnico1').first():
        nuevo_tecnico = User(username='tecnico1', password=generate_password_hash('pass123'), role='tecnico')
        db.session.add(nuevo_tecnico)
        db.session.commit()

    # Crea un usuario de prueba para contadora si no existe
    if not User.query.filter_by(username='contadora').first():
        nueva_contadora = User(username='contadora', password=generate_password_hash('pass123'), role='contadora')
        db.session.add(nueva_contadora)
        db.session.commit()

# ==================== RUTA RAÍZ (ESTO SOLUCIONA EL PROBLEMA EN RENDER) ====================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))
# =======================================================================================

# Rutas
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role_lower = current_user.role.lower()
    if role_lower == 'tecnico':
        ordenes = db.session.query(Orden).filter_by(tecnico_id=current_user.id).all()
        return render_template('dashboard_tecnico.html', ordenes=ordenes)
    elif role_lower == 'coordinador':
        estado_filtro = request.args.get('estado')
        if estado_filtro:
            ordenes = db.session.query(Orden).filter_by(estado=estado_filtro).all()
        else:
            ordenes = db.session.query(Orden).all()
        compras = db.session.query(Compra).all()
        gastos_pendientes = db.session.query(Gasto).filter_by(validado=False, tipo='pasajes').all()
        anticipos = db.session.query(Anticipo).all()
        tecnicos = db.session.query(User).filter(User.role.startswith('tecnico')).all()
        anticipos_data = []
        for anticipo in anticipos:
            validado = db.session.query(db.func.sum(Pasaje.monto)).filter(Pasaje.anticipo_id == anticipo.id, Pasaje.validado == True).scalar() or 0
            por_validar = anticipo.monto - validado
            anticipos_data.append({
                'id': anticipo.id,
                'fecha': anticipo.fecha,
                'tecnico': anticipo.tecnico.username,
                'monto': anticipo.monto,
                'validado': validado,
                'por_validar': por_validar
            })
        return render_template('dashboard_coordinador.html', ordenes=ordenes, compras=compras, gastos_pendientes=gastos_pendientes, anticipos=anticipos_data, tecnicos=tecnicos)
    elif role_lower == 'contadora':
        gastos = db.session.query(Gasto).all()
        ingresos = db.session.query(Ingreso).all()
        salarios = db.session.query(Salario).all()
        compras = db.session.query(Compra).all()
        total_ingresos = sum(i.monto for i in ingresos)
        total_gastos = sum(g.monto for g in gastos)
        total_compras = sum(c.monto for c in compras)
        total_salarios = sum(s.monto for s in salarios)
        balance = total_ingresos - (total_gastos + total_compras + total_salarios)
        return render_template('dashboard_contadora.html', gastos=gastos, ingresos=ingresos, salarios=salarios, compras=compras, total_ingresos=total_ingresos, total_gastos=total_gastos, total_compras=total_compras, total_salarios=total_salarios, balance=balance)
    else:
        return 'Dashboard general'

@app.route('/crear_orden', methods=['GET', 'POST'])
@login_required
def crear_orden():
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        fecha_str = request.form['fecha']
        estado = request.form['estado']
        tipo_aparato = request.form['tipo_aparato']
        tecnico_id = request.form['tecnico_id'] if request.form['tecnico_id'] else None
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        nueva_orden = Orden(cliente_id=cliente_id, fecha=fecha, estado=estado, tipo_aparato=tipo_aparato, tecnico_id=tecnico_id)
        db.session.add(nueva_orden)
        db.session.commit()
        return redirect(url_for('dashboard'))
    clientes = db.session.query(Cliente).all()
    tecnicos = db.session.query(User).filter(User.role.startswith('tecnico')).all()
    return render_template('crear_orden.html', clientes=clientes, tecnicos=tecnicos)

@app.route('/actualizar_orden/<int:orden_id>', methods=['GET', 'POST'])
@login_required
def actualizar_orden(orden_id):
    if current_user.role.lower() not in ['coordinador', 'tecnico']:
        return redirect(url_for('dashboard'))
    orden = db.session.get(Orden, orden_id)
    if not orden:
        return 'Orden no encontrada', 404
    if request.method == 'POST':
        orden.cliente_id = request.form['cliente_id']
        fecha_str = request.form['fecha']
        orden.fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        orden.estado = request.form['estado']
        orden.tecnico_id = request.form['tecnico_id'] if request.form['tecnico_id'] else None
        orden.tipo_aparato = request.form['tipo_aparato']
        orden.falla = request.form['falla']
        orden.resolucion = request.form['resolucion']
        db.session.commit()
        return redirect(url_for('dashboard'))
    clientes = db.session.query(Cliente).all()
    tecnicos = db.session.query(User).filter(User.role.startswith('tecnico')).all()
    return render_template('actualizar_orden.html', orden=orden, clientes=clientes, tecnicos=tecnicos)

@app.route('/clientes')
@login_required
def listar_clientes():
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    clientes = db.session.query(Cliente).all()
    return render_template('listar_clientes.html', clientes=clientes)

@app.route('/crear_cliente', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        nuevo_cliente = Cliente(nombre=nombre, telefono=telefono, direccion=direccion)
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('Cliente creado exitosamente')
        return redirect(url_for('listar_clientes'))
    return render_template('crear_cliente.html')

@app.route('/crear_compra', methods=['GET', 'POST'])
@login_required
def crear_compra():
    if current_user.role.lower() != 'contadora':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        proveedor_id = request.form['proveedor_id']
        fecha_str = request.form['fecha']
        monto = request.form['monto']
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        nueva_compra = Compra(proveedor_id=proveedor_id, fecha=fecha, monto=monto)
        db.session.add(nueva_compra)
        db.session.commit()
        return redirect(url_for('dashboard'))
    proveedores = db.session.query(Proveedor).all()
    return render_template('crear_compra.html', proveedores=proveedores)

@app.route('/crear_gasto', methods=['GET', 'POST'])
@login_required
def crear_gasto():
    if current_user.role.lower() != 'contadora':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        orden_id = request.form['orden_id']
        monto = float(request.form['monto'])
        descripcion = request.form['descripcion']
        nuevo_gasto = Gasto(orden_id=orden_id, monto=monto, descripcion=descripcion)
        db.session.add(nuevo_gasto)
        db.session.commit()
        return redirect(url_for('dashboard'))
    ordenes = db.session.query(Orden).all()
    return render_template('crear_gasto.html', ordenes=ordenes)

@app.route('/crear_ingreso', methods=['GET', 'POST'])
@login_required
def crear_ingreso():
    if current_user.role.lower() != 'contadora':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        orden_id = request.form['orden_id']
        monto = float(request.form['monto'])
        fecha = datetime.now()
        nuevo_ingreso = Ingreso(orden_id=orden_id, monto=monto, fecha=fecha)
        db.session.add(nuevo_ingreso)
        db.session.commit()
        return redirect(url_for('dashboard'))
    ordenes = db.session.query(Orden).all()
    return render_template('crear_ingreso.html', ordenes=ordenes)

@app.route('/crear_salario', methods=['GET', 'POST'])
@login_required
def crear_salario():
    if current_user.role.lower() != 'contadora':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user_id = request.form['user_id']
        monto = float(request.form['monto'])
        fecha = datetime.now()
        nuevo_salario = Salario(user_id=user_id, monto=monto, fecha=fecha)
        db.session.add(nuevo_salario)
        db.session.commit()
        return redirect(url_for('dashboard'))
    usuarios = db.session.query(User).all()
    return render_template('crear_salario.html', usuarios=usuarios)

@app.route('/dar_anticipo', methods=['GET', 'POST'])
@login_required
def dar_anticipo():
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        tecnico_id = request.form['tecnico_id']
        monto = float(request.form['monto'])
        nuevo_anticipo = Anticipo(tecnico_id=tecnico_id, monto=monto)
        db.session.add(nuevo_anticipo)
        db.session.commit()
        return redirect(url_for('dashboard'))
    tecnicos = db.session.query(User).filter(User.role.startswith('tecnico')).all()
    return render_template('dar_anticipo.html', tecnicos=tecnicos)

@app.route('/validar_gasto/<int:gasto_id>', methods=['POST'])
@login_required
def validar_gasto(gasto_id):
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    gasto = db.session.get(Gasto, gasto_id)
    if gasto:
        gasto.validado = True
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/registrar_pasajes/<int:orden_id>', methods=['GET', 'POST'])
@login_required
def registrar_pasajes(orden_id):
    if current_user.role.lower() != 'tecnico':
        return redirect(url_for('dashboard'))
    orden = db.session.get(Orden, orden_id)
    if not orden or orden.tecnico_id != current_user.id:
        return 'Acceso denegado', 403

    # Obtener anticipos del técnico
    anticipos = db.session.query(Anticipo).filter_by(tecnico_id=current_user.id).all()

    if request.method == 'POST':
        origen_destino = request.form['origen_destino']
        monto = float(request.form['monto'])
        anticipo_id = request.form.get('anticipo_id')

        if not anticipo_id:
            flash('Debe seleccionar un anticipo', 'error')
            return redirect(url_for('registrar_pasajes', orden_id=orden_id))

        nuevo_pasaje = Pasaje(
            orden_id=orden_id,
            anticipo_id=anticipo_id,
            origen_destino=origen_destino,
            monto=monto
        )
        db.session.add(nuevo_pasaje)
        db.session.commit()
        flash('Pasaje registrado correctamente', 'success')
        return redirect(url_for('dashboard'))

    return render_template('registrar_pasajes.html', orden=orden, anticipos=anticipos)

@app.route('/ver_pasajes/<int:anticipo_id>', methods=['GET'])
@login_required
def ver_pasajes(anticipo_id):
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    anticipo = db.session.get(Anticipo, anticipo_id)
    if not anticipo:
        return 'Anticipo no encontrado', 404
    pasajes = db.session.query(Pasaje).filter(Pasaje.anticipo_id == anticipo.id).all()
    return render_template('ver_pasajes.html', pasajes=pasajes, anticipo=anticipo)

@app.route('/validar_pasaje/<int:pasaje_id>', methods=['POST'])
@login_required
def validar_pasaje(pasaje_id):
    if current_user.role.lower() != 'coordinador':
        return redirect(url_for('dashboard'))
    pasaje = db.session.get(Pasaje, pasaje_id)
    if pasaje:
        pasaje.validado = True
        db.session.commit()
    return redirect(url_for('dashboard'))

# ==================== ARRANQUE CORRECTO PARA RENDER ====================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
# =====================================================================