import boto3 
import math
import os
from dotenv import load_dotenv
from extensions import db 
from flask import Flask
from flask_migrate import Migrate
from werkzeug.exceptions import RequestEntityTooLarge
from zeep import Client, Settings

from routes.api_routes import api_bp
from routes.auth_routes import auth_bp
from routes.document_actions_routes import doc_actions_bp
from routes.folder_actions_routes import folder_actions_bp
from routes.main_routes import main_bp
from routes.cv_routes import cv_bp

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

app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(doc_actions_bp)
app.register_blueprint(folder_actions_bp)
app.register_blueprint(main_bp)
app.register_blueprint(cv_bp)

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
    from flask import flash
    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    flash(f'File is too large. Maximum allowed size is {max_size_mb:.0f} MB.') 
    return f"File too large (Limit: {max_size_mb:.0f} MB)", 413 

# --- Main entry point ---
if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])