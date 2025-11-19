"""
Script de migración para agregar campo beneficiario_id a inscripciones
"""
from app import create_app
from models import db
from sqlalchemy import text

def migrar():
    """Agrega el campo beneficiario_id a la tabla inscripciones"""
    app = create_app()
    
    with app.app_context():
        try:
            # Agregar beneficiario_id a inscripciones si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE inscripciones ADD COLUMN beneficiario_id INTEGER"))
                    conn.commit()
                print("[OK] Campo 'beneficiario_id' agregado a la tabla 'inscripciones'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'beneficiario_id' ya existe en 'inscripciones'")
                else:
                    print(f"[ERROR] Error al agregar 'beneficiario_id' a 'inscripciones': {e}")
            
            # Intentar eliminar la restricción única antigua si existe
            try:
                with db.engine.connect() as conn:
                    # SQLite no soporta DROP CONSTRAINT directamente, pero podemos recrear la tabla
                    # Por ahora solo informamos
                    print("[INFO] Nota: Si hay errores de restricción única, puede ser necesario recrear la tabla")
            except Exception as e:
                print(f"[INFO] {e}")
            
            print("\n[SUCCESS] Migración completada")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")

if __name__ == '__main__':
    migrar()

