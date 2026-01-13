from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Actividad, Inscripcion, Beneficiario, db
from datetime import datetime, timedelta

socios_bp = Blueprint('socios', __name__)

@socios_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_socio():
        flash('No tienes permisos para acceder a esta página.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Todas las actividades disponibles
    actividades_disponibles = Actividad.query.filter(
        Actividad.fecha > datetime.utcnow()
    ).order_by(Actividad.fecha).all()
    
    # Obtener todas las inscripciones del socio (suyas y de sus beneficiarios)
    inscripciones = Inscripcion.query.filter_by(user_id=current_user.id).all()
    
    # Obtener actividades únicas de las inscripciones
    actividades_ids = {insc.actividad_id for insc in inscripciones}
    actividades_inscrito = Actividad.query.filter(Actividad.id.in_(actividades_ids)).order_by(Actividad.fecha).all()
    
    # Crear un diccionario de inscripciones por actividad
    inscripciones_por_actividad = {}
    for insc in inscripciones:
        if insc.actividad_id not in inscripciones_por_actividad:
            inscripciones_por_actividad[insc.actividad_id] = []
        inscripciones_por_actividad[insc.actividad_id].append(insc)
    
    # Cargar beneficiarios del socio
    beneficiarios = Beneficiario.query.filter_by(socio_id=current_user.id).order_by(Beneficiario.nombre).all()
    
    return render_template('socios/dashboard.html',
                         actividades_disponibles=actividades_disponibles,
                         actividades_inscrito=actividades_inscrito,
                         inscripciones_por_actividad=inscripciones_por_actividad,
                         beneficiarios=beneficiarios)

@socios_bp.route('/perfil')
@login_required
def perfil():
    if not current_user.is_socio():
        flash('No tienes permisos para acceder a esta página.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('socios/perfil.html', usuario=current_user)

@socios_bp.route('/actividades')
@login_required
def actividades():
    if not current_user.is_socio():
        flash('No tienes permisos para acceder a esta página.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Todas las actividades disponibles
    actividades = Actividad.query.filter(
        Actividad.fecha > datetime.utcnow()
    ).order_by(Actividad.fecha).all()
    
    # Cargar beneficiarios del socio
    beneficiarios = Beneficiario.query.filter_by(socio_id=current_user.id).order_by(Beneficiario.nombre).all()
    
    return render_template('socios/actividades.html', actividades=actividades, beneficiarios=beneficiarios)

@socios_bp.route('/actividades/<int:actividad_id>/inscribir', methods=['POST'])
@login_required
def inscribir_actividad(actividad_id):
    if not current_user.is_socio():
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    actividad = Actividad.query.get_or_404(actividad_id)
    beneficiario_id = request.form.get('beneficiario_id', '').strip()
    
    # Determinar si es inscripción del socio o de un beneficiario
    es_beneficiario = beneficiario_id and beneficiario_id != 'socio'
    beneficiario = None
    ano_nacimiento = None
    nombre_inscrito = current_user.nombre
    
    if es_beneficiario:
        try:
            beneficiario_id_int = int(beneficiario_id)
            # Verificar que el beneficiario pertenece al socio
            beneficiario = Beneficiario.query.filter_by(id=beneficiario_id_int, socio_id=current_user.id).first()
            if not beneficiario:
                flash('El beneficiario no pertenece a tu cuenta.', 'error')
                return redirect(url_for('socios.actividades'))
            
            # Verificar si el beneficiario ya está inscrito
            if actividad.beneficiario_inscrito(beneficiario_id_int):
                flash(f'{beneficiario.nombre} ya está inscrito en esta actividad.', 'warning')
                return redirect(url_for('socios.actividades'))
            
            ano_nacimiento = beneficiario.ano_nacimiento
            nombre_inscrito = f"{beneficiario.nombre} {beneficiario.primer_apellido}"
        except ValueError:
            flash('ID de beneficiario inválido.', 'error')
            return redirect(url_for('socios.actividades'))
    else:
        # Verificar si el socio ya está inscrito
        if actividad.usuario_inscrito(current_user.id):
            flash('Ya estás inscrito en esta actividad.', 'warning')
            return redirect(url_for('socios.actividades'))
        
        ano_nacimiento = current_user.ano_nacimiento
    
    # Verificar si hay plazas disponibles
    if not actividad.tiene_plazas_disponibles():
        flash('No hay plazas disponibles para esta actividad.', 'error')
        return redirect(url_for('socios.actividades'))
    
    # Verificar si la actividad no ha pasado
    if actividad.fecha <= datetime.utcnow():
        flash('Esta actividad ya ha terminado.', 'error')
        return redirect(url_for('socios.actividades'))
    
    # Verificar restricción de edad
    if actividad.tiene_restriccion_edad():
        puede_inscribirse, mensaje_error = actividad.puede_inscribirse_por_edad(ano_nacimiento)
        if not puede_inscribirse:
            flash(f'No se puede inscribir en esta actividad: {mensaje_error}', 'error')
            return redirect(url_for('socios.actividades'))
    
    # Crear inscripción
    inscripcion = Inscripcion(
        user_id=current_user.id,
        actividad_id=actividad.id,
        beneficiario_id=beneficiario.id if es_beneficiario else None
    )
    
    try:
        db.session.add(inscripcion)
        db.session.commit()
        
        if es_beneficiario:
            flash(f'{nombre_inscrito} se ha inscrito exitosamente en "{actividad.nombre}".', 'success')
        else:
            flash(f'Te has inscrito exitosamente en "{actividad.nombre}".', 'success')
        
        return redirect(url_for('socios.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al inscribirse en la actividad: {str(e)}. Por favor, inténtalo de nuevo.', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('socios.actividades'))

@socios_bp.route('/actividades/<int:actividad_id>/cancelar', methods=['POST'])
@login_required
def cancelar_inscripcion(actividad_id):
    if not current_user.is_socio():
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    actividad = Actividad.query.get_or_404(actividad_id)
    beneficiario_id = request.form.get('beneficiario_id', '').strip()
    
    # Buscar la inscripción (socio o beneficiario)
    inscripcion = None
    nombre_cancelar = "tu inscripción"
    
    if beneficiario_id and beneficiario_id != 'socio':
        # Es una inscripción de beneficiario
        try:
            beneficiario_id_int = int(beneficiario_id)
            # Verificar que el beneficiario pertenece al socio
            beneficiario = Beneficiario.query.filter_by(id=beneficiario_id_int, socio_id=current_user.id).first()
            if not beneficiario:
                flash('El beneficiario no pertenece a tu cuenta.', 'error')
                return redirect(url_for('socios.dashboard'))
            
            inscripcion = Inscripcion.query.filter_by(
                user_id=current_user.id,
                actividad_id=actividad_id,
                beneficiario_id=beneficiario_id_int
            ).first()
            
            if inscripcion:
                nombre_cancelar = f"{beneficiario.nombre} {beneficiario.primer_apellido}"
        except (ValueError, TypeError):
            flash('ID de beneficiario inválido.', 'error')
            return redirect(url_for('socios.dashboard'))
    else:
        # Es una inscripción del socio (beneficiario_id es None o 'socio')
        inscripcion = Inscripcion.query.filter_by(
            user_id=current_user.id,
            actividad_id=actividad_id,
            beneficiario_id=None
        ).first()
    
    if not inscripcion:
        if beneficiario_id and beneficiario_id != 'socio':
            flash('El beneficiario no está inscrito en esta actividad.', 'error')
        else:
            flash('No estás inscrito en esta actividad.', 'error')
        return redirect(url_for('socios.dashboard'))
    
    # Permitir cancelar en cualquier momento (sin restricción de tiempo)
    try:
        db.session.delete(inscripcion)
        db.session.commit()
        
        if beneficiario_id and beneficiario_id != 'socio':
            flash(f'Has cancelado la inscripción de {nombre_cancelar} en "{actividad.nombre}".', 'success')
        else:
            flash(f'Has cancelado tu inscripción en "{actividad.nombre}".', 'success')
        
        return redirect(url_for('socios.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cancelar la inscripción: {str(e)}. Por favor, inténtalo de nuevo.', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('socios.dashboard'))

@socios_bp.route('/mis-actividades')
@login_required
def mis_actividades():
    if not current_user.is_socio():
        flash('No tienes permisos para acceder a esta página.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Obtener todas las inscripciones del socio (suyas y de sus beneficiarios)
    inscripciones = Inscripcion.query.filter_by(user_id=current_user.id).all()
    
    # Obtener actividades únicas de las inscripciones
    actividades_ids = {insc.actividad_id for insc in inscripciones}
    actividades_inscrito = Actividad.query.filter(Actividad.id.in_(actividades_ids)).order_by(Actividad.fecha).all()
    
    # Crear un diccionario de inscripciones por actividad
    inscripciones_por_actividad = {}
    for insc in inscripciones:
        if insc.actividad_id not in inscripciones_por_actividad:
            inscripciones_por_actividad[insc.actividad_id] = []
        inscripciones_por_actividad[insc.actividad_id].append(insc)
    
    return render_template('socios/mis_actividades.html', 
                         actividades=actividades_inscrito,
                         inscripciones_por_actividad=inscripciones_por_actividad,
                         ahora=datetime.utcnow())
