from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Actividad, Inscripcion, db
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
    
    # Actividades en las que está inscrito
    actividades_inscrito = db.session.query(Actividad).join(Inscripcion).filter(
        Inscripcion.user_id == current_user.id
    ).order_by(Actividad.fecha).all()
    
    return render_template('socios/dashboard.html',
                         actividades_disponibles=actividades_disponibles,
                         actividades_inscrito=actividades_inscrito)

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
    
    return render_template('socios/actividades.html', actividades=actividades)

@socios_bp.route('/actividades/<int:actividad_id>/inscribir', methods=['POST'])
@login_required
def inscribir_actividad(actividad_id):
    if not current_user.is_socio():
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    actividad = Actividad.query.get_or_404(actividad_id)
    
    # Verificar si ya está inscrito
    if actividad.usuario_inscrito(current_user.id):
        flash('Ya estás inscrito en esta actividad.', 'warning')
        return redirect(url_for('socios.actividades'))
    
    # Verificar si hay plazas disponibles
    if not actividad.tiene_plazas_disponibles():
        flash('No hay plazas disponibles para esta actividad.', 'error')
        return redirect(url_for('socios.actividades'))
    
    # Verificar si la actividad no ha pasado
    if actividad.fecha <= datetime.utcnow():
        flash('Esta actividad ya ha terminado.', 'error')
        return redirect(url_for('socios.actividades'))
    
    # Crear inscripción
    inscripcion = Inscripcion(
        user_id=current_user.id,
        actividad_id=actividad.id
    )
    
    db.session.add(inscripcion)
    db.session.commit()
    
    flash(f'Te has inscrito exitosamente en "{actividad.nombre}".', 'success')
    return redirect(url_for('socios.dashboard'))

@socios_bp.route('/actividades/<int:actividad_id>/cancelar', methods=['POST'])
@login_required
def cancelar_inscripcion(actividad_id):
    if not current_user.is_socio():
        flash('No tienes permisos para realizar esta acción.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    actividad = Actividad.query.get_or_404(actividad_id)
    
    # Buscar la inscripción
    inscripcion = Inscripcion.query.filter_by(
        user_id=current_user.id,
        actividad_id=actividad_id
    ).first()
    
    if not inscripcion:
        flash('No estás inscrito en esta actividad.', 'error')
        return redirect(url_for('socios.dashboard'))
    
    # Verificar si se puede cancelar (por ejemplo, no muy cerca de la fecha)
    tiempo_limite = datetime.utcnow() + timedelta(hours=24)  # 24 horas antes
    if actividad.fecha <= tiempo_limite:
        flash('No puedes cancelar la inscripción tan cerca de la fecha de la actividad.', 'error')
        return redirect(url_for('socios.dashboard'))
    
    db.session.delete(inscripcion)
    db.session.commit()
    
    flash(f'Has cancelado tu inscripción en "{actividad.nombre}".', 'success')
    return redirect(url_for('socios.dashboard'))

@socios_bp.route('/mis-actividades')
@login_required
def mis_actividades():
    if not current_user.is_socio():
        flash('No tienes permisos para acceder a esta página.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Actividades en las que está inscrito
    actividades_inscrito = db.session.query(Actividad).join(Inscripcion).filter(
        Inscripcion.user_id == current_user.id
    ).order_by(Actividad.fecha).all()
    
    return render_template('socios/mis_actividades.html', 
                         actividades=actividades_inscrito,
                         ahora=datetime.utcnow())
