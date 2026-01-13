from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, SolicitudSocio, BeneficiarioSolicitud, db
from datetime import datetime
import re
import unicodedata
import os
import shutil
import threading
try:
    import paramiko
    SFTP_AVAILABLE = True
except ImportError:
    SFTP_AVAILABLE = False
    print("[WARNING] paramiko no está instalado. SFTP no estará disponible.")

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
    """Sube el archivo de backup al servidor SFTP"""
    try:
        if not SFTP_AVAILABLE:
            print("[ERROR] paramiko no está disponible. No se puede subir el backup.")
            return False
        
        # Obtener credenciales SFTP de variables de entorno
        # Acepta tanto FTP_PASSWORD como FTP_PASS para compatibilidad
        sftp_host = os.environ.get('FTP_HOST')
        sftp_user = os.environ.get('FTP_USER')
        sftp_password = os.environ.get('FTP_PASSWORD') or os.environ.get('FTP_PASS')
        sftp_directory = os.environ.get('FTP_DIRECTORY', '/')
        
        # Obtener puerto SFTP (por defecto 22)
        sftp_port = int(os.environ.get('SFTP_PORT', '22'))
        
        if not all([sftp_host, sftp_user, sftp_password]):
            print(f"[INFO] Variables SFTP no configuradas completamente:")
            print(f"  FTP_HOST: {'✓' if sftp_host else '✗'}")
            print(f"  FTP_USER: {'✓' if sftp_user else '✗'}")
            print(f"  FTP_PASSWORD/FTP_PASS: {'✓' if sftp_password else '✗'}")
            print(f"  Saltando subida a SFTP")
            return False
        
        if not os.path.exists(backup_filename):
            print(f"[ERROR] Archivo de backup no encontrado: {backup_filename}")
            return False
        
        # Conectar a SFTP
        transport = paramiko.Transport((sftp_host, sftp_port))
        transport.connect(username=sftp_user, password=sftp_password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Cambiar al directorio si se especifica
        if sftp_directory and sftp_directory != '/':
            try:
                sftp.chdir(sftp_directory)
            except IOError:
                # Intentar crear el directorio si no existe
                try:
                    # Crear directorios recursivamente si no existen
                    dirs = sftp_directory.strip('/').split('/')
                    current_path = ''
                    for dir_name in dirs:
                        if dir_name:
                            current_path = current_path + '/' + dir_name if current_path else '/' + dir_name
                            try:
                                sftp.chdir(current_path)
                            except IOError:
                                sftp.mkdir(current_path)
                                sftp.chdir(current_path)
                except Exception as e:
                    print(f"[WARNING] No se pudo crear/entrar al directorio {sftp_directory}: {e}")
        
        # Subir archivo
        remote_path = os.path.join(sftp_directory, backup_filename).replace('\\', '/')
        sftp.put(backup_filename, remote_path)
        
        sftp.close()
        transport.close()
        print(f"[OK] Backup subido a SFTP: {remote_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error al subir backup a SFTP: {e}")
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
        
        ano_nacimiento = request.form.get('ano_nacimiento', '').strip()
        calle = request.form.get('calle', '').strip()
        numero = request.form.get('numero', '').strip()
        piso = request.form.get('piso', '').strip()
        poblacion = request.form.get('poblacion', '').strip()
        
        # Validaciones
        if not all([nombre, primer_apellido, movil, miembros_unidad_familiar, forma_de_pago, password, password_confirm, ano_nacimiento, calle, numero, poblacion]):
            flash('Todos los campos obligatorios deben estar completos.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Validar año de nacimiento
        try:
            ano_nac = int(ano_nacimiento)
            año_actual = datetime.now().year
            if ano_nac < 1900 or ano_nac > año_actual:
                flash('El año de nacimiento debe estar entre 1900 y el año actual.', 'error')
                from datetime import datetime as dt
                año_actual = datetime.now().year
                return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
            # Crear fecha de nacimiento usando el 1 de enero del año indicado
            fecha_nacimiento_obj = datetime(ano_nac, 1, 1).date()
        except ValueError:
            flash('Año de nacimiento inválido.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Validar contraseñas
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Validar forma de pago
        if forma_de_pago not in ['bizum', 'transferencia']:
            flash('Forma de pago inválida.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Validar miembros_unidad_familiar (debe ser numérico)
        try:
            miembros = int(miembros_unidad_familiar)
            if miembros <= 0:
                raise ValueError()
        except ValueError:
            flash('El número de miembros de la unidad familiar debe ser un número positivo.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Convertir a mayúsculas y quitar acentos
        nombre = quitar_acentos(nombre)
        primer_apellido = quitar_acentos(primer_apellido)
        if segundo_apellido:
            segundo_apellido = quitar_acentos(segundo_apellido)
        
        # Validar móvil (solo números)
        if not re.match(r'^\d{9}$', movil):
            flash('El número de móvil debe tener 9 dígitos.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
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
        try:
            db.session.flush()  # Para obtener el ID de la solicitud
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la solicitud: {str(e)}', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Verificar que el ID de la solicitud esté disponible
        if not solicitud.id:
            db.session.rollback()
            flash('Error: No se pudo obtener el ID de la solicitud. Por favor, inténtalo de nuevo.', 'error')
            from datetime import datetime as dt
            año_actual = datetime.now().year
            return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        # Procesar beneficiarios (número de miembros - 1, porque el socio no es beneficiario)
        beneficiarios_count = miembros - 1
        if beneficiarios_count > 0:
            # Debug: mostrar todos los campos del formulario
            print(f"[DEBUG] Procesando {beneficiarios_count} beneficiarios")
            print(f"[DEBUG] Campos del formulario: {list(request.form.keys())}")
            
            for i in range(1, beneficiarios_count + 1):
                beneficiario_nombre = request.form.get(f'beneficiario_nombre_{i}', '').strip()
                beneficiario_primer_apellido = request.form.get(f'beneficiario_primer_apellido_{i}', '').strip()
                beneficiario_segundo_apellido = request.form.get(f'beneficiario_segundo_apellido_{i}', '').strip()
                beneficiario_ano = request.form.get(f'beneficiario_ano_{i}', '').strip()
                
                print(f"[DEBUG] Beneficiario {i}: nombre={beneficiario_nombre}, apellido={beneficiario_primer_apellido}, año={beneficiario_ano}")
                
                # Validar campos obligatorios con mensajes más específicos
                campos_faltantes = []
                if not beneficiario_nombre:
                    campos_faltantes.append('nombre')
                if not beneficiario_primer_apellido:
                    campos_faltantes.append('primer apellido')
                if not beneficiario_ano:
                    campos_faltantes.append('año de nacimiento')
                
                if campos_faltantes:
                    flash(f'Beneficiario {i}: Faltan los siguientes campos obligatorios: {", ".join(campos_faltantes)}.', 'error')
                    db.session.rollback()
                    from datetime import datetime as dt
                    año_actual = datetime.now().year
                    return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
                
                # Validar año de nacimiento
                try:
                    ano_nacimiento = int(beneficiario_ano)
                    año_actual = datetime.now().year
                    if ano_nacimiento < 1900 or ano_nacimiento > año_actual:
                        flash(f'El año de nacimiento del beneficiario {i} no es válido.', 'error')
                        db.session.rollback()
                        from datetime import datetime as dt
                        año_actual = datetime.now().year
                        return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
                except ValueError:
                    flash(f'El año de nacimiento del beneficiario {i} debe ser un número válido.', 'error')
                    db.session.rollback()
                    from datetime import datetime as dt
                    año_actual = datetime.now().year
                    return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
                
                # Convertir a mayúsculas y quitar acentos
                beneficiario_nombre = quitar_acentos(beneficiario_nombre)
                beneficiario_primer_apellido = quitar_acentos(beneficiario_primer_apellido)
                if beneficiario_segundo_apellido:
                    beneficiario_segundo_apellido = quitar_acentos(beneficiario_segundo_apellido)
                
                # Crear beneficiario de la solicitud
                try:
                    beneficiario = BeneficiarioSolicitud(
                        solicitud_id=solicitud.id,
                        nombre=beneficiario_nombre,
                        primer_apellido=beneficiario_primer_apellido,
                        segundo_apellido=beneficiario_segundo_apellido if beneficiario_segundo_apellido else None,
                        ano_nacimiento=ano_nacimiento
                    )
                    db.session.add(beneficiario)
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error al crear el beneficiario {i}: {str(e)}', 'error')
                    import traceback
                    traceback.print_exc()
                    from datetime import datetime as dt
                    año_actual = datetime.now().year
                    return render_template('auth/hazte_socio.html', datetime=dt, current_year=año_actual)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar la solicitud: {str(e)}. Por favor, inténtalo de nuevo.', 'error')
            import traceback
            traceback.print_exc()
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
    
    # Generar nombre de usuario: nombre + iniciales de los dos apellidos + año de nacimiento
    nombre_limpio = solicitud.nombre.lower().replace(' ', '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    
    # Obtener iniciales de los apellidos
    inicial_primer_apellido = solicitud.primer_apellido[0].lower() if solicitud.primer_apellido else ''
    inicial_segundo_apellido = solicitud.segundo_apellido[0].lower() if solicitud.segundo_apellido else 'x'  # Si no hay segundo apellido, usar 'x'
    
    # Obtener año de nacimiento
    ano_nacimiento = solicitud.fecha_nacimiento.year if solicitud.fecha_nacimiento else ''
    
    nombre_usuario = f"{nombre_limpio}{inicial_primer_apellido}{inicial_segundo_apellido}{ano_nacimiento}"
    
    # Verificar si el nombre de usuario ya existe y generar uno único
    contador = 1
    nombre_usuario_original = nombre_usuario
    while User.query.filter_by(nombre_usuario=nombre_usuario).first():
        nombre_usuario = f"{nombre_limpio}{inicial_primer_apellido}{inicial_segundo_apellido}{ano_nacimiento}{contador}"
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
