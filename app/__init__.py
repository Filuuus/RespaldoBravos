from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.models import db
from app.routes.login import login_bp
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    JWTManager(app)

    db.init_app(app)

    # Registrar rutas
    app.register_blueprint(login_bp)

    return app