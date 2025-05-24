from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from connection_pool import active_connections
from models import Contact
from sqlalchemy.orm import Session
from database import get_db
from app.services.message_service import handle_outgoing_message

router = APIRouter()

@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    contact_id = websocket.query_params.get("contact_id")

    if not contact_id:
        await websocket.close(code=1008)
        return

    try:
        contact_id = int(contact_id)
    except ValueError:
        await websocket.close(code=1008)
        return

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    active_connections[str(contact_id)].add(websocket)
    print(f"Connected: contact_id={contact_id}")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                sender_id = contact_id
                receiver_id = int(data["data"]["receiver_id"])
                content = data["data"]["content"]

                receiver = db.query(Contact).filter(Contact.id == receiver_id).first()
                if not receiver:
                    await websocket.send_json({
                        "error": "Receiver contact not found",
                        "receiver_id": receiver_id,
                    })
                    continue

                db_message = await handle_outgoing_message(
                    db, sender_id, receiver_id, content
                )

                message_payload = {
                    "type": "message",
                    "data": {
                        "id": db_message.id,
                        "content": db_message.content,
                        "is_delivered": db_message.is_delivered,
                        "is_read": db_message.is_read,
                        "timestamp": db_message.timestamp.isoformat(),
                        "sender_id": db_message.sender_id,
                        "receiver_id": db_message.receiver_id,
                    },
                }

                # Send to all sender connections
                for ws in active_connections.get(str(sender_id), set()):
                    if ws.application_state == WebSocketState.CONNECTED:
                        sender_response = message_payload.copy()
                        sender_response["data"]["direction"] = "sent"
                        await ws.send_json(sender_response)

                # Send to all receiver connections
                for ws in active_connections.get(str(receiver_id), set()):
                    if ws.application_state == WebSocketState.CONNECTED:
                        receiver_response = message_payload.copy()
                        receiver_response["data"]["direction"] = "received"
                        await ws.send_json(receiver_response)

            else:
                await websocket.send_json({
                    "error": f"Unsupported message type: {msg_type}"
                })

    except WebSocketDisconnect:
        print(f"Disconnected: contact_id={contact_id}")
        active_connections[str(contact_id)].discard(websocket)
        if not active_connections[str(contact_id)]:
            del active_connections[str(contact_id)]

    except Exception as e:
        await websocket.send_json({"error": str(e)})
        active_connections[str(contact_id)].discard(websocket)
        if not active_connections[str(contact_id)]:
            del active_connections[str(contact_id)]
