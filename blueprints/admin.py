from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from models import User, Actividad, Inscripcion, SolicitudSocio, BeneficiarioSolicitud, Beneficiario, db
from datetime import datetime, timedelta
from functools import wraps
import secrets
import string
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
    
    # Cargar beneficiarios para cada socio
    for socio in socios:
        socio.beneficiarios_lista = Beneficiario.query.filter_by(socio_id=socio.id).order_by(Beneficiario.nombre).all()
    
    return render_template('admin/socios.html', socios=socios, search_query=search_query)

@admin_bp.route('/socios/nuevo', methods=['GET', 'POST'])
@login_required
@directiva_required
def nuevo_socio():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')
        ano_nacimiento = request.form.get('ano_nacimiento', '').strip()
        
        # Validaciones
        if not all([nombre, email, password]):
            flash('Todos los campos obligatorios deben estar completos.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            flash('Ya existe un usuario con este email.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        try:
            # Validar año de nacimiento si se proporciona
            ano_nac = None
            if ano_nacimiento:
                ano_nac = int(ano_nacimiento)
                año_actual = datetime.now().year
                if ano_nac < 1900 or ano_nac > año_actual:
                    flash('El año de nacimiento debe estar entre 1900 y el año actual.', 'error')
                    return render_template('admin/nuevo_socio.html')
        except ValueError:
            flash('Año de nacimiento inválido.', 'error')
            return render_template('admin/nuevo_socio.html')
        
        # Fecha de validez siempre al 31/12 del año en curso
        año_actual = datetime.now().year
        fecha_validez = datetime(año_actual, 12, 31, 23, 59, 59)
        
        # Crear nuevo socio
        nuevo_socio = User(
            nombre=nombre,
            email=email,
            rol='socio',
            fecha_alta=datetime.utcnow(),
            fecha_validez=fecha_validez,
            ano_nacimiento=ano_nac
        )
        nuevo_socio.set_password(password)
        
        db.session.add(nuevo_socio)
        db.session.commit()
        
        flash(f'Socio {nombre} registrado exitosamente con validez hasta el 31/12/{año_actual}.', 'success')
        return redirect(url_for('admin.gestion_socios'))
    
    from datetime import datetime as dt
    return render_template('admin/nuevo_socio.html', datetime=dt)

@admin_bp.route('/socios/<int:socio_id>/renovar', methods=['GET', 'POST'])
@login_required
@directiva_required
def renovar_socio(socio_id):
    socio = User.query.get_or_404(socio_id)
    
    if request.method == 'POST':
        # Fecha de validez siempre al 31/12 del año en curso
        año_actual = datetime.now().year
        socio.fecha_validez = datetime(año_actual, 12, 31, 23, 59, 59)
        db.session.commit()
        flash(f'Suscripción de {socio.nombre} renovada exitosamente hasta el 31/12/{año_actual}.', 'success')
        return redirect(url_for('admin.gestion_socios'))
    
    from datetime import datetime as dt
    return render_template('admin/renovar_socio.html', socio=socio, datetime=dt)

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
        edad_minima = request.form.get('edad_minima', '').strip()
        edad_maxima = request.form.get('edad_maxima', '').strip()
        
        # Validaciones
        if not all([nombre, fecha, aforo_maximo]):
            flash('Nombre, fecha y aforo máximo son obligatorios.', 'error')
            return render_template('admin/nueva_actividad.html')
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%dT%H:%M')
            aforo = int(aforo_maximo)
            if aforo <= 0:
                raise ValueError()
            
            # Procesar edades (pueden estar vacías)
            edad_min = int(edad_minima) if edad_minima else None
            edad_max = int(edad_maxima) if edad_maxima else None
            
            # Validar que la edad mínima no sea mayor que la máxima
            if edad_min is not None and edad_max is not None and edad_min > edad_max:
                flash('La edad mínima no puede ser mayor que la edad máxima.', 'error')
                return render_template('admin/nueva_actividad.html')
            
            # Validar rangos de edad
            if edad_min is not None and (edad_min < 0 or edad_min > 120):
                flash('La edad mínima debe estar entre 0 y 120 años.', 'error')
                return render_template('admin/nueva_actividad.html')
            
            if edad_max is not None and (edad_max < 0 or edad_max > 120):
                flash('La edad máxima debe estar entre 0 y 120 años.', 'error')
                return render_template('admin/nueva_actividad.html')
                
        except ValueError:
            flash('Fecha, aforo o edades inválidos.', 'error')
            return render_template('admin/nueva_actividad.html')
        
        # Crear nueva actividad
        nueva_actividad = Actividad(
            nombre=nombre,
            descripcion=descripcion,
            fecha=fecha_obj,
            aforo_maximo=aforo,
            edad_minima=edad_min,
            edad_maxima=edad_max
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
        edad_minima = request.form.get('edad_minima', '').strip()
        edad_maxima = request.form.get('edad_maxima', '').strip()
        
        try:
            fecha_obj = datetime.strptime(request.form.get('fecha'), '%Y-%m-%dT%H:%M')
            actividad.fecha = fecha_obj
            
            # Procesar edades (pueden estar vacías)
            edad_min = int(edad_minima) if edad_minima else None
            edad_max = int(edad_maxima) if edad_maxima else None
            
            # Validar que la edad mínima no sea mayor que la máxima
            if edad_min is not None and edad_max is not None and edad_min > edad_max:
                flash('La edad mínima no puede ser mayor que la edad máxima.', 'error')
                return render_template('admin/editar_actividad.html', actividad=actividad)
            
            # Validar rangos de edad
            if edad_min is not None and (edad_min < 0 or edad_min > 120):
                flash('La edad mínima debe estar entre 0 y 120 años.', 'error')
                return render_template('admin/editar_actividad.html', actividad=actividad)
            
            if edad_max is not None and (edad_max < 0 or edad_max > 120):
                flash('La edad máxima debe estar entre 0 y 120 años.', 'error')
                return render_template('admin/editar_actividad.html', actividad=actividad)
            
            actividad.edad_minima = edad_min
            actividad.edad_maxima = edad_max
            
        except ValueError:
            flash('Fecha o edades inválidos.', 'error')
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

@admin_bp.route('/actividades/pdf')
@login_required
@directiva_required
def actividades_pdf():
    """Genera un PDF con el listado de todas las actividades"""
    actividades = Actividad.query.order_by(Actividad.fecha.desc()).all()
    ahora = datetime.utcnow()
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#333333'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        normal_style = styles['Normal']
        heading_style = styles['Heading2']
        
        story = []
        
        # Título
        story.append(Paragraph("Listado de Actividades", title_style))
        story.append(Paragraph(f"Generado el {ahora.strftime('%d/%m/%Y a las %H:%M')}", 
                              ParagraphStyle('Fecha', parent=normal_style, 
                                           fontSize=10, textColor=colors.grey, 
                                           alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5*cm))
        
        # Información
        story.append(Paragraph(f"<b>Total de actividades:</b> {len(actividades)}", normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Tabla de actividades
        if actividades:
            data = [['Actividad', 'Fecha', 'Inscritos', 'Estado']]
            
            for actividad in actividades:
                estado = "Próxima" if actividad.fecha > ahora else "Pasada"
                fecha_str = f"{actividad.fecha.strftime('%d/%m/%Y')}<br/>{actividad.fecha.strftime('%H:%M')}"
                inscritos_str = f"{actividad.numero_inscritos()}/{actividad.aforo_maximo}"
                
                descripcion = actividad.descripcion[:50] + "..." if actividad.descripcion and len(actividad.descripcion) > 50 else (actividad.descripcion or "")
                nombre_completo = f"<b>{actividad.nombre}</b>"
                if descripcion:
                    nombre_completo += f"<br/><i>{descripcion}</i>"
                
                data.append([
                    Paragraph(nombre_completo, normal_style),
                    Paragraph(fecha_str, normal_style),
                    Paragraph(inscritos_str, normal_style),
                    Paragraph(estado, normal_style)
                ])
            
            table = Table(data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No hay actividades registradas.", normal_style))
        
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        
    except Exception as e:
        flash(f'No se pudo generar el PDF de actividades: {str(e)}', 'error')
        return redirect(url_for('admin.gestion_actividades'))
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=listado_actividades_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

@admin_bp.route('/actividades/<int:actividad_id>/inscritos/pdf')
@login_required
@directiva_required
def inscritos_pdf(actividad_id):
    """Genera un PDF con el listado de inscritos en una actividad"""
    actividad = Actividad.query.get_or_404(actividad_id)
    inscripciones = Inscripcion.query.filter_by(actividad_id=actividad_id).order_by(Inscripcion.fecha_inscripcion).all()
    ahora = datetime.utcnow()
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#333333'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        normal_style = styles['Normal']
        heading_style = styles['Heading2']
        
        story = []
        
        # Título
        story.append(Paragraph("Listado de Inscritos", title_style))
        story.append(Paragraph(f"Generado el {ahora.strftime('%d/%m/%Y a las %H:%M')}", 
                              ParagraphStyle('Fecha', parent=normal_style, 
                                           fontSize=10, textColor=colors.grey, 
                                           alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5*cm))
        
        # Información de la actividad
        story.append(Paragraph(f"<b>{actividad.nombre}</b>", heading_style))
        if actividad.descripcion:
            story.append(Paragraph(f"<i>{actividad.descripcion}</i>", normal_style))
        story.append(Paragraph(f"<b>Fecha:</b> {actividad.fecha.strftime('%d/%m/%Y a las %H:%M')}", normal_style))
        story.append(Paragraph(f"<b>Aforo máximo:</b> {actividad.aforo_maximo} personas", normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Estadísticas
        asistentes = sum(1 for i in inscripciones if i.asiste)
        no_asistentes = len(inscripciones) - asistentes
        plazas_libres = actividad.plazas_disponibles()
        
        stats_data = [
            ['Total Inscritos', 'Asistieron', 'No Asistieron', 'Plazas Libres'],
            [str(len(inscripciones)), str(asistentes), str(no_asistentes), str(plazas_libres)]
        ]
        stats_table = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Tabla de inscritos
        if inscripciones:
            data = [['#', 'Nombre', 'Email', 'Fecha de Inscripción', 'Asistencia']]
            
            for idx, inscripcion in enumerate(inscripciones, 1):
                asistencia = "Asistió" if inscripcion.asiste else "No asistió"
                if inscripcion.beneficiario:
                    nombre_completo = f"{inscripcion.beneficiario.nombre} {inscripcion.beneficiario.primer_apellido}"
                    email_mostrar = f"Beneficiario de {inscripcion.usuario.nombre}"
                else:
                    nombre_completo = inscripcion.usuario.nombre
                    email_mostrar = inscripcion.usuario.email
                
                data.append([
                    str(idx),
                    nombre_completo,
                    email_mostrar,
                    inscripcion.fecha_inscripcion.strftime('%d/%m/%Y %H:%M'),
                    asistencia
                ])
            
            table = Table(data, colWidths=[1*cm, 5*cm, 5*cm, 4*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Columna #
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No hay inscripciones para esta actividad.", normal_style))
        
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        
    except Exception as e:
        flash(f'No se pudo generar el PDF de inscritos: {str(e)}', 'error')
        return redirect(url_for('admin.ver_inscritos', actividad_id=actividad_id))
    
    response = make_response(pdf_bytes)
    nombre_archivo = f"inscritos_{actividad.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={nombre_archivo}'
    
    return response

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
    if inscripcion.beneficiario:
        nombre_mostrar = f"{inscripcion.beneficiario.nombre} {inscripcion.beneficiario.primer_apellido}"
    else:
        nombre_mostrar = inscripcion.usuario.nombre
    
    flash(f'{nombre_mostrar} marcado como que {estado}.', 'success')
    
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

@admin_bp.route('/solicitudes-socios/<int:solicitud_id>')
@login_required
@directiva_required
def ver_solicitud(solicitud_id):
    """Vista para ver el detalle de una solicitud"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    beneficiarios = BeneficiarioSolicitud.query.filter_by(solicitud_id=solicitud_id).order_by(BeneficiarioSolicitud.id).all()
    
    return render_template('admin/ver_solicitud.html',
                         solicitud=solicitud,
                         beneficiarios=beneficiarios)

@admin_bp.route('/solicitudes-socios/<int:solicitud_id>/editar', methods=['GET', 'POST'])
@login_required
@directiva_required
def editar_solicitud(solicitud_id):
    """Vista para editar una solicitud"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    # Solo se puede editar si está por confirmar
    if solicitud.estado != 'por_confirmar':
        flash('Solo se pueden editar solicitudes pendientes de confirmación.', 'error')
        return redirect(url_for('admin.ver_solicitud', solicitud_id=solicitud_id))
    
    beneficiarios = BeneficiarioSolicitud.query.filter_by(solicitud_id=solicitud_id).order_by(BeneficiarioSolicitud.id).all()
    
    if request.method == 'POST':
        # Actualizar datos del socio
        solicitud.nombre = request.form.get('nombre', '').strip().upper()
        solicitud.primer_apellido = request.form.get('primer_apellido', '').strip().upper()
        solicitud.segundo_apellido = request.form.get('segundo_apellido', '').strip().upper() or None
        solicitud.movil = request.form.get('movil', '').strip()
        solicitud.miembros_unidad_familiar = int(request.form.get('miembros_unidad_familiar', 1))
        solicitud.forma_de_pago = request.form.get('forma_de_pago', '').strip()
        
        # Validar móvil
        if not re.match(r'^\d{9}$', solicitud.movil):
            flash('El número de móvil debe tener 9 dígitos.', 'error')
            return render_template('admin/editar_solicitud.html', solicitud=solicitud, beneficiarios=beneficiarios)
        
        # Actualizar o crear beneficiarios
        nuevos_beneficiarios_count = solicitud.miembros_unidad_familiar - 1
        
        # Eliminar beneficiarios existentes
        for beneficiario in beneficiarios:
            db.session.delete(beneficiario)
        
        # Crear nuevos beneficiarios
        if nuevos_beneficiarios_count > 0:
            for i in range(1, nuevos_beneficiarios_count + 1):
                beneficiario_nombre = request.form.get(f'beneficiario_nombre_{i}', '').strip().upper()
                beneficiario_primer_apellido = request.form.get(f'beneficiario_primer_apellido_{i}', '').strip().upper()
                beneficiario_segundo_apellido = request.form.get(f'beneficiario_segundo_apellido_{i}', '').strip().upper() or None
                beneficiario_ano = request.form.get(f'beneficiario_ano_{i}', '').strip()
                
                if beneficiario_nombre and beneficiario_primer_apellido and beneficiario_ano:
                    try:
                        ano_nacimiento = int(beneficiario_ano)
                        año_actual = datetime.now().year
                        if ano_nacimiento < 1900 or ano_nacimiento > año_actual:
                            flash(f'El año de nacimiento del beneficiario {i} no es válido.', 'error')
                            db.session.rollback()
                            return render_template('admin/editar_solicitud.html', solicitud=solicitud, beneficiarios=beneficiarios)
                        
                        nuevo_beneficiario = BeneficiarioSolicitud(
                            solicitud_id=solicitud.id,
                            nombre=beneficiario_nombre,
                            primer_apellido=beneficiario_primer_apellido,
                            segundo_apellido=beneficiario_segundo_apellido,
                            ano_nacimiento=ano_nacimiento
                        )
                        db.session.add(nuevo_beneficiario)
                    except ValueError:
                        flash(f'El año de nacimiento del beneficiario {i} debe ser un número válido.', 'error')
                        db.session.rollback()
                        return render_template('admin/editar_solicitud.html', solicitud=solicitud, beneficiarios=beneficiarios)
        
        db.session.commit()
        flash('Solicitud actualizada correctamente.', 'success')
        return redirect(url_for('admin.ver_solicitud', solicitud_id=solicitud_id))
    
    from datetime import datetime as dt
    return render_template('admin/editar_solicitud.html', solicitud=solicitud, beneficiarios=beneficiarios, datetime=dt)

@admin_bp.route('/solicitudes-socios/<int:solicitud_id>/confirmar', methods=['POST'])
@login_required
@directiva_required
def confirmar_solicitud(solicitud_id):
    """Confirmar una solicitud y crear el usuario"""
    solicitud = SolicitudSocio.query.get_or_404(solicitud_id)
    
    if solicitud.estado != 'por_confirmar':
        flash('Esta solicitud ya ha sido procesada.', 'error')
        return redirect(url_for('admin.solicitudes_socios'))
    
    # Generar número de socio (0001, 0002, etc.)
    ultimo_socio = User.query.filter(User.numero_socio.isnot(None)).order_by(User.numero_socio.desc()).first()
    if ultimo_socio and ultimo_socio.numero_socio:
        try:
            ultimo_numero = int(ultimo_socio.numero_socio)
            nuevo_numero = ultimo_numero + 1
        except ValueError:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    numero_socio = f"{nuevo_numero:04d}"  # Formato 0001, 0002, etc.
    
    # Generar nombre completo
    nombre_completo = f"{solicitud.nombre} {solicitud.primer_apellido}"
    if solicitud.segundo_apellido:
        nombre_completo += f" {solicitud.segundo_apellido}"
    
    # Generar nombre de usuario: nombrenumero_de_socio (sin apellidos, sin guión bajo)
    # Limpiar y normalizar nombre
    nombre_limpio = solicitud.nombre.lower().replace(' ', '').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    nombre_usuario = f"{nombre_limpio}{numero_socio}"
    
    # Verificar si el nombre de usuario ya existe y generar uno único
    contador = 1
    nombre_usuario_original = nombre_usuario
    while User.query.filter_by(email=nombre_usuario).first():
        nombre_usuario = f"{nombre_limpio}{numero_socio}{contador}"
        contador += 1
    
    # Usar la contraseña de la solicitud
    password = solicitud.password_solicitud
    if not password:
        # Si no hay contraseña en la solicitud, generar una temporal
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    # Crear usuario
    # Fecha de validez siempre al 31/12 del año en curso
    año_actual = datetime.now().year
    fecha_validez = datetime(año_actual, 12, 31, 23, 59, 59)
    
    # Calcular año de nacimiento desde fecha_nacimiento
    ano_nacimiento = None
    if solicitud.fecha_nacimiento:
        ano_nacimiento = solicitud.fecha_nacimiento.year
    
    nuevo_socio = User(
        nombre=nombre_completo,
        email=nombre_usuario,  # Usar nombre de usuario como email
        rol='socio',
        fecha_alta=datetime.utcnow(),
        fecha_validez=fecha_validez,
        numero_socio=numero_socio,
        fecha_nacimiento=solicitud.fecha_nacimiento,
        ano_nacimiento=ano_nacimiento,
        password_plain=password  # Guardar contraseña en texto plano para mostrar a admin
    )
    nuevo_socio.set_password(password)
    
    # Actualizar solicitud
    solicitud.estado = 'activa'
    solicitud.fecha_confirmacion = datetime.utcnow()
    
    db.session.add(nuevo_socio)
    db.session.flush()  # Para obtener el ID del nuevo socio
    
    # Crear beneficiarios asociados al socio con números
    beneficiarios_solicitud = BeneficiarioSolicitud.query.filter_by(solicitud_id=solicitud.id).all()
    for index, beneficiario_solicitud in enumerate(beneficiarios_solicitud, start=1):
        numero_beneficiario = f"{numero_socio}-{index}"  # Formato 0001-1, 0001-2, etc.
        beneficiario = Beneficiario(
            socio_id=nuevo_socio.id,
            nombre=beneficiario_solicitud.nombre,
            primer_apellido=beneficiario_solicitud.primer_apellido,
            segundo_apellido=beneficiario_solicitud.segundo_apellido,
            ano_nacimiento=beneficiario_solicitud.ano_nacimiento,
            fecha_validez=fecha_validez,  # Misma fecha de vigencia que el socio
            numero_beneficiario=numero_beneficiario
        )
        db.session.add(beneficiario)
    
    db.session.commit()
    
    beneficiarios_count = len(beneficiarios_solicitud)
    mensaje = f'Solicitud confirmada. Usuario creado: {nombre_usuario} (Número de socio: {numero_socio}) con contraseña: {password}'
    if beneficiarios_count > 0:
        mensaje += f'. Se crearon {beneficiarios_count} beneficiario(s).'
    
    flash(mensaje, 'success')
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
