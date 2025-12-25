-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Servidor: db:3306
-- Tiempo de generación: 25-12-2025 a las 22:27:40
-- Versión del servidor: 10.11.15-MariaDB-ubu2204
-- Versión de PHP: 8.3.29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `cole_db`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `contraseña_imagenes_estudiante`
--

CREATE TABLE `contraseña_imagenes_estudiante` (
  `id` int(11) NOT NULL,
  `id_estudiante` int(11) NOT NULL,
  `url_imagen` varchar(150) NOT NULL,
  `codigo` varchar(155) NOT NULL,
  `es_contraseña` tinyint(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estudiantes`
--

CREATE TABLE `estudiantes` (
  `username` varchar(30) NOT NULL,
  `contraseña` varchar(255) NOT NULL,
  `foto` varchar(150) DEFAULT 'porDefecto.png',
  `tipoContraseña` enum('alfanumerica','pin','imagenes') DEFAULT 'alfanumerica',
  `accesibilidad` set('texto','video','imagenes','pictogramas','audio') DEFAULT 'texto',
  `preferenciasVisualizacion` enum('diarias','semanales') DEFAULT 'diarias',
  `asistenteVoz` tinyint(1) DEFAULT 0,
  `id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `estudiantes`
--

INSERT INTO `estudiantes` (`username`, `contraseña`, `foto`, `tipoContraseña`, `accesibilidad`, `preferenciasVisualizacion`, `asistenteVoz`, `id`) VALUES
('Carlos', 'pbkdf2:sha256:1000000$R5vKi7R8zJOHt38i$496861c5709bac3492bc006e05aa2f03634377d5fadf5f189be1737caee9aaca', 'porDefecto.png', 'alfanumerica', 'texto', 'diarias', 1, 1),
('Luis', 'pbkdf2:sha256:1000000$BtNhkhgfpd2MDPWX$eac7041660f19910af6730cbdd4828edff3d939e32ba0786717897c055393b17', 'porDefecto.png', 'alfanumerica', 'texto', 'diarias', 0, 2),
('Antonio', 'pbkdf2:sha256:1000000$KyjIanmvpox4Af5c$82ff888bd46c034efd9839d409a30e845f1ad72131d8dab1aa0d9c74634509bf', 'porDefecto.png', 'alfanumerica', '', 'diarias', 0, 12);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `profesores`
--

CREATE TABLE `profesores` (
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `tipo` enum('admin','profesor') NOT NULL DEFAULT 'profesor',
  `foto` varchar(250) DEFAULT 'porDefecto.png'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `profesores`
--

INSERT INTO `profesores` (`username`, `password`, `tipo`, `foto`) VALUES
('test_user', 'pbkdf2:sha256:1000000$lJiv7E3RXTDyMdsE$e3b4967d9dd5334e7711fd3a66c20fb7259dd03a292fd1a54fae228cd404339a', 'admin', 'porDefecto.png');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `contraseña_imagenes_estudiante`
--
ALTER TABLE `contraseña_imagenes_estudiante`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_estudiantes` (`id_estudiante`);

--
-- Indices de la tabla `estudiantes`
--
ALTER TABLE `estudiantes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indices de la tabla `profesores`
--
ALTER TABLE `profesores`
  ADD PRIMARY KEY (`username`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `contraseña_imagenes_estudiante`
--
ALTER TABLE `contraseña_imagenes_estudiante`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `estudiantes`
--
ALTER TABLE `estudiantes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `contraseña_imagenes_estudiante`
--
ALTER TABLE `contraseña_imagenes_estudiante`
  ADD CONSTRAINT `fk_estudiantes` FOREIGN KEY (`id_estudiante`) REFERENCES `estudiantes` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
