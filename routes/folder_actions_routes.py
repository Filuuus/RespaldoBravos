# RespaldoBravos/routes/folder_actions_routes.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
)
# Ensure all necessary models are imported
from models import Carpeta, Documento, Usuario, ActividadUsuario 
from extensions import db
# Ensure utils are imported
from utils import login_required, log_activity 
from datetime import datetime, timezone
from sqlalchemy import text # For recursive CTE query in move_folder

folder_actions_bp = Blueprint('folder_actions_bp', __name__, url_prefix='/folder')

@folder_actions_bp.route('/create', methods=['POST'])
@folder_actions_bp.route('/create/<int:parent_folder_id>', methods=['POST'])
@login_required
def create_folder(parent_folder_id=None):
    user_id = session.get('user_id')
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash('Folder name cannot be empty.', 'warning')
        # Assuming main_bp.list_files is the correct endpoint for file/folder listing
        return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id)) 

    # Optional: Validate parent_folder_id belongs to user if it's not None
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
        current_app.logger.error(f"Error creating folder: {str(e)}")
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
                ip_address=request.remote_addr,
                details=f'Attempting to delete empty folder: {folder_name} (ID: {folder_id}, Parent ID: {parent_id_for_redirect})'
            )
            db.session.delete(folder_to_delete)
            db.session.commit()
            flash(f'Folder "{folder_name}" deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting folder (ID: {folder_id}): {str(e)}")
            flash(f"Error deleting folder: {str(e)}", "danger")
            
    return redirect(url_for('main_bp.list_files', folder_id=parent_id_for_redirect))


@folder_actions_bp.route('/rename/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def rename_folder(folder_id):
    user_id = session.get('user_id')
    folder_to_rename = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    parent_folder_id = folder_to_rename.id_carpeta_padre

    if request.method == 'POST': # This will be called by the modal's AJAX request
        new_name = request.form.get('new_folder_name', '').strip()

        if not new_name:
            return jsonify({'success': False, 'message': 'New folder name cannot be empty.'}), 400
        
        if new_name == folder_to_rename.nombre:
            return jsonify({'success': True, 'message': 'New name is the same as the current name. No changes made.'}), 200
        
        try:
            existing_folder = Carpeta.query.filter(
                Carpeta.id_usuario == user_id,
                Carpeta.id_carpeta_padre == parent_folder_id,
                Carpeta.nombre == new_name,
                Carpeta.id_carpeta != folder_id 
            ).first()

            if existing_folder:
                return jsonify({'success': False, 'message': f'A folder named "{new_name}" already exists at this level.'}), 400 # 400 or 409 Conflict
            else:
                old_name = folder_to_rename.nombre
                folder_to_rename.nombre = new_name
                folder_to_rename.fecha_modificacion = datetime.now(timezone.utc)
                db.session.commit()
                
                log_activity(
                    user_id=user_id, 
                    activity_type='RENAME_FOLDER', 
                    folder_id=folder_id,
                    ip_address=request.remote_addr,
                    details=f'Renamed folder "{old_name}" to: {new_name}'
                )
                return jsonify({'success': True, 'message': f'Folder renamed to "{new_name}" successfully.'}), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error renaming folder (ID: {folder_id}) via modal: {str(e)}")
            return jsonify({'success': False, 'message': f'An error occurred while renaming: {str(e)}'}), 500
    
    else: # GET request
        flash("Rename action is performed via a modal.", "info")
        return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))


@folder_actions_bp.route('/move/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def move_folder(folder_id):
    user_id = session.get('user_id')
    folder_to_move = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    original_parent_id = folder_to_move.id_carpeta_padre

    if request.method == 'POST':
        dest_folder_id_str = request.form.get('destination_folder', '')
        
        destination_folder_id = None
        if dest_folder_id_str.isdigit():
            destination_folder_id = int(dest_folder_id_str)
        elif dest_folder_id_str != '': # Not empty and not a digit
            return jsonify({'success': False, 'message': 'Invalid destination folder ID.'}), 400

        if folder_to_move.id_carpeta_padre == destination_folder_id:
            return jsonify({'success': False, 'message': 'Folder is already in that location.'}), 400
        if destination_folder_id == folder_id:
            return jsonify({'success': False, 'message': 'Cannot move a folder into itself.'}), 400

        destination_folder_name_for_msg = "Root Folder"
        if destination_folder_id is not None:
            destination_folder_obj = Carpeta.query.filter_by(id_carpeta=destination_folder_id, id_usuario=user_id).first()
            if not destination_folder_obj:
                return jsonify({'success': False, 'message': 'Destination folder not found or access denied.'}), 404
            destination_folder_name_for_msg = destination_folder_obj.nombre
            
            sql_descendants = text("""
                WITH RECURSIVE subfolders AS (
                    SELECT id_carpeta, id_carpeta_padre FROM carpetas 
                    WHERE id_carpeta = :folder_to_move_id AND id_usuario = :user_id
                    UNION ALL
                    SELECT c.id_carpeta, c.id_carpeta_padre FROM carpetas c
                    INNER JOIN subfolders s ON c.id_carpeta_padre = s.id_carpeta
                    WHERE c.id_usuario = :user_id
                )
                SELECT id_carpeta FROM subfolders;
            """)
            result = db.session.execute(sql_descendants, {'folder_to_move_id': folder_id, 'user_id': user_id})
            descendant_ids = {row[0] for row in result} # Correctly access the first element of the Row object
            
            if destination_folder_id in descendant_ids:
                return jsonify({'success': False, 'message': 'Cannot move a folder into one of its own sub-folders (cycle detected).'}), 400

        conflicting_folder_in_dest = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.id_carpeta_padre == destination_folder_id,
            Carpeta.nombre == folder_to_move.nombre,
            Carpeta.id_carpeta != folder_id
        ).first()
        if conflicting_folder_in_dest:
            return jsonify({'success': False, 'message': f'A folder named "{folder_to_move.nombre}" already exists in "{destination_folder_name_for_msg}".'}), 409

        try:
            old_parent_id_for_log = folder_to_move.id_carpeta_padre
            folder_to_move.id_carpeta_padre = destination_folder_id
            folder_to_move.fecha_modificacion = datetime.now(timezone.utc)
            db.session.commit()
            
            log_activity(
                user_id=user_id, 
                activity_type='MOVE_FOLDER', 
                folder_id=folder_id,
                ip_address=request.remote_addr, 
                details=f"Moved folder '{folder_to_move.nombre}' from parent ID {old_parent_id_for_log} to parent ID: {destination_folder_id if destination_folder_id is not None else 'Root'}"
            )
            return jsonify({'success': True, 'message': f'Folder "{folder_to_move.nombre}" moved successfully to "{destination_folder_name_for_msg}".'}), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error moving folder (ID: {folder_id}): {str(e)}")
            return jsonify({'success': False, 'message': f'An error occurred while moving the folder: {str(e)}'}), 500
    
    else: # GET request
        flash("This action is performed via a modal.", "info")
        return redirect(url_for('main_bp.list_files', folder_id=original_parent_id))
