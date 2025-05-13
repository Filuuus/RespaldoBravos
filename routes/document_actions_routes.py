# RespaldoBravos/routes/document_actions_routes.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_file
)
from models import Documento, Categoria, Carpeta, Usuario # Import all needed models
from extensions import db
from utils import login_required, log_activity # Import from your new utils.py
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import uuid
import os
from datetime import datetime, timezone

doc_actions_bp = Blueprint('doc_actions_bp', __name__, url_prefix='/doc') # Example prefix /doc

@doc_actions_bp.route('/upload', defaults={'parent_folder_id': None}, methods=['GET', 'POST'])
@doc_actions_bp.route('/upload/<int:parent_folder_id>', methods=['GET', 'POST'])
@login_required
def upload_route(parent_folder_id):
    local_s3_client = current_app.s3_client
    user_id = session.get('user_id')
    categories = Categoria.query.order_by(Categoria.nombre).all()
    user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('No selected file.', 'warning')
            return redirect(request.url)
        file = request.files['file']
        id_categoria_str = request.form.get('categoria', '')
        id_carpeta_str = request.form.get('carpeta', '')
        descripcion = request.form.get('descripcion', '')
        periodo_inicio_str = request.form.get('periodo_inicio', '')
        periodo_fin_str = request.form.get('periodo_fin', '')
        favorito = request.form.get('favorito') == 'true'
        custom_title = request.form.get('custom_title', '').strip()
        id_categoria = int(id_categoria_str) if id_categoria_str.isdigit() else None
        id_carpeta_to_save = None
        if id_carpeta_str.isdigit():
            folder_check = Carpeta.query.filter_by(id_carpeta=int(id_carpeta_str), id_usuario=user_id).first()
            if folder_check: id_carpeta_to_save = int(id_carpeta_str)
        periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date() if periodo_inicio_str else None
        periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date() if periodo_fin_str else None
        if file:
            original_filename_for_s3 = secure_filename(file.filename)
            titulo_a_usar = secure_filename(custom_title) if custom_title else original_filename_for_s3
            mime_type = file.mimetype
            current_pos = file.tell()
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(current_pos)
            if file_size > current_app.config['MAX_CONTENT_LENGTH']:
                 flash(f"File size exceeds the limit of {current_app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f} MB.", 'danger')
                 return redirect(request.url)
            if file_size > 2147483647:
                 flash(f'File size ({file_size} bytes) exceeds the database limit (2.14 GB).', 'danger')
                 return redirect(request.url)
            s3_key = f"user_{user_id}/{uuid.uuid4()}_{original_filename_for_s3}"
            if not local_s3_client:
                 flash('S3 service not available. Cannot upload file.', 'danger')
                 return redirect(request.url)
            try:
                local_s3_client.upload_fileobj(file, current_app.config['S3_BUCKET'], s3_key, ExtraArgs={'ContentType': mime_type})
                new_documento = Documento(titulo_original=titulo_a_usar, descripcion=descripcion, s3_bucket=current_app.config['S3_BUCKET'], 
                                        s3_object_key=s3_key, mime_type=mime_type, file_size=file_size, id_usuario=user_id,
                                        id_carpeta=id_carpeta_to_save, id_categoria=id_categoria, periodo_inicio=periodo_inicio, 
                                        periodo_fin=periodo_fin, favorito=favorito)
                db.session.add(new_documento)
                db.session.commit()
                flash(f'File "{titulo_a_usar}" uploaded successfully!', 'success')
                log_activity(user_id=user_id, activity_type='UPLOAD_DOC', document_id=new_documento.id_documento,
                             folder_id=id_carpeta_to_save, ip_address=request.remote_addr, details=f"Uploaded: {original_filename_for_s3}")
                return redirect(url_for('main_bp.list_files', folder_id=id_carpeta_to_save)) # Corrected redirect
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving file: {str(e)}', 'danger')
                try: 
                    if local_s3_client: local_s3_client.delete_object(Bucket=current_app.config['S3_BUCKET'], Key=s3_key)
                except: pass
                return redirect(request.url)
    else: # GET request
        active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 'modified_name': 'Any time', 'period_year_name': 'Any'}
        return render_template('upload.html', categories=categories, folders=user_folders, parent_folder_id=parent_folder_id,
                               current_page='upload', active_filters=active_filters_default, current_folder_id=parent_folder_id)


@doc_actions_bp.route('/download/<int:doc_id>')
@login_required
def download_file(doc_id):
    local_s3_client = current_app.s3_client
    user_id = session.get('user_id')
    document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first_or_404()
    if not local_s3_client:
        flash("S3 service not available.", "danger")
        return redirect(url_for('main_bp.list_files', folder_id=document.id_carpeta))
    try:
        display_filename = document.titulo_original
        presigned_url = local_s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': document.s3_bucket, 'Key': document.s3_object_key, 'ResponseContentDisposition': f'attachment; filename="{secure_filename(display_filename)}"'},
            ExpiresIn=300
        )
        log_activity(user_id=user_id, activity_type='DOWNLOAD_DOC_LINK', document_id=doc_id, ip_address=request.remote_addr)
        return redirect(presigned_url)
    except Exception as e:
        flash(f"Error generating download link: {str(e)}", "danger")
        return redirect(url_for('main_bp.list_files', folder_id=document.id_carpeta))


@doc_actions_bp.route('/edit/<int:doc_id>', methods=['POST']) # Assuming GET is not used for modal
@login_required
def edit_file(doc_id):
    user_id = session.get('user_id')
    document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first_or_404()
    try:
        new_title_str = request.form.get('titulo_nuevo', '').strip()
        id_categoria_str = request.form.get('categoria', '')
        id_carpeta_str = request.form.get('carpeta', '')
        descripcion_str = request.form.get('descripcion', '')
        periodo_inicio_str = request.form.get('periodo_inicio', '')
        periodo_fin_str = request.form.get('periodo_fin', '')
        favorito_str = request.form.get('favorito', 'false')
        if new_title_str: document.titulo_original = secure_filename(new_title_str)
        document.id_categoria = int(id_categoria_str) if id_categoria_str.isdigit() else None
        if id_carpeta_str == '' or not id_carpeta_str.isdigit(): document.id_carpeta = None
        else:
            folder_check = Carpeta.query.filter_by(id_carpeta=int(id_carpeta_str), id_usuario=user_id).first()
            if folder_check: document.id_carpeta = int(id_carpeta_str)
        document.descripcion = descripcion_str
        document.periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date() if periodo_inicio_str else None
        document.periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date() if periodo_fin_str else None
        document.favorito = favorito_str == 'true'
        document.fecha_modificacion = datetime.now(timezone.utc)
        db.session.commit()
        log_activity(user_id=user_id, activity_type='EDIT_DOC_METADATA_MODAL', document_id=doc_id,
                     ip_address=request.remote_addr, details=f"Edited: {document.titulo_original}")
        return jsonify({'success': True, 'message': f'"{document.titulo_original}" updated!'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating document metadata via modal: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@doc_actions_bp.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_file(doc_id):
    local_s3_client = current_app.s3_client
    user_id = session.get('user_id')
    document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first_or_404()
    original_parent_folder_id = document.id_carpeta
    original_filename = document.titulo_original
    s3_bucket_name = document.s3_bucket
    s3_object_key_to_delete = document.s3_object_key
    try:
        if local_s3_client:
            local_s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_object_key_to_delete)
        db.session.delete(document)
        db.session.commit()
        flash(f'File "{original_filename}" deleted successfully.', 'success')
        log_activity(user_id=user_id, activity_type='DELETE_DOC', document_id=doc_id, ip_address=request.remote_addr, details=f"Deleted: {original_filename}")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting file: {str(e)}", "danger")
    return redirect(url_for('main_bp.list_files', folder_id=original_parent_folder_id)) # Corrected redirect


@doc_actions_bp.route('/move_file/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def move_file(doc_id):
    user_id = session.get('user_id')
    doc_to_move = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first_or_404()
    user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
    active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 'modified_name': 'Any time', 'period_year_name': 'Any'} # For GET
    if request.method == 'POST':
        dest_folder_id_str = request.form.get('destination_folder', '')
        destination_folder_id = int(dest_folder_id_str) if dest_folder_id_str.isdigit() else None
        if doc_to_move.id_carpeta == destination_folder_id:
             flash('File is already in that folder.', 'info')
             return redirect(url_for('main_bp.list_files', folder_id=destination_folder_id))
        conflicting_file = Documento.query.filter(Documento.id_usuario == user_id, Documento.id_carpeta == destination_folder_id, Documento.titulo_original == doc_to_move.titulo_original, Documento.id_documento != doc_id).first()
        if conflicting_file:
            dest_name = "Root Folder"
            if destination_folder_id:
                dest_folder_obj = db.session.get(Carpeta, destination_folder_id)
                if dest_folder_obj: dest_name = dest_folder_obj.nombre
            flash(f'A file named "{doc_to_move.titulo_original}" already exists in "{dest_name}".', 'danger')
            return render_template('move_file.html', document=doc_to_move, folders=user_folders, current_page=None, active_filters=active_filters_default, current_folder_id=doc_to_move.id_carpeta)
        doc_to_move.id_carpeta = destination_folder_id
        doc_to_move.fecha_modificacion = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'File "{doc_to_move.titulo_original}" moved successfully.', 'success')
        log_activity(user_id=user_id, activity_type='MOVE_DOC', document_id=doc_id, ip_address=request.remote_addr, details=f"Moved to folder ID: {destination_folder_id}")
        return redirect(url_for('main_bp.list_files', folder_id=destination_folder_id))
    else: # GET
        return render_template('move_file.html', document=doc_to_move, folders=user_folders, current_page=None, active_filters_default=active_filters_default, current_folder_id=doc_to_move.id_carpeta)