# chat_repository.py

import uuid
from datetime import datetime, timezone
from typing import Optional

from mongo import MongoDB


class ChatRepository:

    def __init__(self):

        mongo = MongoDB()

        self._messages_col = mongo.get_collection(
            "chat_messages"
        )

        self._sessions_col = mongo.get_collection(
            "chat_sessions"
        )

    async def save_message(
        self,
        session_id: str,
        payload: dict
    ) -> dict:

        doc = {

            "_id": payload.get(
                "id",
                str(uuid.uuid4())
            ),

            "session_id": session_id,

            "sender_id":
                payload["senderId"],

            "sender_name":
                payload["senderName"],

            "content":
                payload.get("content", ""),

            "image_data":
                payload.get("imageData"),

            "audio_data":
                payload.get("audioData"),

            "created_at":
                datetime.now(
                    timezone.utc
            )
        }

        await self._messages_col.insert_one(
            doc
        )

        return doc

    async def list_messages(
        self,
        session_id: str
    ):

        cursor = (
            self._messages_col
            .find(
                {
                    "session_id":
                    session_id
                }
            )
            .sort(
                "created_at",
                1
            )
        )

        messages = []

        async for doc in cursor:

            messages.append({

                "id":
                    doc["_id"],

                "senderId":
                    doc["sender_id"],

                "senderName":
                    doc["sender_name"],

                "content":
                    doc["content"],

                "imageData":
                    doc.get(
                        "image_data"
                    ),

                "audioData":
                    doc.get(
                        "audio_data"
                    ),

                "createdAt":
                    doc[
                        "created_at"
                    ].isoformat()

            })

        return messages

    async def get_session(
        self,
        session_id: str
    ) -> Optional[dict]:

        return await (
            self._sessions_col
            .find_one(
                {
                    "_id":
                    session_id
                }
            )
        )

    async def is_session_open(
        self,
        session_id: str
    ) -> bool:

        session = await self.get_session(
            session_id
        )

        return bool(
            session and
            session.get(
                "status"
            ) == "active"
        )

    async def close_session(
        self,
        session_id: str
    ):

        result = await (
            self._sessions_col
            .update_one(

                {
                    "_id":
                    session_id
                },

                {
                    "$set": {

                        "status":
                        "closed",

                        "closed_at":
                        datetime.now(
                            timezone.utc
                        )

                    }

                }

            )
        )

        return (
            result.matched_count > 0
        )
