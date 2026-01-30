"""
Script de migración para agregar campo movil2 a solicitudes_socio
"""
from app import create_app
from models import db
from sqlalchemy import text
import os

def migrar():
    """Agrega el campo movil2 a la tabla solicitudes_socio"""
    app = create_app()
    
    with app.app_context():
        try:
            # Obtener la ruta de la base de datos que está usando la aplicación
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'sqlite' in database_url.lower():
                db_path = database_url.replace('sqlite:///', '')
                print(f"[INFO] Base de datos en uso: {db_path}")
            
            # Agregar movil2 a solicitudes_socio si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE solicitudes_socio ADD COLUMN movil2 VARCHAR(20)"))
                    conn.commit()
                print("[OK] Campo 'movil2' agregado a la tabla 'solicitudes_socio'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'movil2' ya existe en 'solicitudes_socio'")
                else:
                    print(f"[ERROR] Error al agregar 'movil2' a 'solicitudes_socio': {e}")
            
            print("\n[SUCCESS] Migración completada")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrar()

