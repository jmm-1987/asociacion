#!/usr/bin/env python3
"""
Script para crear datos de prueba para la Asociación de Vecinos de Montealto
Ejecutar después de la primera instalación para tener datos de ejemplo
"""

from app import create_app
from models import User, Actividad, Inscripcion, db
from datetime import datetime, timedelta
import random

def create_test_data():
    """Crear datos de prueba para la aplicación"""
    app = create_app()
    
    with app.app_context():
        # Verificar si ya hay datos
        if User.query.count() > 2:  # Ya hay más que los usuarios básicos
            print("Ya existen datos de prueba. Saltando creación...")
            return
        
        print("Creando datos de prueba...")
        
        # Crear socios adicionales
        socios_data = [
            ("María García", "maria.garcia@email.com", 45),
            ("Carlos López", "carlos.lopez@email.com", 30),
            ("Ana Martínez", "ana.martinez@email.com", 60),
            ("Pedro Rodríguez", "pedro.rodriguez@email.com", 15),
            ("Laura Sánchez", "laura.sanchez@email.com", 90),
            ("Miguel Torres", "miguel.torres@email.com", 120),
            ("Carmen Ruiz", "carmen.ruiz@email.com", 200),
            ("Francisco Jiménez", "francisco.jimenez@email.com", 10),
        ]
        
        socios = []
        for nombre, email, dias_validez in socios_data:
            socio = User(
                nombre=nombre,
                email=email,
                rol='socio',
                fecha_alta=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                fecha_validez=datetime.utcnow() + timedelta(days=dias_validez)
            )
            socio.set_password('socio123')
            socios.append(socio)
            db.session.add(socio)
        
        # Crear actividades de prueba
        actividades_data = [
            {
                "nombre": "Asamblea General Anual",
                "descripcion": "Reunión anual para revisar las cuentas, proyectos y elecciones de la junta directiva.",
                "fecha": datetime.utcnow() + timedelta(days=30),
                "aforo_maximo": 50
            },
            {
                "nombre": "Fiesta de Verano",
                "descripcion": "Celebración anual de la asociación con comida, música y actividades para toda la familia.",
                "fecha": datetime.utcnow() + timedelta(days=45),
                "aforo_maximo": 100
            },
            {
                "nombre": "Taller de Jardinería",
                "descripcion": "Aprende técnicas básicas de jardinería y mantenimiento de plantas en espacios urbanos.",
                "fecha": datetime.utcnow() + timedelta(days=15),
                "aforo_maximo": 20
            },
            {
                "nombre": "Mercadillo Solidario",
                "descripcion": "Venta de segunda mano con fines benéficos. Trae lo que no uses y encuentra tesoros.",
                "fecha": datetime.utcnow() + timedelta(days=20),
                "aforo_maximo": 30
            },
            {
                "nombre": "Conferencia sobre Energías Renovables",
                "descripcion": "Charla informativa sobre la instalación de paneles solares en comunidades de vecinos.",
                "fecha": datetime.utcnow() + timedelta(days=25),
                "aforo_maximo": 40
            },
            {
                "nombre": "Torneo de Ajedrez",
                "descripcion": "Competición amistosa de ajedrez para todos los niveles. Premios para los ganadores.",
                "fecha": datetime.utcnow() + timedelta(days=35),
                "aforo_maximo": 16
            },
            {
                "nombre": "Limpieza del Barrio",
                "descripcion": "Jornada de voluntariado para mantener limpio nuestro barrio. Se proporcionarán materiales.",
                "fecha": datetime.utcnow() + timedelta(days=10),
                "aforo_maximo": 25
            },
            {
                "nombre": "Taller de Cocina Saludable",
                "descripcion": "Aprende a preparar platos nutritivos y económicos con ingredientes de temporada.",
                "fecha": datetime.utcnow() + timedelta(days=40),
                "aforo_maximo": 15
            }
        ]
        
        actividades = []
        for act_data in actividades_data:
            actividad = Actividad(
                nombre=act_data["nombre"],
                descripcion=act_data["descripcion"],
                fecha=act_data["fecha"],
                aforo_maximo=act_data["aforo_maximo"],
                fecha_creacion=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            actividades.append(actividad)
            db.session.add(actividad)
        
        # Confirmar cambios antes de crear inscripciones
        db.session.commit()
        
        # Crear inscripciones aleatorias
        print("Creando inscripciones...")
        for actividad in actividades:
            # Cada actividad tendrá entre 30% y 80% de su aforo ocupado
            num_inscripciones = random.randint(
                int(actividad.aforo_maximo * 0.3),
                int(actividad.aforo_maximo * 0.8)
            )
            
            # Seleccionar socios aleatorios (incluyendo el socio de prueba)
            todos_socios = User.query.filter_by(rol='socio').all()
            socios_inscritos = random.sample(todos_socios, min(num_inscripciones, len(todos_socios)))
            
            for socio in socios_inscritos:
                inscripcion = Inscripcion(
                    user_id=socio.id,
                    actividad_id=actividad.id,
                    fecha_inscripcion=datetime.utcnow() - timedelta(days=random.randint(1, 20))
                )
                db.session.add(inscripcion)
        
        db.session.commit()
        
        print("✅ Datos de prueba creados exitosamente!")
        print(f"📊 Estadísticas:")
        print(f"   - Socios: {User.query.filter_by(rol='socio').count()}")
        print(f"   - Actividades: {Actividad.query.count()}")
        print(f"   - Inscripciones: {Inscripcion.query.count()}")
        print("\n🎯 Puedes iniciar sesión con:")
        print("   Directiva: admin@asociacion.com / admin123")
        print("   Socio: juan@email.com / socio123")
        print("   O cualquier socio creado con contraseña: socio123")

def clear_test_data():
    """Eliminar todos los datos de prueba (mantener solo usuarios básicos)"""
    app = create_app()
    
    with app.app_context():
        print("⚠️  Eliminando datos de prueba...")
        
        # Eliminar inscripciones
        Inscripcion.query.delete()
        
        # Eliminar actividades
        Actividad.query.delete()
        
        # Eliminar socios adicionales (mantener solo admin y juan)
        User.query.filter(User.email.notin_(['admin@asociacion.com', 'juan@email.com'])).delete()
        
        db.session.commit()
        print("✅ Datos de prueba eliminados!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_test_data()
    else:
        create_test_data()
