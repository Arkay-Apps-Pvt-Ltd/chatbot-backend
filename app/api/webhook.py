from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import App, Contact, Message
import phonenumbers
from phonenumbers import geocoder
import json

from app.crud.message import (
    get_recent_conversations_ws,
    get_contact_by_by_id_ws,
    get_messages_by_contact_ws,
    handle_send_message
)

from app.websocket import broadcast_to_app

router = APIRouter(tags=["Webhook"])


def extract_country_info(wa_id: str):
    try:
        parsed = phonenumbers.parse("+" + wa_id)
        country_code = str(parsed.country_code)
        country_iso = phonenumbers.region_code_for_number(parsed)
        country_name = geocoder.description_for_number(parsed, "en")
        local_number = (
            wa_id[len(country_code) :] if wa_id.startswith(country_code) else wa_id
        )
        return {
            "country_code": country_code,
            "country_iso": country_iso,
            "country_name": country_name,
            "local_number": local_number,
        }
    except Exception:
        return {
            "country_code": "",
            "country_iso": "",
            "country_name": "",
            "local_number": wa_id,
        }


def get_or_create_contact(
    db: Session,
    app_id: int,
    wa_id: str,
    local_number: str,
    name: str,
    country_info: dict,
):
    contact = db.query(Contact).filter_by(app_id=app_id, wa_id=wa_id).first()
    if not contact:
        contact = Contact(
            app_id=app_id,
            wa_id=wa_id,
            mobile_number=local_number,
            country_code=country_info["country_code"],
            name=name,
            last_active_at=datetime.utcnow(),
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
    else:
        contact.last_active_at = datetime.utcnow()
        db.commit()
    return contact


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0].get("value", {})

        # Extract sender info
        contact_data = change.get("contacts", [])[0]
        sender_wa_id = contact_data.get("wa_id")
        if not sender_wa_id:
            raise HTTPException(status_code=400, detail="Missing sender wa_id")
        country_info = extract_country_info(sender_wa_id)
        sender_name = contact_data.get("profile", {}).get("name", "Unknown")
        local_number = country_info["local_number"]

        # Extract message info
        messages = change.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="No message found")
        message_data = messages[0]
        message_type = message_data.get("type", "text")
        timestamp = datetime.fromtimestamp(
            int(message_data.get("timestamp", datetime.utcnow().timestamp()))
        )

        # Extract receiver info (business account)
        receiver_number = change.get("metadata", {}).get("display_phone_number")
        if not receiver_number:
            raise HTTPException(status_code=400, detail="Missing receiver number")
        db_app = db.query(App).filter(App.whatsapp_number == receiver_number).first()
        if not db_app:
            raise HTTPException(status_code=404, detail="App not found for receiver")

        # Get or create sender and receiver contacts
        sender = get_or_create_contact(
            db, db_app.id, sender_wa_id, local_number, sender_name, country_info
        )

        payload = message_data.get(message_type, [])

        # Create Message entry
        message = Message(
            app_id=db_app.id,
            contact_id=sender.id,
            from_number=sender_wa_id,
            to_number=receiver_number,
            message_type=message_type,
            payload=payload,
            direction="inbound",
            status="sent",
            sent_at=timestamp,
            created_at=datetime.utcnow(),
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        result = await get_recent_conversations_ws(db, db_app.id)
        await broadcast_to_app(db_app.id, result)

        msg_result = await get_messages_by_contact_ws(db, db_app.id, sender_wa_id)
        await broadcast_to_app(db_app.id, msg_result)

        return {"status": "success", "message_id": message.id}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Webhook processing error: {str(e)}"
        )
