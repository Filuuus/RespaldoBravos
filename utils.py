# RespaldoBravos/utils.py
from flask import session, redirect, url_for, flash, request, current_app
from functools import wraps
from models import ActividadUsuario 
from extensions import db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
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
        # print(f"UTILS LOG: User {user_id}, Type: {activity_type}, IP: {ip_address}, Details: {details}")
    except Exception as e:
        db.session.rollback()
        print(f"!!! UTILS ERROR logging activity: {e}")