# Guía de Despliegue en Render

## Pasos para desplegar la aplicación

### 1. Preparar el repositorio
- Asegúrate de que todos los cambios estén commiteados
- Sube el código a GitHub, GitLab o Bitbucket

### 2. Crear servicio Web en Render

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Click en "New +" → "Web Service"
3. Conecta tu repositorio
4. Configura el servicio:
   - **Name**: asociacion-vecinos (o el nombre que prefieras)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
   - **Plan**: Free (o el plan que prefieras)

### 3. Configurar Base de Datos SQLite con Disco Persistente

**Opción A: SQLite con Disco Persistente (Recomendado para esta aplicación)**

1. En Render Dashboard, ve a tu servicio web
2. En la sección "Disks", click en "Add Disk"
3. Configura el disco persistente:
   - **Mount Path**: `/mnt/disk`
   - **Size**: Elige el tamaño que necesites (mínimo 1GB recomendado)
4. La aplicación detectará automáticamente el disco y usará SQLite en `/mnt/disk/asociacion.db`

**Opción B: PostgreSQL (Alternativa)**

Si prefieres usar PostgreSQL:
1. En Render Dashboard, click en "New +" → "PostgreSQL"
2. Configura la base de datos:
   - **Name**: asociacion-db
   - **Database**: asociacion
   - **User**: asociacion_user
   - **Plan**: Free (o el plan que prefieras)
3. Anota la **Internal Database URL** y **External Database URL**

### 4. Configurar Variables de Entorno

En la configuración del servicio web, añade estas variables de entorno:

- **SECRET_KEY**: Genera una clave secreta segura (puedes usar: `python -c "import secrets; print(secrets.token_hex(32))"`)
- **FLASK_ENV**: `production` (opcional)

**Para SQLite con disco persistente (Opción A):**
- **NO** configures `DATABASE_URL` (o déjala vacía)
- La aplicación usará automáticamente `/mnt/disk/asociacion.db`

**Para PostgreSQL (Opción B):**
- **DATABASE_URL**: Usa la **Internal Database URL** de la base de datos PostgreSQL creada

### 5. Desplegar

1. Click en "Create Web Service"
2. Render comenzará a construir y desplegar tu aplicación
3. Una vez completado, tu aplicación estará disponible en la URL proporcionada

### 6. Inicializar la Base de Datos

La aplicación creará automáticamente las tablas al iniciar. Los usuarios de prueba se crearán automáticamente si no existen.

**Credenciales por defecto:**
- **Directiva**: admin@asociacion.com / admin123
- **Socio**: juan@email.com / socio123

⚠️ **IMPORTANTE**: Cambia estas contraseñas después del primer inicio de sesión en producción.

## Notas Importantes

- La aplicación detecta automáticamente el tipo de base de datos:
  - Si hay `DATABASE_URL` con PostgreSQL, usa PostgreSQL
  - Si hay disco persistente montado en `/mnt/disk`, usa SQLite en esa ubicación
  - Si no hay ninguna de las anteriores, usa SQLite local en `instance/`
- El archivo `render.yaml` puede usarse para desplegar automáticamente, pero también puedes hacerlo manualmente
- Asegúrate de que el `SECRET_KEY` sea único y seguro en producción
- La base de datos se inicializa automáticamente con las tablas necesarias
- **SQLite con disco persistente**: Los datos se guardan en `/mnt/disk/asociacion.db` y persisten entre despliegues

## Solución de Problemas

### Error de conexión a la base de datos
- **Para SQLite**: Verifica que el disco persistente esté montado en `/mnt/disk`
- **Para PostgreSQL**: Verifica que `DATABASE_URL` esté correctamente configurada
- Asegúrate de usar la **Internal Database URL** (no la External) si la base de datos está en el mismo servicio de Render
- Verifica los logs para ver qué ruta de base de datos está usando la aplicación

### Error al iniciar
- Revisa los logs en Render Dashboard
- Verifica que todas las dependencias estén en `requirements.txt`
- Asegúrate de que el comando de inicio sea correcto: `gunicorn app:app`

