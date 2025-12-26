from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from moviepy.editor import VideoFileClip
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from models import User, Orden, Cliente, Anticipo, Pasaje
from datetime import datetime, timezone
import os

app = Flask(__name__)

# PostgreSQL persistente desde Render (Free plan)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Render usa 'postgres://' pero SQLAlchemy prefiere 'postgresql://'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://')
else:
    # Fallback local (para pruebas en tu PC)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novafrost_erp.db'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nova_frost_2025_super_secreto_ultra_seguro_1234567890!@#')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# "now" como datetime real (funciona con .strftime en templates)
app.jinja_env.globals['now'] = datetime.now(timezone.utc)

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
    print("BD creada o existente")

    try:
        # Admin principal
        if not User.query.filter_by(email='admin@novafrostperu.com').first():
            print("Creando admin@novafrostperu.com")
            admin = User(
                email='admin@novafrostperu.com',
                nombre='Admin',
                apellido='NovaFrost',
                role='admin',
                activo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin creado con éxito")
        else:
            print("Admin ya existe")

        # Usuarios de prueba
        print("Intentando crear usuarios de prueba...")
        usuarios_prueba = [
            ('coordinador@novafrostperu.com', 'Carlos', 'Ramírez', 'coordinador', 'pass123'),
            ('juan.perez@novafrostperu.com', 'Juan', 'Pérez', 'tecnico', 'pass123'),
            ('maria.gomez@novafrostperu.com', 'María', 'Gómez', 'tecnico', 'pass123'),
            ('contadora@novafrostperu.com', 'Ana', 'López', 'contadora', 'pass123')
        ]
        for email, nombre, apellido, rol, password in usuarios_prueba:
            if not User.query.filter_by(email=email).first():
                print(f"Creando {email}")
                u = User(email=email, nombre=nombre, apellido=apellido, role=rol, activo=True)
                u.set_password(password)
                db.session.add(u)
        db.session.commit()
        print("Todos los usuarios de prueba creados o ya existentes")
    except Exception as e:
        print(f"ERROR al crear usuarios: {str(e)}")
        db.session.rollback()

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
        return redirect(url_for('admin_usuarios'))  # Cambiado a panel completo de usuarios

    elif current_user.role == 'contadora':
        return render_template('dashboard_contadora.html')

    return render_template('dashboard.html')

# ====================== ADMIN USUARIOS (PANEL COMPLETO) ======================
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if current_user.role != 'admin':
        flash('Acceso restringido: solo administradores', 'danger')
        return redirect(url_for('dashboard'))
    usuarios = User.query.order_by(User.role, User.apellido).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if current_user.role != 'admin':
        flash('Solo administradores', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email ya registrado', 'danger')
        else:
            nuevo = User(
                email=email,
                nombre=request.form['nombre'].strip(),
                apellido=request.form['apellido'].strip(),
                role=request.form['role'],
                activo=True
            )
            nuevo.set_password(request.form['password'])
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Usuario {email} creado con éxito', 'success')
            return redirect(url_for('admin_usuarios'))
    
    return render_template('admin/nuevo_usuario.html')

@app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    if current_user.role != 'admin':
        flash('Solo administradores', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.nombre = request.form['nombre'].strip()
        user.apellido = request.form['apellido'].strip()
        user.role = request.form['role']
        user.activo = 'activo' in request.form
        
        if request.form['password']:
            user.set_password(request.form['password'])
        
        db.session.commit()
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('admin/editar_usuario.html', user=user)

@app.route('/admin/usuarios/desactivar/<int:user_id>', methods=['POST'])
@login_required
def desactivar_usuario(user_id):
    if current_user.role != 'admin':
        flash('Solo administradores', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin' and user.id != current_user.id:
        flash('No puedes desactivar otros admins', 'danger')
    else:
        user.activo = False
        db.session.commit()
        flash(f'Usuario {user.email} desactivado', 'warning')
    
    return redirect(url_for('admin_usuarios'))

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

# ====================== RUTAS RESTANTES (crear_orden, actualizar_orden, etc.) ======================
# (Aquí va el resto de tu código que ya tienes: crear_orden, actualizar_orden, serve_video, registrar_pasajes, clientes, etc.)
# No lo repito para no hacer el mensaje eterno, pero déjalo tal cual está.

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
            # Cliente por ID (buscador PRO)
            cliente_id = request.form.get('cliente_id')
            if not cliente_id or not cliente_id.isdigit():
                flash('Debe seleccionar un cliente de la lista', 'danger')
                return redirect(url_for('crear_orden'))
            cliente = Cliente.query.get_or_404(int(cliente_id))

            # Campos básicos
            falla = request.form['falla'].strip()
            tecnico_id = request.form['tecnico_id']
            tipo_aparato = request.form['tipo_aparato']
            total = float(request.form['total'])
            urgente = 'urgente' in request.form

            # NUEVOS CAMPOS OBLIGATORIOS
            fecha_hora_str = request.form['fecha_hora_atencion']
            medio_pago = request.form['medio_pago']
            tipo_comprobante = request.form['tipo_comprobante']

            # Crear orden con todos los datos
            orden = Orden(
                cliente_id=cliente.id,
                tecnico_id=tecnico_id,
                falla=falla,
                tipo_aparato=tipo_aparato,
                total=total,
                estado='urgente' if urgente else 'pendiente',
                fecha=datetime.utcnow(),
                fecha_hora_atencion=datetime.fromisoformat(fecha_hora_str),
                medio_pago=medio_pago,
                tipo_comprobante=tipo_comprobante
            )
            db.session.add(orden)
            db.session.commit()

            # === WHATSAPP AUTOMÁTICO ===
            tecnico = User.query.get(tecnico_id)

            # Al técnico
            if tecnico.numero_whatsapp:
                enviar_whatsapp(
                    to=tecnico.numero_whatsapp,
                    template_name="nueva_orden_tecnico",
                    params=[
                        {"type": "text", "text": tecnico.nombre_completo()},
                        {"type": "text", "text": str(orden.id)},
                        {"type": "text", "text": cliente.nombre},
                        {"type": "text", "text": falla},
                        {"type": "text", "text": fecha_hora_str.replace("T", " a las ")}
                    ]
                )

            # Al cliente
            if cliente.telefono:
                enviar_whatsapp(
                    to="51" + cliente.telefono.replace(" ", ""),
                    template_name="orden_creada_cliente",
                    params=[
                        {"type": "text", "text": cliente.nombre.split()[0]},
                        {"type": "text", "text": str(orden.id)},
                        {"type": "text", "text": fecha_hora_str.replace("T", " a las ")},
                        {"type": "text", "text": tecnico.nombre_completo()},
                        {"type": "text", "text": f"S/. {total}"},
                        {"type": "text", "text": medio_pago.upper()},
                        {"type": "text", "text": tipo_comprobante.upper()}
                    ]
                )

            flash(f'Orden #{orden.id} creada y notificaciones enviadas', 'success')
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

# ====================== RUTA ACTUALIZAR ORDEN ======================
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
           # NO TOCAMOS orden.falla (queda la original del cliente)
           orden.falla_encontrada = request.form['falla_encontrada'].strip()
           orden.justificacion_demora = request.form.get('justificacion_demora', '').strip()

           # GUARDAR VIDEOS
           upload_folder = os.path.join(current_app.root_path, 'static', 'videos')
           os.makedirs(upload_folder, exist_ok=True)

           for campo in ['video_inicial', 'video_falla', 'video_final', 'video_demora']:
               file = request.files.get(campo)
               if file and file.filename:
                   # Limitar tamaño máximo (10MB)
                   file.seek(0, os.SEEK_END)
                   file_size = file.tell()
                   file.seek(0)
                   if file_size > 10 * 1024 * 1024:
                       flash(f'Video {campo} demasiado grande (máximo 10MB)', 'danger')
                       continue

                   ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'mp4'
                   timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                   filename = f"orden_{orden.id}_{campo}_{timestamp}.{ext}"
                   filepath = os.path.join(upload_folder, filename)
                   file.save(filepath)

                   # Compresión automática
                   clip = VideoFileClip(filepath)
                   compressed_path = filepath  # Sobrescribir el original
                   clip.write_videofile(compressed_path, codec='libx264', bitrate='1000k', ffmpeg_params=["-movflags", "+faststart"])
                   clip.close()

                   setattr(orden, campo, f"/videos/{filename}")
                   print(f"Video guardado y comprimido: {campo} → {filename}")

           db.session.commit()
           flash('¡Orden actualizada y videos guardados con éxito!', 'success')
           return redirect(url_for('dashboard'))

       except Exception as e:
           db.session.rollback()
           flash(f'Error al guardar: {str(e)}', 'danger')

    return render_template('actualizar_orden.html', orden=orden)

# Nueva ruta protegida para servir videos
@app.route('/videos/<filename>')
@login_required
def serve_video(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/videos'), filename)

# ====================== REGISTRAR PASAJES ======================
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

# ====================== GESTIÓN DE CLIENTES ======================
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
            medio_contacto = request.form['medio_contacto']

            existe = Cliente.query.filter_by(nombre=nombre).first()
            if existe:
                flash('Este cliente ya existe', 'warning')
            else:
                nuevo = Cliente(
                    nombre=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    distrito=distrito,
                    medio_contacto=medio_contacto
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

# CREAR CLIENTE DESDE ORDEN Y VOLVER
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
        return redirect(url_for('crear_orden', cliente_nuevo_id=nuevo.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear cliente: {str(e)}', 'danger')
        return redirect(url_for('crear_orden'))
    
@app.route('/check_orden/<int:orden_id>', methods=['GET'])
@login_required
def check_orden(orden_id):
    if current_user.role != 'coordinador':
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))

    orden = Orden.query.get_or_404(orden_id)

    if orden.cliente.telefono:
        enviar_whatsapp(orden.cliente.telefono, 'orden_completada_cliente', params=[
            orden.cliente.nombre.split()[0],
            str(orden.id),
            orden.video_final,
            str(orden.total),
            orden.medio_pago.upper(),
            orden.tipo_comprobante.upper()
        ])

    flash(f'Orden #{orden.id} confirmada y notificación enviada al cliente', 'success')
    return redirect(url_for('dashboard'))

@app.route('/ver_orden/<int:orden_id>')
@login_required
def ver_orden(orden_id):
    orden = Orden.query.get_or_404(orden_id)
    
    if current_user.role not in ['coordinador', 'tecnico'] or \
       (current_user.role == 'tecnico' and orden.tecnico_id != current_user.id):
        flash('Acceso restringido', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('ver_orden.html', orden=orden)

# ====================== NUEVA RUTA: FINALIZAR ORDEN ======================
@app.route('/finalizar_orden/<int:orden_id>', methods=['POST'])
@login_required
def finalizar_orden(orden_id):
    if current_user.role != 'tecnico':
        flash('Solo técnicos pueden finalizar órdenes', 'danger')
        return redirect(url_for('dashboard'))

    orden = Orden.query.get_or_404(orden_id)
    if orden.tecnico_id != current_user.id:
        flash('Esta orden no te pertenece', 'danger')
        return redirect(url_for('dashboard'))

    # Validación de videos obligatorios
    if not orden.video_inicial or not orden.video_falla or not orden.video_final:
        flash('No puedes finalizar la orden: faltan videos obligatorios (Inicial, Falla o Final)', 'danger')
        return redirect(url_for('dashboard'))

    # Cambiar estado (ajusta 'completada' si usas otro valor)
    orden.estado = 'completada'
    db.session.commit()

    flash(f'Orden #{orden.id} finalizada con éxito. Listo para revisión del coordinador.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

@app.route('/firebase-messaging-sw.js')
def serve_firebase_sw():
    return send_from_directory('static', 'firebase-messaging-sw.js')

# ====================== RUN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
