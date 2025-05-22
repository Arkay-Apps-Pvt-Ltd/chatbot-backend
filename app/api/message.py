from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from schemas import MessageCreate, ChatItemSchema, MessageBase
from app.crud import message as crud_message
from models import Contact, Message
from sqlalchemy import desc, and_, or_, func
from app.auth.dependencies import get_current_user
from datetime import datetime, timedelta
from utils import format_time
import httpx
import json


router = APIRouter(tags=["Messages"])


@router.get("/conversations", response_model=list[ChatItemSchema])
def get_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get chat contacts with last message info and unread counts for the current user.
    """
    current_contact_id = current_user.contact_id

    # Get contact IDs that have exchanged messages with current user
    contact_ids = (
        db.query(Message.sender_id)
        .filter(Message.receiver_id == current_contact_id)
        .union(
            db.query(Message.receiver_id).filter(
                Message.sender_id == current_contact_id
            )
        )
        .distinct()
        .all()
    )

    # Flatten list of tuples
    contact_ids = [id[0] for id in contact_ids]

    # Query contact details
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

    chat_items = []

    for contact in contacts:
        # Get last message between current user and this contact
        last_msg = (
            db.query(Message)
            .filter(
                or_(
                    and_(
                        Message.sender_id == current_contact_id,
                        Message.receiver_id == contact.id,
                    ),
                    and_(
                        Message.sender_id == contact.id,
                        Message.receiver_id == current_contact_id,
                    ),
                )
            )
            .order_by(desc(Message.timestamp))
            .first()
        )

        if not last_msg:
            continue

        # Count unread messages sent by contact to current user
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.sender_id == contact.id,
                Message.receiver_id == current_contact_id,
                Message.is_read == False,
            )
            .scalar()
        )

        chat_items.append(
            ChatItemSchema(
                contact_id=contact.id,
                name=contact.name,
                avatar=getattr(contact, "avatar_url", None),
                lastMessage=last_msg.content,
                time=format_time(last_msg.timestamp),
                unread=unread_count,
                online=contact.last_active_at is not None
                and (datetime.utcnow() - contact.last_active_at) < timedelta(minutes=5),
            )
        )

    return chat_items


@router.get("/conversations/{receiver_id}/messages")
def get_chat_history(
    receiver_id: int,
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get chat message history between current user and another contact.
    """
    sender_id = current_user.contact_id

    messages = crud_message.get_chat_messages(
        db, sender_id, receiver_id, skip, limit
    )

    return [
        {
            "id": msg.id,
            "content": msg.content,
            "is_delivered": msg.is_delivered,
            "is_read": msg.is_read,
            "direction": "sent" if msg.sender_id == sender_id else "received",
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in reversed(messages)  # ascending order
    ]


@router.post("/conversations/{receiver_id}/send")
def send_message(
    receiver_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sender_id = current_user.contact_id

    # Fetch receiver contact to get their number
    receiver_contact = db.query(Contact).filter_by(id=receiver_id).first()
    if not receiver_contact:
        raise HTTPException(status_code=404, detail="Receiver contact not found")

    json_message = {"type": "text", "text": message.content}
    # Prepare payload for Gupshup
    payload = {
        "channel": "whatsapp",
        "source": 15557546242,
        "destination": receiver_contact.mobile_number,
        "message": json.dumps(json_message),
        "src.name": "arkayappsv1",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": "awdxg2aymfgsjcrrrufuvu5y4u1hd5xi",
    }

    # Send message to Gupshup
    try:
        response = httpx.post(
            "https://api.gupshup.io/sm/api/v1/msg", data=payload, headers=headers
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Gupshup error: {e.response.text}")

    # Save message to DB after successful API send

    full_message_data = MessageBase(
        **message.dict(), sender_id=sender_id, receiver_id=receiver_id
    )
    db_message = crud_message.create_message(db, full_message_data)

    return {
        "id": db_message.id,
        "content": db_message.content,
        "is_delivered": db_message.is_delivered,
        "is_read": db_message.is_read,
        "direction": "sent" if db_message.sender_id == sender_id else "received",
        "timestamp": db_message.timestamp.isoformat(),
    }


@router.get("/conversations/{msg_id}/mark-delivered")
def mark_message_delivered(msg_id: int, db: Session = Depends(get_db)):
    """
    Mark a message as delivered.
    """
    success = crud_message.mark_as_delivered(db, msg_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "delivered", "message_id": msg_id}


@router.get("/conversations/{msg_id}/mark-read")
def mark_message_read(msg_id: int, db: Session = Depends(get_db)):
    """
    Mark a message as read.
    """
    success = crud_message.mark_as_read(db, msg_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "read", "message_id": msg_id}
