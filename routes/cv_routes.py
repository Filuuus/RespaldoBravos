from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models import Usuario, Documento
from extensions import db
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')

@cv_bp.route('/', methods=['GET', 'POST'])
def generate_cv():
    user_id = session.get('user_id')
    if not user_id:
        flash("Debes iniciar sesión para generar tu currículum.")
        return redirect(url_for('auth.login'))
    user = Usuario.query.filter_by(id_usuario=user_id).first()
    # Solo documentos con todos los campos llenos
    documentos = Documento.query.filter_by(id_usuario=user_id).filter(
        Documento.titulo_original.isnot(None),
        Documento.titulo_original != '',
        Documento.descripcion.isnot(None),
        Documento.descripcion != '',
        Documento.periodo_inicio.isnot(None),
        Documento.periodo_fin.isnot(None)
    ).all()
    contactos_extra = []
    numero = ''
    email = ''
    if request.method == 'POST':
        user.nombre_completo = request.form.get('nombre', user.nombre_completo)
        user.descripcion_personal = request.form.get('descripcion_personal', getattr(user, 'descripcion_personal', ''))
        numero = request.form.get('numero', '')
        email = request.form.get('email', '')
        contactos_extra = [c for c in request.form.getlist('contactos_extra') if c.strip()][:3]
        db.session.commit()
        flash("Datos actualizados.")
        docs_ids = [doc_id for doc_id in request.form.getlist('docs') if doc_id.isdigit()]
        if docs_ids:
            documentos = Documento.query.filter(
                Documento.id_documento.in_(docs_ids),
                Documento.titulo_original.isnot(None),
                Documento.titulo_original != '',
                Documento.descripcion.isnot(None),
                Documento.descripcion != '',
                Documento.periodo_inicio.isnot(None),
                Documento.periodo_fin.isnot(None)
            ).all()
        else:
            documentos = []

        # --- Generar PDF con ReportLab (formato mejorado) ---
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        margin = 50
        y = height - margin

        # Nombre grande
        p.setFont("Helvetica-Bold", 22)
        p.drawString(margin, y, user.nombre_completo)
        y -= 30

        # Información de contacto principal
        p.setFont("Helvetica", 12)
        p.drawString(margin, y, f"Tel: {numero} | Email: {email}")
        y -= 18

        # Contactos extra (solo si existen)
        for contacto in contactos_extra:
            p.drawString(margin, y, contacto)
            y -= 15

        # Línea horizontal
        p.setLineWidth(1)
        p.line(margin, y, width - margin, y)
        y -= 20

        # Descripción personal
        if getattr(user, 'descripcion_personal', ''):
            p.setFont("Helvetica-Bold", 14)
            p.drawString(margin, y, "Perfil Profesional")
            y -= 18
            p.setFont("Helvetica", 12)
            text = p.beginText(margin, y)
            for line in user.descripcion_personal.splitlines():
                text.textLine(line)
            p.drawText(text)
            y = text.getY() - 15

        # Otra línea
        p.setLineWidth(0.5)
        p.line(margin, y, width - margin, y)
        y -= 20

        # Documentos (como experiencia, educación, etc.)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(margin, y, "Formación Académica")
        y -= 18

        p.setFont("Helvetica", 12)
        for doc in documentos:
            if y < margin + 80:
                p.showPage()
                y = height - margin

            # Título en negrita y más grande
            p.setFont("Helvetica-Bold", 13)
            p.drawString(margin, y, doc.titulo_original)
            y -= 16

            # Fechas (debajo del título)
            fecha_inicio = doc.periodo_inicio.strftime('%B %Y') if doc.periodo_inicio else ''
            fecha_fin = doc.periodo_fin.strftime('%B %Y') if doc.periodo_fin else ''
            fechas = f"{fecha_inicio} - {fecha_fin}" if fecha_inicio and fecha_fin else ""
            if fechas:
                p.setFont("Helvetica", 11)
                p.drawString(margin, y, fechas)
                y -= 14

            # Descripción (en viñetas si hay saltos de línea)
            if getattr(doc, 'descripcion', ''):
                p.setFont("Helvetica-Oblique", 11)
                for linea in doc.descripcion.splitlines():
                    if linea.strip():
                        p.drawString(margin + 15, y, u"\u2022 " + linea.strip())
                        y -= 13
            y -= 8  # Espacio extra entre documentos

        p.save()
        buffer.seek(0)
        return send_file(
            buffer,
            download_name="curriculum.pdf",
            as_attachment=True,
            mimetype='application/pdf'
        )

    return render_template('cv/cv_form.html', user=user, documentos=documentos, current_folder_id=None)