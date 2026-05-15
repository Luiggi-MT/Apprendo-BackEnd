import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

websocket_router = APIRouter(prefix="/chat", tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.client_ids: dict[WebSocket, str] = {}
        self.client_names: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

        client_id = str(uuid.uuid4())
        client_name = websocket.query_params.get(
            "name") or f"PARTICIPANTE-{client_id[:4].upper()}"

        self.client_ids[websocket] = client_id
        self.client_names[websocket] = client_name

        return client_id, client_name

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.client_ids.pop(websocket, None)
        self.client_names.pop(websocket, None)

    async def send_personal_message(self, payload: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def broadcast(self, payload: dict):
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    client_id, client_name = await manager.connect(websocket)

    await manager.send_personal_message(
        {
            "type": "welcome",
            "clientId": client_id,
            "senderName": client_name,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        },
        websocket,
    )

    try:
        while True:
            data = await websocket.receive_text()

            text = ""
            sender_name = manager.client_names.get(websocket, client_name)

            try:
                body = json.loads(data)
                text = str(body.get("text", "")).strip()
                sender_name = str(
                    body.get("senderName", sender_name)).strip() or sender_name
                client_message_id = str(
                    body.get("clientMessageId", "")).strip()
            except Exception:
                text = str(data).strip()
                client_message_id = ""

            if not text:
                continue

            message_payload = {
                "type": "message",
                "id": str(uuid.uuid4()),
                "senderId": manager.client_ids.get(websocket, client_id),
                "senderName": sender_name,
                "text": text,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }

            if client_message_id:
                message_payload["clientMessageId"] = client_message_id

            await manager.broadcast(message_payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
