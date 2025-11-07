from db import db  # Importa db desde db.py
from flask_login import UserMixin  # Importa UserMixin
from datetime import datetime  # Importa datetime para defaults

class User(db.Model, UserMixin):  # Hereda de UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    fecha = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    tipo_aparato = db.Column(db.String(50), nullable=False, default='Refrigerador')  # Nuevo: "Refrigerador" o "Lavadora"
    falla = db.Column(db.String(200), nullable=True)  # Concepto de la falla, ingresado por técnico
    resolucion = db.Column(db.String(200), nullable=True)  # Cómo se resolvió, ingresado por técnico
    cliente = db.relationship('Cliente', backref='ordenes', lazy=True)  # Relación para acceder al nombre del cliente
    tecnico = db.relationship('User', backref='ordenes_tecnico', lazy=True)  # Relación para técnico
    valor = db.Column(db.Float, nullable=True)  # Monto sin IGV
    igv = db.Column(db.Float, nullable=True)  # IGV 18%
    total = db.Column(db.Float, nullable=True)  # Total = valor + igv

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)  # Nuevo campo: Dirección del cliente

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
    tipo = db.Column(db.String(50), nullable=False, default='general')  # Nuevo: 'pasajes' para gastos de pasajes
    validado = db.Column(db.Boolean, nullable=False, default=False)  # Nuevo: validado por coordinador

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
    tecnico = db.relationship('User', backref='anticipos', lazy=True)  # Relación para técnico

class Pasaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden.id'), nullable=False)
    anticipo_id = db.Column(db.Integer, db.ForeignKey('anticipo.id'), nullable=False)  # Asegúrate de que esté así
    origen_destino = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    validado = db.Column(db.Boolean, nullable=False, default=False)
    orden = db.relationship('Orden', backref='pasajes', lazy=True)
    anticipo = db.relationship('Anticipo', backref='pasajes', lazy=True)