# 🖥️ Cole API - Backend (Flask)

Este es el servidor central del proyecto **Cole**, desarrollado en Python utilizando el framework Flask. Se encarga de la gestión de usuarios, almacenamiento de archivos, transcripción de audio mediante IA y la lógica de negocio del sistema.

## 🛠️ Tecnologías y Stack

* **Lenguaje:** Python 3.9
* **Framework:** Flask
* **Base de Datos:** MariaDB 10 / MySQL
* **Contenedores:** Docker & Docker Compose
* **IA:** OpenAI (Whisper API) para transcripción de audio.
* **Testing:** Pytest para pruebas unitarias y de integración.

## ⚙️ Configuración del Entorno


1.  **Instalación Manual (Opcional):**
    Si prefieres correrlo sin Docker:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python app.py
    ```

## 🐳 Despliegue con Docker (Recomendado)

El proyecto incluye una configuración de Docker optimizada para desarrollo:

* **Levantar servicios:** `docker-compose up -d`
* **Acceso a Base de Datos:** MariaDB corre en el puerto `3306`.
* **Administrador de DB:** phpMyAdmin disponible en `http://localhost:8080`.

## 📂 Estructura del Proyecto

```text
├── routes/             # Blueprints y controladores de la API
├── test/               # Suite de pruebas unitarias (Pytest)
├── venv/               # Entorno virtual (ignorado en Git)
├── app.py              # Punto de entrada de la aplicación
├── db.py               # Gestión de conexión a Base de Datos
├── const.py            # Constantes y configuraciones globales
└── docker-compose.yml  # Orquestación de contenedores