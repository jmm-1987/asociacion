"""
Script de migración para cambiar de email a nombre_usuario
Ejecutar en producción después de desplegar el código actualizado
"""
from app import create_app
from models import db, User
from sqlalchemy import text, inspect

def migrar():
    """Migra la base de datos de email a nombre_usuario"""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            print("=" * 60)
            print("Migración: email → nombre_usuario")
            print("=" * 60)
            
            # Paso 1: Agregar nombre_usuario si no existe
            if 'nombre_usuario' not in columns:
                print("\n[1/3] Agregando columna 'nombre_usuario'...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE users ADD COLUMN nombre_usuario VARCHAR(120)"))
                        conn.commit()
                    print("[OK] Columna 'nombre_usuario' agregada")
                except Exception as e:
                    print(f"[ERROR] Error al agregar 'nombre_usuario': {e}")
                    return
            else:
                print("[INFO] La columna 'nombre_usuario' ya existe")
            
            # Paso 2: Migrar datos de email a nombre_usuario (si email existe y nombre_usuario está vacío)
            if 'email' in columns:
                print("\n[2/3] Migrando datos de 'email' a 'nombre_usuario'...")
                usuarios = User.query.all()
                migrados = 0
                for usuario in usuarios:
                    if not usuario.nombre_usuario and hasattr(usuario, 'email') and usuario.email:
                        # Usar el email como nombre_usuario temporalmente
                        usuario.nombre_usuario = usuario.email
                        migrados += 1
                
                if migrados > 0:
                    db.session.commit()
                    print(f"[OK] {migrados} usuario(s) migrado(s)")
                else:
                    print("[INFO] No hay usuarios para migrar")
            else:
                print("[INFO] No existe columna 'email', saltando migración de datos")
            
            # Paso 3: Hacer nombre_usuario único y NOT NULL
            print("\n[3/3] Configurando restricciones...")
            try:
                with db.engine.connect() as conn:
                    # Verificar si hay usuarios sin nombre_usuario
                    usuarios_sin_usuario = User.query.filter(
                        (User.nombre_usuario == None) | (User.nombre_usuario == '')
                    ).count()
                    
                    if usuarios_sin_usuario > 0:
                        print(f"[ADVERTENCIA] Hay {usuarios_sin_usuario} usuario(s) sin nombre_usuario")
                        print("   Por favor, asigna nombres de usuario manualmente antes de continuar")
                        return
                    
                    # Intentar agregar restricción única (puede fallar si hay duplicados)
                    try:
                        # PostgreSQL
                        conn.execute(text("ALTER TABLE users ADD CONSTRAINT unique_nombre_usuario UNIQUE (nombre_usuario)"))
                        conn.commit()
                        print("[OK] Restricción única agregada a 'nombre_usuario'")
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            print("[INFO] La restricción única ya existe")
                        else:
                            print(f"[ADVERTENCIA] No se pudo agregar restricción única: {e}")
                            print("   Puede haber nombres de usuario duplicados")
                    
                    # Hacer NOT NULL
                    try:
                        conn.execute(text("ALTER TABLE users ALTER COLUMN nombre_usuario SET NOT NULL"))
                        conn.commit()
                        print("[OK] 'nombre_usuario' configurado como NOT NULL")
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo configurar NOT NULL: {e}")
                        
            except Exception as e:
                print(f"[ERROR] Error al configurar restricciones: {e}")
            
            print("\n" + "=" * 60)
            print("[SUCCESS] Migración completada")
            print("=" * 60)
            print("\nNOTA: La columna 'email' aún existe en la base de datos.")
            print("      Puedes eliminarla manualmente más adelante si lo deseas.")
            print("      O puedes dejarla para compatibilidad con backups antiguos.")
            
        except Exception as e:
            print(f"\n[ERROR] Error general en la migración: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    import os
    import sys
    
    print("=" * 60)
    print("Script de migración: email → nombre_usuario")
    print("=" * 60)
    
    # Verificar entorno
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///asociacion.db')
    if 'postgres' in database_url.lower():
        print("✓ Modo: PRODUCCIÓN (PostgreSQL)")
    else:
        print("✓ Modo: DESARROLLO (SQLite)")
    
    print(f"Base de datos: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    print("=" * 60)
    
    # Preguntar confirmación
    respuesta = input("\n¿Deseas ejecutar la migración? (s/n): ").lower().strip()
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Migración cancelada.")
        sys.exit(0)
    
    print("\nIniciando migración...\n")
    migrar()


