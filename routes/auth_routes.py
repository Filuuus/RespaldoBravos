# RespaldoBravos/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime, timezone
# Assuming your models are in a top-level 'models.py' and db in 'extensions.py'
from models import Usuario
from extensions import db

# If log_activity is a shared utility, import it from its location (e.g., from ..utils import log_activity)
# For now, defining a placeholder or assuming it's globally available via app context if registered.
# A better practice is to import it from a utils module.
def log_activity(user_id, activity_type, ip_address=None, details=None, **kwargs):
    # This is a placeholder. Replace with your actual log_activity import or implementation.
    # If log_activity itself uses 'request', it should be fine as 'request' is context-local.
    print(f"Auth_BP LOG: User {user_id}, Type: {activity_type}, IP: {ip_address}, Details: {details}")
    # To call the main app's log_activity if it's attached to current_app:
    # if hasattr(current_app, 'log_activity_func'):
    #     current_app.log_activity_func(user_id=user_id, ...) # Example
    # Or, better, from ..app import log_activity (if app.py is importable and log_activity is defined there)

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Access siiau_client from current_app where it was attached
    local_siiau_client = current_app.siiau_client

    if 'user_id' in session:
        # Assuming home_dashboard is an app-level route or in a different blueprint
        return redirect(url_for('home_dashboard')) 

    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nip = request.form.get('nip')
        next_url = request.form.get('next')

        if not codigo or not nip:
            flash('Please enter both Código and NIP.', 'warning')
            return render_template('login.html')

        if not local_siiau_client: # Check the client obtained from current_app
             flash('Authentication service is currently unavailable.', 'danger')
             return render_template('login.html')
        
        try:
            key = current_app.config.get('SIIAU_VALIDA_KEY')
            if not key:
                 raise ValueError("SIIAU Valida Key not configured.")

            # Use local_siiau_client obtained from current_app
            response_siiau = local_siiau_client.service.valida(usuario=codigo, password=nip, key=key)
            
            if response_siiau == "0" or not response_siiau:
                 flash('Invalid CODE or NIP.', 'danger')
                 # Call your actual log_activity function here
                 log_activity(user_id=None, activity_type='LOGIN_FAIL', ip_address=request.remote_addr, details=f"Failed login for codigo: {codigo}")
                 return render_template('login.html')
            else:
                 try:
                     parts = response_siiau.split(',', 4)
                     if len(parts) < 5:
                          raise ValueError("Unexpected response format from auth service.")
                     
                     tipo, codigo_resp, nombre, plantel, seccion = [p.strip() for p in parts]

                     user = Usuario.query.filter_by(codigo_usuario=codigo_resp).first()
                     if user:
                         user.nombre_completo = nombre
                         user.tipo_usuario = tipo
                         user.plantel = plantel
                         user.seccion = seccion
                         user.ultimo_login = datetime.now(timezone.utc)
                         user.is_active = True
                     else:
                         user = Usuario(
                             codigo_usuario=codigo_resp, nombre_completo=nombre, tipo_usuario=tipo,
                             plantel=plantel, seccion=seccion, ultimo_login=datetime.now(timezone.utc)
                         )
                         db.session.add(user)
                     db.session.commit()

                     session['user_id'] = user.id_usuario
                     session.permanent = True
                     
                     flash(f'Welcome back, {user.nombre_completo}!', 'success')
                     log_activity(user_id=user.id_usuario, activity_type='LOGIN_SUCCESS', ip_address=request.remote_addr)
                     # Assuming list_files is an app-level route or in a different blueprint
                     return redirect(next_url or url_for('list_files')) 

                 except Exception as e:
                      db.session.rollback()
                      print(f"Error processing SIIAU response or saving user: {e}")
                      flash('Login succeeded but failed to process user data.', 'danger')
                      return render_template('login.html')

        except Exception as e: # Catch Zeep Faults and other errors
             print(f"SIIAU Call Error: {e}")
             flash(f'Error communicating with authentication service: {str(e)}', 'danger')
             log_activity(user_id=None, activity_type='LOGIN_FAIL', ip_address=request.remote_addr, details=f"SIIAU call error for {codigo}")
             return render_template('login.html')
    else: # GET request
        return render_template('login.html', now={'year': datetime.now(timezone.utc).year})


@auth_bp.route('/dev_login')
def dev_login():
    if not current_app.debug:
        flash('This login method is only available in development mode.', 'danger')
        return redirect(url_for('.login')) 

    DEFAULT_USER_CODIGO = "DEV_USER"
    DEFAULT_USER_NAME = "Developer Teammate"
    dev_user = Usuario.query.filter_by(codigo_usuario=DEFAULT_USER_CODIGO).first()
    if not dev_user:
        dev_user = Usuario(codigo_usuario=DEFAULT_USER_CODIGO, nombre_completo=DEFAULT_USER_NAME, ultimo_login=datetime.now(timezone.utc))
        db.session.add(dev_user)
    else:
        dev_user.ultimo_login = datetime.now(timezone.utc)
        dev_user.is_active = True
    db.session.commit()
    session['user_id'] = dev_user.id_usuario
    session.permanent = True
    flash(f'Successfully logged in as default user: {dev_user.nombre_completo}', 'success')
    log_activity(user_id=dev_user.id_usuario, activity_type='DEV_LOGIN_SUCCESS', ip_address=request.remote_addr)
    return redirect(url_for('list_files')) # Assuming list_files is app-level or in another blueprint


@auth_bp.route('/logout')
# @login_required # If login_required is defined in app.py, it needs to be imported or passed
def logout():
    # Simple check for session before trying to log activity
    user_id_to_log = session.get('user_id')
    if not user_id_to_log: # If no user is logged in, just redirect
        return redirect(url_for('.login'))

    session.pop('user_id', None)
    flash('You have been successfully logged out.', 'info')
    if user_id_to_log: # This will now always be true if we passed the above check
         log_activity(user_id=user_id_to_log, activity_type='LOGOUT', ip_address=request.remote_addr)
    return redirect(url_for('.login'))