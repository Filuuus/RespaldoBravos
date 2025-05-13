import os
import boto3 
import uuid 
import math
from datetime import datetime, timedelta, timezone 
from dotenv import load_dotenv
from extensions import db 
from flask import Flask
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify, send_file
from flask_migrate import Migrate
from functools import wraps 
from models import ActividadUsuario, Usuario
from sqlalchemy import asc, desc, text, or_, text, func as sql_func
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from zeep import Client, Settings, Transport
from zeep.exceptions import Fault 

from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.document_actions_routes import doc_actions_bp
from routes.api_routes import api_bp
from utils import log_activity, login_required

load_dotenv() 

# Initialize Flask app
app = Flask(__name__)

# --- 1. Load Configuration ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_fallback_secret_key_for_dev_only') 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///default.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['S3_BUCKET'] = os.environ.get('S3_BUCKET')
app.config['S3_KEY'] = os.environ.get('S3_KEY')
app.config['S3_SECRET'] = os.environ.get('S3_SECRET')
app.config['S3_REGION'] = os.environ.get('S3_REGION')
MAX_MB = int(os.environ.get('MAX_CONTENT_LENGTH_MB', 50)) 
app.config['MAX_CONTENT_LENGTH'] = MAX_MB * 1024 * 1024 
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

app.config['SIIAU_WSDL_URL'] = os.environ.get('SIIAU_WSDL_URL')
app.config['SIIAU_VALIDA_KEY'] = os.environ.get('SIIAU_VALIDA_KEY')

app.config['ITEMS_PER_PAGE'] = 30 

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(doc_actions_bp)
app.register_blueprint(api_bp)

# --- 2. Initialize Extensions that NEED config (like DB) ---
db.init_app(app) 
migrate = Migrate(app,db)

# --- 3. Initialize Boto3 S3 Client (can now safely read app.config) ---
app.s3_client = None # Initialize as an attribute of app
try:
    if (app.config['S3_KEY'] and
        app.config['S3_SECRET'] and
        app.config['S3_REGION'] and
        app.config['S3_BUCKET']):
        # Assign to app.s3_client
        app.s3_client = boto3.client(
           "s3",
           aws_access_key_id=app.config['S3_KEY'],
           aws_secret_access_key=app.config['S3_SECRET'],
           region_name=app.config['S3_REGION']
        )
        print("Boto3 S3 Client Initialized Successfully and attached to app.")
    else:
        print("S3 credentials or configuration missing, S3 client not initialized.")
except Exception as e:
    print(f"Error initializing Boto3 S3 Client: {e}")
    app.s3_client = None

# --- Initialize Zeep SOAP Client AND ATTACH TO APP ---
app.siiau_client = None # Initialize as an attribute of app
if app.config['SIIAU_WSDL_URL']:
    try:
        from zeep import Client, Settings
        settings = Settings(strict=False, xml_huge_tree=True)
        # Assign to app.siiau_client
        app.siiau_client = Client(app.config['SIIAU_WSDL_URL'], settings=settings)
        print("Zeep SIIAU Client Initialized Successfully and attached to app.")
    except Exception as e:
        print(f"Error initializing Zeep SIIAU Client: {e}")
        app.siiau_client = None
else:
    print("SIIAU WSDL URL missing, Zeep client not initialized.")

# --- Models (Import after app and db are configured if models depend on them at import time) ---
from models import ActividadUsuario, Usuario, Documento, Carpeta, Categoria

# --- Jinja Custom Filter for File Size ---
def format_file_size(size_bytes):
    """Converts bytes to KB, MB, GB, etc."""
    if size_bytes is None or size_bytes == 0:
       return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# Register the filter with Jinja environment
app.jinja_env.filters['format_file_size'] = format_file_size
# ---------------------------------------

# --- File Upload Route ---
# Modify route definition to accept optional parent folder ID
@app.route('/upload', defaults={'parent_folder_id': None}, methods=['GET', 'POST'])
@app.route('/upload/<int:parent_folder_id>', methods=['GET', 'POST'])
@login_required # Protect this route
def upload_route(parent_folder_id):
    # --- Import models needed specifically for this route ---
    from models import Documento, Categoria, Carpeta
    local_s3_client = current_app.s3_client 
    # --------------------------------------------------------

    # Optional: Validate parent_folder_id belongs to user if not None (in GET)
    if request.method == 'GET' and parent_folder_id is not None:
        user_id = session.get('user_id')
        parent_folder = Carpeta.query.filter_by(id_carpeta=parent_folder_id, id_usuario=user_id).first()
        if not parent_folder:
             flash("Target folder not found or access denied.", "warning")
             return redirect(url_for('main_bp.list_files')) # Redirect to root

    # --- Handle POST Request (File Upload) ---
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id: 
            flash('User session error.', 'danger')
            return redirect(url_for('login'))

        # 1. Check file part
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('No selected file.', 'warning')
            return redirect(request.url)
        
        file = request.files['file']

    # 3. Get other form data 
        id_categoria = request.form.get('categoria', default=None, type=int)

        # --- Adjust folder ID retrieval ---
        id_carpeta_str = request.form.get('carpeta', default='') # Get submitted value (empty string for root)
        if id_carpeta_str == '':
            parent_folder_id_to_save = None # Root folder
        elif id_carpeta_str.isdigit():
            parent_folder_id_to_save = int(id_carpeta_str)
            # Re-validate this ID belongs to user (important!) - You already have this logic
            user_id_for_validation = session.get('user_id')
            from models import Carpeta # Import if needed
            parent_folder = Carpeta.query.filter_by(id_carpeta=parent_folder_id_to_save, id_usuario=user_id_for_validation).first()
            if not parent_folder:
                flash("Invalid target folder specified.", "danger")
                # Redirect appropriately, maybe back to upload form?
                return redirect(url_for('doc_actions_bp.upload_route', parent_folder_id=parent_folder_id)) 
        else:
            # Invalid value submitted? Default to root or show error?
            flash("Invalid folder selection.", "warning")
            parent_folder_id_to_save = None # Defaulting to root on error
        # ------------------------------------

        id_categoria = request.form.get('categoria', default=None, type=int)
        descripcion = request.form.get('descripcion', default=None)
        periodo_inicio_str = request.form.get('periodo_inicio', default=None)
        periodo_fin_str = request.form.get('periodo_fin', default=None)
        favorito = request.form.get('favorito') == 'true' 

        # Convert date strings
        periodo_inicio = None
        if periodo_inicio_str:
            try:
                periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
            except ValueError: pass 
        
        periodo_fin = None
        if periodo_fin_str:
            try:
                periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()
            except ValueError: pass 

        if file: 
            original_filename = secure_filename(file.filename)
            mime_type = file.mimetype
            # Get file size accurately
            current_pos = file.tell() # Remember current position
            file.seek(0, os.SEEK_END) 
            file_size = file.tell() 
            file.seek(current_pos) # Reset stream position to where it was
            

            # Check against INTEGER limit
            if file_size > 2147483647: 
                 flash(f'File size ({file_size} bytes) exceeds the database limit (2.14 GB).', 'danger')
                 return redirect(request.url)

            # Generate unique S3 key
            s3_key = f"user_{user_id}/{uuid.uuid4()}_{original_filename}"

            # Check S3 client
            if not local_s3_client:
                 flash('S3 client not available. Cannot upload file.', 'danger')
                 return redirect(request.url)
                
            # 7. Upload to S3
            try:
                local_s3_client.upload_fileobj(
                    file,                   
                    app.config['S3_BUCKET'],
                    s3_key,                 
                    ExtraArgs={'ContentType': mime_type}
                )

            except Exception as e: 
                flash(f'Error uploading file to S3: {e}', 'danger')
                return redirect(request.url)

            # 8. Save metadata to Database
            try:
                # Documento should already be imported from start of function
                new_documento = Documento( 
                    titulo_original=original_filename,
                    descripcion=descripcion,
                    s3_bucket=app.config['S3_BUCKET'],
                    s3_object_key=s3_key,
                    mime_type=mime_type,
                    file_size=file_size, 
                    id_usuario=user_id,
                    id_carpeta=parent_folder_id_to_save, # Use validated/determined folder ID
                    id_categoria=id_categoria, 
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    favorito=favorito
                )
                db.session.add(new_documento)
                db.session.commit()
                flash(f'File "{original_filename}" uploaded successfully!', 'success')
                
                # --- Log Call ---
                log_activity(
                    user_id=user_id, 
                    activity_type='UPLOAD_DOC', 
                    document_id=new_documento.id_documento, # Get ID from newly created object
                    folder_id=parent_folder_id_to_save,
                    ip_address=request.remote_addr,
                    details=f"Uploaded: {original_filename}"
                )
                # --------------------

                # Redirect back to the folder where file was uploaded
                return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id_to_save)) 

            except Exception as e:
                db.session.rollback() 
                flash(f'Error saving file metadata to database: {e}', 'danger')
                
                # Attempt to delete orphaned S3 object
                try:
                    local_s3_client.delete_object(Bucket=app.config['S3_BUCKET'], Key=s3_key)
                except Exception as s3_e:
                    flash('Database error occurred. Orphaned file might remain in storage.', 'warning')
                    
                return redirect(request.url) # Redirect back to original upload URL? Or list?

        else: 
             flash('File processing error.', 'danger')
             return redirect(request.url)

# --- Handle GET Request (Display Upload Form) ---
    else: # request.method == 'GET'
        # Import models needed for GET request
        from models import Categoria, Carpeta 

        user_id = session.get('user_id') # Need user_id to fetch folders
        if not user_id: # Should be caught by @login_required, but check anyway
             flash("Login required.", "warning")
             return redirect(url_for('login'))

        categories = Categoria.query.order_by(Categoria.nombre).all()
        # --- Fetch all folders for this user ---
        user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        # ---------------------------------------

        # Pass folders list and parent_folder_id to the template
        return render_template('upload.html', 
                               categories=categories, 
                               folders=user_folders, # Pass folders
                               parent_folder_id=parent_folder_id) # Keep passing this
    
    # --- Folder Creation Route ---
@app.route('/create_folder', methods=['POST']) # Only accept POST requests
@app.route('/create_folder/<int:parent_folder_id>', methods=['POST']) # Allow parent ID in URL
@login_required
def create_folder(parent_folder_id=None): # Default parent is None (root)
    # --- Import models needed specifically for this route ---
    from models import Carpeta 
    # --------------------------------------------------------

    user_id = session.get('user_id')
    # ... (rest of validation for user_id and folder_name as before) ...
    folder_name = request.form.get('folder_name', '').strip()
    if not folder_name:
        flash('Folder name cannot be empty.', 'warning')
        # Redirect back to the specific folder view if parent_folder_id exists
        return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id)) 

    # TODO: Validate parent_folder_id belongs to user if it's not None

    try:
        # Check if folder exists with same name under the *specific parent*
        existing_folder = Carpeta.query.filter_by(
            id_usuario=user_id,
            id_carpeta_padre=parent_folder_id, # Use the passed parent ID
            nombre=folder_name
        ).first()

        if existing_folder:
            flash(f'A folder named "{folder_name}" already exists here.', 'warning')
        else:
            # Create the new folder with the correct parent ID
            new_folder = Carpeta(
                nombre=folder_name,
                id_usuario=user_id,
                id_carpeta_padre=parent_folder_id 
            )
            db.session.add(new_folder)
            db.session.commit()
            flash(f'Folder "{folder_name}" created successfully.', 'success')

            # --- Add Log Call ---
            log_activity(
                user_id=user_id, 
                activity_type='CREATE_FOLDER', 
                folder_id=new_folder.id_carpeta, # ID of the folder just created
                ip_address=request.remote_addr,
                # Remove parent_folder_id_param, add info to details
                details=f'Created folder: {folder_name} (in Parent ID: {parent_folder_id})' 
            )
            # --------------------------
            
    except Exception as e:
        db.session.rollback()
        print(f"Error creating folder: {e}")
        flash('An error occurred while creating the folder.', 'danger')

    # Redirect back to the folder view where the creation happened
    return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))


# --- Folder Deletion Route ---
@app.route('/delete_folder/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    # --- Import models needed ---
    from models import Carpeta, Documento
    # ----------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    try:
        # 1. Find the folder, ensuring it belongs to the current user
        folder_to_delete = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first()

        if not folder_to_delete:
            flash('Folder not found or access denied.', 'danger')
            return redirect(url_for('main_bp.list_files')) # Redirect to root or previous location?

        # --- Store parent ID BEFORE deleting for redirection ---
        parent_folder_id = folder_to_delete.id_carpeta_padre 
        folder_name = folder_to_delete.nombre # For flash message
        # -------------------------------------------------------

        # 2. Check if the folder is empty (contains no sub-folders)
        has_subfolders = Carpeta.query.filter_by(id_carpeta_padre=folder_id, id_usuario=user_id).first()

        # 3. Check if the folder is empty (contains no files)
        has_files = Documento.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first()

        # 4. Proceed with deletion ONLY if both checks are empty
        if has_subfolders or has_files:
            flash(f'Folder "{folder_name}" is not empty. Please delete its contents first.', 'warning')
            # Redirect back to the view containing the non-empty folder
            return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id)) 
        else:
            # Store details before deleting
            folder_id_to_log = folder_to_delete.id_carpeta
            folder_name_to_log = folder_to_delete.nombre
            parent_id_to_log = folder_to_delete.id_carpeta_padre

            # Log call BEFORE DB delete/commit - correct
            log_activity(
                user_id=user_id, 
                activity_type='DELETE_FOLDER', 
                folder_id=None, 
                ip_address=request.remote_addr,
                details=f'Deleted empty folder: {folder_name_to_log} (Parent ID: {parent_id_to_log})' # Add parent ID here
            )
            # ----------------------------------------
            # Folder is empty, proceed with deletion
            db.session.delete(folder_to_delete)
            db.session.commit()
            flash(f'Folder "{folder_name}" deleted successfully.', 'success')
            parent_folder_id = parent_id_to_log # Ensure redirect uses stored parent ID
            


    except Exception as e:
        db.session.rollback()
        print(f"Error deleting folder: {e}")
        flash('An error occurred while deleting the folder.', 'danger')
        # Redirect back to parent folder even on error
        # Need to fetch parent_folder_id again if error happened before storing it
        parent_folder_id = None # Default redirect if error is early
        folder_check = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first()
        if folder_check:
             parent_folder_id = folder_check.id_carpeta_padre
        return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))

    # Redirect back to the parent folder's view after deletion attempt
    return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))


# --- Folder Rename Route ---
@app.route('/rename_folder/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def rename_folder(folder_id):
    # --- Import model needed ---
    from models import Carpeta 
    # --------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # Fetch the folder to rename, ensuring ownership
    folder_to_rename = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404() 
    # Using first_or_404() is convenient - automatically returns 404 if not found

    parent_folder_id = folder_to_rename.id_carpeta_padre # Needed for validation and redirect

    if request.method == 'POST':
        new_name = request.form.get('new_folder_name', '').strip()

        # Basic Validation
        if not new_name:
            flash('New folder name cannot be empty.', 'warning')
            # Re-render the form on validation error
            return render_template('rename_folder.html', folder=folder_to_rename) 
        
        if new_name == folder_to_rename.nombre:
             flash('New name is the same as the current name.', 'info')
             return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))

        # TODO: Add validation for invalid characters if needed (e.g., '/')

        try:
            # Check if another folder with the new name already exists in the same parent folder
            existing_folder = Carpeta.query.filter(
                Carpeta.id_usuario == user_id,
                Carpeta.id_carpeta_padre == parent_folder_id,
                Carpeta.nombre == new_name,
                Carpeta.id_carpeta != folder_id # Exclude the folder itself from the check
            ).first()

            if existing_folder:
                flash(f'A folder named "{new_name}" already exists at this level.', 'warning')
                # Re-render the form if name conflict
                return render_template('rename_folder.html', folder=folder_to_rename)
            else:
                # Update the folder name
                folder_to_rename.nombre = new_name
                # Update modification timestamp if your model has one
                # folder_to_rename.fecha_modificacion = datetime.utcnow() 
                db.session.commit()
                flash(f'Folder renamed to "{new_name}" successfully.', 'success')


                # --- Log Call ---
                log_activity(
                    user_id=user_id, 
                    activity_type='RENAME_FOLDER', 
                    folder_id=folder_id, # folder_id is parameter to the route
                    ip_address=request.remote_addr,
                    details=f'Renamed folder to: {new_name}'
                )
                # --------------------
                
                # Redirect back to the parent folder view
                return redirect(url_for('main_bp.list_files', folder_id=parent_folder_id))

        except Exception as e:
            db.session.rollback()
            print(f"Error renaming folder: {e}")
            flash('An error occurred while renaming the folder.', 'danger')
            # Re-render form on other errors
            return render_template('rename_folder.html', folder=folder_to_rename)

    # --- Handle GET Request (Show Rename Form) ---
    else: # request.method == 'GET'
        return render_template('rename_folder.html', folder=folder_to_rename)
# ----------------------------------------------------------------------------

# --- Move Folder Route ---
@app.route('/move_folder/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def move_folder(folder_id):
    # --- Import models needed ---
    from models import Carpeta, Documento # Need Documento for name conflict check
    from sqlalchemy import text # For recursive query
    # --------------------------

    user_id = session.get('user_id')
    if not user_id: # Defensive check
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # Fetch the folder to move, ensuring ownership
    folder_to_move = Carpeta.query.filter_by(id_carpeta=folder_id, id_usuario=user_id).first_or_404()
    original_parent_id = folder_to_move.id_carpeta_padre # Store for redirects/logging

    if request.method == 'POST':
        dest_folder_id_str = request.form.get('destination_folder', '') # "" for root

        # 1. Determine Target Folder ID (None for root)
        destination_folder_id = None
        if dest_folder_id_str.isdigit():
            destination_folder_id = int(dest_folder_id_str)
        elif dest_folder_id_str != '':
             flash("Invalid destination folder value.", "danger")
             # Re-render needed info for GET part
             user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
             return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)

        # 2. === Validation Checks ===

        # 2a. Cannot move to the same folder (Technically redundant with 2c check)
        if folder_to_move.id_carpeta_padre == destination_folder_id:
            flash('Folder is already in that location.', 'info')
            return redirect(url_for('main_bp.list_files', folder_id=original_parent_id))

        # 2b. Cannot move folder into itself
        if destination_folder_id == folder_id:
             flash("Cannot move a folder into itself.", "danger")
             user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
             return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)

        # 2c. Cycle Check: Cannot move folder into one of its own descendants
        #     We need to get all descendant folder IDs of the folder being moved
        if destination_folder_id is not None: # No need to check if moving to root
            descendant_ids = set()
            # Use a recursive query to find all children, grandchildren, etc.
            sql_descendants = text("""
                WITH RECURSIVE subfolders AS (
                    SELECT id_carpeta FROM carpetas WHERE id_carpeta = :start_folder_id AND id_usuario = :user_id
                    UNION ALL
                    SELECT c.id_carpeta FROM carpetas c JOIN subfolders s ON c.id_carpeta_padre = s.id_carpeta
                    WHERE c.id_usuario = :user_id
                )
                SELECT id_carpeta FROM subfolders WHERE id_carpeta != :start_folder_id; 
            """) # Exclude the start folder itself
            
            result = db.session.execute(sql_descendants, {'start_folder_id': folder_id, 'user_id': user_id})
            descendant_ids = {row.id_carpeta for row in result}
            
            if destination_folder_id in descendant_ids:
                 flash("Cannot move a folder into one of its own sub-folders.", "danger")
                 user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
                 return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)

        # 2d. Name Conflict Check: Check if folder/file with same name exists in destination
        destination_folder_obj = None # Store destination folder object if applicable
        if destination_folder_id is not None:
            destination_folder_obj = Carpeta.query.filter_by(id_carpeta=destination_folder_id, id_usuario=user_id).first()
            if not destination_folder_obj:
                 flash("Destination folder not found or access denied.", "danger")
                 user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
                 return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)

        conflicting_folder = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.id_carpeta_padre == destination_folder_id,
            Carpeta.nombre == folder_to_move.nombre,
            Carpeta.id_carpeta != folder_id # Exclude self
        ).first()

        # Also check for conflicting *file* names in destination
        conflicting_file = Documento.query.filter(
            Documento.id_usuario == user_id,
            Documento.id_carpeta == destination_folder_id,
            Documento.titulo_original == folder_to_move.nombre # Check file title against folder name
        ).first()

        if conflicting_folder or conflicting_file:
            dest_name = destination_folder_obj.nombre if destination_folder_obj else "Root Folder"
            flash(f'An item named "{folder_to_move.nombre}" already exists in "{dest_name}". Cannot move folder.', 'danger')
            user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
            return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)
        # --- End Validation Checks ---

        # 3. Perform the Move
        try:
            folder_to_move.id_carpeta_padre = destination_folder_id # Update parent ID
            db.session.commit()
            flash(f'Folder "{folder_to_move.nombre}" moved successfully.', 'success')

            # Log activity
            log_activity(
                user_id=user_id,
                activity_type='MOVE_FOLDER',
                folder_id=folder_id,
                ip_address=request.remote_addr,
                details=f"Moved folder '{folder_to_move.nombre}' to Parent ID: {destination_folder_id}"
            )
            
            # Redirect to the new parent folder
            return redirect(url_for('main_bp.list_files', folder_id=destination_folder_id))

        except Exception as e:
            db.session.rollback()
            print(f"Error moving folder: {e}")
            flash('An error occurred while moving the folder.', 'danger')
            user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
            return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)


    # --- Handle GET Request (Show Move Form) ---
    else: # request.method == 'GET'
        # Fetch all folders for this user to populate the destination dropdown
        # We pass ALL folders here; the template filters out current parent/self.
        # For a more robust UI preventing moving into descendants, filtering happens here.
        user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        return render_template('move_folder.html', folder_to_move=folder_to_move, destination_folders=user_folders)
    # ------------------------------------------------------------------------------------------

# --- Context processor ---

@app.context_processor
def inject_current_user():
    from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app
    from models import Usuario, Documento, Carpeta
    user_id = session.get('user_id')
    if user_id:
        user = Usuario.query.get(user_id) # Fetch user object from DB using ID in session
        return dict(current_user=user)
    return dict(current_user=None) # No user in session

# --- Error Handlers ---
@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    # This error handler doesn't need models, but importing Flask functions here is okay too
    from flask import flash # Moved flash import here just for this handler
    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    flash(f'File is too large. Maximum allowed size is {max_size_mb:.0f} MB.') 
    # Note: Redirecting from an error handler can sometimes be tricky, 
    # returning an error response is often preferred.
    return f"File too large (Limit: {max_size_mb:.0f} MB)", 413 

# --- Main entry point ---
if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])