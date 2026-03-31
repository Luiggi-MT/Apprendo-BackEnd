# Cole API Backend (Flask)

Backend del proyecto Cole. Expone endpoints para autenticacion, gestion academica, tareas, materiales, comandas, notificaciones y funciones con IA.

## Funcionalidades principales

- Autenticacion con JWT para perfiles de administracion, profesorado y alumnado.
- Gestion de estudiantes, profesores, aulas y asignacion de tareas.
- Gestion de materiales y archivos (subida y consulta).
- Comandas de comedor y exportacion a PDF.
- Integracion con OpenAI para voz y procesamiento de texto.
- Integracion con Firebase/Expo para notificaciones push.

## Stack tecnico

- Python 3 + Flask.
- Flask-CORS y Flask-JWT-Extended.
- MariaDB/MySQL (PyMySQL y DBUtils).
- OpenAI SDK.
- Google Cloud Storage / Firestore.
- Docker y Docker Compose.

## Requisitos

- Python 3.10 o superior recomendado.
- Docker y Docker Compose (recomendado para entorno completo).
- Variables de entorno configuradas en `.env`.

## Ejecucion local (sin Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

La API arrancara normalmente en `http://localhost:5000` (segun configuracion de `app.py`).

## Ejecucion con Docker

Entorno de desarrollo:

```bash
docker compose -f docker-compose-dev.yml up --build
```

Entorno estandar:

```bash
docker compose up --build
```

Para detener servicios:

```bash
docker compose down
```

## Testing

```bash
pytest
```

## Estructura del proyecto (resumen)

```text
server/
├── app.py
├── const.py
├── db.py
├── routes/
├── test/
├── components/
├── media/
├── Dockerfile
├── docker-compose.yml
├── docker-compose-dev.yml
├── init.sql
└── requirements.txt
```

## Endpoints principales (resumen)

Autenticacion y sesion:

- `POST /login`
- `POST /login_student`
- `GET /session`

Usuarios y perfiles:

- `GET /students`
- `POST /students`
- `PUT /students/:id`
- `GET /profesor`

Aulas y tareas:

- `GET /aulas`
- `POST /aulas`
- `GET /tareas`
- `POST /tareas`

Comandas y menu:

- `GET /menu`
- `POST /menu`
- `GET /comanda`
- `POST /comanda/pedido`

Material escolar y archivos:

- `GET /materiales`
- `POST /materiales`
- `POST /files/upload`

Notificaciones e IA:

- `POST /guardar-token`
- `POST /guardar-token-profesor`
- `GET /generar-voz`
- `POST /openai/transcribir`

Nota:

- Esta lista es orientativa. Revisa los blueprints en `routes/` para el detalle exacto de rutas, metodos y payloads.

## Seguridad y credenciales

- No subir secretos a Git (service accounts, claves privadas, tokens).
- Mantener `.env` y credenciales fuera del control de versiones.
- Rotar cualquier credencial que se haya expuesto en commits anteriores.
