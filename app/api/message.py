from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import App, Contact, Message
from sqlalchemy import func, desc, and_
from datetime import datetime
import os
from utils import human_readable_time_diff
from schemas import MessageCreate
from fastapi.responses import JSONResponse
import uuid
import shutil
from config import config

router = APIRouter(tags=["Messages"])
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate a unique filename to avoid conflicts
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"{config['base_url']}/uploads/{unique_name}"

        return JSONResponse(
            content={
                "success": True,
                "filename": unique_name,
                "original_filename": file.filename,
                "url": file_url,  # You can change this as per how you serve static files
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            Contact.wa_id.label("wa_id"),
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
    for msg, contact_name, wa_id in last_messages:
        display_name = contact_name or wa_id
        time_display = human_readable_time_diff(msg.sent_at)

        conversations.append(
            {
                "wa_id": wa_id,
                "contact_name": display_name,
                "last_message_type": msg.message_type,
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
    message_in: MessageCreate,
    db: Session = Depends(get_db),
):
    # Validate app
    db_app = db.query(App).filter(App.id == message_in.app_id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="App not found")

    # Validate contact
    db_contact = db.query(Contact).filter(Contact.wa_id == message_in.to_number).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Validate payload type matches message_type
    payload_type = message_in.message_type
    if not payload_type:
        raise HTTPException(status_code=400, detail="Payload must include 'type' field")

    if payload_type != message_in.message_type:
        raise HTTPException(
            status_code=400,
            detail=f"Payload type '{payload_type}' does not match message_type '{message_in.message_type}'",
        )

    # Build message record
    db_msg = Message(
        app_id=db_app.id,
        contact_id=db_contact.id,
        from_number=db_app.whatsapp_number,
        to_number=message_in.to_number,
        message_type=message_in.message_type,
        payload=message_in.payload,
        direction="outbound",
        status="sent",
        sent_at=datetime.utcnow(),
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
