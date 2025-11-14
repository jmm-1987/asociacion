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
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (o el plan que prefieras)

### 3. Crear Base de Datos PostgreSQL

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
- **DATABASE_URL**: Usa la **Internal Database URL** de la base de datos PostgreSQL creada
- **FLASK_ENV**: `production` (opcional)

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

- La aplicación usa PostgreSQL en producción y SQLite en desarrollo local
- El archivo `render.yaml` puede usarse para desplegar automáticamente, pero también puedes hacerlo manualmente
- Asegúrate de que el `SECRET_KEY` sea único y seguro en producción
- La base de datos se inicializa automáticamente con las tablas necesarias

## Solución de Problemas

### Error de conexión a la base de datos
- Verifica que `DATABASE_URL` esté correctamente configurada
- Asegúrate de usar la **Internal Database URL** (no la External) si la base de datos está en el mismo servicio de Render

### Error al iniciar
- Revisa los logs en Render Dashboard
- Verifica que todas las dependencias estén en `requirements.txt`
- Asegúrate de que el comando de inicio sea correcto: `gunicorn app:app`

