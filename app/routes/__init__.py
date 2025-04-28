from flask import Blueprint
from app.routes.login import login_bp

# Aquí puedes agregar más blueprints si tienes otras rutas
# from app.routes.other_routes import other_bp

def register_routes(app):
    """
    Registra todos los blueprints de rutas en la aplicación Flask.
    """
    app.register_blueprint(login_bp)
    # app.register_blueprint(other_bp)  # Descomenta si tienes más rutas