"""
Script para crear usuarios administradores (directiva)
Puede ejecutarse en producción de forma segura.
"""
import os
import sys
from app import create_app
from models import User, db
from datetime import datetime, timedelta, timezone

# Lista de administradores a crear
# Si no se especifica 'password', se usa PASSWORD por defecto
ADMINISTRADORES = [
    {'nombre': 'Coco', 'nombre_usuario': 'coco'},
    {'nombre': 'Lidia', 'nombre_usuario': 'lidia'},
    {'nombre': 'Bego', 'nombre_usuario': 'bego'},
    {'nombre': 'David', 'nombre_usuario': 'david'},
    {'nombre': 'jmurillo', 'nombre_usuario': 'jmurillo', 'password': '7GMZ%elA'},
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
            usuario_existente = User.query.filter_by(nombre_usuario=admin_data['nombre_usuario']).first()
            
            # Obtener la contraseña específica o usar la por defecto
            password_usuario = admin_data.get('password', PASSWORD)
            
            if usuario_existente:
                # Si el usuario existe pero queremos actualizar su contraseña, lo hacemos
                if 'password' in admin_data:
                    usuario_existente.set_password(password_usuario)
                    db.session.commit()
                    print(f"[UPDATE] Contraseña actualizada para {admin_data['nombre']} ({admin_data['nombre_usuario']}).")
                else:
                    print(f"[!] El usuario {admin_data['nombre']} ({admin_data['nombre_usuario']}) ya existe.")
                existentes += 1
            else:
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
                password_display = "personalizada" if 'password' in admin_data else PASSWORD
                print(f"[OK] Usuario {admin_data['nombre']} ({admin_data['nombre_usuario']}) creado exitosamente con contraseña {password_display}.")
                creados += 1
        
        if creados > 0:
            db.session.commit()
            print(f"\n[SUCCESS] Se crearon {creados} administrador(es) exitosamente.")
        
        if existentes > 0:
            print(f"[INFO] {existentes} usuario(s) ya existian.")
        
        if creados == 0 and existentes > 0:
            print("\n[INFO] Todos los usuarios ya existen. No se realizaron cambios.")

if __name__ == '__main__':
    # Verificar que estamos en el contexto correcto
    print("=" * 60)
    print("Script de creación de usuarios administradores")
    print("=" * 60)
    
    # Mostrar información del entorno
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///asociacion.db')
    if 'postgres' in database_url.lower():
        print("✓ Modo: PRODUCCIÓN (PostgreSQL)")
    else:
        print("✓ Modo: DESARROLLO (SQLite)")
    
    print(f"Base de datos: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    print("\nUsuarios a crear:")
    for admin in ADMINISTRADORES:
        password_info = admin.get('password', PASSWORD)
        password_display = "personalizada" if 'password' in admin else PASSWORD
        print(f"  - {admin['nombre']} (nombre_usuario: {admin['nombre_usuario']}, contraseña: {password_display})")
    print(f"\nContraseña por defecto: {PASSWORD}")
    print("=" * 60)
    
    # Preguntar confirmación
    respuesta = input("\n¿Deseas crear estos administradores? (s/n): ").lower().strip()
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Operación cancelada.")
        sys.exit(0)
    
    print("\nIniciando creación de administradores...\n")
    crear_administradores()

