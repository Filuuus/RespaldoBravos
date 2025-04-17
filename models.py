# models.py

from datetime import datetime
# Assuming 'db' is the SQLAlchemy instance initialized in your main app file (e.g., app.py)
from app import db 
# Import specific types if needed, or use db.* directly
# from sqlalchemy import Integer, String, Text, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# --- User Model ---
class Usuario(db.Model):
    """Represents a user authenticated via the external school system."""
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True) # Corresponds to SERIAL PRIMARY KEY
    codigo_usuario = db.Column(db.String(20), unique=True, nullable=False)
    nombre_completo = db.Column(db.Text, nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=True)
    plantel = db.Column(db.String(100), nullable=True)
    seccion = db.Column(db.String(100), nullable=True)
    fecha_registro = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now())
    ultimo_login = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships (One-to-Many: One User has Many...)
    # cascade="all, delete-orphan": Deletes related items if user is deleted. Review if this is desired.
    documentos = db.relationship('Documento', backref='usuario', lazy=True, cascade="all, delete-orphan", foreign_keys='Documento.id_usuario')
    carpetas = db.relationship('Carpeta', backref='usuario', lazy=True, cascade="all, delete-orphan", foreign_keys='Carpeta.id_usuario')
    actividades = db.relationship('ActividadUsuario', backref='usuario', lazy=True, cascade="all, delete-orphan", foreign_keys='ActividadUsuario.id_usuario')

    def __repr__(self):
        return f"<Usuario {self.id_usuario} | {self.codigo_usuario}>"

# --- Folder Model ---
class Carpeta(db.Model):
    """Represents a folder in the hierarchy."""
    __tablename__ = 'carpetas'

    id_carpeta = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    id_carpeta_padre = db.Column(db.Integer, db.ForeignKey('carpetas.id_carpeta', ondelete='CASCADE'), nullable=True) # Self-referential FK
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), nullable=False)
    fecha_creacion = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now())
    # Note: fecha_modificacion relies on the DB trigger for updates, default handles creation
    fecha_modificacion = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now(), onupdate=db.func.now()) 

    # Relationships
    # 1. Relationship to parent folder (Many-to-One)
    # remote_side=[id_carpeta] is needed for self-referential relationship
    parent = db.relationship('Carpeta', remote_side=[id_carpeta], backref='children', lazy=True)
    
    # 2. Relationship to documents within this folder (One-to-Many)
    documentos = db.relationship('Documento', backref='carpeta', lazy='dynamic', cascade="all, delete-orphan", foreign_keys='Documento.id_carpeta')
    
    # 3. Relationship to activities related to this folder (One-to-Many)
    actividades = db.relationship('ActividadUsuario', backref='carpeta', lazy=True, cascade="all, delete-orphan", foreign_keys='ActividadUsuario.id_carpeta')

    # Define Unique constraint for name within parent+user
    __table_args__ = (db.UniqueConstraint('id_usuario', 'id_carpeta_padre', 'nombre', name='idx_carpetas_unicas_por_padre'),)


    def __repr__(self):
        return f"<Carpeta {self.id_carpeta} | {self.nombre}>"

# --- Category Model ---
class Categoria(db.Model):
    """Represents a predefined document category."""
    __tablename__ = 'categorias'

    id_categoria = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False)

    # Relationship (One-to-Many: One Category has Many Documents)
    documentos = db.relationship('Documento', backref='categoria', lazy=True, foreign_keys='Documento.id_categoria')

    def __repr__(self):
        return f"<Categoria {self.id_categoria} | {self.nombre}>"

# --- Document Model ---
class Documento(db.Model):
    """Represents a document's metadata."""
    __tablename__ = 'documentos'

    id_documento = db.Column(db.Integer, primary_key=True)
    titulo_original = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    s3_bucket = db.Column(db.String(255), nullable=False)
    s3_object_key = db.Column(db.String(1024), unique=True, nullable=False)
    s3_version_id = db.Column(db.String(1024), nullable=True)
    mime_type = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True) # Remember the < 2.14 GB limit
    fecha_carga = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now())
    # Note: fecha_modificacion relies on the DB trigger for updates
    fecha_modificacion = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now(), onupdate=db.func.now())
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='RESTRICT'), nullable=False) # Matches SQL
    id_carpeta = db.Column(db.Integer, db.ForeignKey('carpetas.id_carpeta', ondelete='SET NULL'), nullable=True) # Matches SQL
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria', ondelete='SET NULL'), nullable=True) # Matches SQL
    periodo_inicio = db.Column(db.Date, nullable=True)
    periodo_fin = db.Column(db.Date, nullable=True)
    favorito = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships (Many-to-One defined via backref from Usuario, Carpeta, Categoria)
    # Relationship to activities related to this document (One-to-Many)
    actividades = db.relationship('ActividadUsuario', backref='documento', lazy=True, cascade="all, delete-orphan", foreign_keys='ActividadUsuario.id_documento')


    def __repr__(self):
        return f"<Documento {self.id_documento} | {self.titulo_original}>"


# --- Activity Log Model ---
class ActividadUsuario(db.Model):
    """Represents a log entry for user activity."""
    __tablename__ = 'actividad_usuario'

    id_actividad = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime(timezone=True), nullable=False, default=db.func.now())
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario', ondelete='SET NULL'), nullable=False) # Matches SQL
    direccion_ip = db.Column(db.String(50), nullable=True)
    tipo_actividad = db.Column(db.String(100), nullable=False)
    id_documento = db.Column(db.Integer, db.ForeignKey('documentos.id_documento', ondelete='SET NULL'), nullable=True) # Matches SQL
    id_carpeta = db.Column(db.Integer, db.ForeignKey('carpetas.id_carpeta', ondelete='SET NULL'), nullable=True) # Matches SQL
    detalle = db.Column(db.Text, nullable=True)

    # Relationships (Many-to-One defined via backref from Usuario, Documento, Carpeta)

    def __repr__(self):
        return f"<Actividad {self.id_actividad} | User {self.id_usuario} | {self.tipo_actividad}>"