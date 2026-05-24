import json
import os
import uuid
import asyncio
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, WebSocketException, status, HTTPException

from chat_repository import ChatRepository
from db import Database
from mongo import MongoDB
from routes.notificaciones import enviar_push

websocket_router = APIRouter(prefix="/chat", tags=["websocket"])

# Autentificacion


def _verify_token(token: str) -> dict:
    """Decodificar el JWT de Flask-JWT-Extender. Lanza excepción si es inválido."""
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        raise RuntimeError("FLASK_SECRET_KEY no configurada en el entorno")
    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except pyjwt.ExpiredSignatureError:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Token expirado")
    except pyjwt.InvalidTokenError:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido")


def _verify_http_token(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")

    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        raise HTTPException(
            status_code=500, detail="FLASK_SECRET_KEY no configurada")

    try:
        return pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def _resolve_sender_name(claims: dict) -> str:
    """Obtiene un nombre legible del JWT (compatible con admin y estudiante)."""
    for key in ("name", "username", "sub", "nombre"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    user_id = claims.get("id")
    if user_id is not None:
        return f"USUARIO {user_id}"

    return "USUARIO"


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# Connection Manager para manejar conexiones WebSocket
class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, dict[str, WebSocket]] = {}

    def _room(self, session_id: str) -> dict[str, WebSocket]:
        if session_id not in self.rooms:
            self.rooms[session_id] = {}
        return self.rooms[session_id]

    async def connect(self, session_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        room = self._room(session_id)
        room[user_id] = websocket

    def disconnect(self, session_id: str, user_id: str):
        room = self.rooms.get(session_id, {})
        room.pop(user_id, None)
        if not room:
            self.rooms.pop(session_id, None)

    async def send(self, websocket: WebSocket, payload: dict):
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def broadcast(self, session_id: str, payload: dict):
        dead = []
        for uid, ws in list(self._room(session_id).items()):
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)


manager = ConnectionManager()
db = Database()


async def _send_chat_push_if_offline(
    session_id: str,
    session: dict,
    sender_id: str,
    sender_tipo: str,
    sender_name: str,
    text: str,
    has_image: bool = False,
    has_audio: bool = False,
):
    """Envia push al otro participante del chat."""
    try:
        recipient_id = None
        recipient_table = ""

        sender_tipo_normalized = (sender_tipo or "").strip().lower()

        if sender_tipo_normalized == "estudiante":
            recipient_id = session.get("profesor_id")
            recipient_table = "profesores"

            # Fallback para sesiones antiguas sin profesor_id en Mongo.
            if not recipient_id:
                admin_row = db.fetch_query(
                    "SELECT id FROM profesores WHERE tipo = 'admin' LIMIT 1",
                    fetchone=True,
                )
                recipient_id = admin_row.get("id") if admin_row else None

            # Fallback adicional por SQL para mantener el profesor real de la sesión.
            if not recipient_id:
                professor_row = db.fetch_query(
                    "SELECT profesor_id FROM pedido_profesor_estudiante WHERE chat_id = %s LIMIT 1",
                    (session_id,),
                    fetchone=True,
                )
                recipient_id = professor_row.get(
                    "profesor_id") if professor_row else None
        else:
            recipient_id = session.get("estudiante_id")
            recipient_table = "estudiantes"

            # Fallback para sesiones antiguas sin estudiante_id en Mongo.
            if not recipient_id:
                student_row = db.fetch_query(
                    "SELECT estudiante_id FROM tarea_estudiante WHERE chat_session_id = %s LIMIT 1",
                    (session_id,),
                    fetchone=True,
                )
                recipient_id = student_row.get(
                    "estudiante_id") if student_row else None

        if not recipient_id:
            return

        recipient_id_str = str(recipient_id)
        if recipient_id_str == sender_id:
            return

        if recipient_table == "profesores":
            recipient = db.fetch_query(
                "SELECT expo_push_token FROM profesores WHERE id = %s LIMIT 1",
                (recipient_id,),
                fetchone=True,
            )
        else:
            recipient = db.fetch_query(
                "SELECT expo_push_token FROM estudiantes WHERE id = %s LIMIT 1",
                (recipient_id,),
                fetchone=True,
            )

        token = recipient.get("expo_push_token") if recipient else None
        if not token:
            print(
                f"Push de chat sin token. session_id={session_id}, sender_id={sender_id}, sender_tipo={sender_tipo_normalized}, recipient_id={recipient_id}, recipient_table={recipient_table}"
            )
            return

        preview = text.strip()
        if len(preview) > 120:
            preview = preview[:117] + "..."

        title = "NUEVO MENSAJE"
        body = (
            f"{sender_name}: {preview}"
            if preview
            else (
                f"{sender_name} te ha enviado una imagen"
                if has_image
                else (
                    f"{sender_name} te ha enviado un audio"
                    if has_audio
                    else f"{sender_name} te ha enviado un mensaje"
                )
            )
        )

        sent = await asyncio.to_thread(enviar_push, token, title, body)
        if not sent:
            print(
                f"Push de chat no enviada. session_id={session_id}, sender_id={sender_id}, sender_tipo={sender_tipo_normalized}, recipient_id={recipient_id}, recipient_table={recipient_table}"
            )
        else:
            print(
                f"Push de chat enviada. session_id={session_id}, sender_id={sender_id}, sender_tipo={sender_tipo_normalized}, recipient_id={recipient_id}, recipient_table={recipient_table}"
            )
    except Exception as e:
        print(f"Error enviando notificación push de chat: {e}")


@websocket_router.get("/open-students")
def get_open_chat_students(request: Request):
    claims = _verify_http_token(request)
    if claims.get("tipo") != "admin":
        raise HTTPException(status_code=403, detail="Acceso no autorizado")

    try:
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        offset = 0

    try:
        limit = int(request.query_params.get("limit", 6))
    except ValueError:
        limit = 6

    if offset < 0:
        offset = 0
    if limit <= 0:
        limit = 6

    search = (request.query_params.get("search", "") or "").strip()

    where_clauses = [
        "te.completado = 0",
        "te.chat_session_id IS NOT NULL",
        "te.chat_session_id <> ''",
    ]
    params = []

    if search:
        where_clauses.append("e.username LIKE %s")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT e.id, e.username, e.foto, COUNT(*) AS open_chats
        FROM tarea_estudiante te
        JOIN estudiantes e ON e.id = te.estudiante_id
        WHERE {where_sql}
        GROUP BY e.id, e.username, e.foto
        ORDER BY e.username
        LIMIT %s OFFSET %s
    """

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT e.id
            FROM tarea_estudiante te
            JOIN estudiantes e ON e.id = te.estudiante_id
            WHERE {where_sql}
            GROUP BY e.id
        ) AS grouped_students
    """

    try:
        rows = db.fetch_query(query, tuple(params + [limit, offset]))
        count_row = db.fetch_query(count_query, tuple(params), fetchone=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estudiantes con chats abiertos: {e}",
        )

    total = count_row.get("total", 0) if count_row else 0
    return {
        "ok": True,
        "students": rows,
        "count": total,
        "offset": offset + limit,
    }


@websocket_router.get("/open-sessions/{student_id}")
async def get_open_chat_sessions_by_student(student_id: int, request: Request):
    claims = _verify_http_token(request)
    if claims.get("tipo") != "admin":
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    admin_id = str(claims.get("id", ""))

    try:
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        offset = 0

    try:
        limit = int(request.query_params.get("limit", 6))
    except ValueError:
        limit = 6

    if offset < 0:
        offset = 0
    if limit <= 0:
        limit = 6

    search = (request.query_params.get("search", "") or "").strip()

    where_clauses = [
        "te.estudiante_id = %s",
        "te.completado = 0",
        "te.chat_session_id IS NOT NULL",
        "te.chat_session_id <> ''",
    ]
    params = [student_id]

    if search:
        where_clauses.append("t.nombre LIKE %s")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses)

    query = f"""
         SELECT te.chat_session_id, te.tarea_id, te.fecha, t.nombre AS tarea_nombre,
             t.categoria, COALESCE(pm.id_pictograma, t.id_pictograma) AS id_pictograma
        FROM tarea_estudiante te
        JOIN tarea t ON t.id = te.tarea_id
        LEFT JOIN pedido_material pm ON pm.id = t.id
        WHERE {where_sql}
        ORDER BY te.fecha DESC, t.nombre ASC
        LIMIT %s OFFSET %s
    """

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM tarea_estudiante te
        JOIN tarea t ON t.id = te.tarea_id
        WHERE {where_sql}
    """

    try:
        rows = db.fetch_query(query, tuple(params + [limit, offset]))
        count_row = db.fetch_query(count_query, tuple(params), fetchone=True)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener sesiones de chat abiertas: {e}",
        )

    # Enriquecemos con un contador de "no leídos" para el admin.
    # Se calcula desde la última vez que el admin abrió ese chat.
    try:
        messages_col = MongoDB().get_collection("chat_messages")
        sessions_col = MongoDB().get_collection("chat_sessions")
        for row in rows:
            session_id = row.get("chat_session_id")
            if not session_id:
                row["unread_count"] = 0
                continue

            session_doc = await sessions_col.find_one(
                {"_id": session_id},
                {f"admin_last_read_at.{admin_id}": 1},
            )

            last_read_at = None
            if session_doc:
                last_read_map = session_doc.get("admin_last_read_at", {})
                if isinstance(last_read_map, dict):
                    last_read_at = last_read_map.get(admin_id)

            mongo_filter = {
                "session_id": session_id,
                "sender_id": {"$ne": admin_id},
            }
            if last_read_at is not None:
                mongo_filter["created_at"] = {"$gt": last_read_at}

            unread_count = await messages_col.count_documents(mongo_filter)
            row["unread_count"] = int(unread_count or 0)
    except Exception:
        for row in rows:
            row["unread_count"] = 0

    total = count_row.get("total", 0) if count_row else 0
    return {
        "ok": True,
        "sessions": rows,
        "count": total,
        "offset": offset + limit,
    }

# Endpoint


@websocket_router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    # Extraer token de query params
    token = websocket.query_params.get("token", "")
    if not token:
        print(f"[WS] Rechazo: token requerido. session_id={session_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token requerido")
        return

    try:
        claims = _verify_token(token)  # Verificar token y extraer claims
    except WebSocketException as e:
        print(
            f"[WS] Rechazo: token inválido/expirado. session_id={session_id}, reason={e.reason}")
        await websocket.close(code=e.code, reason=e.reason)
        return

    user_id = str(claims.get("id", ""))
    sender_name = _resolve_sender_name(claims)
    sender_tipo = str(claims.get("tipo", ""))

    repo = ChatRepository()

    session = await repo.get_session(session_id)
    if not session:
        try:
            # Reparación defensiva: para sesiones antiguas, reconstruimos chat_sessions desde SQL.
            query = """
                SELECT te.chat_session_id, te.tarea_id, te.estudiante_id, te.fecha, te.completado,
                       ppe.profesor_id
                FROM tarea_estudiante te
                LEFT JOIN pedido_profesor_estudiante ppe
                  ON ppe.chat_id = te.chat_session_id
                WHERE te.chat_session_id = %s
                LIMIT 1
            """
            sql_row = db.fetch_query(query, (session_id,), fetchone=True)
        except Exception as e:
            print(
                f"[WS] Rechazo: error consultando sesión en SQL. session_id={session_id}, error={e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Sesion no encontrada")
            return

        if not sql_row:
            print(
                f"[WS] Rechazo: sesión no encontrada. session_id={session_id}, user_id={user_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Sesion no encontrada")
            return

        try:
            chat_collection = MongoDB().get_collection("chat_sessions")
            status_value = "closed" if int(
                sql_row.get("completado", 0)) == 1 else "active"
            await chat_collection.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "tarea_id": sql_row.get("tarea_id"),
                        "estudiante_id": sql_row.get("estudiante_id"),
                        "profesor_id": sql_row.get("profesor_id"),
                        "fecha": str(sql_row.get("fecha")),
                        "status": status_value,
                        "closed_at": datetime.now(timezone.utc) if status_value == "closed" else None,
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
            session = await repo.get_session(session_id)
            print(
                f"[WS] Sesión reconstruida desde SQL. session_id={session_id}, status={status_value}")
        except Exception as e:
            print(
                f"[WS] Rechazo: error reconstruyendo sesión en Mongo. session_id={session_id}, error={e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Sesion no encontrada")
            return

    is_read_only = session.get("status") != "active"

    # Si el usuario es admin y abre el chat, lo marcamos como leído para ese admin.
    if claims.get("tipo") == "admin":
        try:
            chat_collection = MongoDB().get_collection("chat_sessions")
            await chat_collection.update_one(
                {"_id": session_id},
                {"$set": {
                    f"admin_last_read_at.{user_id}": datetime.now(timezone.utc)}},
                upsert=False,
            )
        except Exception:
            pass

    # Conectar a la sala
    await manager.connect(session_id, user_id, websocket)

    # Enviar historial al recien conectado
    history = await repo.list_messages(session_id)
    await manager.send(websocket, {"type": "history", "messages": history})

    if is_read_only:
        await manager.send(websocket, {
            "type": "system",
            "message": "La sesion esta cerrada. Solo lectura.",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })

    try:
        while True:
            data = await websocket.receive_text()

            text = ""
            image_data = ""
            audio_data = ""
            client_message_id = ""

            try:
                body = json.loads(data)
                raw_text = body.get("content", "")
                raw_image = body.get("imageData", "")
                raw_audio = body.get("audioData", "")
                text = str(raw_text).strip() if raw_text is not None else ""
                image_data = str(raw_image).strip(
                ) if raw_image is not None else ""
                audio_data = str(raw_audio).strip(
                ) if raw_audio is not None else ""
                client_message_id = str(
                    body.get("clientMessageId", "")).strip()
            except Exception:
                text = str(data).strip()

            if not text and not image_data and not audio_data:
                continue

            if is_read_only or not await repo.is_session_open(session_id):
                await manager.send(websocket, {
                    "type": "system",
                    "message": "La sesion esta cerrada. No se pueden enviar mensajes.",
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                })
                continue

            message_payload = {
                "type": "message",
                "id": str(uuid.uuid4()),
                "senderId": user_id,
                "senderName": sender_name,
                "content": text,
                "imageData": image_data or None,
                "audioData": audio_data or None,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if client_message_id:
                message_payload["clientMessageId"] = client_message_id

            # Guardar mensaje en DB
            await repo.save_message(session_id, message_payload)

            # Broadcast a la sala
            await manager.broadcast(session_id, message_payload)

            # Push para el otro participante si no está conectado (app cerrada/en segundo plano).
            await _send_chat_push_if_offline(
                session_id=session_id,
                session=session,
                sender_id=user_id,
                sender_tipo=sender_tipo,
                sender_name=sender_name,
                text=text,
                has_image=bool(image_data),
                has_audio=bool(audio_data),
            )
    except WebSocketDisconnect:
        manager.disconnect(session_id, user_id)
