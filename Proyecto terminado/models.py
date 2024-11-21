from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio_inicial = db.Column(db.Float, nullable=False)
    precio_actual = db.Column(db.Float, nullable=False)
    tiempo_fin = db.Column(db.DateTime, nullable=False)
    imagen = db.Column(db.String(255), nullable=True)  
    
    
