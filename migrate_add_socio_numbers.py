"""
Script de migración para agregar campos de números de socio y contraseña
"""
from app import create_app
from models import db
from sqlalchemy import text

def migrar():
    """Agrega los campos de números y contraseña a las tablas"""
    app = create_app()
    
    with app.app_context():
        try:
            # Agregar numero_socio a users si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN numero_socio VARCHAR(10)"))
                    conn.commit()
                print("[OK] Campo 'numero_socio' agregado a la tabla 'users'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'numero_socio' ya existe en 'users'")
                else:
                    print(f"[ERROR] Error al agregar 'numero_socio' a 'users': {e}")
            
            # Agregar password_plain a users si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_plain VARCHAR(255)"))
                    conn.commit()
                print("[OK] Campo 'password_plain' agregado a la tabla 'users'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'password_plain' ya existe en 'users'")
                else:
                    print(f"[ERROR] Error al agregar 'password_plain' a 'users': {e}")
            
            # Agregar numero_beneficiario a beneficiarios si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE beneficiarios ADD COLUMN numero_beneficiario VARCHAR(15)"))
                    conn.commit()
                print("[OK] Campo 'numero_beneficiario' agregado a la tabla 'beneficiarios'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'numero_beneficiario' ya existe en 'beneficiarios'")
                else:
                    print(f"[ERROR] Error al agregar 'numero_beneficiario' a 'beneficiarios': {e}")
            
            # Agregar password_solicitud a solicitudes_socio si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE solicitudes_socio ADD COLUMN password_solicitud VARCHAR(255)"))
                    conn.commit()
                print("[OK] Campo 'password_solicitud' agregado a la tabla 'solicitudes_socio'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'password_solicitud' ya existe en 'solicitudes_socio'")
                else:
                    print(f"[ERROR] Error al agregar 'password_solicitud' a 'solicitudes_socio': {e}")
            
            print("\n[SUCCESS] Migración completada")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")

if __name__ == '__main__':
    migrar()

