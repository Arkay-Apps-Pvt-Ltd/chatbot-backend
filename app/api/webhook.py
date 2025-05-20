from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal  # Ensure you have this or similar function
from models import Contact, Message
import phonenumbers

def extract_country_code(wa_id: str):
    parsed = phonenumbers.parse("+" + wa_id)
    return str(parsed.country_code)


# Dependency to get DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(tags=["Webhook"])

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    data = await request.json()
    try:
        change = data["entry"][0]["changes"][0]["value"]

        # Extract sender info
        contact_data = change["contacts"][0]
        sender_wa_id = contact_data["wa_id"]  # e.g. "917990152399"
        country_code = extract_country_code(sender_wa_id)
        sender_name = contact_data["profile"]["name"]

        # Extract message info
        message_data = change["messages"][0]
        text = message_data["text"]["body"]
        timestamp = datetime.fromtimestamp(int(message_data["timestamp"]))

        # Extract receiver info (your business account)
        receiver_number = change["metadata"]["display_phone_number"]  # e.g. "15557546242"

        # Get or create sender contact
        sender = db.query(Contact).filter_by(mobile_number=sender_wa_id).first()
        if not sender:
            sender = Contact(
                name=sender_name,
                country_code=country_code,
                mobile_number=sender_wa_id,
                last_active_at=timestamp
            )
            db.add(sender)
            db.commit()
            db.refresh(sender)
        else:
            sender.last_active_at = timestamp
            db.commit()

        # Get or create receiver contact (your business number)
        receiver = db.query(Contact).filter_by(mobile_number=receiver_number).first()
        if not receiver:
            receiver = Contact(
                name="Business Number",
                mobile_number=receiver_number,
                last_active_at=timestamp
            )
            db.add(receiver)
            db.commit()
            db.refresh(receiver)

        # Create and store message
        message = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=text,
            timestamp=timestamp
        )
        db.add(message)
        db.commit()

        return {"status": "success"}

    except KeyError as e:
        return {"status": "error", "message": f"Invalid request format: {str(e)}"}
