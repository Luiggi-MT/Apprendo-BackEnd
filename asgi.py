from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from app import app as flask_app
from routes.webSocket import websocket_router

app = FastAPI(title="Cole API + WebSocket")

# Rutas websocket nativas (ASGI)
app.include_router(websocket_router)

# Rutas REST actuales de Flask (WSGI)
app.mount("/", WSGIMiddleware(flask_app))
