from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

# Inicializar SQLAlchemy aquí
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'directiva' o 'socio'
    fecha_alta = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_validez = db.Column(db.DateTime, nullable=False)
    
    # Relaciones
    inscripciones = db.relationship('Inscripcion', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash y guarda la contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def is_directiva(self):
        """Verifica si el usuario es de la directiva"""
        return self.rol == 'directiva'
    
    def is_socio(self):
        """Verifica si el usuario es socio"""
        return self.rol == 'socio'
    
    def suscripcion_vencida(self):
        """Verifica si la suscripción está vencida"""
        return datetime.utcnow() > self.fecha_validez
    
    def suscripcion_por_vencer(self, dias=30):
        """Verifica si la suscripción está por vencer en los próximos X días"""
        limite = datetime.utcnow() + timedelta(days=dias)
        return datetime.utcnow() < self.fecha_validez <= limite
    
    def __repr__(self):
        return f'<User {self.nombre}>'

class Actividad(db.Model):
    __tablename__ = 'actividades'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False)
    aforo_maximo = db.Column(db.Integer, nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    inscripciones = db.relationship('Inscripcion', backref='actividad', lazy=True, cascade='all, delete-orphan')
    
    def plazas_disponibles(self):
        """Calcula las plazas disponibles"""
        return self.aforo_maximo - len(self.inscripciones)
    
    def tiene_plazas_disponibles(self):
        """Verifica si hay plazas disponibles"""
        return self.plazas_disponibles() > 0
    
    def numero_inscritos(self):
        """Retorna el número de inscritos"""
        return len(self.inscripciones)
    
    def usuario_inscrito(self, user_id):
        """Verifica si un usuario está inscrito"""
        return Inscripcion.query.filter_by(user_id=user_id, actividad_id=self.id).first() is not None
    
    def __repr__(self):
        return f'<Actividad {self.nombre}>'

class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    fecha_inscripcion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    asiste = db.Column(db.Boolean, nullable=False, default=False)  # Campo para marcar asistencia
    
    # Restricción única para evitar inscripciones duplicadas
    __table_args__ = (db.UniqueConstraint('user_id', 'actividad_id', name='unique_user_actividad'),)
    
    def __repr__(self):
        return f'<Inscripcion {self.user_id} - {self.actividad_id}>'

class SolicitudSocio(db.Model):
    __tablename__ = 'solicitudes_socio'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=True)
    movil = db.Column(db.String(20), nullable=False)
    miembros_unidad_familiar = db.Column(db.Integer, nullable=False)
    forma_de_pago = db.Column(db.String(20), nullable=False)  # 'bizum', 'transferencia', 'contado'
    estado = db.Column(db.String(20), nullable=False, default='por_confirmar')  # 'por_confirmar', 'activa', 'rechazada'
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_confirmacion = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<SolicitudSocio {self.nombre} {self.primer_apellido} - {self.estado}>'
