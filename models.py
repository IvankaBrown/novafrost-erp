from db import db  # Importa db desde db.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    
    # ← AHORA USAMOS EMAIL COMO IDENTIFICADOR (más profesional y fácil)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Password ahora se guarda hasheado (seguridad)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Rol: 'admin', 'tecnico', 'coordinador'
    role = db.Column(db.String(20), nullable=False, default='tecnico')
    
    # ← CAMPOS NUEVOS PARA NOMBRES REALES
    nombre = db.Column(db.String(100), nullable=False, default='')
    apellido = db.Column(db.String(100), nullable=False, default='')
    
    # Para activar/desactivar técnicos
    activo = db.Column(db.Boolean, default=True)
    
    # Token FCM para notificaciones push (ya lo tenías, lo dejo)
    push_token = db.Column(db.String(500), nullable=True)
    
    # Fecha de registro
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones que ya tenías
    ordenes_tecnico = db.relationship('Orden', backref='tecnico', lazy=True)
    anticipos = db.relationship('Anticipo', backref='tecnico_rel', lazy=True)
    salarios = db.relationship('Salario', backref='tecnico', lazy=True)

    # Métodos para manejar password de forma segura
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Nombre completo para mostrar en dashboard y listas
    def nombre_completo(self):
        if self.nombre and self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.email.split('@')[0].title()

    # Para Flask-Login
    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} - {self.role}>'
    
    numero_whatsapp = db.Column(db.String(20), nullable=True)  # ej: '960632630'
    
# EL RESTO DE TUS MODELOS QUEDA EXACTAMENTE IGUAL
# (Solo copio los que ya tenías para que no pierdas nada)

class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    fecha = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    tipo_aparato = db.Column(db.String(50), nullable=False, default='Refrigerador')
    falla = db.Column(db.String(200), nullable=True)
    falla_encontrada = db.Column(db.Text, nullable=True)  # Diagnóstico del técnico
    resolucion = db.Column(db.String(200), nullable=True)
    valor = db.Column(db.Float, nullable=True)
    igv = db.Column(db.Float, nullable=True)
    total = db.Column(db.Float, nullable=True)
    video_inicial = db.Column(db.String(255), nullable=True)
    video_falla = db.Column(db.String(255), nullable=True)
    video_final = db.Column(db.String(255), nullable=True)
    video_demora = db.Column(db.String(255), nullable=True)
    justificacion_demora = db.Column(db.Text, nullable=True)

    # NUEVOS CAMPOS PARA WHATSAPP Y PAGO
    fecha_hora_atencion = db.Column(db.DateTime, nullable=True)  # Fecha y hora programada
    medio_pago = db.Column(db.String(50), nullable=True)  # yape, plin, efectivo, otro
    tipo_comprobante = db.Column(db.String(50), nullable=True)  # boleta, factura, otro

    cliente = db.relationship('Cliente', backref='ordenes', lazy=True)
    pasajes = db.relationship('Pasaje', backref='orden', lazy=True)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    distrito = db.Column(db.String(100), nullable=True)
    medio_contacto = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # ¡NO pongas esta línea! La relación se crea automáticamente desde el modelo Orden
    # ordenes = db.relationship('Orden', backref='cliente', lazy=True)

    def __repr__(self):
        return f'<Cliente {self.nombre}>'
    
class Proveedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)

class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    monto = db.Column(db.Float, nullable=False)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(200), nullable=True)
    tipo = db.Column(db.String(50), nullable=False, default='general')
    validado = db.Column(db.Boolean, nullable=False, default=False)

class Ingreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)

class Salario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)

class Anticipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    pasajes = db.relationship('Pasaje', backref='anticipo', lazy=True)

class Pasaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    anticipo_id = db.Column(db.Integer, db.ForeignKey('anticipo.id'), nullable=False)
    origen_destino = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    validado = db.Column(db.Boolean, nullable=False, default=False)