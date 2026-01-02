from db import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='tecnico')
    nombre = db.Column(db.String(100), nullable=False, default='')
    apellido = db.Column(db.String(100), nullable=False, default='')
    activo = db.Column(db.Boolean, default=True)
    push_token = db.Column(db.String(500), nullable=True)
    numero_whatsapp = db.Column(db.String(20), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    ordenes = db.relationship('Orden', backref='tecnico', lazy=True)
    anticipos = db.relationship('Anticipo', backref='tecnico', lazy=True)
    salarios = db.relationship('Salario', backref='tecnico_user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def nombre_completo(self):
        if self.nombre and self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.email.split('@')[0].title()

    def is_admin(self):
        return self.role == 'admin'
    
        # Campos para rastreo GPS
    last_lat = db.Column(db.Float, nullable=True)                # Última latitud
    last_lng = db.Column(db.Float, nullable=True)                # Última longitud
    last_location_update = db.Column(db.DateTime, nullable=True) # Hora de la última actualización

class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    cliente = db.relationship('Cliente', backref='todas_sus_ordenes') 
    
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default='pendiente') # pendiente, urgente, completado
    tipo_aparato = db.Column(db.String(50), default='Refrigerador')
    falla = db.Column(db.String(200))
    falla_encontrada = db.Column(db.Text)
    resolucion = db.Column(db.String(200))
    
    # Costos
    valor = db.Column(db.Float, default=0.0)
    igv = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    
    # Evidencia
    video_inicial = db.Column(db.String(255))
    video_falla = db.Column(db.String(255))
    video_final = db.Column(db.String(255))
    video_demora = db.Column(db.String(255))
    justificacion_demora = db.Column(db.Text)

    # Datos de Pago
    fecha_hora_atencion = db.Column(db.DateTime)
    medio_pago = db.Column(db.String(50)) # yape, plin, efectivo
    tipo_comprobante = db.Column(db.String(50)) # boleta, factura

    pasajes = db.relationship('Pasaje', backref='orden_rel', lazy=True)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    distrito = db.Column(db.String(100))
    medio_contacto = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Pasaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    anticipo_id = db.Column(db.Integer, db.ForeignKey('anticipo.id'), nullable=True) # Puede ser nulo si no se dio anticipo previo
    origen_destino = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    validado = db.Column(db.Boolean, default=False)

class Anticipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    pasajes = db.relationship('Pasaje', backref='anticipo_rel', lazy=True)

# Otros modelos simplificados
class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(200))
    tipo = db.Column(db.String(50), default='general')
    validado = db.Column(db.Boolean, default=False)

class Salario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)