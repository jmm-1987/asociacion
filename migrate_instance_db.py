"""Script temporal para migrar instance/asociacion.db"""
import sqlite3
import os

db_path = 'instance/asociacion.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('ALTER TABLE solicitudes_socio ADD COLUMN movil2 VARCHAR(20)')
        conn.commit()
        print(f'[OK] Campo movil2 agregado a {db_path}')
        conn.close()
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
            print(f'[INFO] El campo movil2 ya existe en {db_path}')
        else:
            print(f'[ERROR] {e}')
else:
    print(f'[ERROR] No se encontró {db_path}')

