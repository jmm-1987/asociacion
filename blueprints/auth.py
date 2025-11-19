from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, SolicitudSocio, BeneficiarioSolicitud, db
from datetime import datetime
import re
import unicodedata

auth_bp = Blueprint('auth', __name__)

def quitar_acentos(texto):
    """Convierte texto a mayúsculas y quita acentos, pero preserva la ñ"""
    # Usar un marcador único que no puede aparecer en el texto
    MARKER = '\uE000'  # Carácter privado Unicode que no se usa
    # Preservar la ñ antes de quitar acentos
    texto = texto.replace('ñ', MARKER).replace('Ñ', MARKER)
    # Normalizar a NFD (descomponer caracteres)
    texto = unicodedata.normalize('NFD', texto)
    # Filtrar solo caracteres sin acentos
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    # Restaurar la ñ
    texto = texto.replace(MARKER, 'Ñ')
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
            flash('Nombre de usuario o contraseña incorrectos.', 'error')
    
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
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        fecha_nacimiento = request.form.get('fecha_nacimiento', '').strip()
        
        # Validaciones
        if not all([nombre, primer_apellido, movil, miembros_unidad_familiar, forma_de_pago, password, password_confirm, fecha_nacimiento]):
            flash('Todos los campos obligatorios deben estar completos.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar fecha de nacimiento
        try:
            fecha_nacimiento_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
            if fecha_nacimiento_obj > datetime.now().date():
                flash('La fecha de nacimiento no puede ser futura.', 'error')
                return render_template('auth/hazte_socio.html')
        except ValueError:
            flash('Fecha de nacimiento inválida.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar contraseñas
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('auth/hazte_socio.html')
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'error')
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
        
        # Crear solicitud (guardar contraseña en texto plano para mostrar a admin)
        solicitud = SolicitudSocio(
            nombre=nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido if segundo_apellido else None,
            movil=movil,
            fecha_nacimiento=fecha_nacimiento_obj,
            miembros_unidad_familiar=miembros,
            forma_de_pago=forma_de_pago,
            estado='por_confirmar',
            password_solicitud=password  # Guardar contraseña temporalmente
        )
        
        db.session.add(solicitud)
        db.session.flush()  # Para obtener el ID de la solicitud
        
        # Procesar beneficiarios (número de miembros - 1, porque el socio no es beneficiario)
        beneficiarios_count = miembros - 1
        if beneficiarios_count > 0:
            for i in range(1, beneficiarios_count + 1):
                beneficiario_nombre = request.form.get(f'beneficiario_nombre_{i}', '').strip()
                beneficiario_primer_apellido = request.form.get(f'beneficiario_primer_apellido_{i}', '').strip()
                beneficiario_segundo_apellido = request.form.get(f'beneficiario_segundo_apellido_{i}', '').strip()
                beneficiario_ano = request.form.get(f'beneficiario_ano_{i}', '').strip()
                
                # Validar campos obligatorios
                if not all([beneficiario_nombre, beneficiario_primer_apellido, beneficiario_ano]):
                    flash(f'Faltan datos del beneficiario {i}. Todos los campos obligatorios deben estar completos.', 'error')
                    db.session.rollback()
                    return render_template('auth/hazte_socio.html')
                
                # Validar año de nacimiento
                try:
                    ano_nacimiento = int(beneficiario_ano)
                    año_actual = datetime.now().year
                    if ano_nacimiento < 1900 or ano_nacimiento > año_actual:
                        flash(f'El año de nacimiento del beneficiario {i} no es válido.', 'error')
                        db.session.rollback()
                        return render_template('auth/hazte_socio.html')
                except ValueError:
                    flash(f'El año de nacimiento del beneficiario {i} debe ser un número válido.', 'error')
                    db.session.rollback()
                    return render_template('auth/hazte_socio.html')
                
                # Convertir a mayúsculas y quitar acentos
                beneficiario_nombre = quitar_acentos(beneficiario_nombre)
                beneficiario_primer_apellido = quitar_acentos(beneficiario_primer_apellido)
                if beneficiario_segundo_apellido:
                    beneficiario_segundo_apellido = quitar_acentos(beneficiario_segundo_apellido)
                
                # Crear beneficiario de la solicitud
                beneficiario = BeneficiarioSolicitud(
                    solicitud_id=solicitud.id,
                    nombre=beneficiario_nombre,
                    primer_apellido=beneficiario_primer_apellido,
                    segundo_apellido=beneficiario_segundo_apellido if beneficiario_segundo_apellido else None,
                    ano_nacimiento=ano_nacimiento
                )
                db.session.add(beneficiario)
        
        db.session.commit()
        
        # Redirigir a la página de confirmación con el ID de la solicitud
        return redirect(url_for('auth.confirmacion_solicitud', solicitud_id=solicitud.id))
    
    from datetime import datetime as dt
    return render_template('auth/hazte_socio.html', datetime=dt)

@auth_bp.route('/confirmacion-solicitud/<int:solicitud_id>')
def confirmacion_solicitud(solicitud_id):
    """Muestra la página de confirmación con todos los datos de la solicitud"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    # Números de pago (estos deberían estar en configuración, por ahora hardcodeados)
    NUMERO_BIZUM = "612 345 678"
    NUMERO_CUENTA = "ES12 3456 7890 1234 5678 9012"
    
    return render_template('auth/confirmacion_solicitud.html', 
                         solicitud=solicitud,
                         numero_bizum=NUMERO_BIZUM,
                         numero_cuenta=NUMERO_CUENTA)
