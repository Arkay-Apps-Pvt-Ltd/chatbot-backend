# services/message_service.py

import json
import httpx
from fastapi import HTTPException
from models import Contact
from schemas import MessageBase
from app.crud.message import create_message
from connection_pool import active_connections

GUPSHUP_URL = "https://api.gupshup.io/sm/api/v1/msg"
GUPSHUP_SOURCE = "15557546242"
GUPSHUP_APP_NAME = "arkayappsv1"
GUPSHUP_APIKEY = "awdxg2aymfgsjcrrrufuvu5y4u1hd5xi"

async def send_message_to_gupshup(receiver_contact, message_text):
    json_message = {"type": "text", "text": message_text}
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE,
        "destination": receiver_contact.mobile_number,
        "message": json.dumps(json_message),
        "src.name": GUPSHUP_APP_NAME,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": GUPSHUP_APIKEY,
    }

    try:
        response = httpx.post(GUPSHUP_URL, data=payload, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Gupshup error: {e.response.text}")


async def handle_outgoing_message(db, sender_id, receiver_id, content):
    # Get receiver contact
    receiver_contact = db.query(Contact).filter_by(id=receiver_id).first()
    if not receiver_contact:
        raise HTTPException(status_code=404, detail="Receiver not found")

    # 1. Send via Gupshup
    await send_message_to_gupshup(receiver_contact, content)

    # 2. Save in DB
    message_data = MessageBase(
        sender_id=sender_id, receiver_id=receiver_id, content=content
    )
    db_message = create_message(db, message_data)

    # 3. Notify via WebSocket
    receiver_user_id = (
        db.query(Contact.user_id)  # adjust if `user_id` is from another table
        .filter(Contact.id == receiver_id)
        .scalar()
    )
    if receiver_user_id:
        receiver_ws = active_connections.get(str(receiver_user_id))
        if receiver_ws:
            await receiver_ws.send_json({
                "type": "message",
                "data": {
                    "id": db_message.id,
                    "content": db_message.content,
                    "is_delivered": db_message.is_delivered,
                    "is_read": db_message.is_read,
                    "direction": "received",
                    "timestamp": db_message.timestamp.isoformat(),
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                }
            })

    return db_message
