from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from models import Carpeta, Documento, Usuario, ActividadUsuario
from extensions import db
from utils import login_required, log_activity
from datetime import datetime, timezone
from sqlalchemy import text

folder_actions_bp = Blueprint('folder_actions_bp', __name__, url_prefix='/folder')

@folder_actions_bp.route('/create', methods=['POST'])
@folder_actions_bp.route('/create/<int:parent_folder_id>', methods=['POST'])
@login_required
def create_folder(parent_folder_id=None):
    user_id = session.get('user_id')
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash('Folder name cannot be empty.', 'warning')
        return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id)) 

    # Optional: Validate parent_folder_id belongs to user
    if parent_folder_id is not None:
        parent_check = Carpeta.query.filter_by(id_carpeta=parent_folder_id, id_usuario=user_id).first()
        if not parent_check:
            flash("Parent folder not found or access denied.", "danger")
            return redirect(url_for('main_bp.list_files'))


    try:
        existing_folder = Carpeta.query.filter_by(
            id_usuario=user_id,
            id_carpeta_padre=parent_folder_id,
            nombre=folder_name
        ).first()

        if existing_folder:
            flash(f'A folder named "{folder_name}" already exists here.', 'warning')
        else:
            new_folder = Carpeta(
                nombre=folder_name,
                id_usuario=user_id,
                id_carpeta_padre=parent_folder_id 
            )
            db.session.add(new_folder)
            db.session.commit()
            flash(f'Folder "{folder_name}" created successfully.', 'success')
            log_activity(
                user_id=user_id, 
                activity_type='CREATE_FOLDER', 
                folder_id=new_folder.id_carpeta,
                ip_address=request.remote_addr,
                details=f'Created folder: {folder_name} (in Parent ID: {parent_folder_id})' 
            )
    except Exception as e:
        db.session.rollback()
        print(f"Error creating folder: {e}")
        flash('An error occurred while creating the folder.', 'danger')

    return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))


@folder_actions_bp.route('/delete/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    user_id = session.get('user_id')
    folder_to_delete = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    
    parent_id_for_redirect = folder_to_delete.id_carpeta_padre 
    folder_name = folder_to_delete.nombre

    has_subfolders = Carpeta.query.filter_by(id_carpeta_padre=folder_id, id_usuario=user_id).first()
    has_files = Documento.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first()

    if has_subfolders or has_files:
        flash(f'Folder "{folder_name}" is not empty. Please delete its contents first.', 'warning')
    else:
        try:
            log_activity(
                user_id=user_id, 
                activity_type='DELETE_FOLDER', 
                # folder_id=folder_id, # Log before it's gone or use stored var
                ip_address=request.remote_addr,
                details=f'Attempting to delete empty folder: {folder_name} (ID: {folder_id}, Parent ID: {parent_id_for_redirect})'
            )
            db.session.delete(folder_to_delete)
            db.session.commit()
            flash(f'Folder "{folder_name}" deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting folder: {str(e)}", "danger")
            
    return redirect(url_for('main_bp.list_files', folder_id=parent_id_for_redirect))


@folder_actions_bp.route('/rename/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def rename_folder(folder_id):
    user_id = session.get('user_id')
    folder_to_rename = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    parent_folder_id = folder_to_rename.id_carpeta_padre

    if request.method == 'POST':
        new_name = request.form.get('new_folder_name', '').strip()
        if not new_name:
            flash('New folder name cannot be empty.', 'warning')
            return render_template('rename_folder.html', folder=folder_to_rename, current_page=None, active_filters={}, current_folder_id=parent_folder_id)
        
        if new_name == folder_to_rename.nombre:
             flash('New name is the same as the current name.', 'info')
             return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))
        
        try:
            existing_folder = Carpeta.query.filter(
                Carpeta.id_usuario == user_id,
                Carpeta.id_carpeta_padre == parent_folder_id,
                Carpeta.nombre == new_name,
                Carpeta.id_carpeta != folder_id
            ).first()

            if existing_folder:
                flash(f'A folder named "{new_name}" already exists at this level.', 'warning')
            else:
                folder_to_rename.nombre = new_name
                folder_to_rename.fecha_modificacion = datetime.now(timezone.utc)
                db.session.commit()
                flash(f'Folder renamed to "{new_name}" successfully.', 'success')
                log_activity(user_id=user_id, activity_type='RENAME_FOLDER', folder_id=folder_id,
                             ip_address=request.remote_addr, details=f'Renamed folder to: {new_name}')
                return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while renaming the folder: {str(e)}', 'danger')
        
        # If error or name conflict, re-render form
        return render_template('rename_folder.html', folder=folder_to_rename, current_page=None, active_filters={}, current_folder_id=parent_folder_id)
    else: # GET
        active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 'modified_name': 'Any time', 'period_year_name': 'Any'}
        return render_template('rename_folder.html', folder=folder_to_rename, current_page=None, active_filters=active_filters_default, current_folder_id=parent_folder_id)


@folder_actions_bp.route('/move/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def move_folder(folder_id):
    user_id = session.get('user_id')
    folder_to_move = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    original_parent_id = folder_to_move.id_carpeta_padre

    if request.method == 'POST':
        dest_folder_id_str = request.form.get('destination_folder', '')
        destination_folder_id = int(dest_folder_id_str) if dest_folder_id_str.isdigit() else None
        if dest_folder_id_str == '' and request.form.get('destination_folder') is not None : # Explicitly choosing root
            destination_folder_id = None


        if folder_to_move.id_carpeta_padre == destination_folder_id:
            flash('Folder is already in that location.', 'info')
            return redirect(url_for('main_bp.list_files', folder_id=original_parent_id))
        if destination_folder_id == folder_id:
             flash("Cannot move a folder into itself.", "danger")
             return redirect(url_for('.move_folder', folder_id=folder_id)) # Redirect to GET of this route

        if destination_folder_id is not None:
            descendant_ids = set()
            sql_descendants = text("""
                WITH RECURSIVE subfolders AS (
                    SELECT id_carpeta FROM carpetas WHERE id_carpeta = :start_folder_id AND id_usuario = :user_id
                    UNION ALL
                    SELECT c.id_carpeta FROM carpetas c JOIN subfolders s ON c.id_carpeta_padre = s.id_carpeta
                    WHERE c.id_usuario = :user_id
                )
                SELECT id_carpeta FROM subfolders WHERE id_carpeta != :start_folder_id; 
            """)
            result = db.session.execute(sql_descendants, {'start_folder_id': folder_id, 'user_id': user_id})
            descendant_ids = {row[0] for row in result} # Access by index for Row object
            if destination_folder_id in descendant_ids:
                 flash("Cannot move a folder into one of its own sub-folders.", "danger")
                 return redirect(url_for('.move_folder', folder_id=folder_id))

        destination_folder_obj = None
        if destination_folder_id is not None:
            destination_folder_obj = Carpeta.query.filter_by(id_carpeta=destination_folder_id, id_usuario=user_id).first()
            if not destination_folder_obj:
                 flash("Destination folder not found or access denied.", "danger")
                 return redirect(url_for('.move_folder', folder_id=folder_id))
        
        conflicting_folder = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.id_carpeta_padre == destination_folder_id,
            Carpeta.nombre == folder_to_move.nombre,
            Carpeta.id_carpeta != folder_id
        ).first()
        conflicting_file = Documento.query.filter(
            Documento.id_usuario == user_id,
            Documento.id_carpeta == destination_folder_id,
            Documento.titulo_original == folder_to_move.nombre
        ).first()

        if conflicting_folder or conflicting_file:
            dest_name = destination_folder_obj.nombre if destination_folder_obj else "Root Folder"
            flash(f'An item named "{folder_to_move.nombre}" already exists in "{dest_name}". Cannot move folder.', 'danger')
            return redirect(url_for('.move_folder', folder_id=folder_id))

        try:
            folder_to_move.id_carpeta_padre = destination_folder_id
            folder_to_move.fecha_modificacion = datetime.now(timezone.utc)
            db.session.commit()
            flash(f'Folder "{folder_to_move.nombre}" moved successfully.', 'success')
            log_activity(user_id=user_id, activity_type='MOVE_FOLDER', folder_id=folder_id,
                         ip_address=request.remote_addr, details=f"Moved folder '{folder_to_move.nombre}' to Parent ID: {destination_folder_id}")
            return redirect(url_for('main_bp.list_files', folder_id=destination_folder_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while moving the folder: {str(e)}', 'danger')
            return redirect(url_for('.move_folder', folder_id=folder_id))
    else: # GET
        user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        # Exclude self and descendants from destination options for GET request
        # This is a more complex query for the GET request, often simplified for the form
        # and validated more strictly on POST. For now, passing all user_folders.
        active_filters_default = {'category_name': 'Any', 'mime_type_name': 'Any', 'modified_name': 'Any time', 'period_year_name': 'Any'}
        return render_template('move_folder.html', folder_to_move=folder_to_move, 
                               destination_folders=user_folders, current_page=None, 
                               active_filters=active_filters_default, current_folder_id=original_parent_id)