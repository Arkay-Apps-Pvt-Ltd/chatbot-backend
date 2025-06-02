from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from connection_pool import active_connections
from models import App, Contact
from sqlalchemy.orm import Session
from database import get_db

from app.crud.message import (
    get_recent_conversations_ws,
    get_contact_by_by_id_ws,
    get_messages_by_contact_ws,
    handle_send_message
)

from typing import List
from collections import defaultdict

router = APIRouter()

# Active WebSocket connections per app_id
active_connections = defaultdict(list)


# 🔥 Real-time WebSocket (filtered by app_id)
@router.websocket("/ws-test")
async def websocket_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    app_id = websocket.query_params.get("app_id")

    if not app_id:
        await websocket.close(code=1008, reason="Missing app_id")
        return

    app = db.query(App).filter(App.id == int(app_id)).first()
    if not app:
        await websocket.close(code=1008, reason="Invalid app_id")
        return

    active_connections[app_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            type = data.get("type")

            if type == "conversations":
                result = await get_recent_conversations_ws(db, int(app_id))
                await websocket.send_json(result)

            elif type == "get_contact":
                wa_id = data.get("wa_id")
                if not wa_id:
                    await websocket.send_json({"error": "Missing wa_id"})
                    continue
                result = await get_contact_by_by_id_ws(
                    db, int(app_id), wa_id
                )
                await websocket.send_json(result)

            elif type == "get_messages":
                wa_id = data.get("wa_id")
                offset = data.get("offset") or 0         # Default to 0
                limit = data.get("limit") or 30         # Default to 30

                if not wa_id:
                    await websocket.send_json({"error": "Missing wa_id"})
                    continue
                result = await get_messages_by_contact_ws(
                    db, int(app_id), wa_id, offset=offset, limit=limit
                )
                await websocket.send_json(result)

            elif type == "send_message":
                data = data.get("payload")
                if not data:
                    await websocket.send_json({"error": "Missing message payload"})
                    continue

                result = await handle_send_message(db, int(app_id), data)
                await websocket.send_json(result)

            else:
                await websocket.send_text(f"Unsupported message type: {type}")

    except WebSocketDisconnect:
        active_connections[app_id].remove(websocket)
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        active_connections[app_id].remove(websocket)


# Broadcast to all sockets in an app_id
async def broadcast_to_app(app_id: int, message: dict):
    websockets = active_connections.get(str(app_id), [])
    for ws in websockets:
        try:
            await ws.send_json(message)
        except:
            pass  # Handle disconnects gracefully
