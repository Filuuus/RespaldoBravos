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
from models import ActividadUsuario
from flask import request
from sqlalchemy import asc, desc, text, or_

from zeep import Client, Settings, Transport # Import Zeep classes
from zeep.exceptions import Fault # Import specific Zeep exception
from models import Usuario # Import User model where needed
from datetime import datetime, timezone # Add timezone here

from flask import current_app
from sqlalchemy import or_

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

app.config['SIIAU_WSDL_URL'] = os.environ.get('SIIAU_WSDL_URL')
app.config['SIIAU_VALIDA_KEY'] = os.environ.get('SIIAU_VALIDA_KEY')

app.config['ITEMS_PER_PAGE'] = 30 

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


# --- Initialize Zeep SOAP Client ---
siiau_client = None
try:
    if app.config['SIIAU_WSDL_URL']:
        # strict=False can help with compatibility with some SOAP services
        settings = Settings(strict=False, xml_huge_tree=True) 
        # transport = Transport(timeout=10) # Optional: set timeout
        siiau_client = Client(app.config['SIIAU_WSDL_URL'], settings=settings) #, transport=transport)
        print("Zeep SIIAU Client Initialized Successfully.")
        # Optional: Check if service/methods expected are available
        # print(siiau_client.service)
    else:
        print("SIIAU WSDL URL missing, Zeep client not initialized.")
except Exception as e:
    print(f"Error initializing Zeep SIIAU Client: {e}")
    siiau_client = None
# ---------------------------------



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
# @app.route('/login') 
# def login():
#     user_id_to_log = 1 # Use the dummy ID
#     session['user_id'] = user_id_to_log 
#     flash('You were logged in (dummy login).', 'success')
#     # Log after setting session
#     log_activity(user_id=user_id_to_log, activity_type='LOGIN_SUCCESS', ip_address=request.remote_addr) 
#     return redirect(request.args.get('next') or url_for('hello_world'))


# --- Real Login Route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect them away from login page
    if 'user_id' in session:
        return redirect(url_for('list_files')) 

    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nip = request.form.get('nip')
        next_url = request.form.get('next') # Get redirect URL if provided

        if not codigo or not nip:
            flash('Please enter both Código and NIP.', 'warning')
            return render_template('login.html')

        # Check if Zeep client is available
        if not siiau_client:
             flash('Authentication service is currently unavailable.', 'danger')
             return render_template('login.html')
        
        # Call the SIIAU valida service
        try:
            print(f"Calling SIIAU valida for user: {codigo}") # Log attempt
            key = app.config.get('SIIAU_VALIDA_KEY')
            if not key:
                 raise ValueError("SIIAU Valida Key not configured in application.")

            # Call the service using parameter names from WSDL/example
            response = siiau_client.service.valida(usuario=codigo, password=nip, key=key) 
            print(f"SIIAU Response: {response}") # Log raw response

            # Process the response
            if response == "0" or not response: # Check for '0' or empty/None response
                 flash('Invalid CODE or NIP.', 'danger')
                #  log_activity(user_id=None, activity_type='LOGIN_FAIL', ip_address=request.remote_addr, details=f"Failed login attempt for codigo: {codigo}")
                 return render_template('login.html')
            else:
                 # Successful authentication - Parse the response string
                 # Expected: "T/E/A,Nombre Completo,Campus,SiglasCarrera/Campus"
                 try:
                     parts = response.split(',', 4) # Split only 3 times to keep name intact
                     if len(parts) < 5: 
                          raise ValueError("Unexpected response format from auth service.")
                     
                     tipo = parts[0].strip()
                     codigo = parts[1].strip()
                     nombre = parts[2].strip()
                     plantel = parts[3].strip()
                     seccion = parts[4].strip() 

                     # Find or Create user in local database
                     user = Usuario.query.filter_by(codigo_usuario=codigo).first()

                     if user:
                         # User exists, update details and last login
                         print(f"Found existing user: {user.id_usuario}")
                         user.nombre_completo = nombre
                         user.tipo_usuario = tipo
                         user.plantel = plantel
                         user.seccion = seccion
                         user.ultimo_login = datetime.now(timezone.utc) # Or db.func.now()
                         user.is_active = True # Ensure user is active on successful login
                     else:
                         # User doesn't exist, create new record
                         print(f"Creating new user for codigo: {codigo}")
                         user = Usuario(
                             codigo_usuario=codigo,
                             nombre_completo=nombre,
                             tipo_usuario=tipo,
                             plantel=plantel,
                             seccion=seccion,
                             ultimo_login=datetime.utcnow() # Or db.func.now()
                             # fecha_registro has default, is_active has default
                         )
                         db.session.add(user)
                     
                     db.session.commit() # Commit update or new user

                     # Store LOCAL user ID in session
                     session['user_id'] = user.id_usuario 
                     session.permanent = True # Make session last longer (configure duration via app.permanent_session_lifetime)
                     
                     flash(f'Welcome back, {user.nombre_completo}!', 'success')
                     log_activity(user_id=user.id_usuario, activity_type='LOGIN_SUCCESS', ip_address=request.remote_addr)
                     
                     # Redirect to the originally requested page or default file list
                     return redirect(next_url or url_for('list_files'))

                 except Exception as e:
                      db.session.rollback() # Rollback DB changes if parsing/saving failed
                      print(f"Error processing successful SIIAU response or saving user: {e}")
                      flash('Login succeeded but failed to process user data.', 'danger')
                      return render_template('login.html')

        # Handle exceptions during the SOAP call (e.g., connection errors, timeouts, SOAP Faults)
        except Fault as fault: # Specific Zeep exception for SOAP faults
             print(f"SIIAU SOAP Fault: {fault}")
             flash(f'Authentication service error: {fault.message}', 'danger')
             log_activity(user_id=None, activity_type='LOGIN_FAIL', ip_address=request.remote_addr, details=f"Failed login attempt for codigo: {codigo} - SOAP Fault: {fault.message}")
             return render_template('login.html')
        except Exception as e: # Catch other potential errors (network, etc.)
             print(f"SIIAU Call Error: {e}")
             flash(f'Error communicating with authentication service: {e}', 'danger')
             log_activity(user_id=None, activity_type='LOGIN_FAIL', ip_address=request.remote_addr, details=f"Failed login attempt for codigo: {codigo} - Connection/Other Error")
             return render_template('login.html')

    # --- Handle GET Request (Show Login Form) ---
    else: # request.method == 'GET'
        # Pass current year to template for optional footer display
        current_year = datetime.now(timezone.utc).year 
        return render_template('login.html', now={'year': current_year})


@app.route('/dev_login')
def dev_login():
    # IMPORTANT: Only allow this route in debug/development mode for security
    if not current_app.debug: # current_app.debug directly uses app.config['DEBUG']
        flash('This login method is only available in development mode.', 'danger')
        return redirect(url_for('login')) # Redirect to normal login

    DEFAULT_USER_CODIGO = "DEV_USER"  # Or any code you prefer
    DEFAULT_USER_NAME = "Developer Teammate"
    DEFAULT_USER_TIPO = "E" # Example: 'E' for Estudiante, adjust as needed
    DEFAULT_USER_PLANTEL = "CUCEI_DEV" # Example
    DEFAULT_USER_SECCION = "DEV_SECTION" # Example

    # Try to find the default user
    dev_user = Usuario.query.filter_by(codigo_usuario=DEFAULT_USER_CODIGO).first()

    if not dev_user:
        # If default user doesn't exist, create them
        print(f"Creating default development user: {DEFAULT_USER_CODIGO}")
        dev_user = Usuario(
            codigo_usuario=DEFAULT_USER_CODIGO,
            nombre_completo=DEFAULT_USER_NAME,
            tipo_usuario=DEFAULT_USER_TIPO,
            plantel=DEFAULT_USER_PLANTEL,
            seccion=DEFAULT_USER_SECCION,
            # fecha_registro will be set by default
            ultimo_login=datetime.now(timezone.utc) # Set last login
        )
        db.session.add(dev_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating dev user: {e}', 'danger')
            return redirect(url_for('login'))
    else:
        # Update last login if user already exists
        dev_user.ultimo_login = datetime.now(timezone.utc)
        dev_user.is_active = True # Ensure user is active
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating dev user login time: {e}', 'danger')
            return redirect(url_for('login'))


    # Log the user in by setting the session
    session['user_id'] = dev_user.id_usuario
    session.permanent = True  # Make session last longer

    flash(f'Successfully logged in as default user: {dev_user.nombre_completo}', 'success')

    # Log this special login activity
    log_activity(
        user_id=dev_user.id_usuario,
        activity_type='DEV_LOGIN_SUCCESS',
        ip_address=request.remote_addr, # request should be available here
        details=f"Logged in via /dev_login route as {DEFAULT_USER_CODIGO}"
    )

    return redirect(url_for('list_files')) # Or your main dashboard/file list route


# --- Update Logout ---
@app.route('/logout')
@login_required # Add decorator to ensure user is logged in before logging out
def logout():
    user_id_to_log = session.get('user_id') 
    session.pop('user_id', None) 
    flash('You have been successfully logged out.', 'info')
    if user_id_to_log: 
         log_activity(user_id=user_id_to_log, activity_type='LOGOUT', ip_address=request.remote_addr)
    return redirect(url_for('login')) 

# @app.route('/logout')
# def logout():
#     user_id_to_log = session.get('user_id') # Get ID *before* popping
#     session.pop('user_id', None) 
#     flash('You were logged out.', 'info')
#     if user_id_to_log: # Only log if a user was actually logged in
#          log_activity(user_id=user_id_to_log, activity_type='LOGOUT', ip_address=request.remote_addr)
#     return redirect(url_for('login'))

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
                return redirect(url_for('upload_route', parent_folder_id=parent_folder_id)) 
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

# --- File Listing Route ---
@app.route('/files', defaults={'folder_id': None}, methods=['GET'])
@app.route('/files/<int:folder_id>', methods=['GET'])
@login_required
def list_files(folder_id):
    # --- Import models needed ---
    from models import Documento, Categoria, Carpeta, Usuario
    from sqlalchemy import asc, desc, text, or_ # Ensure text and or_ are imported
    # ----------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # --- Get Sort and Search Parameters ---
    sort_by = request.args.get('sort_by', 'name')
    sort_dir = request.args.get('sort_dir', 'asc')
    search_term = request.args.get('q', '').strip()

    # --- Determine Sort Columns and Direction ---
    folder_order_by = Carpeta.nombre
    document_order_by = Documento.titulo_original
    # Map sort_by parameter (check previous response for full logic if needed)
    if sort_by == 'name': folder_order_by, document_order_by = Carpeta.nombre, Documento.titulo_original
    elif sort_by == 'date': folder_order_by, document_order_by = Carpeta.fecha_modificacion, Documento.fecha_carga
    elif sort_by == 'size': document_order_by = Documento.file_size # folder order remains default
    # Type sort handled later with join

    # Determine sort direction function
    if sort_dir == 'desc': folder_order_func, document_order_func = desc, desc
    else: sort_dir, folder_order_func, document_order_func = 'asc', asc, asc

    # Initialize lists/variables
    sub_folders = []
    documents_in_folder = []
    current_folder_name = "My Files (Root)"
    breadcrumbs = []

    try:
        # --- Fetch Current Folder and Ancestors (Breadcrumbs) ---
        # This whole block needs to be present if folder_id is not None
        if folder_id:
            sql_query = text("""
                WITH RECURSIVE folder_path AS (
                    SELECT id_carpeta, nombre, id_carpeta_padre
                    FROM carpetas WHERE id_carpeta = :current_folder_id AND id_usuario = :user_id
                    UNION ALL
                    SELECT c.id_carpeta, c.nombre, c.id_carpeta_padre
                    FROM carpetas c JOIN folder_path fp ON c.id_carpeta = fp.id_carpeta_padre
                    WHERE c.id_usuario = :user_id
                )
                SELECT id_carpeta, nombre, id_carpeta_padre FROM folder_path;
            """)
            result = db.session.execute(sql_query, {'current_folder_id': folder_id, 'user_id': user_id})
            
            try:
                 all_ancestors = [dict(row) for row in result.mappings()]
            except Exception as mapping_e:
                 print(f"Warning: Error converting breadcrumb query result: {mapping_e}")
                 all_ancestors = []

            path_data = {row['id_carpeta']: row for row in all_ancestors}

            if folder_id not in path_data:
                 flash("Folder not found or access denied.", "warning")
                 return redirect(url_for('list_files', folder_id=None))

            # Reconstruct path from root to current
            curr_id = folder_id
            visited = set()
            while curr_id is not None:
                if curr_id in visited or len(visited) > 20: # Safety limit
                    print(f"Warning: Breadcrumb cycle detected or limit reached at {curr_id}")
                    breadcrumbs = [] ; break
                visited.add(curr_id)
                folder_info = path_data.get(curr_id)
                if folder_info:
                    breadcrumbs.insert(0, {'id': folder_info['id_carpeta'], 'nombre': folder_info['nombre']})
                    curr_id = folder_info['id_carpeta_padre']
                else:
                    if curr_id in path_data: pass # Reached root successfully
                    else: print(f"Warning: Could not find ancestor data for ID {curr_id} in path_data.")
                    break
            
            if breadcrumbs: current_folder_name = breadcrumbs[-1]['nombre']
            else: current_folder_name = "Error Loading Name"
        # --- End of Breadcrumb Logic ---

        # --- Fetch Contents (Apply Search Filter first) ---
        # Base Queries
        folder_query = Carpeta.query.filter_by(id_usuario=user_id, id_carpeta_padre=folder_id)
        doc_query = Documento.query.filter_by(id_usuario=user_id, id_carpeta=folder_id)

        # Apply Search Filter IF search_term exists
        if search_term:
            search_like = f"%{search_term}%"
            folder_query = folder_query.filter(Carpeta.nombre.ilike(search_like))
            doc_query = doc_query.filter(
                or_(
                    Documento.titulo_original.ilike(search_like),
                    Documento.descripcion.ilike(search_like)
                )
            )

        # --- Apply Sorting ---
        sub_folders = folder_query.order_by(folder_order_func(folder_order_by)).all()

        if sort_by == 'type':
             doc_query = doc_query.outerjoin(Categoria, Documento.id_categoria == Categoria.id_categoria)\
                                  .order_by(document_order_func(Categoria.nombre), asc(Documento.titulo_original))
        else:
             doc_query = doc_query.order_by(document_order_func(document_order_by))

        documents_in_folder = doc_query.all()

    except Exception as e:
        db.session.rollback()
        print(f"Database query error in list_files: {e}")
        flash('Error retrieving contents from database.', 'danger')
        sub_folders, documents_in_folder, breadcrumbs = [], [], []
        current_folder_name = "Error"

    # Render the template
    return render_template(
        # 'file_list.html',
        'drive_home.html',
        folders=sub_folders,
        documents=documents_in_folder,
        current_folder_id=folder_id,
        current_folder_name=current_folder_name,
        breadcrumbs=breadcrumbs,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search_term=search_term
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
            Params={'Bucket': app.config['S3_BUCKET'], 'Key': s3_key}, 
            ExpiresIn=3600  # URL expires in 1 hour
        )

        # --- Add Log Call ---
        log_activity(
            user_id=user_id, 
            activity_type='DOWNLOAD_DOC_LINK', # Log link generation, not actual download
            document_id=doc_id,
            ip_address=request.remote_addr,
            details=f'Generated download link for: {document.titulo_original}'
        )
        # --------------------

        # 4. Redirect the user to the presigned URL
        return redirect(presigned_url)


    except Exception as e:
        print(f"Error downloading file: {e}")
        flash('Error downloading file.', 'danger')
        return redirect(url_for('list_files'))


# --- Activity Logging Helper Function ---
def log_activity(user_id, activity_type, ip_address=None, document_id=None, folder_id=None, details=None):
    """Logs an activity to the database."""
    from extensions import db 
    
    # Get IP address from request if not provided
    if ip_address is None and request:
        ip_address = request.remote_addr

    try:
        log_entry = ActividadUsuario(
            id_usuario=user_id,
            tipo_actividad=activity_type,
            direccion_ip=ip_address,
            id_documento=document_id,
            id_carpeta=folder_id,
            detalle=details
            # 'fecha' column has a default value in the database/model
        )
        db.session.add(log_entry)
        db.session.commit()
        print(f"Activity Logged: User {user_id} - {activity_type}") # Optional console log
    except Exception as e:
        db.session.rollback()
        # Log the error to the console or a file, but don't let logging failure stop the main action
        print(f"!!! ERROR logging activity: {e}")
        print(f"!!! Original log data: User={user_id}, Type={activity_type}, IP={ip_address}, Doc={document_id}, Folder={folder_id}, Details={details}")

# ---------------------------------------



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

        # --- Log Call ---
        log_activity(
            user_id=user_id, 
            activity_type='DELETE_DOC', 
            document_id=None, # Log the ID that was deleted
            ip_address=request.remote_addr,
            details=f"Deleted file: {original_filename} (S3 Key: {s3_key})"
        )
        # --------------------

        # 4. Delete the record from the Database
        db.session.delete(document)
        db.session.commit()
        
        flash(f'File "{original_filename}" deleted successfully.', 'success')
        

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
    # Import all needed models at the start of the function
    from models import Documento, Categoria, Carpeta 
    # --------------------------------------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # 1. Fetch the document to edit, ensuring ownership
    # Using first() and checking is fine, first_or_404() is an alternative
    document = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first() 
    if not document:
        flash('File not found or access denied.', 'danger')
        return redirect(url_for('list_files')) 

    # Store parent ID for redirection after POST
    parent_folder_id = document.id_carpeta 

    # --- Handle POST Request (Save Changes) ---
    if request.method == 'POST':
        try:
            # Get updated data from the form
            new_title = request.form.get('titulo_nuevo', default=None)
            # Handle category - ensure None is stored if "" is submitted
            id_categoria_str = request.form.get('categoria', default='')
            id_categoria = int(id_categoria_str) if id_categoria_str.isdigit() else None
            
            # --- Correctly process folder ID from dropdown ---
            id_carpeta_str = request.form.get('carpeta', default='') # Get submitted value ("" for root)
            if id_carpeta_str == '':
                id_carpeta = None # Root folder selected
            elif id_carpeta_str.isdigit():
                id_carpeta_to_check = int(id_carpeta_str)
                # Validate folder exists and belongs to user
                folder_check = Carpeta.query.filter_by(id_carpeta=id_carpeta_to_check, id_usuario=user_id).first()
                if folder_check:
                    id_carpeta = id_carpeta_to_check # Use the valid ID
                else:
                    flash("Invalid folder selected. Keeping original.", "warning")
                    id_carpeta = document.id_carpeta # Keep original if invalid selection
            else:
                # Invalid non-digit value submitted? Keep original
                flash("Invalid folder value submitted. Keeping original.", "warning")
                id_carpeta = document.id_carpeta 
            # --------------------------------------------------
            
            descripcion = request.form.get('descripcion', default=None)
            periodo_inicio_str = request.form.get('periodo_inicio', default=None)
            periodo_fin_str = request.form.get('periodo_fin', default=None)
            favorito = 'favorito' in request.form 

            # Update Title only if a new one was provided and non-empty
            if new_title and new_title.strip():
                 # Consider adding validation for title length if needed
                 document.titulo_original = secure_filename(new_title.strip()) 

            # Update other fields
            document.id_categoria = id_categoria 
            document.id_carpeta = id_carpeta # Use the validated ID from dropdown logic
            document.descripcion = descripcion # Allow setting description to empty string if desired

            # Parse and update dates (Allow clearing dates)
            if periodo_inicio_str is not None: # Check if field was submitted
                 if periodo_inicio_str == '':
                     document.periodo_inicio = None
                 else:
                     try:
                         document.periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
                     except ValueError:
                          flash('Invalid start date format ignored. Use YYYY-MM-DD.', 'warning')
            
            if periodo_fin_str is not None: # Check if field was submitted
                 if periodo_fin_str == '':
                      document.periodo_fin = None
                 else:
                      try:
                          document.periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()
                      except ValueError:
                           flash('Invalid end date format ignored. Use YYYY-MM-DD.', 'warning')

            document.favorito = favorito

            # Commit changes to the database
            db.session.commit()
            flash(f'Metadata for "{document.titulo_original}" updated successfully!', 'success')

            # Log activity
            log_activity(
                user_id=user_id, 
                activity_type='EDIT_DOC_METADATA', 
                document_id=doc_id,
                ip_address=request.remote_addr,
                details=f"Edited metadata for: {document.titulo_original}"
            )
            
            # Redirect back to the PARENT folder of the document
            return redirect(url_for('list_files', folder_id=document.id_carpeta))

        except Exception as e:
            db.session.rollback() 
            print(f"Error updating document metadata: {e}")
            flash(f'Error updating metadata: {e}', 'danger')
            # Re-fetch data needed for the form in case of error during POST
            categories = Categoria.query.order_by(Categoria.nombre).all()
            user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
            # Re-render the edit form with existing data and error message
            return render_template('edit_file.html', 
                                   document=document, # Pass the original document back
                                   categories=categories, 
                                   folders=user_folders)


    # --- Handle GET Request (Show Edit Form) ---
    else: # request.method == 'GET'
         # Fetch categories and folders needed for the form dropdowns
         categories = Categoria.query.order_by(Categoria.nombre).all()
         user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
         
         # --- CORRECTED RENDER_TEMPLATE CALL ---
         # Pass the 'document' object fetched at the start of the function
         return render_template('edit_file.html', 
                                document=document, 
                                categories=categories, 
                                folders=user_folders)
         # --------------------------------------

    
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
# ----------------------------------------------------------------------------

# --- Move File Route ---
@app.route('/move_file/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def move_file(doc_id):
    # --- Import models needed ---
    from models import Documento, Carpeta
    # --------------------------

    user_id = session.get('user_id')
    if not user_id:
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # Fetch the document to move, ensuring ownership
    doc_to_move = Documento.query.filter_by(id_documento=doc_id, id_usuario=user_id).first_or_404()

    if request.method == 'POST':
        dest_folder_id_str = request.form.get('destination_folder', '') # "" for root

        # Determine target folder ID (None for root)
        destination_folder_id = None
        destination_folder = None # To store folder object if not root
        if dest_folder_id_str.isdigit():
            destination_folder_id = int(dest_folder_id_str)
            # Validate destination folder exists and belongs to user
            destination_folder = Carpeta.query.filter_by(id_carpeta=destination_folder_id, id_usuario=user_id).first()
            if not destination_folder:
                 flash("Invalid destination folder selected.", "danger")
                 # Re-render move form with current data
                 user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
                 return render_template('move_file.html', document=doc_to_move, folders=user_folders)
        elif dest_folder_id_str != '':
             # Submitted value wasn't empty string or digits - invalid selection
             flash("Invalid destination folder value.", "danger")
             user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
             return render_template('move_file.html', document=doc_to_move, folders=user_folders)

        # Check if trying to move to the same folder
        if doc_to_move.id_carpeta == destination_folder_id:
             flash('File is already in the destination folder.', 'info')
             return redirect(url_for('list_files', folder_id=destination_folder_id))

        # --- Validation: Check for name conflict in destination ---
        conflicting_file = Documento.query.filter(
            Documento.id_usuario == user_id,
            Documento.id_carpeta == destination_folder_id, # Check destination
            Documento.titulo_original == doc_to_move.titulo_original,
            Documento.id_documento != doc_id # Exclude the file itself
        ).first()

        if conflicting_file:
            dest_name = destination_folder.nombre if destination_folder else "Root Folder"
            flash(f'A file named "{doc_to_move.titulo_original}" already exists in "{dest_name}". Cannot move file.', 'danger')
            user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
            return render_template('move_file.html', document=doc_to_move, folders=user_folders)
        # --- End Name Conflict Check ---

        # Proceed with the move
        try:
            original_parent_id = doc_to_move.id_carpeta # For logging/redirect if needed
            doc_to_move.id_carpeta = destination_folder_id # Update the foreign key
            db.session.commit()
            flash(f'File "{doc_to_move.titulo_original}" moved successfully.', 'success')

            # Log activity
            log_activity(
                user_id=user_id, 
                activity_type='MOVE_DOC', 
                document_id=doc_id,
                folder_id=original_parent_id, # Log original location?
                ip_address=request.remote_addr,
                details=f"Moved '{doc_to_move.titulo_original}' to Folder ID: {destination_folder_id}"
            )
            
            # Redirect to the destination folder
            return redirect(url_for('list_files', folder_id=destination_folder_id))

        except Exception as e:
            db.session.rollback()
            print(f"Error moving file: {e}")
            flash('An error occurred while moving the file.', 'danger')
            user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
            return render_template('move_file.html', document=doc_to_move, folders=user_folders)

    # --- Handle GET Request (Show Move Form) ---
    else: # request.method == 'GET'
        # Fetch all folders for this user to populate the dropdown
        user_folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        return render_template('move_file.html', document=doc_to_move, folders=user_folders)
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
            return redirect(url_for('list_files', folder_id=original_parent_id))

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
            return redirect(url_for('list_files', folder_id=destination_folder_id))

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


# --- Activity Log Viewing Route ---
@app.route('/activity_log')
@login_required
def activity_log():
    # --- Import model needed ---
    from models import ActividadUsuario
    # --------------------------
    
    user_id = session.get('user_id')
    if not user_id: # Should be caught by decorator, but defensive check
        flash('User session error.', 'danger')
        return redirect(url_for('login'))

    # Get page number from query args, default to 1, type integer
    page = request.args.get('page', 1, type=int)
    
    try:
        # Query logs for the current user, ordered by date descending
        # Use paginate instead of .all()
        log_pagination = ActividadUsuario.query.filter_by(id_usuario=user_id)\
            .order_by(ActividadUsuario.fecha.desc())\
            .paginate(
                page=page, 
                per_page=app.config['ITEMS_PER_PAGE'], 
                error_out=False # If page out of range, show empty list instead of 404
            )
            
    except Exception as e:
        db.session.rollback() # Good practice in case of query issues
        print(f"Database query error in activity_log: {e}")
        flash('Error retrieving activity log.', 'danger')
        log_pagination = None # Set to None on error

    # Pass the pagination object to the template
    return render_template('activity_log.html', log_pagination=log_pagination)

# --- Global search Route ---

@app.route('/search', methods=['GET'])
@login_required

def global_search_route():
    from models import Documento, Carpeta, Usuario
    user_id = session.get('user_id')
    search_term = request.args.get('q_global', '').strip() 

    found_documents = []
    found_folders = []

    if search_term:
        search_like = f"%{search_term}%"

        # Query documents across all user's folders
        found_documents = Documento.query.filter(
            Documento.id_usuario == user_id,
            or_(
                Documento.titulo_original.ilike(search_like),
                Documento.descripcion.ilike(search_like)
                # Add other fields to search in documents if desired
            )
        ).all()

        # Query folders across all user's folders (root and sub-folders)
        found_folders = Carpeta.query.filter(
            Carpeta.id_usuario == user_id,
            Carpeta.nombre.ilike(search_like)
        ).all()

        log_activity(
            user_id=user_id,
            activity_type='GLOBAL_SEARCH',
            ip_address=request.remote_addr,
            details=f"Searched for: '{search_term}'. Found {len(found_documents)} docs, {len(found_folders)} folders."
        )

    
    return render_template(
        'search_results.html',
        search_term=search_term,
        documents=found_documents,
        folders=found_folders,
        current_page='search_results' 
    )

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

    