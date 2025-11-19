"""
Script de migración para agregar campos de edad a las tablas
"""
from app import create_app
from models import db
from sqlalchemy import text

def migrar():
    """Agrega los campos de edad a las tablas"""
    app = create_app()
    
    with app.app_context():
        try:
            # Agregar ano_nacimiento a users si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN ano_nacimiento INTEGER"))
                    conn.commit()
                print("[OK] Campo 'ano_nacimiento' agregado a la tabla 'users'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'ano_nacimiento' ya existe en 'users'")
                else:
                    print(f"[ERROR] Error al agregar 'ano_nacimiento' a 'users': {e}")
            
            # Agregar edad_minima a actividades si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE actividades ADD COLUMN edad_minima INTEGER"))
                    conn.commit()
                print("[OK] Campo 'edad_minima' agregado a la tabla 'actividades'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'edad_minima' ya existe en 'actividades'")
                else:
                    print(f"[ERROR] Error al agregar 'edad_minima' a 'actividades': {e}")
            
            # Agregar edad_maxima a actividades si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE actividades ADD COLUMN edad_maxima INTEGER"))
                    conn.commit()
                print("[OK] Campo 'edad_maxima' agregado a la tabla 'actividades'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'edad_maxima' ya existe en 'actividades'")
                else:
                    print(f"[ERROR] Error al agregar 'edad_maxima' a 'actividades': {e}")
            
            print("\n[SUCCESS] Migración completada")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")

if __name__ == '__main__':
    migrar()


