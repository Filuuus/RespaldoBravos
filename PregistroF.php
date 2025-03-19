<?php
// Activar reporte de errores
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// Configuración de la conexión a la base de datos
$servername = "localhost";
$username = "root";
$password = "";
$dbname = "db_profesores_universitarios";

$conn = new mysqli($servername, $username, $password, $dbname);

// Verificar conexión
if ($conn->connect_error) {
    die("Error de conexión: " . $conn->connect_error);
}

echo "Conexión a la base de datos establecida correctamente.<br>";

// Verificar si el formulario ha sido enviado
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    echo "Formulario recibido. Procesando datos...<br>";
    
    // Recoger y limpiar datos del formulario
    $nombre = isset($_POST['nombre']) ? $conn->real_escape_string($_POST['nombre']) : '';
    $apellidos = isset($_POST['apellidos']) ? $conn->real_escape_string($_POST['apellidos']) : '';
    $email = isset($_POST['email']) ? $conn->real_escape_string($_POST['email']) : '';
    $password = isset($_POST['password']) ? $_POST['password'] : '';
    
    // Verificar si los datos llegaron correctamente
    echo "Datos recibidos: Nombre=$nombre, Apellidos=$apellidos, Email=$email, Password=" . (!empty($password) ? "Sí se recibió" : "NO se recibió") . "<br>";
    
    // Validar datos
    if (empty($nombre) || empty($apellidos) || empty($email) || empty($password)) {
        echo "Error: Todos los campos son obligatorios.";
        exit;
    }
    
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo "Error: Formato de email inválido.";
        exit;
    }
    
    // Verificar si el email ya existe
    $check_email = "SELECT id_usuario FROM usuarios WHERE email = ?";
    $stmt = $conn->prepare($check_email);
    if (!$stmt) {
        echo "Error en la preparación de la consulta: " . $conn->error;
        exit;
    }
    
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result->num_rows > 0) {
        echo "Error: Este email ya está registrado.";
        exit;
    }
    
    $stmt->close();
    
    // Insertar nuevo usuario (sin encriptar la contraseña)
    $sql = "INSERT INTO usuarios (nombre, apellidos, email, password, rol, fecha_registro) 
            VALUES (?, ?, ?, ?, 'profesor', NOW())";
    
    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        echo "Error en la preparación de la consulta de inserción: " . $conn->error;
        exit;
    }
    
    $rol = 'profesor';
    $stmt->bind_param("ssss", $nombre, $apellidos, $email, $password);
    
    if ($stmt->execute()) {
        echo "Registro exitoso. Usuario añadido a la base de datos.<br>";
        
        // Mostrar los usuarios registrados
        echo "<h2>Usuarios registrados:</h2>";
        $query = "SELECT id_usuario, nombre, apellidos, email, password, rol, fecha_registro FROM usuarios";
        $result = $conn->query($query);
        
        if ($result->num_rows > 0) {
            echo "<table border='1'>";
            echo "<tr><th>ID</th><th>Nombre</th><th>Apellidos</th><th>Email</th><th>Password</th><th>Rol</th><th>Fecha Registro</th></tr>";
            
            while ($row = $result->fetch_assoc()) {
                echo "<tr>";
                echo "<td>" . $row['id_usuario'] . "</td>";
                echo "<td>" . $row['nombre'] . "</td>";
                echo "<td>" . $row['apellidos'] . "</td>";
                echo "<td>" . $row['email'] . "</td>";
                echo "<td>" . $row['password'] . "</td>";
                echo "<td>" . $row['rol'] . "</td>";
                echo "<td>" . $row['fecha_registro'] . "</td>";
                echo "</tr>";
            }
            
            echo "</table>";
        } else {
            echo "No hay usuarios registrados.";
        }
        
        // Comentamos la redirección para ver los resultados
        // header("Location: login.php?registro=exitoso");
        // exit;
    } else {
        echo "Error al registrar: " . $stmt->error;
    }
    
    $stmt->close();
} else {
    echo "No se ha recibido ningún formulario. Método actual: " . $_SERVER["REQUEST_METHOD"];
}

$conn->close();
?>
