from sqlalchemy.orm import Session
from models import App, Contact, Message
from utils import human_readable_time_diff
from sqlalchemy import func, desc, asc, and_, or_, case
from datetime import datetime
import os
from fastapi import (
    UploadFile
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from sqlalchemy import func, case, or_, and_, desc

async def get_recent_conversations_ws(db: Session, app_id: int):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found"}

    subq = (
        db.query(Message.contact_id, func.max(Message.sent_at).label("last_sent_at"))
        .filter(Message.app_id == app_id)
        .group_by(Message.contact_id)
        .subquery()
    )

    last_messages = (
        db.query(
            Message,
            Contact.name.label("contact_name"),
            Contact.wa_id.label("contact_number"),
        )
        .join(
            subq,
            and_(
                Message.contact_id == subq.c.contact_id,
                Message.sent_at == subq.c.last_sent_at,
            ),
        )
        .join(Contact, Contact.id == Message.contact_id)
        .order_by(desc(Message.sent_at))
        .all()
    )

    # Prepare response
    conversations = []
    for msg, contact_name, contact_number in last_messages:
        display_name = contact_name or contact_number
        time_display = human_readable_time_diff(msg.sent_at)

        conversations.append(
            {
                "contact_number": contact_number,
                "contact_name": display_name,
                "last_message_type": msg.message_type,
                "last_message": (
                    msg.content if msg.message_type == "text" else f"[{msg.message_type}]"
                ),
                "last_message_time": time_display,
            }
        )
        
    return {"conversations": conversations}



async def get_contact_by_by_id_ws(
    db: Session, app_id: int, wa_id: str
):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found", "messages": []}

    # Fetch profile (Contact)
    contact = (
        db.query(Contact)
        .filter(Contact.app_id == app_id, Contact.wa_id == wa_id)
        .first()
    )

    return {
        "type": "contact",
        "contact": {
            "id": contact.id,
            "wa_id": contact.wa_id,
            "name": contact.name,
            "number": contact.wa_id,
            "source": contact.source,
            "is_active": contact.is_active,
            "last_active_at": (
                contact.last_active_at.isoformat() if contact.last_active_at else None
            ),
            "created_at": (
                contact.created_at.isoformat() if contact.created_at else None
            ),
        },
    }


async def get_messages_by_contact_ws(db: Session, app_id: int, wa_id: str, offset: int = 0, limit: int = 30):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found", "messages": []}
    
    contact = db.query(Contact).filter(Contact.wa_id == wa_id).first()
    if not contact:
        return {"error": "Contact not found", "messages": []}

    total_messages = (
        db.query(func.count(Message.id))
        .filter(
            Message.app_id == app_id,
            Message.contact_id == contact.id
        )
        .scalar()
    )

    # Calculate reverse offset: start from the most recent
    reverse_offset = max(total_messages - offset - limit, 0)

    messages_query = (
        db.query(Message)
        .filter(
            Message.app_id == app_id,
            Message.contact_id == contact.id
        )
        .order_by(asc(Message.created_at))  # Oldest to newest
        .offset(reverse_offset)
        .limit(limit)
    )
    messages = messages_query.all()

    def serialize_message(m):
        return {
            "id": m.id,
            "app_id": m.app_id,
            "contact_id": m.contact_id,
            "from_number": m.from_number,
            "to_number": m.to_number,
            "message_type": m.message_type,
            "content": m.content,
            "media_url": m.media_url,
            "media_mime_type": m.media_mime_type,
            "media_size": m.media_size,
            "media_caption": m.media_caption,
            "location_latitude": m.location_latitude,
            "location_longitude": m.location_longitude,
            "location_name": m.location_name,
            "contact_name": m.contact_name,
            "contact_phone": m.contact_phone,
            "direction": m.direction,
            "status": m.status,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "read_at": m.read_at.isoformat() if m.read_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    serialized_messages = [serialize_message(m) for m in messages]

    return {
        "type": "messages",
        "messages": serialized_messages,
        "count": len(serialized_messages),
    }


async def handle_send_message(db: Session, app_id: int, data: dict, file: UploadFile = None):
    allowed_types = {
        "image": ["image/jpeg", "image/png"],
        "video": ["video/mp4"],
        "audio": ["audio/mpeg", "audio/ogg"],
        "document": ["application/pdf", "application/msword"],
        "sticker": ["image/webp"],
    }

    # Validate app
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found"}
    
    contact = db.query(Contact).filter(Contact.wa_id == data["to_number"]).first()
    if not contact:
        return {"error": "Contact not found", "messages": []}

    # Initialize media fields
    media_url, media_mime_type, media_size = None, None, None

    # Handle media upload
    if file:
        if data["message_type"] not in allowed_types:
            return {"error": f"Unsupported message_type: {data['message_type']}"}

        if file.content_type not in allowed_types[data["message_type"]]:
            return {
                "error": f"Invalid file type {file.content_type} for {data['message_type']}"
            }

        contents = await file.read()
        media_size = len(contents)
        max_size = 10 * 1024 * 1024  # 10MB limit
        if media_size > max_size:
            return {"error": "File size exceeds 10MB limit"}

        filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        media_url = f"/uploads/{filename}"
        media_mime_type = file.content_type

    # Validate fields
    if data["message_type"] == "text" and not data.get("content"):
        return {"error": "Text message requires content"}
    elif data["message_type"] == "location" and not (
        data.get("location_latitude") and data.get("location_longitude")
    ):
        return {"error": "Location message requires latitude and longitude"}
    elif data["message_type"] == "contact" and not (
        data.get("contact_name") and data.get("contact_phone")
    ):
        return {"error": "Contact message requires name and phone"}
    elif data["message_type"] in allowed_types and not file:
        return {"error": f"{data['message_type']} message requires a file"}

    # Convert timestamps
    sent_at = datetime.utcnow()
    received_at = None
    read_at = None

    # Create message
    db_msg = Message(
        app_id=app.id,
        contact_id=contact.id,
        to_number=data["to_number"],
        from_number=app.whatsapp_number,
        message_type=data["message_type"],
        content=data.get("content"),
        media_url=media_url,
        media_mime_type=media_mime_type,
        media_size=media_size,
        media_caption=data.get("media_caption"),
        location_latitude=data.get("location_latitude"),
        location_longitude=data.get("location_longitude"),
        location_name=data.get("location_name"),
        contact_name=data.get("contact_name"),
        contact_phone=data.get("contact_phone"),
        direction="outbound",
        status="sent",
        sent_at=sent_at,
        received_at=received_at,
        read_at=read_at,
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    msg_data = jsonable_encoder(db_msg)

    return {
        "type": "new_message",
        "contact_number": data["to_number"],
        "message": msg_data,
    }
