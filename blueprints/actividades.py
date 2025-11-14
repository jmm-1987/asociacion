from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Actividad, Inscripcion, db
from datetime import datetime

actividades_bp = Blueprint('actividades', __name__)

@actividades_bp.route('/<int:actividad_id>')
@login_required
def detalle_actividad(actividad_id):
    actividad = Actividad.query.get_or_404(actividad_id)
    
    # Verificar si el usuario está inscrito
    inscrito = False
    if current_user.is_socio():
        inscrito = actividad.usuario_inscrito(current_user.id)
    
    return render_template('actividades/detalle.html', 
                         actividad=actividad, 
                         inscrito=inscrito,
                         ahora=datetime.utcnow())
