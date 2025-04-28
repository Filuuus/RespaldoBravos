from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models import Usuario, db
from app.utils.soap_client import SOAPClient
from app.config import Config

login_bp = Blueprint('login', __name__)

soap_client = SOAPClient(Config.WSDL_URL)

@login_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    try:
        # Validar usuario
        result = soap_client.validar_usuario(username, password, Config.KEY_VALIDA)
        if result != 'true':
            return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401

        # Buscar usuario en la base de datos
        user = Usuario.query.filter_by(codigo=username).first()

        if not user:
            # Obtener datos del usuario
            datos_result = soap_client.obtener_datos_usuario(username, Config.KEY_DATOS)
            tipo_result = soap_client.obtener_tipo_usuario(username, password, Config.KEY_TIPO)

            nombre = f"{datos_result['nombre']} {datos_result['apPat']} {datos_result['apMat']}"
            correo = datos_result['correo']
            tipo = tipo_result

            # Crear nuevo usuario
            user = Usuario(codigo=username, nombre=nombre, tipo_usuario=tipo, correo=correo)
            db.session.add(user)
            db.session.commit()

        # Generar token JWT
        access_token = create_access_token(identity={'codigo': user.codigo, 'nombre': user.nombre, 'tipo_usuario': user.tipo_usuario})

        return jsonify({'success': True, 'token': access_token})

    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500