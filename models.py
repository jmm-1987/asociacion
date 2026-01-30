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
    nombre_usuario = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    password_plain = db.Column(db.String(255), nullable=True)  # Contraseña en texto plano (solo para mostrar a admin)
    rol = db.Column(db.String(20), nullable=False)  # 'directiva' o 'socio'
    fecha_alta = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_validez = db.Column(db.DateTime, nullable=False)
    ano_nacimiento = db.Column(db.Integer, nullable=True)  # Año de nacimiento para verificar edad en actividades
    fecha_nacimiento = db.Column(db.Date, nullable=True)  # Fecha completa de nacimiento
    numero_socio = db.Column(db.String(10), unique=True, nullable=True)  # Número de socio (0001, 0002, etc.)
    calle = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    piso = db.Column(db.String(20), nullable=True)  # Opcional
    poblacion = db.Column(db.String(100), nullable=True)
    
    # Relaciones
    inscripciones = db.relationship('Inscripcion', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def calcular_edad(self):
        """Calcula la edad del usuario basándose en el año de nacimiento"""
        if not self.ano_nacimiento:
            return None
        año_actual = datetime.now().year
        return año_actual - self.ano_nacimiento
    
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
    edad_minima = db.Column(db.Integer, nullable=True)  # Edad mínima requerida (None = sin restricción)
    edad_maxima = db.Column(db.Integer, nullable=True)  # Edad máxima permitida (None = sin restricción)
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
        """Verifica si un usuario está inscrito (sin beneficiario)"""
        return Inscripcion.query.filter_by(user_id=user_id, actividad_id=self.id, beneficiario_id=None).first() is not None
    
    def beneficiario_inscrito(self, beneficiario_id):
        """Verifica si un beneficiario está inscrito"""
        return Inscripcion.query.filter_by(beneficiario_id=beneficiario_id, actividad_id=self.id).first() is not None
    
    def tiene_restriccion_edad(self):
        """Verifica si la actividad tiene restricción de edad"""
        return self.edad_minima is not None or self.edad_maxima is not None
    
    def puede_inscribirse_por_edad(self, ano_nacimiento):
        """Verifica si una persona con un año de nacimiento puede inscribirse"""
        if not self.tiene_restriccion_edad():
            return True, None
        
        if ano_nacimiento is None:
            return False, "No se puede verificar la edad. Falta el año de nacimiento."
        
        año_actual = datetime.now().year
        edad = año_actual - ano_nacimiento
        
        if self.edad_minima is not None and edad < self.edad_minima:
            return False, f"La edad mínima requerida es {self.edad_minima} años. Tienes {edad} años."
        
        if self.edad_maxima is not None and edad > self.edad_maxima:
            return False, f"La edad máxima permitida es {self.edad_maxima} años. Tienes {edad} años."
        
        return True, None
    
    def __repr__(self):
        return f'<Actividad {self.nombre}>'

class Inscripcion(db.Model):
    __tablename__ = 'inscripciones'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    beneficiario_id = db.Column(db.Integer, db.ForeignKey('beneficiarios.id'), nullable=True)  # Opcional: si es inscripción de beneficiario
    fecha_inscripcion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    asiste = db.Column(db.Boolean, nullable=False, default=False)  # Campo para marcar asistencia
    
    # Relaciones
    beneficiario = db.relationship('Beneficiario', backref='inscripciones')
    
    # Restricción única: un usuario o beneficiario solo puede inscribirse una vez por actividad
    __table_args__ = (db.UniqueConstraint('user_id', 'actividad_id', 'beneficiario_id', name='unique_inscripcion'),)
    
    def __repr__(self):
        if self.beneficiario_id:
            return f'<Inscripcion Beneficiario {self.beneficiario_id} - Actividad {self.actividad_id}>'
        return f'<Inscripcion User {self.user_id} - Actividad {self.actividad_id}>'

class SolicitudSocio(db.Model):
    __tablename__ = 'solicitudes_socio'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=False)
    movil = db.Column(db.String(20), nullable=False)
    movil2 = db.Column(db.String(20), nullable=True)  # Segundo móvil para grupo de WhatsApp (opcional)
    fecha_nacimiento = db.Column(db.Date, nullable=True)  # Fecha de nacimiento del socio
    miembros_unidad_familiar = db.Column(db.Integer, nullable=False)
    forma_de_pago = db.Column(db.String(20), nullable=False)  # 'bizum', 'transferencia', 'contado'
    estado = db.Column(db.String(20), nullable=False, default='por_confirmar')  # 'por_confirmar', 'activa', 'rechazada'
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_confirmacion = db.Column(db.DateTime, nullable=True)
    password_solicitud = db.Column(db.String(255), nullable=True)  # Contraseña temporal hasta confirmación
    token = db.Column(db.String(255), nullable=True, unique=True)  # Token único para acceso seguro a la confirmación
    calle = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    piso = db.Column(db.String(20), nullable=True)  # Opcional
    poblacion = db.Column(db.String(100), nullable=False)
    
    # Relaciones
    beneficiarios = db.relationship('BeneficiarioSolicitud', backref='solicitud', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SolicitudSocio {self.nombre} {self.primer_apellido} - {self.estado}>'

class BeneficiarioSolicitud(db.Model):
    __tablename__ = 'beneficiarios_solicitud'
    
    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes_socio.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=False)
    ano_nacimiento = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<BeneficiarioSolicitud {self.nombre} {self.primer_apellido}>'

class Beneficiario(db.Model):
    __tablename__ = 'beneficiarios'
    
    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=True)
    ano_nacimiento = db.Column(db.Integer, nullable=False)
    fecha_validez = db.Column(db.DateTime, nullable=False)  # Misma fecha que el socio
    numero_beneficiario = db.Column(db.String(15), unique=True, nullable=True)  # Número de beneficiario (0001-1, 0001-2, etc.)
    
    # Relaciones
    socio = db.relationship('User', backref='beneficiarios')
    
    def __repr__(self):
        return f'<Beneficiario {self.nombre} {self.primer_apellido}>'
