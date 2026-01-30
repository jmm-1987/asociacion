from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from datetime import datetime, timedelta
import os

# Inicializar extensiones
from models import db
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuración - usar variables de entorno para producción
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tu_clave_secreta_muy_segura_aqui_cambiar_en_produccion')
    
    # Base de datos - SQLite con disco persistente en Render, SQLite local en desarrollo
    database_url = os.environ.get('DATABASE_URL')
    
    # Si hay DATABASE_URL y es PostgreSQL, usarlo
    if database_url and database_url.startswith('postgres'):
        # Render proporciona DATABASE_URL con postgres://, pero SQLAlchemy necesita postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Usar SQLite - determinar la ruta según el entorno
        # En Render con disco persistente, usar /mnt/disk
        # En desarrollo local, usar instance/
        persistent_disk_path = os.environ.get('PERSISTENT_DISK_PATH')
        is_render = os.environ.get('RENDER') == 'true'
        
        if persistent_disk_path:
            # Ruta personalizada del disco persistente
            db_path = os.path.join(persistent_disk_path, 'asociacion.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        elif is_render:
            # En Render, usar /mnt/disk (ruta estándar del disco persistente)
            db_path = '/mnt/disk/asociacion.db'
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        else:
            # Desarrollo local - usar instance/
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asociacion.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuración específica según el tipo de base de datos
    if database_url and 'sqlite' in database_url.lower():
        # Configuración optimizada para SQLite en producción
        # IMPORTANTE: No usar isolation_level=None para mantener consistencia transaccional
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {
                'timeout': 30,  # Timeout de 30 segundos para operaciones
                'check_same_thread': False,  # Permitir múltiples hilos (necesario para Flask)
            },
            'pool_pre_ping': True,
            'poolclass': None,  # SQLite no necesita pool de conexiones
        }
    elif database_url:
        # Configuración para PostgreSQL
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
    else:
        # SQLite local (desarrollo)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {
                'timeout': 30,
                'check_same_thread': False,
            },
            'pool_pre_ping': True,
            'poolclass': None,
        }
    
    # Inicializar extensiones con la app
    db.init_app(app)
    
    # Configurar SQLite con WAL mode para mejor consistencia y rendimiento
    # Los PRAGMAs se ejecutarán automáticamente en cada nueva conexión
    with app.app_context():
        try:
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' in database_url.lower():
                from sqlalchemy import event
                
                # Registrar evento para configurar PRAGMAs en cada nueva conexión
                @event.listens_for(db.engine, "connect")
                def set_sqlite_pragmas(dbapi_conn, connection_record):
                    """Configura PRAGMAs de SQLite en cada nueva conexión para garantizar consistencia"""
                    try:
                        cursor = dbapi_conn.cursor()
                        # Configurar PRAGMAs para mejor consistencia y rendimiento
                        cursor.execute('PRAGMA journal_mode=WAL;')  # Write-Ahead Logging para mejor consistencia
                        cursor.execute('PRAGMA synchronous=NORMAL;')  # Balance entre seguridad y rendimiento
                        cursor.execute('PRAGMA foreign_keys=ON;')  # Habilitar claves foráneas
                        cursor.execute('PRAGMA busy_timeout=30000;')  # 30 segundos timeout para evitar bloqueos
                        cursor.execute('PRAGMA cache_size=-64000;')  # 64MB cache para mejor rendimiento
                        cursor.execute('PRAGMA temp_store=FILE;')  # Usar archivo temporal en disco persistente
                        cursor.close()
                    except Exception as e:
                        print(f"[WARNING] No se pudieron configurar PRAGMAs de SQLite: {e}")
                
                print("[INFO] SQLite configurado con WAL mode y optimizaciones para producción")
                print(f"[INFO] Ruta de base de datos: {database_url.replace('sqlite:///', '')}")
        except Exception as e:
            print(f"[WARNING] No se pudo configurar SQLite: {e}")
    login_manager.init_app(app)
    
    # Configurar Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Registrar blueprints
    from blueprints.auth import auth_bp
    from blueprints.socios import socios_bp
    from blueprints.actividades import actividades_bp
    from blueprints.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(socios_bp, url_prefix='/socios')
    app.register_blueprint(actividades_bp, url_prefix='/actividades')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Ruta principal
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.rol == 'directiva':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('socios.dashboard'))
        return redirect(url_for('auth.login'))
    
    # Crear tablas de base de datos (con manejo de errores)
    try:
        with app.app_context():
            # Asegurar que el directorio de la base de datos existe
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' in database_url.lower():
                # Extraer la ruta del archivo SQLite
                db_path = database_url.replace('sqlite:///', '')
                if db_path and db_path != ':memory:':
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)
                        print(f"[INFO] Directorio de base de datos creado: {db_dir}")
                    
                    # IMPORTANTE: En producción con disco persistente, NUNCA copiar BD desde el repositorio
                    # La BD debe crearse solo con db.create_all() para evitar sobrescribir datos de producción
                    # El disco persistente (/mnt/disk) persiste entre deployments, así que la BD ya existe
                    if not os.path.exists(db_path):
                        print(f"[INFO] Base de datos no encontrada en {db_path}. Se creará automáticamente con db.create_all()")
            
            db.create_all()
            
            # Verificar y añadir columnas faltantes (migraciones automáticas)
            try:
                database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if 'sqlite' in database_url.lower():
                    from sqlalchemy import text, inspect
                    inspector = inspect(db.engine)
                    
                    # Verificar si existe la tabla solicitudes_socio
                    if 'solicitudes_socio' in inspector.get_table_names():
                        # Obtener columnas existentes
                        columnas_existentes = [col['name'] for col in inspector.get_columns('solicitudes_socio')]
                        
                        # Añadir movil2 si no existe
                        if 'movil2' not in columnas_existentes:
                            try:
                                with db.engine.connect() as conn:
                                    conn.execute(text('ALTER TABLE solicitudes_socio ADD COLUMN movil2 VARCHAR(20)'))
                                    conn.commit()
                                print("[INFO] Columna 'movil2' añadida automáticamente a 'solicitudes_socio'")
                            except Exception as e:
                                error_msg = str(e).lower()
                                if "duplicate column name" in error_msg or "already exists" in error_msg:
                                    print("[INFO] La columna 'movil2' ya existe en 'solicitudes_socio'")
                                else:
                                    print(f"[WARNING] No se pudo añadir la columna 'movil2': {e}")
                                    import traceback
                                    traceback.print_exc()
                    else:
                        print("[INFO] La tabla 'solicitudes_socio' no existe aún, se creará con db.create_all()")
            except Exception as e:
                print(f"[WARNING] Error al verificar columnas: {e}")
            
            # Crear usuarios administradores automáticamente si no existen
            from models import User
            from datetime import datetime, timedelta, timezone
            
            # Lista de administradores a crear (igual que en create_admins.py)
            ADMINISTRADORES = [
                {'nombre': 'Coco', 'nombre_usuario': 'coco'},
                {'nombre': 'Lidia', 'nombre_usuario': 'lidia'},
                {'nombre': 'Bego', 'nombre_usuario': 'bego'},
                {'nombre': 'David', 'nombre_usuario': 'david'},
                {'nombre': 'jmurillo', 'nombre_usuario': 'jmurillo', 'password': '7GMZ%elA'},
            ]
            PASSWORD_DEFAULT = 'admin123'
            
            try:
                creados = 0
                for admin_data in ADMINISTRADORES:
                    # Verificar si el usuario ya existe
                    usuario_existente = User.query.filter_by(nombre_usuario=admin_data['nombre_usuario']).first()
                    
                    if not usuario_existente:
                        # Obtener la contraseña específica o usar la por defecto
                        password_usuario = admin_data.get('password', PASSWORD_DEFAULT)
                        
                        # Crear nuevo administrador
                        admin = User(
                            nombre=admin_data['nombre'],
                            nombre_usuario=admin_data['nombre_usuario'],
                            rol='directiva',
                            fecha_alta=datetime.now(timezone.utc),
                            fecha_validez=datetime.now(timezone.utc) + timedelta(days=3650)  # 10 años de validez
                        )
                        admin.set_password(password_usuario)
                        db.session.add(admin)
                        creados += 1
                
                if creados > 0:
                    db.session.commit()
                    print(f"[INFO] Se crearon {creados} administrador(es) automáticamente al iniciar la aplicación.")
            except Exception as e:
                print(f"[WARNING] No se pudieron crear los administradores automáticamente: {e}")
                db.session.rollback()
    except Exception as e:
        # Si hay un error al inicializar la BD, lo registramos pero no fallamos
        # La app seguirá funcionando y la BD se inicializará en el primer request
        import sys
        print(f"Warning: Error inicializando base de datos: {e}", file=sys.stderr)
    
    return app

# Crear la instancia de la app para gunicorn
try:
    app = create_app()
except Exception as e:
    import sys
    print(f"Error crítico al crear la aplicación: {e}", file=sys.stderr)
    raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
