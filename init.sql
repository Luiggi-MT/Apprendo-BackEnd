-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Servidor: db:3306
-- Tiempo de generación: 21-01-2026 a las 22:31:52
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

--
-- Volcado de datos para la tabla `contraseña_imagenes_estudiante`
--

INSERT INTO `contraseña_imagenes_estudiante` (`id`, `id_estudiante`, `url_imagen`, `codigo`, `es_contraseña`) VALUES
(6, 38, 'fotoPerfil/38/contraseñaImagen/96FCA5A3-FEC8-4D45-B79C-F54559C92F04.jpg', '1769029310970_0_86ehbomze', 1),
(7, 38, 'fotoPerfil/38/contraseñaImagen/A40CAD91-43F4-46D3-8EFE-5F4B0C6E2575.jpg', '1769029310970_1_j3kfuu50e', 1),
(8, 38, 'fotoPerfil/38/contraseñaImagen/023CC7AB-F4D7-4E52-B5E8-7C9F13DE3B84.heic', '1769029319372_0_tyy54f4gm', 0);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estudiantes`
--

CREATE TABLE `estudiantes` (
  `username` varchar(30) NOT NULL,
  `contraseña` varchar(255) DEFAULT NULL,
  `foto` varchar(150) DEFAULT 'porDefecto.png',
  `tipoContraseña` enum('alfanumerica','pin','imagenes') DEFAULT 'alfanumerica',
  `accesibilidad` set('texto','video','imagenes','pictogramas','audio') DEFAULT 'texto',
  `preferenciasVisualizacion` enum('diarias','semanales') DEFAULT 'diarias',
  `asistenteVoz` enum('none','unidireccional','bidireccional') NOT NULL DEFAULT 'none',
  `id` int(11) NOT NULL,
  `sexo` enum('masculino','femenino','otro') DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `estudiantes`
--

INSERT INTO `estudiantes` (`username`, `contraseña`, `foto`, `tipoContraseña`, `accesibilidad`, `preferenciasVisualizacion`, `asistenteVoz`, `id`, `sexo`) VALUES
('MENSUAL', 'pbkdf2:sha256:1000000$2esGjaJ3zWpEhcGi$eafda121e3dbb77f84a207cb576d1d716a7e4fdc1c3042a5393e7a03d0ab9233', 'porDefecto.png', 'alfanumerica', 'audio', 'semanales', 'bidireccional', 36, 'masculino'),
('DIARIAS', 'pbkdf2:sha256:1000000$tM2p4RseHuysRcRm$59a6f50e909d284e259c3c116fd00c7fa1b3ae342cf2dd81034b9bdde0ec2fb6', 'porDefecto.png', 'alfanumerica', 'imagenes', 'diarias', 'unidireccional', 37, 'masculino'),
('LUIS', NULL, '38/fotoPerfil', 'imagenes', 'video,audio', 'diarias', 'none', 38, 'masculino');

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de la tabla `estudiantes`
--
ALTER TABLE `estudiantes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=39;

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
