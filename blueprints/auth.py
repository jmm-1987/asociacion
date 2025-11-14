from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, SolicitudSocio, db
from datetime import datetime
import re
import unicodedata

auth_bp = Blueprint('auth', __name__)

def quitar_acentos(texto):
    """Convierte texto a mayúsculas y quita acentos"""
    # Normalizar a NFD (descomponer caracteres)
    texto = unicodedata.normalize('NFD', texto)
    # Filtrar solo caracteres sin acentos
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    # Convertir a mayúsculas
    return texto.upper()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.rol == 'directiva':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('socios.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'¡Bienvenido/a, {user.nombre}!', 'success')
            
            # Redirigir según el rol
            if user.rol == 'directiva':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('socios.dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/hazte-socio', methods=['GET', 'POST'])
def hazte_socio():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        primer_apellido = request.form.get('primer_apellido', '').strip()
        segundo_apellido = request.form.get('segundo_apellido', '').strip()
        movil = request.form.get('movil', '').strip()
        miembros_unidad_familiar = request.form.get('miembros_unidad_familiar', '').strip()
        forma_de_pago = request.form.get('forma_de_pago', '').strip()
        
        # Validaciones
        if not all([nombre, primer_apellido, movil, miembros_unidad_familiar, forma_de_pago]):
            flash('Todos los campos obligatorios deben estar completos.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar forma de pago
        if forma_de_pago not in ['bizum', 'transferencia', 'contado']:
            flash('Forma de pago inválida.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar miembros_unidad_familiar (debe ser numérico)
        try:
            miembros = int(miembros_unidad_familiar)
            if miembros <= 0:
                raise ValueError()
        except ValueError:
            flash('El número de miembros de la unidad familiar debe ser un número positivo.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Convertir a mayúsculas y quitar acentos
        nombre = quitar_acentos(nombre)
        primer_apellido = quitar_acentos(primer_apellido)
        if segundo_apellido:
            segundo_apellido = quitar_acentos(segundo_apellido)
        
        # Validar móvil (solo números)
        if not re.match(r'^\d{9}$', movil):
            flash('El número de móvil debe tener 9 dígitos.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Crear solicitud
        solicitud = SolicitudSocio(
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido if segundo_apellido else None,
            movil=movil,
            miembros_unidad_familiar=miembros,
            forma_de_pago=forma_de_pago,
            estado='por_confirmar'
        )
        
        db.session.add(solicitud)
        db.session.commit()
        
        flash('¡Solicitud enviada correctamente! Te contactaremos pronto para confirmar tu inscripción.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/hazte_socio.html')
