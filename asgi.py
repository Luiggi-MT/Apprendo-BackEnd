from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse

from app import app as flask_app
from routes.webSocket import websocket_router

from mongo import MongoDB

app = FastAPI(title="Cole API + WebSocket")

# CORS para rutas FastAPI (incluye /chat/*). Flask ya gestiona sus propias rutas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Crear índices mongo al arrancar
@app.on_event("startup")
async def startup():
    mongo = MongoDB()

    messages = mongo.get_collection(
        "chat_messages"
    )

    await messages.create_index(
        [
            ("session_id", 1),
            ("created_at", 1)
        ]
    )
    print("Índices de MongoDB creados correctamente")
# Healthcheck para docker-compose


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

# Rutas websocket nativas (ASGI)
app.include_router(websocket_router)

# Rutas REST actuales de Flask (WSGI)
app.mount("/", WSGIMiddleware(flask_app))
