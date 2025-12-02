"""
Script para generar 50 usuarios de prueba desde el formulario de inscripción
"""
import random
import unicodedata
from datetime import datetime, timedelta
from app import app, db
from models import SolicitudSocio, BeneficiarioSolicitud

# Función para quitar acentos (igual que en auth.py)
def quitar_acentos(texto):
    """Convierte texto a mayúsculas y quita acentos, pero preserva la ñ"""
    # Usar un marcador único que no puede aparecer en el texto
    MARKER = '\uE000'  # Carácter privado Unicode que no se usa
    # Preservar la ñ antes de quitar acentos
    texto = texto.replace('ñ', MARKER).replace('Ñ', MARKER)
    # Normalizar a NFD (descomponer caracteres)
    texto = unicodedata.normalize('NFD', texto)
    # Filtrar solo caracteres sin acentos
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    # Restaurar la ñ
    texto = texto.replace(MARKER, 'Ñ')
    # Convertir a mayúsculas
    return texto.upper()

# Listas de nombres y apellidos españoles
nombres = [
    'MARIA', 'CARMEN', 'JOSE', 'JOSE ANTONIO', 'JOSE MANUEL', 'FRANCISCO', 'ANTONIO',
    'JUAN', 'MANUEL', 'PEDRO', 'JESUS', 'ANGEL', 'MIGUEL', 'RAFAEL', 'PABLO',
    'ANA', 'LAURA', 'CRISTINA', 'MARTA', 'PATRICIA', 'LUCIA', 'SARA', 'PAULA',
    'GARCIA', 'RODRIGUEZ', 'GONZALEZ', 'FERNANDEZ', 'LOPEZ', 'MARTINEZ', 'SANCHEZ',
    'PEREZ', 'GOMEZ', 'MARTIN', 'JIMENEZ', 'RUIZ', 'HERNANDEZ', 'DIAZ', 'MORENO',
    'MUÑOZ', 'ALVAREZ', 'ROMERO', 'ALONSO', 'GUTIERREZ', 'NAVARRO', 'TORRES', 'DOMINGUEZ'
]

apellidos = [
    'GARCIA', 'RODRIGUEZ', 'GONZALEZ', 'FERNANDEZ', 'LOPEZ', 'MARTINEZ', 'SANCHEZ',
    'PEREZ', 'GOMEZ', 'MARTIN', 'JIMENEZ', 'RUIZ', 'HERNANDEZ', 'DIAZ', 'MORENO',
    'MUÑOZ', 'ALVAREZ', 'ROMERO', 'ALONSO', 'GUTIERREZ', 'NAVARRO', 'TORRES', 'DOMINGUEZ',
    'VASQUEZ', 'RAMOS', 'GIL', 'RAMIREZ', 'SERRANO', 'BLANCO', 'SUAREZ', 'MOLINA',
    'MORALES', 'ORTEGA', 'DELGADO', 'CASTRO', 'ORTIZ', 'RUBIO', 'MARIN', 'SANZ'
]

calles = [
    'CALLE MAYOR', 'CALLE REAL', 'AVENIDA DE ESPAÑA', 'CALLE DEL SOL', 'PLAZA MAYOR',
    'CALLE SAN JOSE', 'AVENIDA DE LA CONSTITUCION', 'CALLE VIRGEN', 'CALLE SANTA MARIA',
    'CALLE CERVANTES', 'AVENIDA DE EUROPA', 'CALLE LOPE DE VEGA', 'CALLE VELAZQUEZ',
    'CALLE GOYA', 'CALLE PICASSO', 'AVENIDA DE AMERICA', 'CALLE GRAN VIA'
]

poblaciones = [
    'MADRID', 'BARCELONA', 'VALENCIA', 'SEVILLA', 'ZARAGOZA', 'MALAGA', 'MURCIA',
    'PALMA', 'LAS PALMAS', 'BILBAO', 'ALICANTE', 'CORDOBA', 'VALLADOLID', 'VIGO',
    'GIJON', 'GRANADA', 'VITORIA', 'A CORUÑA', 'ELCHE', 'SANTA CRUZ DE TENERIFE'
]

def generar_telefono():
    """Genera un número de teléfono móvil español válido"""
    return ''.join([str(random.randint(6, 7))] + [str(random.randint(0, 9)) for _ in range(8)])

def generar_ano_nacimiento():
    """Genera un año de nacimiento entre 1950 y 2005"""
    return random.randint(1950, 2005)

def generar_datos_usuario():
    """Genera datos aleatorios para un usuario"""
    nombre = random.choice(nombres)
    primer_apellido = random.choice(apellidos)
    segundo_apellido = random.choice(apellidos) if random.random() > 0.3 else None
    
    # Asegurar que las ñ se preserven
    nombre = quitar_acentos(nombre)
    primer_apellido = quitar_acentos(primer_apellido)
    if segundo_apellido:
        segundo_apellido = quitar_acentos(segundo_apellido)
    
    movil = generar_telefono()
    ano_nacimiento = generar_ano_nacimiento()
    miembros = random.randint(1, 5)  # Entre 1 y 5 miembros
    forma_pago = random.choice(['bizum', 'transferencia'])
    
    # Dirección
    calle = quitar_acentos(random.choice(calles))
    numero = str(random.randint(1, 200))
    piso = None
    if random.random() > 0.4:  # 60% de probabilidad de tener piso
        piso = f"{random.randint(1, 10)}º {random.choice(['A', 'B', 'C', 'D'])}"
    poblacion = quitar_acentos(random.choice(poblaciones))
    
    # Contraseña simple para pruebas
    password = '123456'
    
    return {
        'nombre': nombre,
        'primer_apellido': primer_apellido,
        'segundo_apellido': segundo_apellido,
        'movil': movil,
        'ano_nacimiento': ano_nacimiento,
        'miembros': miembros,
        'forma_pago': forma_pago,
        'calle': calle,
        'numero': numero,
        'piso': piso,
        'poblacion': poblacion,
        'password': password
    }

def generar_beneficiarios(solicitud_id, cantidad):
    """Genera beneficiarios para una solicitud"""
    beneficiarios = []
    for i in range(cantidad):
        nombre = quitar_acentos(random.choice(nombres))
        primer_apellido = quitar_acentos(random.choice(apellidos))
        segundo_apellido = quitar_acentos(random.choice(apellidos)) if random.random() > 0.3 else None
        ano_nacimiento = random.randint(2000, 2020)  # Beneficiarios más jóvenes
        
        beneficiarios.append({
            'solicitud_id': solicitud_id,
            'nombre': nombre,
            'primer_apellido': primer_apellido,
            'segundo_apellido': segundo_apellido,
            'ano_nacimiento': ano_nacimiento
        })
    return beneficiarios

def crear_solicitudes_test(numero_usuarios=50):
    """Crea las solicitudes de prueba"""
    with app.app_context():
        print(f"Generando {numero_usuarios} usuarios de prueba...")
        
        creados = 0
        errores = 0
        
        for i in range(1, numero_usuarios + 1):
            try:
                datos = generar_datos_usuario()
                
                # Crear fecha de nacimiento
                fecha_nacimiento = datetime(datos['ano_nacimiento'], 1, 1).date()
                
                # Crear solicitud
                solicitud = SolicitudSocio(
                    nombre=datos['nombre'],
                    primer_apellido=datos['primer_apellido'],
                    segundo_apellido=datos['segundo_apellido'],
                    movil=datos['movil'],
                    fecha_nacimiento=fecha_nacimiento,
                    miembros_unidad_familiar=datos['miembros'],
                    forma_de_pago=datos['forma_pago'],
                    estado='por_confirmar',
                    password_solicitud=datos['password'],
                    calle=datos['calle'],
                    numero=datos['numero'],
                    piso=datos['piso'],
                    poblacion=datos['poblacion']
                )
                
                db.session.add(solicitud)
                db.session.flush()  # Para obtener el ID
                
                # Crear beneficiarios (número de miembros - 1)
                beneficiarios_count = datos['miembros'] - 1
                if beneficiarios_count > 0:
                    beneficiarios_data = generar_beneficiarios(solicitud.id, beneficiarios_count)
                    for ben_data in beneficiarios_data:
                        beneficiario = BeneficiarioSolicitud(
                            solicitud_id=ben_data['solicitud_id'],
                            nombre=ben_data['nombre'],
                            primer_apellido=ben_data['primer_apellido'],
                            segundo_apellido=ben_data['segundo_apellido'],
                            ano_nacimiento=ben_data['ano_nacimiento']
                        )
                        db.session.add(beneficiario)
                
                # Commit individual para cada solicitud
                db.session.commit()
                creados += 1
                
                if i % 10 == 0:
                    print(f"  Procesados {i}/{numero_usuarios} usuarios... ({creados} creados, {errores} errores)")
                    
            except Exception as e:
                db.session.rollback()
                errores += 1
                print(f"  ✗ Error al crear usuario {i}: {e}")
                continue
        
        print(f"\n✓ Proceso completado:")
        print(f"  - Solicitudes creadas: {creados}")
        print(f"  - Errores: {errores}")
        if creados > 0:
            print(f"  Puedes revisar las solicitudes en el panel de administración.")

if __name__ == '__main__':
    crear_solicitudes_test(50)

