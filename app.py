import os
import boto3 
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import text 

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
db = SQLAlchemy(app) 

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
        # Optional: Test connection - requires ListBuckets permission for the IAM user
        # print("Attempting to list buckets to verify S3 connection...")
        # s3_client.list_buckets() 
        print("Boto3 S3 Client Initialized Successfully.")
    else:
        print("S3 credentials or configuration missing, S3 client not initialized.")
except Exception as e:
    print(f"Error initializing Boto3 S3 Client: {e}")
    s3_client = None # Ensure client is None if initialization failed
# ---------------------------------------------------------------------

# --- 4. Import Models (after db is initialized) ---
#from models import Usuario, Documento, Carpeta, Categoria, ActividadUsuario
#Removed to prevent circular import

# --- Define Routes ---
@app.route('/') 
def hello_world():
    # ... (hello_world code as before) ...
    bucket_name = app.config.get('S3_BUCKET', 'Not Set') 
    try:
        db.session.execute(text('SELECT 1')) 
        db_status = "Database Connection OK"
    except Exception as e:
        db_status = f"Database Connection Error: {e}"
    
    # Check S3 client status
    s3_status = "S3 Client OK" if s3_client else "S3 Client NOT Initialized"
    
    return f'Hello, World! Configured S3 Bucket: {bucket_name}<br>{db_status}<br>{s3_status}'


# --- Error Handlers ---
@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    # ... (error handler code as before) ...
    from flask import flash, redirect, request, url_for 
    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    # Flashing requires SECRET_KEY to be set
    flash(f'File is too large. Maximum allowed size is {max_size_mb:.0f} MB.') 
    return f"File too large (Limit: {max_size_mb:.0f} MB)", 413 

# --- Main entry point ---
if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])