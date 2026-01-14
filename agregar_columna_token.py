"""
Script para agregar la columna 'token' a la tabla solicitudes_socio
Ejecutar este script una vez para actualizar la base de datos existente
"""
import os
import sqlite3
from app import create_app

def agregar_columna_token():
    """Agrega la columna token a la tabla solicitudes_socio"""
    app = create_app()
    
    with app.app_context():
        # Obtener la ruta de la base de datos
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///asociacion.db')
        
        # Extraer la ruta del archivo SQLite
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            
            # Si es ruta relativa, buscar en instance/
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.instance_path, db_path)
        else:
            print("[ERROR] No se pudo determinar la ruta de la base de datos SQLite")
            return
        
        print(f"[INFO] Conectando a la base de datos: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"[ERROR] No se encontró el archivo de base de datos en: {db_path}")
            return
        
        try:
            # Conectar directamente a SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar si la columna ya existe
            cursor.execute("PRAGMA table_info(solicitudes_socio)")
            columnas = [col[1] for col in cursor.fetchall()]
            
            if 'token' in columnas:
                print("[INFO] La columna 'token' ya existe en la tabla solicitudes_socio")
            else:
                print("[INFO] Agregando columna 'token' a la tabla solicitudes_socio...")
                
                # Agregar la columna token
                cursor.execute("""
                    ALTER TABLE solicitudes_socio 
                    ADD COLUMN token VARCHAR(64) NULL
                """)
                
                # Crear índice único para el token
                try:
                    cursor.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS ix_solicitudes_socio_token 
                        ON solicitudes_socio(token)
                    """)
                    print("[INFO] Índice único creado para la columna 'token'")
                except sqlite3.OperationalError as e:
                    print(f"[WARNING] No se pudo crear el índice único (puede que ya exista): {e}")
                
                conn.commit()
                print("[SUCCESS] Columna 'token' agregada exitosamente")
            
            # Mostrar información sobre las solicitudes existentes
            cursor.execute("SELECT COUNT(*) FROM solicitudes_socio")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM solicitudes_socio WHERE token IS NULL")
            sin_token = cursor.fetchone()[0]
            
            print(f"[INFO] Total de solicitudes: {total}")
            print(f"[INFO] Solicitudes sin token: {sin_token}")
            
            if sin_token > 0:
                print(f"[INFO] Las solicitudes existentes sin token no serán accesibles por URL directa.")
                print(f"[INFO] Esto es el comportamiento esperado de seguridad.")
            
            conn.close()
            print("[SUCCESS] Migración completada exitosamente")
            
        except sqlite3.Error as e:
            print(f"[ERROR] Error al modificar la base de datos: {e}")
            if conn:
                conn.rollback()
                conn.close()
        except Exception as e:
            print(f"[ERROR] Error inesperado: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("Script de migración: Agregar columna 'token'")
    print("=" * 60)
    agregar_columna_token()
    print("=" * 60)


