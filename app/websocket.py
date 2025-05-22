from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from connection_pool import active_connections
from models import Contact, User
from sqlalchemy.orm import Session
from database import get_db
from app.services.message_service import handle_outgoing_message

router = APIRouter()


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
                sender_id = int(data["data"]["sender_id"])
                receiver_id = int(data["data"]["receiver_id"])
                content = data["data"]["content"]

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

                db_message = await handle_outgoing_message(
                    db, sender_id, receiver_id, content
                )

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
