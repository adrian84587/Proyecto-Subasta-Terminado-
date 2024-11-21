import threading
import time
from flask import Flask, render_template, redirect, url_for, request, session, flash , send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime, timedelta
from models import db, Producto
from werkzeug.utils import secure_filename
import os
from sqlalchemy.orm import joinedload

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Adrian@localhost/Subasta'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

# Modelo de Usuario
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(10), nullable=False, default='usuario')  # Puede ser 'usuario' o 'admin'

    def __repr__(self):
        return f'<Usuario {self.nombre}, Rol: {self.rol}>'

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio_inicial = db.Column(db.Float, nullable=False)
    precio_actual = db.Column(db.Float, nullable=False)
    tiempo_fin = db.Column(db.DateTime, nullable=False)
    imagen = db.Column(db.String(255), nullable=True)  

    
class HistorialPuja(db.Model):
    __tablename__ = 'historial_pujas'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    puja = db.Column(db.Float, nullable=False)
    usuario = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        if 'login' in request.form:  
            email = request.form['email']
            password = request.form['password']

            usuario = Usuario.query.filter_by(email=email).first()
            if usuario and check_password_hash(usuario.password, password):
                session['usuario_id'] = usuario.id
                session['rol'] = usuario.rol
                flash("Inicio de sesión exitoso.")
                return redirect(url_for('dashboard'))
            else:
                flash("Credenciales incorrectas. Inténtalo de nuevo.")
        
        elif 'register' in request.form:
            nombre = request.form['nombre']
            email = request.form['email']
            password = generate_password_hash(request.form['password'])
            rol = 'usuario' 

            
            nuevo_usuario = Usuario(nombre=nombre, email=email, password=password, rol=rol)
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            flash("Usuario registrado exitosamente. Ahora puedes iniciar sesión.")
            return redirect(url_for('login'))

    return render_template('login_register.html')


@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login')) 


@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    

    if session.get('rol') == 'admin':
        return redirect(url_for('admin_panel'))
    else:
        return redirect(url_for('subasta'))


@app.route('/admin')
def admin_panel():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)


@app.route('/admin/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_inicial = float(request.form['precio_inicial'])
        horas = int(request.form['tiempo_horas'])
        minutos = int(request.form['tiempo_minutos'])  

        if horas < 0 or horas > 72:
            flash("El tiempo de horas debe estar entre 0 y 72")
            return redirect(url_for('agregar_producto'))

        tiempo_fin = datetime.utcnow() + timedelta(hours=horas, minutes=minutos)


        imagen_file = request.files['imagen']
        imagen_filename = None
        if imagen_file:
            imagen_filename = secure_filename(imagen_file.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename)
            imagen_file.save(imagen_path) 
            
        nuevo_producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio_inicial=precio_inicial,
            tiempo_fin=tiempo_fin,
            precio_actual=precio_inicial,
            imagen=imagen_filename    
             )
        db.session.add(nuevo_producto)
        db.session.commit()
        

       
        flash("Producto agregado exitosamente.")
        return redirect(url_for('admin_panel'))
    return render_template('agregar_producto.html')



@app.route('/admin/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    producto = Producto.query.get(id)
    if producto:
        HistorialPuja.query.filter_by(producto_id=producto.id).delete() 
        db.session.delete(producto)
        db.session.commit()
        flash("Producto eliminado junto con su historial de pujas.")
    return redirect(url_for('admin_panel'))




@app.route('/admin/historial')
def historial():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    historial = HistorialPuja.query.order_by(HistorialPuja.fecha.desc()).all()
    return render_template('historial.html', historial=historial)


@app.route('/subasta')
def subasta():
    if session.get('rol') == 'admin':
        return redirect(url_for('admin_panel'))
    productos = Producto.query.filter(Producto.tiempo_fin > datetime.utcnow()).all()
    return render_template('subasta.html', productos=productos, datetime=datetime)


#......................................................AUN NO SIRVE..........................................................

def verificar_subastas_finalizadas():
    with app.app_context():  
        while True:
            time.sleep(60) 
            productos_finalizados = Producto.query.filter(Producto.tiempo_fin <= datetime.utcnow()).all()
            for producto in productos_finalizados:
                puja_ganadora = HistorialPuja.query.filter_by(producto_id=producto.id).order_by(HistorialPuja.puja.desc()).first()
                if puja_ganadora:
                    usuario_ganador = puja_ganadora.usuario
                    socketio.emit('notificar_ganador', {
                        'producto': producto.nombre,
                        'ganador': usuario_ganador,
                        'puja': puja_ganadora.puja
                    }, broadcast=True)
                db.session.delete(producto)  
                db.session.commit()

#.................................................................................................................................         

@socketio.on('puja')
def handle_puja(data):
    print(f"Recibida puja: {data}") 
    producto_id = data['producto_id']
    nueva_puja = float(data['nueva_puja'])
    usuario = data['usuario']
    
    producto = Producto.query.get(producto_id)
    if producto and nueva_puja > producto.precio_actual:
        producto.precio_actual = nueva_puja
        db.session.commit()

      
        historial = HistorialPuja(producto_id=producto_id, puja=nueva_puja, usuario=usuario)
        db.session.add(historial)
        db.session.commit()

       
        emit('actualizar_puja', {
            'producto_id': producto_id,
            'nueva_puja': nueva_puja,
            'usuario': usuario
        }, broadcast=True)


if __name__ == '__main__':
    threading.Thread(target=verificar_subastas_finalizadas, daemon=True).start()
    socketio.run(app, debug=True)
