#!/usr/bin/env python3
"""
Script de prueba para verificar que la aplicación se puede importar correctamente
"""
import sys

try:
    print("Intentando importar app...")
    from app import app
    print(f"✓ App importada exitosamente: {type(app)}")
    print(f"✓ App tiene atributo 'config': {hasattr(app, 'config')}")
    print(f"✓ App tiene atributo 'route': {hasattr(app, 'route')}")
    print("✓ La aplicación está lista para usar con gunicorn")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error al importar app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

