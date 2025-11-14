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
    
    # Base de datos - PostgreSQL en producción, SQLite en desarrollo
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render proporciona DATABASE_URL con postgres://, pero SQLAlchemy necesita postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///asociacion.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Inicializar extensiones con la app
    db.init_app(app)
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
            db.create_all()
            
            # Crear usuarios de prueba si no existen
            from models import User
            if not User.query.first():
                # Usuario directiva
                directiva = User(
                    nombre='Administrador',
                    email='admin@asociacion.com',
                    rol='directiva',
                    fecha_alta=datetime.now(),
                    fecha_validez=datetime.now() + timedelta(days=365)
                )
                directiva.set_password('admin123')
                
                # Usuario socio
                socio = User(
                    nombre='Juan Pérez',
                    email='juan@email.com',
                    rol='socio',
                    fecha_alta=datetime.now(),
                    fecha_validez=datetime.now() + timedelta(days=30)
                )
                socio.set_password('socio123')
                
                db.session.add(directiva)
                db.session.add(socio)
                db.session.commit()
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
