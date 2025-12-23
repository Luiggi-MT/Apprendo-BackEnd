-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Servidor: db:3306
-- Tiempo de generación: 12-12-2025 a las 17:42:34
-- Versión del servidor: MariaDB
-- Versión de PHP: 8.3.28

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
-- Estructura de tabla para la tabla `estudiantes`
--

CREATE TABLE `estudiantes` (
  `username` varchar(30) NOT NULL,
  `contraseña` varchar(255) NOT NULL,
  `formato` enum('foto','imagen','pictográma','video','texto','audio') DEFAULT NULL,
  `foto` varchar(150) DEFAULT 'porDefecto.png'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `estudiantes`
--

INSERT INTO `estudiantes` (`username`, `contraseña`, `formato`, `foto`) VALUES
('ejemplo', 'contraseña', 'pictográma', 'porDefecto.png'),
('estudiante_a_01', 'password01', 'pictográma', 'porDefecto.png'),
('estudiante_b_02', 'password02', 'pictográma', 'porDefecto.png'),
('estudiante_c_03', 'password03', 'pictográma', 'porDefecto.png'),
('estudiante_d_04', 'password04', 'pictográma', 'porDefecto.png'),
('estudiante_e_05', 'password05', 'pictográma', 'porDefecto.png'),
('estudiante_f_06', 'password06', 'pictográma', 'porDefecto.png'),
('estudiante_g_07', 'password07', 'pictográma', 'porDefecto.png'),
('estudiante_h_08', 'password08', 'pictográma', 'porDefecto.png'),
('estudiante_i_09', 'password09', 'pictográma', 'porDefecto.png'),
('estudiante_j_10', 'password10', 'pictográma', 'porDefecto.png'),
('estudiante_k_11', 'password11', 'pictográma', 'porDefecto.png'),
('estudiante_l_12', 'password12', 'pictográma', 'porDefecto.png'),
('estudiante_m_13', 'password13', 'pictográma', 'porDefecto.png'),
('estudiante_n_14', 'password14', 'pictográma', 'porDefecto.png'),
('estudiante_o_15', 'password15', 'pictográma', 'porDefecto.png'),
('estudiante_p_16', 'password16', 'pictográma', 'porDefecto.png'),
('estudiante_q_17', 'password17', 'pictográma', 'porDefecto.png'),
('estudiante_r_18', 'password18', 'pictográma', 'porDefecto.png'),
('estudiante_s_19', 'password19', 'pictográma', 'porDefecto.png'),
('estudiante_t_20', 'password20', 'pictográma', 'porDefecto.png');

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
-- Indices de la tabla `estudiantes`
--
ALTER TABLE `estudiantes`
  ADD PRIMARY KEY (`username`);

--
-- Indices de la tabla `profesores`
--
ALTER TABLE `profesores`
  ADD PRIMARY KEY (`username`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;