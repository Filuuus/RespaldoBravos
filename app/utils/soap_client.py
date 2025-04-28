from zeep import Client

class SOAPClient:
    def __init__(self, wsdl_url):
        self.client = Client(wsdl_url)

    def validar_usuario(self, username, password, key):
        return self.client.service.valida(usuario=username, password=password, key=key)

    def obtener_datos_usuario(self, codigo, key):
        return self.client.service.datosUsuario(codigo=codigo, key=key)

    def obtener_tipo_usuario(self, codigo, password, key):
        return self.client.service.esAlumnoProfesor(codigo=codigo, password=password, key=key)