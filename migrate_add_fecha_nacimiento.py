"""
Script de migración para agregar campo fecha_nacimiento
"""
from app import create_app
from models import db
from sqlalchemy import text

def migrar():
    """Agrega el campo fecha_nacimiento a las tablas"""
    app = create_app()
    
    with app.app_context():
        try:
            # Agregar fecha_nacimiento a users si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN fecha_nacimiento DATE"))
                    conn.commit()
                print("[OK] Campo 'fecha_nacimiento' agregado a la tabla 'users'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'fecha_nacimiento' ya existe en 'users'")
                else:
                    print(f"[ERROR] Error al agregar 'fecha_nacimiento' a 'users': {e}")
            
            # Agregar fecha_nacimiento a solicitudes_socio si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE solicitudes_socio ADD COLUMN fecha_nacimiento DATE"))
                    conn.commit()
                print("[OK] Campo 'fecha_nacimiento' agregado a la tabla 'solicitudes_socio'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'fecha_nacimiento' ya existe en 'solicitudes_socio'")
                else:
                    print(f"[ERROR] Error al agregar 'fecha_nacimiento' a 'solicitudes_socio': {e}")
            
            print("\n[SUCCESS] Migración completada")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")

if __name__ == '__main__':
    migrar()

