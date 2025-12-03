from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, SolicitudSocio, BeneficiarioSolicitud, db
from datetime import datetime
import re
import unicodedata
import os
import shutil
from ftplib import FTP
import threading

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

@auth_bp.route('/login')
def login():
    """Página principal/portada sin formulario de login"""
    return render_template('auth/login.html')

@auth_bp.route('/acceso-socios', methods=['GET', 'POST'])
def acceso_socios():
    """Página dedicada para el acceso de socios"""
    if current_user.is_authenticated:
        if current_user.rol == 'directiva':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('socios.dashboard'))
    
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        password = request.form.get('password')
        
        if not nombre_usuario or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('auth/acceso_socios.html')
        
        user = User.query.filter_by(nombre_usuario=nombre_usuario).first()
        
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
    
    return render_template('auth/acceso_socios.html')

def crear_backup_bd():
    """Crea un backup de la base de datos SQLite y lo sube a FTP"""
    try:
        # Obtener la URL de la base de datos desde la configuración de Flask
        from flask import current_app
        database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///asociacion.db')
        fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Solo funciona con SQLite
        if 'postgres' in database_url.lower():
            print("[INFO] Backup automático solo disponible para SQLite")
            return False
        
        # SQLite - copiar archivo
        db_path = database_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            # Ruta relativa, buscar en instance/
            db_path = os.path.join('instance', db_path)
        
        backup_filename = f'backup_sqlite_{fecha_str}.db'
        try:
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_filename)
                print(f"[OK] Backup creado: {backup_filename}")
            else:
                print(f"[ERROR] Archivo de BD no encontrado: {db_path}")
                return False
        except Exception as e:
            print(f"[ERROR] Error al copiar SQLite: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Subir a FTP
        if subir_backup_ftp(backup_filename):
            # Eliminar archivo local después de subir
            try:
                if os.path.exists(backup_filename):
                    os.remove(backup_filename)
                    print(f"[OK] Archivo local eliminado después de subir")
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo eliminar archivo local: {e}")
            return True
        else:
            # Si no se pudo subir, dejar el archivo local
            print(f"[INFO] Backup guardado localmente: {backup_filename}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error general en backup: {e}")
        import traceback
        traceback.print_exc()
        return False


def subir_backup_ftp(backup_filename):
    """Sube el archivo de backup al servidor FTP"""
    try:
        # Obtener credenciales FTP de variables de entorno
        ftp_host = os.environ.get('FTP_HOST')
        ftp_user = os.environ.get('FTP_USER')
        ftp_password = os.environ.get('FTP_PASSWORD')
        ftp_directory = os.environ.get('FTP_DIRECTORY', '/')
        
        if not all([ftp_host, ftp_user, ftp_password]):
            print("[INFO] Variables FTP no configuradas, saltando subida")
            return False
        
        if not os.path.exists(backup_filename):
            print(f"[ERROR] Archivo de backup no encontrado: {backup_filename}")
            return False
        
        # Conectar a FTP
        ftp = FTP(ftp_host)
        ftp.login(ftp_user, ftp_password)
        
        # Cambiar al directorio si se especifica
        if ftp_directory and ftp_directory != '/':
            try:
                ftp.cwd(ftp_directory)
            except:
                # Intentar crear el directorio si no existe
                try:
                    ftp.mkd(ftp_directory)
                    ftp.cwd(ftp_directory)
                except:
                    pass
        
        # Subir archivo
        with open(backup_filename, 'rb') as f:
            ftp.storbinary(f'STOR {backup_filename}', f)
        
        ftp.quit()
        print(f"[OK] Backup subido a FTP: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error al subir backup a FTP: {e}")
        import traceback
        traceback.print_exc()
        return False

@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra sesión y crea backup automático de la BD"""
    from flask import current_app
    
    # Obtener la instancia de la app antes de crear el hilo
    app_instance = current_app._get_current_object()
    
    # Crear backup en segundo plano (no bloquear el logout)
    def backup_async():
        try:
            # Necesitamos el contexto de la aplicación Flask
            with app_instance.app_context():
                crear_backup_bd()
        except Exception as e:
            print(f"[ERROR] Error en backup asíncrono: {e}")
            import traceback
            traceback.print_exc()
    
    # Ejecutar backup en un hilo separado para no bloquear
    thread = threading.Thread(target=backup_async)
    thread.daemon = True
    thread.start()
    
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.acceso_socios'))

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
        
        ano_nacimiento = request.form.get('ano_nacimiento', '').strip()
        calle = request.form.get('calle', '').strip()
        numero = request.form.get('numero', '').strip()
        piso = request.form.get('piso', '').strip()
        poblacion = request.form.get('poblacion', '').strip()
        
        # Validaciones
        if not all([nombre, primer_apellido, movil, miembros_unidad_familiar, forma_de_pago, password, password_confirm, ano_nacimiento, calle, numero, poblacion]):
            flash('Todos los campos obligatorios deben estar completos.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar año de nacimiento
        try:
            ano_nac = int(ano_nacimiento)
            año_actual = datetime.now().year
            if ano_nac < 1900 or ano_nac > año_actual:
                flash('El año de nacimiento debe estar entre 1900 y el año actual.', 'error')
                return render_template('auth/hazte_socio.html')
            # Crear fecha de nacimiento usando el 1 de enero del año indicado
            fecha_nacimiento_obj = datetime(ano_nac, 1, 1).date()
        except ValueError:
            flash('Año de nacimiento inválido.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar contraseñas
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('auth/hazte_socio.html')
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Validar forma de pago
        if forma_de_pago not in ['bizum', 'transferencia']:
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
        
        # Convertir dirección a mayúsculas
        calle = quitar_acentos(calle.upper())
        poblacion = quitar_acentos(poblacion.upper())
        numero = numero.strip()
        piso = piso.strip() if piso else None
        
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
            password_solicitud=password,  # Guardar contraseña temporalmente
            calle=calle,
            numero=numero,
            piso=piso,
            poblacion=poblacion
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
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar la solicitud. Por favor, inténtalo de nuevo.', 'error')
            return render_template('auth/hazte_socio.html')
        
        # Redirigir a la página de confirmación con el ID de la solicitud
        return redirect(url_for('auth.confirmacion_solicitud', solicitud_id=solicitud.id))
    
    from datetime import datetime as dt
    año_actual = datetime.now().year
    return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)

@auth_bp.route('/confirmacion-solicitud/<int:solicitud_id>')
def confirmacion_solicitud(solicitud_id):
    """Muestra la página de confirmación con todos los datos de la solicitud"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    # Generar nombre de usuario de forma predictiva (igual que en admin.py)
    # Calcular el próximo número de socio
    from models import User
    ultimo_socio = User.query.filter(User.numero_socio.isnot(None)).order_by(User.numero_socio.desc()).first()
    if ultimo_socio and ultimo_socio.numero_socio:
        try:
            ultimo_numero = int(ultimo_socio.numero_socio)
            nuevo_numero = ultimo_numero + 1
        except ValueError:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    numero_socio = f"{nuevo_numero:04d}"  # Formato 0001, 0002, etc.
    
    # Generar nombre de usuario: nombrenumero_de_socio
    nombre_limpio = solicitud.nombre.lower().replace(' ', '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    nombre_usuario = f"{nombre_limpio}{numero_socio}"
    
    # Verificar si el nombre de usuario ya existe y generar uno único
    contador = 1
    nombre_usuario_original = nombre_usuario
    while User.query.filter_by(nombre_usuario=nombre_usuario).first():
        nombre_usuario = f"{nombre_limpio}{numero_socio}{contador}"
        contador += 1
    
    # Números de pago (estos deberían estar en configuración, por ahora hardcodeados)
    NUMERO_BIZUM = "612 345 678"
    NUMERO_CUENTA = "ES12 3456 7890 1234 5678 9012"
    
    return render_template('auth/confirmacion_solicitud.html', 
                         solicitud=solicitud,
                         numero_bizum=NUMERO_BIZUM,
                         numero_cuenta=NUMERO_CUENTA,
                         nombre_usuario=nombre_usuario,
                         numero_socio=numero_socio)
