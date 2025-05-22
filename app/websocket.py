from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import Dict
from app.crud import message as crud_message
from models import Contact, User
from sqlalchemy.orm import Session
from database import get_db
from schemas import MessageBase

router = APIRouter()


@router.websocket("/example")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Connected to /messages/ws/chat")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except:
        await websocket.close()


# In-memory storage for active connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    db: Session = Depends(get_db),
):
    await websocket.accept()
    active_connections[user_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                message_data = data.get("data", {})
                sender_id = message_data.get("sender_id")
                receiver_id = message_data.get("receiver_id")
                content = message_data.get("content")

                if not all([sender_id, receiver_id, content]):
                    await websocket.send_json({"error": "Invalid message payload"})
                    continue

                # Validate receiver
                receiver = db.query(Contact).filter(Contact.id == receiver_id).first()
                if not receiver:
                    await websocket.send_json(
                        {
                            "error": "Receiver contact not found",
                            "receiver_id": receiver_id,
                        }
                    )
                    continue

                # Fetch receiver's user_id
                receiver_user_id = (
                    db.query(User.id).filter(User.contact_id == receiver_id).scalar()
                )

                # Save to database
                message_create = MessageBase(
                    sender_id=int(sender_id),
                    receiver_id=int(receiver_id),
                    content=content,
                )
                db_message = crud_message.create_message(db, message_create)

                # Message response payload (for sender)
                sender_response = {
                    "type": "message",
                    "data": {
                        "id": db_message.id,
                        "content": db_message.content,
                        "is_delivered": db_message.is_delivered,
                        "is_read": db_message.is_read,
                        "direction": "sent",
                        "timestamp": db_message.timestamp.isoformat(),
                        "sender_id": db_message.sender_id,
                        "receiver_id": db_message.receiver_id,
                    },
                }

                # Acknowledgment to sender
                await websocket.send_json(sender_response)

                # Message to receiver
                receiver_ws = active_connections.get(str(receiver_user_id))
                if receiver_ws:
                    receiver_response = sender_response.copy()
                    receiver_response["data"]["direction"] = "received"
                    await receiver_ws.send_json(receiver_response)
            else:
                await websocket.send_json(
                    {"error": f"Unsupported message type: {msg_type}"}
                )

    except WebSocketDisconnect:
        active_connections.pop(user_id, None)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        active_connections.pop(user_id, None)
