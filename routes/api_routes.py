from flask import Blueprint, jsonify, session
from models import Categoria, Carpeta, Usuario # Import necessary models
from utils import login_required # Import from your utils.py

api_bp = Blueprint('api_bp', __name__, url_prefix='/api')

@api_bp.route('/get_categories')
def get_categories_api():
    try:
        categories = Categoria.query.order_by(Categoria.nombre).all()    
        return jsonify([{'id': cat.id_categoria, 'name': cat.nombre} for cat in categories])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/get_user_folders')
@login_required
def get_user_folders_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    try:
        folders = Carpeta.query.filter_by(id_usuario=user_id).order_by(Carpeta.nombre).all()
        return jsonify([{'id': f.id_carpeta, 'name': f.nombre} for f in folders])
    except Exception as e:
        return jsonify({'error': str(e)}), 500