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
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {
                'timeout': 30,  # Timeout de 30 segundos para operaciones
                'check_same_thread': False,  # Permitir múltiples hilos
                'isolation_level': None,  # Usar autocommit para mejor control
            },
            'pool_pre_ping': True,
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
                'isolation_level': None,
            },
            'pool_pre_ping': True,
        }
    
    # Inicializar extensiones con la app
    db.init_app(app)
    
    # Configurar SQLite con WAL mode para mejor consistencia y rendimiento
    with app.app_context():
        try:
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' in database_url.lower():
                # Habilitar WAL mode para mejor consistencia y rendimiento
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text('PRAGMA journal_mode=WAL;'))
                    conn.execute(text('PRAGMA synchronous=NORMAL;'))
                    conn.execute(text('PRAGMA foreign_keys=ON;'))
                    conn.execute(text('PRAGMA busy_timeout=30000;'))  # 30 segundos timeout
                    conn.execute(text('PRAGMA cache_size=-64000;'))  # 64MB cache
                    conn.commit()
                print("[INFO] SQLite configurado con WAL mode y optimizaciones para producción")
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
                    
                    # Si estamos en Render con disco persistente y la BD no existe,
                    # intentar copiar desde el repositorio
                    is_render = os.environ.get('RENDER') == 'true'
                    if is_render and not os.path.exists(db_path):
                        import shutil
                        # Obtener el directorio base del proyecto
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        
                        # Buscar la base de datos en posibles ubicaciones del repositorio
                        posibles_rutas = [
                            os.path.join(base_dir, 'instance', 'asociacion.db'),
                            os.path.join(base_dir, 'asociacion.db'),
                            'instance/asociacion.db',
                            'asociacion.db',
                        ]
                        
                        # Añadir instance_path si existe
                        if hasattr(app, 'instance_path'):
                            posibles_rutas.insert(0, os.path.join(app.instance_path, 'asociacion.db'))
                        
                        for ruta_origen in posibles_rutas:
                            if ruta_origen and os.path.exists(ruta_origen):
                                try:
                                    shutil.copy2(ruta_origen, db_path)
                                    print(f"[INFO] Base de datos copiada desde {ruta_origen} a {db_path}")
                                    break
                                except Exception as e:
                                    print(f"[WARNING] No se pudo copiar la BD desde {ruta_origen}: {e}")
                            else:
                                print(f"[DEBUG] Buscando BD en: {ruta_origen} - No encontrada")
            
            db.create_all()
            
            # Crear usuario jmurillo automáticamente si no existe
            from models import User
            from datetime import datetime, timedelta, timezone
            usuario_jmurillo = User.query.filter_by(nombre_usuario='jmurillo').first()
            if not usuario_jmurillo:
                try:
                    jmurillo = User(
                        nombre='jmurillo',
                        nombre_usuario='jmurillo',
                        rol='directiva',
                        fecha_alta=datetime.now(timezone.utc),
                        fecha_validez=datetime.now(timezone.utc) + timedelta(days=3650)  # 10 años de validez
                    )
                    jmurillo.set_password('7GMZ%elA')
                    db.session.add(jmurillo)
                    db.session.commit()
                    print("[INFO] Usuario jmurillo creado automáticamente con contraseña personalizada.")
                except Exception as e:
                    print(f"[WARNING] No se pudo crear el usuario jmurillo automáticamente: {e}")
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
