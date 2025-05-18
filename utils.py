# RespaldoBravos/utils.py
from flask import session, redirect, url_for, flash, request, current_app
from functools import wraps
# Assuming models.py and extensions.py are at the root or accessible
# For log_activity, it needs ActividadUsuario and db
from models import ActividadUsuario 
from extensions import db
import math # Import math for log in format_file_size

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            # Ensure this points to the auth blueprint's login
            return redirect(url_for('auth_bp.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(user_id, activity_type, ip_address=None, document_id=None, folder_id=None, details=None):
    if ip_address is None and request: # request is available in app context
        ip_address = request.remote_addr
    try:
        log_entry = ActividadUsuario(
            id_usuario=user_id,
            tipo_actividad=activity_type,
            direccion_ip=ip_address,
            id_documento=document_id,
            id_carpeta=folder_id,
            detalle=details
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"!!! UTILS ERROR logging activity: {e}")

def format_file_size(size_bytes):
    """Converts bytes to a human-readable string (B, KB, MB, GB, TB)."""
    if size_bytes is None or size_bytes == 0: # Added check for None
        return "0 B"
    
    # Ensure size_bytes is a number, handle potential non-numeric types if necessary
    if not isinstance(size_bytes, (int, float)):
        try:
            size_bytes = float(size_bytes)
        except (ValueError, TypeError):
            return "N/A" # Or some other indicator of invalid input

    size_name = ("B", "KB", "MB", "GB", "TB")
    if size_bytes < 0: # Handle negative sizes if they can occur
        return "Invalid size"

    # Prevent log(0) or log of negative by handling 0 B case above
    i = 0
    if size_bytes > 0: # Only calculate log if size_bytes is positive
        # Check if math.log is available
        if math and hasattr(math, 'log'):
            i = math.floor(math.log(size_bytes, 1024))
            # Ensure i doesn't exceed the bounds of size_name
            if i >= len(size_name):
                i = len(size_name) - 1
        else: # Fallback if math.log is not available for some reason (highly unlikely in standard Python)
            temp_size = size_bytes
            while temp_size >= 1024 and i < len(size_name) - 1:
                temp_size /= 1024.0
                i += 1
    
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"