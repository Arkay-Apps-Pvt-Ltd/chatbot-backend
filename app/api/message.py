from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import App, Contact, Message
from sqlalchemy import func, desc, and_
from datetime import datetime
import os
from utils import human_readable_time_diff

router = APIRouter(tags=["Messages"])
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/conversations")
def get_recent_conversations(app_id: int, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

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

    return conversations


@router.get("/messages/{contact_number}")
def get_messages_by_contact(
    app_id: int, contact_number: str, db: Session = Depends(get_db)
):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    return (
        db.query(Message)
        .filter(
            Message.app_id == app_id,
            (
                (Message.from_number == contact_number)
                | (Message.to_number == contact_number)
            ),
        )
        .order_by(Message.created_at.desc())
        .all()
    )


@router.post("/messages")
async def create_message(
    db: Session = Depends(get_db),
    # Support multipart/form-data for media messages
    app_id: int = Form(None),
    to_number: str = Form(None),
    message_type: str = Form(None),
    content: str = Form(None),
    media_caption: str = Form(None),
    location_latitude: float = Form(None),
    location_longitude: float = Form(None),
    location_name: str = Form(None),
    contact_name: str = Form(None),
    contact_phone: str = Form(None),
    file: UploadFile = File(None),
):
    data = {
        "app_id": app_id,
        "to_number": to_number,
        "message_type": message_type,
        "content": content,
        "media_caption": media_caption,
        "location_latitude": location_latitude,
        "location_longitude": location_longitude,
        "location_name": location_name,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
    }

    allowed_types = {
        "image": ["image/jpeg", "image/png"],
        "video": ["video/mp4"],
        "audio": ["audio/mpeg", "audio/ogg"],
        "document": ["application/pdf", "application/msword"],
        "sticker": ["image/webp"],
    }

    # Validate app
    db_app = db.query(App).filter(App.id == data["app_id"]).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="App not found")

    # Fetch Contact IDs
    db_contact = db.query(Contact).filter(Contact.wa_id == data["to_number"]).first()

    # Initialize media fields
    media_url, media_mime_type, media_size = None, None, None

    # Handle media upload
    if file:
        if data["message_type"] not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message_type: {data['message_type']}",
            )

        if file.content_type not in allowed_types[data["message_type"]]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type {file.content_type} for {data['message_type']}",
            )

        contents = await file.read()
        media_size = len(contents)
        max_size = 10 * 1024 * 1024  # 10MB limit
        if media_size > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

        filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        media_url = f"/uploads/{filename}"
        media_mime_type = file.content_type

    # Validate fields
    if data["message_type"] == "text" and not data.get("content"):
        raise HTTPException(status_code=400, detail="Text message requires content")
    elif data["message_type"] == "location" and not (
        data.get("location_latitude") and data.get("location_longitude")
    ):
        raise HTTPException(
            status_code=400, detail="Location message requires latitude and longitude"
        )
    elif data["message_type"] == "contact" and not (
        data.get("contact_name") and data.get("contact_phone")
    ):
        raise HTTPException(
            status_code=400, detail="Contact message requires name and phone"
        )
    elif data["message_type"] in allowed_types and not file:
        raise HTTPException(
            status_code=400, detail=f"{data['message_type']} message requires a file"
        )

    # Create message
    db_msg = Message(
        app_id=db_app.id,
        contact_id=db_contact.id,
        from_number=db_app.whatsapp_number,
        to_number=data["to_number"],
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
        sent_at=datetime.utcnow(),
        received_at=None,
        read_at=None,
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    return {"message_id": db_msg.id, "status": "created"}


@router.get("/messages/{msg_id}/mark-delivered")
def mark_message_delivered(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.status = "delivered"
    msg.received_at = datetime.utcnow()
    db.commit()
    return {"status": "delivered", "message_id": msg_id}


@router.get("/messages/{msg_id}/mark-read")
def mark_message_read(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.status = "read"
    msg.read_at = datetime.utcnow()
    db.commit()
    return {"status": "read", "message_id": msg_id}
