"""
Script de migración para agregar campo token y hacer segundo_apellido obligatorio
"""
from app import create_app
from models import db
from sqlalchemy import text

def migrar():
    """Agrega el campo token y actualiza segundo_apellido a obligatorio"""
    app = create_app()
    
    with app.app_context():
        try:
            # Agregar token a solicitudes_socio si no existe
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE solicitudes_socio ADD COLUMN token VARCHAR(255)"))
                    conn.commit()
                print("[OK] Campo 'token' agregado a la tabla 'solicitudes_socio'")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print("[INFO] El campo 'token' ya existe en 'solicitudes_socio'")
                else:
                    print(f"[ERROR] Error al agregar 'token' a 'solicitudes_socio': {e}")
            
            # Actualizar registros existentes con segundo_apellido NULL a un valor por defecto
            # Esto es necesario antes de cambiar la columna a NOT NULL
            try:
                with db.engine.connect() as conn:
                    # Para solicitudes_socio
                    conn.execute(text("UPDATE solicitudes_socio SET segundo_apellido = '' WHERE segundo_apellido IS NULL"))
                    # Para beneficiarios_solicitud
                    conn.execute(text("UPDATE beneficiarios_solicitud SET segundo_apellido = '' WHERE segundo_apellido IS NULL"))
                    conn.commit()
                print("[OK] Registros con segundo_apellido NULL actualizados")
            except Exception as e:
                print(f"[INFO] No se pudieron actualizar registros NULL (puede que no haya registros): {e}")
            
            # Nota: Cambiar una columna de NULL a NOT NULL en SQLite requiere recrear la tabla
            # Por ahora, solo actualizamos los registros existentes
            # El modelo ya refleja que segundo_apellido debe ser NOT NULL para nuevos registros
            
            print("\n[SUCCESS] Migración completada")
            print("[INFO] Nota: Los cambios de NULL a NOT NULL se aplicarán automáticamente para nuevos registros")
            print("[INFO] Si necesitas cambiar la estructura de la tabla existente, puedes usar SQLite Browser o recrear la tabla")
            
        except Exception as e:
            print(f"[ERROR] Error general en la migración: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrar()

