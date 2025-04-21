import os
import boto3 
from flask import Flask
from dotenv import load_dotenv
#from flask_sqlalchemy import SQLAlchemy 
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import text 
import uuid 
from werkzeug.utils import secure_filename
# Imports used in routes moved here for clarity
from flask import render_template, request, redirect, url_for, flash, session 
from datetime import datetime 
from functools import wraps 
import math # Needed for formatting file size
from flask import send_file

from extensions import db 
from flask_migrate import Migrate

load_dotenv() 

# Initialize Flask app
app = Flask(__name__)

# --- 1. Load Configuration FIRST ---
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

# --- 2. Initialize Extensions that NEED config (like DB) ---
db.init_app(app) 

migrate = Migrate(app,db)

# --- 3. Initialize Boto3 S3 Client (can now safely read app.config) ---
s3_client = None # Define outside try block
try:
    # Check if essential S3 config values were actually loaded
    if (app.config['S3_KEY'] and 
        app.config['S3_SECRET'] and 
        app.config['S3_REGION'] and 
        app.config['S3_BUCKET']):
        
        s3_client = boto3.client(
           "s3",
           aws_access_key_id=app.config['S3_KEY'],
           aws_secret_access_key=app.config['S3_SECRET'],
           region_name=app.config['S3_REGION']
        )
        print("Boto3 S3 Client Initialized Successfully.")
    else:
        print("S3 credentials or configuration missing, S3 client not initialized.")
except Exception as e:
    print(f"Error initializing Boto3 S3 Client: {e}")
    s3_client = None 
# ---------------------------------------------------------------------


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


# --- 4. Import Models ---
# Models are now imported inside routes/functions where needed
# from models import Usuario, Documento, Carpeta, Categoria, ActividadUsuario # KEEP THIS COMMENTED OUT

# --- Define Routes ---
@app.route('/') 
def hello_world():
    # This route doesn't need models currently
    bucket_name = app.config.get('S3_BUCKET', 'Not Set') 
    try:
        db.session.execute(text('SELECT 1')) 
        db_status = "Database Connection OK"
    except Exception as e:
        db_status = f"Database Connection Error: {e}"
    
    s3_status = "S3 Client OK" if s3_client else "S3 Client NOT Initialized"
    
    return f'Hello, World! Configured S3 Bucket: {bucket_name}<br>{db_status}<br>{s3_status}'


# --- Simple Login Required Decorator (Placeholder) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url)) 
        return f(*args, **kwargs)
    return decorated_function

# --- Dummy Login/Logout Routes (Placeholders) ---
@app.route('/login') 
def login():
    # This route doesn't need models currently
    session['user_id'] = 1 # Example User ID
    flash('You were logged in (dummy login).', 'success')
    return redirect(request.args.get('next') or url_for('hello_world')) 

@app.route('/logout')
def logout():
     # This route doesn't need models currently
    session.pop('user_id', None) 
    flash('You were logged out.', 'info')
    return redirect(url_for('login')) 

# --- File Upload Route ---
# Modify route definition to accept optional parent folder ID
@app.route('/upload', defaults={'parent_folder_id': None}, methods=['GET', 'POST'])
@app.route('/upload/<int:parent_folder_id>', methods=['GET', 'POST'])
@login_required # Protect this route
def upload_route(parent_folder_id):
    # --- Import models needed specifically for this route ---
    from models import Documento, Categoria, Carpeta
    # --------------------------------------------------------

    # Optional: Validate parent_folder_id belongs to user if not None (in GET)
    if request.method == 'GET' and parent_folder_id is not None:
        user_id = session.get('user_id')
        parent_folder = Carpeta.query.filter_by(id_carpeta=parent_folder_id, id_usuario=user_id).first()
        if not parent_folder:
             flash("Target folder not found or access denied.", "warning")
             return redirect(url_for('list_files')) # Redirect to root

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
        # Get parent folder ID from hidden field
        parent_folder_id_from_form = request.form.get('parent_folder_id', default=None)

        # Logic to determine folder ID to save
        parent_folder_id_to_save = None
        if parent_folder_id_from_form == '': # Explicitly empty string means root
            parent_folder_id_to_save = None
        elif parent_folder_id_from_form and parent_folder_id_from_form.isdigit():
            parent_folder_id_to_save = int(parent_folder_id_from_form)
            # Re-validate this ID belongs to user (important for security)
            user_id_for_validation = session.get('user_id') # Ensure user_id is fresh
            parent_folder = Carpeta.query.filter_by(id_carpeta=parent_folder_id_to_save, id_usuario=user_id_for_validation).first()
            if not parent_folder:
                  flash("Invalid target folder specified.", "danger")
                  # Redirect back to the upload form for the *intended* parent, or root?
                  return redirect(url_for('upload_route', parent_folder_id=parent_folder_id)) 
        else: 
            # If form field exists but isn't empty or digit, default to root? Or error?
            parent_folder_id_to_save = None 

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
            if not s3_client:
                 flash('S3 client not available. Cannot upload file.', 'danger')
                 return redirect(request.url)
                
            # 7. Upload to S3
            try:
                s3_client.upload_fileobj(
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
                
                # Optional: Log activity 
                # print("--- DEBUG: Logging activity...") # DEBUG: Log
                # log_activity(...) 

                # Redirect back to the folder where file was uploaded
                return redirect(url_for('list_files', folder_id=parent_folder_id_to_save)) 

            except Exception as e:
                db.session.rollback() 
                flash(f'Error saving file metadata to database: {e}', 'danger')
                
                # Attempt to delete orphaned S3 object
                try:
                    s3_client.delete_object(Bucket=app.config['S3_BUCKET'], Key=s3_key)
                except Exception as s3_e:
                    flash('Database error occurred. Orphaned file might remain in storage.', 'warning')
                    
                return redirect(request.url) # Redirect back to original upload URL? Or list?

        else: 
             flash('File processing error.', 'danger')
             return redirect(request.url)

    # --- Handle GET Request (Display Upload Form) ---
    else: # request.method == 'GET'
        # Categoria should already be imported from start of function
        categories = Categoria.query.order_by(Categoria.nombre).all() 
        return render_template('upload.html', categories=categories, parent_folder_id=parent_folder_id)

# --- File Listing Route ---
@app.route('/files', defaults={'folder_id': None}, methods=['GET']) 
@app.route('/files/<int:folder_id>', methods=['GET'])
@login_required
def list_files(folder_id):
    # --- Import models needed ---
    from models import Documento, Categoria, Carpeta 
    # ----------------------------
    
    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    sub_folders = []
    documents_in_folder = []
    current_folder_name = "My Files (Root)" # Default for root
    breadcrumbs = [] # Initialize empty list for breadcrumbs

    try:
        # --- Fetch Current Folder and Ancestors (Breadcrumbs) ---
        current_folder = None
        if folder_id:
            # Use a recursive query to get the path from root to current folder
            sql_query = text("""
                WITH RECURSIVE folder_path AS (
                    -- Anchor member: Select the current folder
                    SELECT id_carpeta, nombre, id_carpeta_padre
                    FROM carpetas
                    WHERE id_carpeta = :current_folder_id AND id_usuario = :user_id

                    UNION ALL

                    -- Recursive member: Select the parent of the previous level
                    SELECT c.id_carpeta, c.nombre, c.id_carpeta_padre
                    FROM carpetas c
                    JOIN folder_path fp ON c.id_carpeta = fp.id_carpeta_padre
                    WHERE c.id_usuario = :user_id -- Ensure all ancestors belong to the user
                )
                -- Select the path (ordering handled in Python)
                SELECT id_carpeta, nombre, id_carpeta_padre FROM folder_path;
            """)
            
            result = db.session.execute(sql_query, {'current_folder_id': folder_id, 'user_id': user_id})
            
            # Build the breadcrumb list from the query result
            path_data = {row.id_carpeta: row for row in result.mappings()} # Fetch all ancestors into a dict

            if folder_id not in path_data: # Check if current folder was found / belongs to user
                 flash("Folder not found or access denied.", "warning")
                 return redirect(url_for('list_files', folder_id=None)) # Redirect to root

            # Reconstruct path from root to current
            curr_id = folder_id
            while curr_id is not None:
                folder_info = path_data.get(curr_id)
                if folder_info:
                    # Insert at beginning to get Root -> ... -> Current order
                    breadcrumbs.insert(0, {'id': folder_info['id_carpeta'], 'nombre': folder_info['nombre']}) 
                    curr_id = folder_info['id_carpeta_padre']
                else:
                    # Should not happen if query is correct and IDs are valid, but break defensively
                    print(f"Warning: Could not find ancestor data for ID {curr_id} in path.")
                    break 
            
            current_folder_name = breadcrumbs[-1]['nombre'] # Get name from last breadcrumb item
            current_folder = True # Mark as not root (used only to simplify query below)

        # --- Fetch Contents of the Current Folder ---
        # Query for sub-folders within the current folder_id for this user
        sub_folders = Carpeta.query.filter_by(
            id_usuario=user_id, 
            id_carpeta_padre=folder_id # None for root level
        ).order_by(Carpeta.nombre).all()

        # Query for documents within the current folder_id for this user
        documents_in_folder = Documento.query.filter_by(
            id_usuario=user_id, 
            id_carpeta=folder_id # None for root level
        ).order_by(Documento.titulo_original).all()
        
    except Exception as e:
        db.session.rollback() # Rollback in case the execute caused issues
        print(f"Database query error in list_files: {e}")
        flash('Error retrieving contents from database.', 'danger')
        sub_folders = []
        documents_in_folder = []
        breadcrumbs = []
        current_folder_name = "Error"

    # Render the template, passing the lists and breadcrumbs
    return render_template(
        'file_list.html', 
        folders=sub_folders, 
        documents=documents_in_folder,
        current_folder_id=folder_id,
        current_folder_name=current_folder_name,
        breadcrumbs=breadcrumbs # Pass the breadcrumb list
    )


# --- File Download Route ---
@app.route('/download/<int:doc_id>')
@login_required # Protect the route
def download_file(doc_id):
    # --- Import models needed specifically for this route ---
    from models import Documento # Import here
    # --------------------------------------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    try:
        # 1. Retrieve the document from the database
        document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first()
        if not document:
            flash('File not found or access denied.', 'danger')
            return redirect(url_for('list_files'))  # Or handle differently

        # 2. Get the S3 object key
        s3_key = document.s3_object_key  # Assuming this field contains the S3 key

# 3. Generate a pre-signed URL for the S3 object.
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            # --- CHANGE THIS LINE ---
            Params={'Bucket': app.config['S3_BUCKET'], 'Key': s3_key}, 
            # --- END CHANGE ---
            ExpiresIn=3600  # URL expires in 1 hour
        )

        # 4. Redirect the user to the presigned URL
        return redirect(presigned_url)


    except Exception as e:
        print(f"Error downloading file: {e}")
        flash('Error downloading file.', 'danger')
        return redirect(url_for('list_files'))

    
# --- File Deletion Route ---
@app.route('/delete/<int:doc_id>', methods=['POST']) # Accept only POST requests
@login_required
def delete_file(doc_id):
    # --- Import models needed specifically for this route ---
    from models import Documento 
    # --------------------------------------------------------
    
    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    try:
        # 1. Find the document record, ensuring it belongs to the current user
        document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first()

        if not document:
            flash('File not found or access denied.', 'danger')
            return redirect(url_for('list_files'))

        # 2. Get S3 details BEFORE deleting DB record
        s3_bucket = document.s3_bucket
        s3_key = document.s3_object_key
        original_filename = document.titulo_original # For flash message

        # 3. Delete the object from S3
        if s3_client: # Check if client is initialized
            try:
                print(f"Deleting S3 object: {s3_key} from bucket {s3_bucket}")
                s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                print("S3 object deleted successfully.")
            except Exception as e:
                # Log the error, but often proceed to delete DB record anyway
                # Otherwise, you might have an orphaned S3 file if DB delete succeeds later
                print(f"Error deleting S3 object {s3_key}: {e}")
                flash(f'Could not delete file from S3 storage, but removing database record. Error: {e}', 'warning')
        else:
             flash('S3 client not available. Cannot delete file from storage, but removing database record.', 'warning')

        # 4. Delete the record from the Database
        db.session.delete(document)
        db.session.commit()
        
        flash(f'File "{original_filename}" deleted successfully.', 'success')
        
        # Optional: Log activity
        # log_activity(user_id, 'DELETE_DOC', detalle=f'Deleted file: {original_filename}, S3 key: {s3_key}')

    except Exception as e:
        db.session.rollback() # Roll back DB changes if any error occurred during commit
        print(f"Error deleting file record from database: {e}")
        flash('An error occurred while deleting the file record.', 'danger')

    # Redirect back to the file list regardless of S3 outcome (if DB delete was attempted)
    return redirect(url_for('list_files'))


# --- File Metadata Edit Route ---
@app.route('/edit/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def edit_file(doc_id):
    # --- Import models needed specifically for this route ---
    from models import Documento, Categoria, Carpeta # Import here
    # --------------------------------------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # 1. Fetch the document to edit, ensuring ownership
    # Use first_or_404 to automatically handle not found cases if preferred
    document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first()
    if not document:
        flash('File not found or access denied.', 'danger')
        return redirect(url_for('list_files')) 

    # --- Handle POST Request (Save Changes) ---
    if request.method == 'POST':
        try:
            # Get updated data from the form
            new_title = request.form.get('titulo_nuevo', default=None)
            id_categoria = request.form.get('categoria', default=None, type=int) # Converts to int, None if empty/invalid
            id_carpeta_str = request.form.get('carpeta', default=None)
            descripcion = request.form.get('descripcion', default=None)
            periodo_inicio_str = request.form.get('periodo_inicio', default=None)
            periodo_fin_str = request.form.get('periodo_fin', default=None)
            # Checkbox value: 'favorito' key exists in form only if checked
            favorito = 'favorito' in request.form 

            # Update Folder ID (handle empty string input for root)
            id_carpeta = None
            if id_carpeta_str and id_carpeta_str.isdigit():
                id_carpeta = int(id_carpeta_str)
                # Optional: Validate folder exists and belongs to user here
            elif id_carpeta_str == '': # Explicitly empty means root
                 id_carpeta = None
            else: # Invalid input, keep original folder? Or error? For now, keep original
                id_carpeta = document.id_carpeta # Keep original if input is invalid/missing


            # Update Title only if a new one was provided
            if new_title and new_title.strip():
                 document.titulo_original = secure_filename(new_title.strip()) # Secure the new title


            # Update other fields
            document.id_categoria = id_categoria # Okay to set to None if category cleared
            document.id_carpeta = id_carpeta
            document.descripcion = descripcion if descripcion is not None else document.descripcion # Keep original if None

            # Parse and update dates
            if periodo_inicio_str:
                document.periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
            elif periodo_inicio_str == '': # Allow clearing the date
                 document.periodo_inicio = None
            # else: Keep original date if field wasn't submitted or invalid (depends on desired behavior)

            if periodo_fin_str:
                document.periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()
            elif periodo_fin_str == '': # Allow clearing the date
                 document.periodo_fin = None

            document.favorito = favorito

            # Commit changes to the database
            db.session.commit()
            flash(f'Metadata for "{document.titulo_original}" updated successfully!', 'success')

            # Optional: Log activity
            # log_activity(user_id, 'EDIT_DOC', documento_id=document.id_documento, ...)

            return redirect(url_for('list_files'))

        except Exception as e:
            db.session.rollback() # Roll back DB changes on error
            print(f"Error updating document metadata: {e}")
            flash(f'Error updating metadata: {e}', 'danger')
            # Re-render the edit form with existing data on error
            categories = Categoria.query.order_by(Categoria.nombre).all()
            return render_template('edit_file.html', document=document, categories=categories)


    # --- Handle GET Request (Show Edit Form) ---
    else: # request.method == 'GET'
        # Fetch categories and potentially folders to populate dropdowns
        categories = Categoria.query.order_by(Categoria.nombre).all()
        # folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all() # If needed for dropdown
        return render_template('edit_file.html', document=document, categories=categories)
    
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
        return redirect(url_for('list_files', folder_id=parent_folder_id)) 

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
            
    except Exception as e:
        db.session.rollback()
        print(f"Error creating folder: {e}")
        flash('An error occurred while creating the folder.', 'danger')

    # Redirect back to the folder view where the creation happened
    return redirect(url_for('list_files', folder_id=parent_folder_id))


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
            return redirect(url_for('list_files')) # Redirect to root or previous location?

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
            return redirect(url_for('list_files', folder_id=parent_folder_id)) 
        else:
            # Folder is empty, proceed with deletion
            db.session.delete(folder_to_delete)
            db.session.commit()
            flash(f'Folder "{folder_name}" deleted successfully.', 'success')
            
            # Optional: Log activity
            # log_activity(user_id, 'DELETE_FOLDER', detalle=f'Deleted empty folder: {folder_name} (ID: {folder_id})')

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
        return redirect(url_for('list_files', folder_id=parent_folder_id))

    # Redirect back to the parent folder's view after deletion attempt
    return redirect(url_for('list_files', folder_id=parent_folder_id))


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
             return redirect(url_for('list_files', folder_id=parent_folder_id))

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

                # Optional: Log activity
                # log_activity(user_id, 'RENAME_FOLDER', carpeta_id=folder_id, detalle=f'Renamed folder to: {new_name}')
                
                # Redirect back to the parent folder view
                return redirect(url_for('list_files', folder_id=parent_folder_id))

        except Exception as e:
            db.session.rollback()
            print(f"Error renaming folder: {e}")
            flash('An error occurred while renaming the folder.', 'danger')
            # Re-render form on other errors
            return render_template('rename_folder.html', folder=folder_to_rename)

    # --- Handle GET Request (Show Rename Form) ---
    else: # request.method == 'GET'
        return render_template('rename_folder.html', folder=folder_to_rename)

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