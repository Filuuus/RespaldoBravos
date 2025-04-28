from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:hanna21-Santy@fttboxdb.czw4ggskai0p.us-west-1.rds.amazonaws.com/fttboxdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'super-secret-key'  # Cambia esto por una llave más segura
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    WSDL_URL = 'http://ms.mw.siiau.udg.mx/WSValidaUsuarios/ValidaUsuarios?wsdl'
    KEY_VALIDA = 'UdGSIIAUWebServiceValidaUsuario'
    KEY_DATOS = 'UdGSIIAUWebServiceDatosUsuario'
    KEY_TIPO = 'UdGSIIAUWebServiceEsAlumnoProfesor'