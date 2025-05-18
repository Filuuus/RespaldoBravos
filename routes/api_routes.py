# RespaldoBravos/routes/api_routes.py
from flask import Blueprint, jsonify, session, current_app
from models import Categoria, Carpeta, Usuario, Documento # Import necessary models
from utils import login_required, format_file_size # Changed to format_file_size_simple
from sqlalchemy import func as sql_func
from extensions import db

api_bp = Blueprint('api_bp', __name__, url_prefix='/api')

@api_bp.route('/get_categories')
@login_required 
def get_categories_api():
    try:
        categories = Categoria.query.order_by(Categoria.nombre).all()    
        return jsonify([{'id': cat.id_categoria, 'name': cat.nombre} for cat in categories])
    except Exception as e:
        current_app.logger.error(f"Error in /api/get_categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/get_user_folders')
@login_required
def get_user_folders_api():
    user_id = session.get('user_id')

    try:
        folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        return jsonify([{'id': f.id_carpeta, 'name': f.nombre} for f in folders])
    except Exception as e:
        current_app.logger.error(f"Error in /api/get_user_folders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/get_user_storage_info')
@login_required
def get_user_storage_info_api():
    user_id = session.get('user_id')

    try:
        # Calculate total size of documents for the user
        total_size_bytes_value = db.session.query(
            sql_func.sum(Documento.file_size)
        ).filter(
            Documento.id_usuario == user_id
        ).scalar() # Use .scalar() to get the single value from the sum

        total_size_bytes = total_size_bytes_value if total_size_bytes_value is not None else 0
        
        # Use the formatting function imported from utils.py
        formatted_size = format_file_size(total_size_bytes)
        
        return jsonify({
            'success': True, 
            'storage_used_bytes': total_size_bytes,
            'storage_used_formatted': formatted_size 
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching user storage info: {str(e)}")
        return jsonify({'success': False, 'error': 'Could not retrieve storage information.'}), 500
