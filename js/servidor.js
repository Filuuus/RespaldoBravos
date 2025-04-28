const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const soap = require('strong-soap').soap;
const { Pool } = require('pg');

const app = express();
app.use(cors());
app.use(bodyParser.json());

const WSDL_URL = 'http://ms.mw.siiau.udg.mx/WSValidaUsuarios/ValidaUsuarios?wsdl';
const KEY_VALIDA = 'UdGSIIAUWebServiceValidaUsuario';
const KEY_DATOS = 'UdGSIIAUWebServiceDatosUsuario';
const KEY_TIPO = 'UdGSIIAUWebServiceEsAlumnoProfesor';

// Configuración de PostgreSQL
const pool = new Pool({
    user: 'postgres',
    host: 'fttboxdb.czw4ggskai0p.us-west-1.rds.amazonaws.com',
    database: 'fttboxdb',
    password: 'hanna21-Santy',
    port: 5432,
});

// Ruta de inicio de sesión
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;

    soap.createClient(WSDL_URL, async (err, client) => {
        if (err) return res.status(500).json({ success: false, message: 'Error con el servicio SOAP' });

        client.valida({ usuario: username, password, key: KEY_VALIDA }, async (err, result) => {
            if (err || result.return !== 'true') {
                return res.status(401).json({ success: false, message: 'Credenciales incorrectas' });
            }

            try {
                // Verificamos si ya está registrado
                const existingUser = await pool.query('SELECT * FROM usuarios WHERE codigo = $1', [username]);

                if (existingUser.rows.length === 0) {
                    // Obtener datos del usuario
                    client.datosUsuario({ codigo: username, key: KEY_DATOS }, async (err, datosResult) => {
                        if (err) return res.status(500).json({ success: false, message: 'Error al obtener datos del usuario' });

                        client.esAlumnoProfesor({ codigo: username, password, key: KEY_TIPO }, async (err, tipoResult) => {
                            if (err) return res.status(500).json({ success: false, message: 'Error al verificar tipo de usuario' });

                            const datos = datosResult.return;
                            const tipo = tipoResult.return;

                            const nombre = `${datos.nombre} ${datos.apPat} ${datos.apMat}`;
                            const correo = datos.correo;

                            await pool.query(`
                INSERT INTO usuarios (codigo, nombre, tipo_usuario, correo)
                VALUES ($1, $2, $3, $4)
              `, [username, nombre, tipo, correo]);
                        });
                    });
                }

                // Login exitoso (puedes generar token si lo necesitas)
                res.json({ success: true, token: 'fake-jwt-token' });
            } catch (dbErr) {
                console.error(dbErr);
                res.status(500).json({ success: false, message: 'Error en la base de datos' });
            }
        });
    });
});

// Iniciar servidor
const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Servidor corriendo en http://localhost:${PORT}`);
});
