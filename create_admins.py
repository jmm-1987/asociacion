"""
Script para crear usuarios administradores (directiva)
"""
from app import create_app
from models import User, db
from datetime import datetime, timedelta, timezone

# Lista de administradores a crear
ADMINISTRADORES = [
    {'nombre': 'Coco', 'email': 'coco@asociacion.com'},
    {'nombre': 'Lidia', 'email': 'lidia@asociacion.com'},
    {'nombre': 'David', 'email': 'david@asociacion.com'},
    {'nombre': 'Bego', 'email': 'bego@asociacion.com'},
]

PASSWORD = 'admin123'

def crear_administradores():
    """Crea los usuarios administradores si no existen"""
    app = create_app()
    
    with app.app_context():
        db.create_all()
        
        creados = 0
        existentes = 0
        
        for admin_data in ADMINISTRADORES:
            # Verificar si el usuario ya existe
            usuario_existente = User.query.filter_by(email=admin_data['email']).first()
            
            if usuario_existente:
                print(f"[!] El usuario {admin_data['nombre']} ({admin_data['email']}) ya existe.")
                existentes += 1
            else:
                # Crear nuevo administrador
                admin = User(
                    nombre=admin_data['nombre'],
                    email=admin_data['email'],
                    rol='directiva',
                    fecha_alta=datetime.now(timezone.utc),
                    fecha_validez=datetime.now(timezone.utc) + timedelta(days=3650)  # 10 años de validez
                )
                admin.set_password(PASSWORD)
                
                db.session.add(admin)
                print(f"[OK] Usuario {admin_data['nombre']} ({admin_data['email']}) creado exitosamente.")
                creados += 1
        
        if creados > 0:
            db.session.commit()
            print(f"\n[SUCCESS] Se crearon {creados} administrador(es) exitosamente.")
        
        if existentes > 0:
            print(f"[INFO] {existentes} usuario(s) ya existian.")
        
        if creados == 0 and existentes > 0:
            print("\n[INFO] Todos los usuarios ya existen. No se realizaron cambios.")

if __name__ == '__main__':
    crear_administradores()

