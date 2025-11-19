from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Actividad, Inscripcion, Beneficiario, db
from datetime import datetime

actividades_bp = Blueprint('actividades', __name__)

@actividades_bp.route('/<int:actividad_id>')
@login_required
def detalle_actividad(actividad_id):
    actividad = Actividad.query.get_or_404(actividad_id)
    
    # Obtener todas las inscripciones del socio para esta actividad
    inscripciones_actividad = []
    beneficiarios = []
    if current_user.is_socio():
        inscripciones_actividad = Inscripcion.query.filter_by(
            user_id=current_user.id,
            actividad_id=actividad_id
        ).all()
        beneficiarios = Beneficiario.query.filter_by(socio_id=current_user.id).order_by(Beneficiario.nombre).all()
    
    return render_template('actividades/detalle.html', 
                         actividad=actividad, 
                         inscripciones_actividad=inscripciones_actividad,
                         beneficiarios=beneficiarios,
                         ahora=datetime.utcnow())
