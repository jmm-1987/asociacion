# 🏘️ Sistema de Gestión - Asociación de Vecinos

Una aplicación web completa desarrollada con **Flask** para la gestión de una Asociación de Vecinos, incluyendo autenticación, gestión de socios y actividades.

## 🚀 Características

### 👥 Gestión de Usuarios
- **Dos tipos de usuarios**: Directiva y Socio
- **Autenticación segura** con Flask-Login
- **Control de acceso** basado en roles
- **Gestión de suscripciones** con fechas de validez

### 📅 Gestión de Actividades
- **Creación y edición** de actividades
- **Sistema de inscripciones** con control de aforo
- **Vista detallada** de cada actividad
- **Listado de inscritos** para la directiva

### 🎯 Panel de Directiva
- **Dashboard** con estadísticas y resúmenes
- **Gestión completa de socios** (alta, renovación)
- **Administración de actividades**
- **Seguimiento de socios próximos a vencer**

### 👤 Panel de Socio
- **Dashboard personal** con información relevante
- **Inscripción en actividades**
- **Gestión de inscripciones propias**
- **Vista del perfil y estado de suscripción**

## 🛠️ Tecnologías Utilizadas

- **Backend**: Flask 2.3.3
- **Base de datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Autenticación**: Flask-Login
- **Frontend**: HTML5, CSS3, Bootstrap 5.3
- **JavaScript**: Vanilla JS con funcionalidades interactivas
- **Templates**: Jinja2
- **Servidor WSGI**: Gunicorn (producción)

## 🚀 Despliegue en Render

La aplicación está preparada para desplegarse en Render. Consulta el archivo [DEPLOY.md](DEPLOY.md) para instrucciones detalladas.

**Resumen rápido:**
1. Crea un servicio Web en Render
2. Crea una base de datos PostgreSQL
3. Configura las variables de entorno (SECRET_KEY, DATABASE_URL)
4. Despliega

## 📦 Instalación Local

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd asociacion
```

### 2. Crear entorno virtual
```bash
python -m venv venv
```

### 3. Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 5. Ejecutar la aplicación
```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## 👤 Usuarios de Prueba

### Directiva
- **Email**: `admin@asociacion.com`
- **Contraseña**: `admin123`

### Socio
- **Email**: `juan@email.com`
- **Contraseña**: `socio123`

## 📁 Estructura del Proyecto

```
asociacion/
├── app.py                 # Aplicación principal
├── models.py             # Modelos de base de datos
├── requirements.txt      # Dependencias
├── README.md            # Este archivo
├── blueprints/          # Módulos de la aplicación
│   ├── __init__.py
│   ├── auth.py          # Autenticación
│   ├── admin.py         # Panel de directiva
│   ├── socios.py        # Panel de socios
│   └── actividades.py   # Gestión de actividades
├── templates/           # Plantillas HTML
│   ├── base.html
│   ├── auth/
│   │   └── login.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── socios.html
│   │   ├── nuevo_socio.html
│   │   ├── renovar_socio.html
│   │   ├── actividades.html
│   │   ├── nueva_actividad.html
│   │   ├── editar_actividad.html
│   │   └── inscritos.html
│   ├── socios/
│   │   ├── dashboard.html
│   │   ├── perfil.html
│   │   ├── actividades.html
│   │   └── mis_actividades.html
│   └── actividades/
│       └── detalle.html
└── static/              # Archivos estáticos
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## 🗄️ Modelos de Base de Datos

### User (Usuario)
- `id`: Identificador único
- `nombre`: Nombre completo
- `email`: Correo electrónico (único)
- `password_hash`: Contraseña hasheada
- `rol`: 'directiva' o 'socio'
- `fecha_alta`: Fecha de registro
- `fecha_validez`: Fecha de vencimiento de suscripción

### Actividad
- `id`: Identificador único
- `nombre`: Nombre de la actividad
- `descripcion`: Descripción detallada
- `fecha`: Fecha y hora de la actividad
- `aforo_maximo`: Número máximo de participantes
- `fecha_creacion`: Fecha de creación

### Inscripcion
- `id`: Identificador único
- `user_id`: ID del usuario inscrito
- `actividad_id`: ID de la actividad
- `fecha_inscripcion`: Fecha de inscripción

## 🔐 Funcionalidades de Seguridad

- **Autenticación obligatoria** para todas las rutas protegidas
- **Control de acceso** basado en roles (directiva/socio)
- **Contraseñas hasheadas** con Werkzeug
- **Protección CSRF** en formularios
- **Validación de datos** en frontend y backend

## 🎨 Interfaz de Usuario

- **Diseño responsivo** con Bootstrap 5
- **Tema moderno** y profesional
- **Navegación intuitiva** según el rol del usuario
- **Mensajes flash** para feedback al usuario
- **Iconos** de Bootstrap Icons
- **Animaciones** y transiciones suaves

## 📱 Responsive Design

La aplicación está optimizada para:
- **Desktop** (1200px+)
- **Tablet** (768px - 1199px)
- **Mobile** (menos de 768px)

## 🚀 Funcionalidades Principales

### Para la Directiva:
- ✅ Dashboard con estadísticas
- ✅ Gestión completa de socios
- ✅ Creación y edición de actividades
- ✅ Visualización de inscripciones
- ✅ Alertas de socios próximos a vencer
- ✅ Renovación de suscripciones

### Para los Socios:
- ✅ Dashboard personal
- ✅ Vista del perfil y estado
- ✅ Inscripción en actividades
- ✅ Gestión de inscripciones propias
- ✅ Cancelación de inscripciones (24h antes)
- ✅ Listado de actividades disponibles

## 🔧 Configuración Avanzada

### Variables de Entorno
La aplicación usa variables de entorno para configuración:

```bash
# Desarrollo local
export SECRET_KEY="tu_clave_secreta_muy_segura"
export DATABASE_URL="sqlite:///asociacion.db"  # Opcional, SQLite por defecto
export FLASK_ENV="development"

# Producción (Render)
SECRET_KEY="clave_generada_aleatoriamente"
DATABASE_URL="postgresql://user:pass@host/db"  # Proporcionado por Render
FLASK_ENV="production"
```

### Base de Datos
- **Desarrollo**: SQLite (por defecto)
- **Producción**: PostgreSQL (configurado automáticamente en Render)

La aplicación detecta automáticamente el tipo de base de datos según la variable `DATABASE_URL`.

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa la documentación
2. Busca en los issues existentes
3. Crea un nuevo issue con detalles del problema

## 🔄 Próximas Mejoras

- [ ] Sistema de notificaciones por email
- [ ] Exportación de datos a Excel/PDF
- [ ] Sistema de pagos online
- [ ] API REST para móviles
- [ ] Dashboard con gráficos avanzados
- [ ] Sistema de backup automático
- [ ] Multiidioma
- [ ] Temas personalizables

---

**Desarrollado con ❤️ para la gestión eficiente de Asociaciones de Vecinos**

