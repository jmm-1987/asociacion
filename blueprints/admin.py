from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, Actividad, Inscripcion, SolicitudSocio, db
from datetime import datetime, timedelta
from functools import wraps
import secrets
import string

admin_bp = Blueprint('admin', __name__)

def directiva_required(f):
    """Decorador para requerir rol de directiva"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_directiva():
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('socios.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@directiva_required
def dashboard():
    # Socios próximos a vencer (30 días)
    limite_vencimiento = datetime.utcnow() + timedelta(days=30)
    socios_por_vencer = User.query.filter(
        User.rol == 'socio',
        User.fecha_validez <= limite_vencimiento,
        User.fecha_validez > datetime.utcnow()
    ).order_by(User.fecha_validez).all()
    
    # Todas las actividades con número de inscritos
    actividades = Actividad.query.order_by(Actividad.fecha.desc()).all()
    
    # Estadísticas
    total_socios = User.query.filter_by(rol='socio').count()
    total_actividades = Actividad.query.count()
    solicitudes_pendientes = SolicitudSocio.query.filter_by(estado='por_confirmar').count()
    
    return render_template('admin/dashboard.html',
                         socios_por_vencer=socios_por_vencer,
                         actividades=actividades,
                         total_socios=total_socios,
                         total_actividades=total_actividades,
                         solicitudes_pendientes=solicitudes_pendientes)

@admin_bp.route('/socios')
@login_required
@directiva_required
def gestion_socios():
    # Obtener parámetro de búsqueda
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Buscar en nombre, email o fecha de validez
        socios = User.query.filter(
            User.rol == 'socio',
            db.or_(
                User.nombre.contains(search_query),
                User.email.contains(search_query),
                db.func.strftime('%d/%m/%Y', User.fecha_validez).contains(search_query)
            )
        ).order_by(User.nombre).all()
    else:
        socios = User.query.filter_by(rol='socio').order_by(User.nombre).all()
    
    return render_template('admin/socios.html', socios=socios, search_query=search_query)

@admin_bp.route('/socios/nuevo', methods=['GET', 'POST'])
@login_required
@directiva_required
def nuevo_socio():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        fecha_validez = request.form.get('fecha_validez')
        password = request.form.get('password')
        
        # Validaciones
        if not all([nombre, email, fecha_validez, password]):
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            flash('Ya existe un usuario con este email.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        try:
            fecha_validez_obj = datetime.strptime(fecha_validez, '%Y-%m-%d')
        except ValueError:
            flash('Fecha de validez inválida.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        # Crear nuevo socio
        nuevo_socio = User(
            nombre=nombre,
            email=email,
            rol='socio',
            fecha_alta=datetime.utcnow(),
            fecha_validez=fecha_validez_obj
        )
        nuevo_socio.set_password(password)
        
        db.session.add(nuevo_socio)
        db.session.commit()
        
        flash(f'Socio {nombre} registrado exitosamente.', 'success')
        return redirect(url_for('admin.gestion_socios'))
    
    return render_template('admin/nuevo_socio.html')

@admin_bp.route('/socios/<int:socio_id>/renovar', methods=['GET', 'POST'])
@login_required
@directiva_required
def renovar_socio(socio_id):
    socio = User.query.get_or_404(socio_id)
    
    if request.method == 'POST':
        nueva_fecha = request.form.get('fecha_validez')
        
        try:
            fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d')
            socio.fecha_validez = fecha_obj
            db.session.commit()
            flash(f'Suscripción de {socio.nombre} renovada exitosamente.', 'success')
            return redirect(url_for('admin.gestion_socios'))
        except ValueError:
            flash('Fecha inválida.', 'error')
    
    return render_template('admin/renovar_socio.html', socio=socio)

@admin_bp.route('/actividades')
@login_required
@directiva_required
def gestion_actividades():
    # Obtener parámetro de búsqueda
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Buscar en nombre, descripción o fecha
        actividades = Actividad.query.filter(
            db.or_(
                Actividad.nombre.contains(search_query),
                Actividad.descripcion.contains(search_query),
                db.func.strftime('%d/%m/%Y', Actividad.fecha).contains(search_query)
            )
        ).order_by(Actividad.fecha.desc()).all()
    else:
        actividades = Actividad.query.order_by(Actividad.fecha.desc()).all()
    
    return render_template('admin/actividades.html', actividades=actividades, ahora=datetime.utcnow(), search_query=search_query)

@admin_bp.route('/actividades/nueva', methods=['GET', 'POST'])
@login_required
@directiva_required
def nueva_actividad():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        fecha = request.form.get('fecha')
        aforo_maximo = request.form.get('aforo_maximo')
        
        # Validaciones
        if not all([nombre, fecha, aforo_maximo]):
            flash('Nombre, fecha y aforo máximo son obligatorios.', 'error')
            return render_template('admin/nueva_actividad.html')
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%dT%H:%M')
            aforo = int(aforo_maximo)
            if aforo <= 0:
                raise ValueError()
        except ValueError:
            flash('Fecha o aforo inválidos.', 'error')
            return render_template('admin/nueva_actividad.html')
        
        # Crear nueva actividad
        nueva_actividad = Actividad(
            nombre=nombre,
            descripcion=descripcion,
            fecha=fecha_obj,
            aforo_maximo=aforo
        )
        
        db.session.add(nueva_actividad)
        db.session.commit()
        
        flash(f'Actividad "{nombre}" creada exitosamente.', 'success')
        return redirect(url_for('admin.gestion_actividades'))
    
    return render_template('admin/nueva_actividad.html')

@admin_bp.route('/actividades/<int:actividad_id>/editar', methods=['GET', 'POST'])
@login_required
@directiva_required
def editar_actividad(actividad_id):
    actividad = Actividad.query.get_or_404(actividad_id)
    
    if request.method == 'POST':
        actividad.nombre = request.form.get('nombre')
        actividad.descripcion = request.form.get('descripcion')
        actividad.aforo_maximo = int(request.form.get('aforo_maximo'))
        
        try:
            fecha_obj = datetime.strptime(request.form.get('fecha'), '%Y-%m-%dT%H:%M')
            actividad.fecha = fecha_obj
        except ValueError:
            flash('Fecha inválida.', 'error')
            return render_template('admin/editar_actividad.html', actividad=actividad)
        
        db.session.commit()
        flash(f'Actividad "{actividad.nombre}" actualizada exitosamente.', 'success')
        return redirect(url_for('admin.gestion_actividades'))
    
    return render_template('admin/editar_actividad.html', actividad=actividad)

@admin_bp.route('/actividades/<int:actividad_id>/eliminar', methods=['POST'])
@login_required
@directiva_required
def eliminar_actividad(actividad_id):
    actividad = Actividad.query.get_or_404(actividad_id)
    nombre_actividad = actividad.nombre
    
    db.session.delete(actividad)
    db.session.commit()
    
    flash(f'Actividad "{nombre_actividad}" eliminada exitosamente.', 'success')
    return redirect(url_for('admin.gestion_actividades'))

@admin_bp.route('/actividades/<int:actividad_id>/inscritos')
@login_required
@directiva_required
def ver_inscritos(actividad_id):
    actividad = Actividad.query.get_or_404(actividad_id)
    inscripciones = Inscripcion.query.filter_by(actividad_id=actividad_id).all()
    
    return render_template('admin/inscritos.html', 
                         actividad=actividad, 
                         inscripciones=inscripciones)

@admin_bp.route('/actividades/<int:actividad_id>/marcar-asistencia/<int:inscripcion_id>', methods=['POST'])
@login_required
@directiva_required
def marcar_asistencia(actividad_id, inscripcion_id):
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    
    # Verificar que la inscripción pertenece a la actividad
    if inscripcion.actividad_id != actividad_id:
        flash('Error: La inscripción no pertenece a esta actividad.', 'error')
        return redirect(url_for('admin.ver_inscritos', actividad_id=actividad_id))
    
    # Cambiar el estado de asistencia
    inscripcion.asiste = not inscripcion.asiste
    db.session.commit()
    
    estado = "asistió" if inscripcion.asiste else "no asistió"
    flash(f'{inscripcion.usuario.nombre} marcado como que {estado}.', 'success')
    
    return redirect(url_for('admin.ver_inscritos', actividad_id=actividad_id))

@admin_bp.route('/solicitudes-socios')
@login_required
@directiva_required
def solicitudes_socios():
    """Vista para ver las solicitudes de nuevos socios"""
    estado_filtro = request.args.get('estado', 'por_confirmar')
    
    if estado_filtro == 'todas':
        solicitudes = SolicitudSocio.query.order_by(SolicitudSocio.fecha_solicitud.desc()).all()
    else:
        solicitudes = SolicitudSocio.query.filter_by(estado=estado_filtro).order_by(SolicitudSocio.fecha_solicitud.desc()).all()
    
    # Contar por estado
    total_por_confirmar = SolicitudSocio.query.filter_by(estado='por_confirmar').count()
    total_activas = SolicitudSocio.query.filter_by(estado='activa').count()
    total_rechazadas = SolicitudSocio.query.filter_by(estado='rechazada').count()
    
    return render_template('admin/solicitudes_socios.html',
                         solicitudes=solicitudes,
                         estado_filtro=estado_filtro,
                         total_por_confirmar=total_por_confirmar,
                         total_activas=total_activas,
                         total_rechazadas=total_rechazadas)

@admin_bp.route('/solicitudes-socios/<int:solicitud_id>/confirmar', methods=['POST'])
@login_required
@directiva_required
def confirmar_solicitud(solicitud_id):
    """Confirmar una solicitud y crear el usuario"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    if solicitud.estado != 'por_confirmar':
        flash('Esta solicitud ya ha sido procesada.', 'error')
        return redirect(url_for('admin.solicitudes_socios'))
    
    # Generar email único
    nombre_completo = f"{solicitud.nombre} {solicitud.primer_apellido}"
    if solicitud.segundo_apellido:
        nombre_completo += f" {solicitud.segundo_apellido}"
    
    # Crear email basado en nombre y apellidos
    base_email = f"{solicitud.nombre.lower()}.{solicitud.primer_apellido.lower()}"
    if solicitud.segundo_apellido:
        base_email += f".{solicitud.segundo_apellido.lower()}"
    email = f"{base_email}@asociacion.com"
    
    # Verificar si el email ya existe y generar uno único
    contador = 1
    email_original = email
    while User.query.filter_by(email=email).first():
        email = f"{base_email}{contador}@asociacion.com"
        contador += 1
    
    # Generar contraseña temporal aleatoria
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    # Crear usuario
    nuevo_socio = User(
        nombre=nombre_completo,
        email=email,
        rol='socio',
        fecha_alta=datetime.utcnow(),
        fecha_validez=datetime.utcnow() + timedelta(days=365)  # 1 año por defecto
    )
    nuevo_socio.set_password(password)
    
    # Actualizar solicitud
    solicitud.estado = 'activa'
    solicitud.fecha_confirmacion = datetime.utcnow()
    
    db.session.add(nuevo_socio)
    db.session.commit()
    
    flash(f'Solicitud confirmada. Usuario creado: {email} con contraseña temporal: {password}', 'success')
    return redirect(url_for('admin.solicitudes_socios'))

@admin_bp.route('/solicitudes-socios/<int:solicitud_id>/rechazar', methods=['POST'])
@login_required
@directiva_required
def rechazar_solicitud(solicitud_id):
    """Rechazar una solicitud"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    if solicitud.estado != 'por_confirmar':
        flash('Esta solicitud ya ha sido procesada.', 'error')
        return redirect(url_for('admin.solicitudes_socios'))
    
    solicitud.estado = 'rechazada'
    db.session.commit()
    
    flash('Solicitud rechazada.', 'info')
    return redirect(url_for('admin.solicitudes_socios'))
