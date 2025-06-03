from sqlalchemy.orm import Session
from models import App, Contact, Message
from utils import human_readable_time_diff
from sqlalchemy import func, desc, asc, and_
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from schemas import MessageCreate
from app.services.message_service import send_message_via_gupshup


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

    return {"conversations": conversations}


async def get_contact_by_by_id_ws(db: Session, app_id: int, wa_id: str):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found", "messages": []}

    # Fetch profile (Contact)
    contact = (
        db.query(Contact)
        .filter(Contact.app_id == app_id, Contact.wa_id == wa_id)
        .first()
    )
    if not contact:
        return {"error": "Contact not found", "messages": []}

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


async def get_messages_by_contact_ws(
    db: Session, app_id: int, wa_id: str, offset: int = 0, limit: int = 30
):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return {"error": "App not found", "messages": []}

    contact = db.query(Contact).filter(Contact.wa_id == wa_id).first()
    if not contact:
        return {"error": "Contact not found", "messages": []}

    total_messages = (
        db.query(func.count(Message.id))
        .filter(Message.app_id == app_id, Message.contact_id == contact.id)
        .scalar()
    )

    # Calculate reverse offset: start from the most recent
    reverse_offset = max(total_messages - offset - limit, 0)

    messages_query = (
        db.query(Message)
        .filter(Message.app_id == app_id, Message.contact_id == contact.id)
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
            "payload": m.payload,
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


async def handle_send_message(
    db: Session, message_in: MessageCreate
):
    # Validate app
    db_app = db.query(App).filter(App.id == message_in.app_id).first()
    if not db_app:
        return {"error": "App not found"}

    db_contact = db.query(Contact).filter(Contact.wa_id == message_in.to_number).first()
    if not db_contact:
        return {"error": "Contact not found", "messages": []}

    # Convert timestamps
    sent_at = datetime.utcnow()
    received_at = None
    read_at = None

    # Create message
    db_msg = Message(
        app_id=db_app.id,
        contact_id=db_contact.id,
        from_number=db_app.whatsapp_number,
        to_number=message_in.to_number,
        message_type=message_in.message_type,
        payload=message_in.payload,
        direction="outbound",
        status="sent",
        sent_at=sent_at,
        received_at=received_at,
        read_at=read_at,
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    # Send via Gupshup
    try:
        await send_message_via_gupshup(db_msg)
    except Exception as e:
        print(e)
        raise e

    msg_data = jsonable_encoder(db_msg)

    return {
        "type": "new_message",
        "contact_number": message_in.to_number,
        "message": msg_data,
    }
