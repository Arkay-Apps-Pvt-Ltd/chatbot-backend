import httpx
from fastapi import HTTPException
import json

from models import Message

GUPSHUP_API_URL = "https://api.gupshup.io/sm/api/v1/msg"
GUPSHUP_SOURCE = "15557546242"
GUPSHUP_APP_NAME = "arkayappsv1"
GUPSHUP_API_KEY = "awdxg2aymfgsjcrrrufuvu5y4u1hd5xi"


async def send_message_via_gupshup(message: Message):
    # Prepare common fields
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE,  # your business whatsapp number
        "destination": message.to_number,  # recipient number
        "src.name": GUPSHUP_APP_NAME,
    }

    # Build message body depending on type
    if message.message_type == "text":
        message_data = {
            "type": "text",
            "text": (
                message.payload.get("body")
                if isinstance(message.payload, dict)
                else str(message.payload)
            ),
        }
    elif message.message_type == "contacts":
        # Ensure payload is list of contacts
        message_data = {"type": "contacts", "contacts": message.payload}
    elif message.message_type == "image":
        message_data = {
            "type": "image",
            "originalUrl": message.payload.get("url"),
            "previewUrl": message.payload.get("caption", ""),
        }
    elif message.message_type == "video":
        message_data = {
            "type": "video",
            "url": message.payload.get("url")
        }
    elif message.message_type == "document":
        message_data = {
            "type": "file",
            "url": message.payload.get("url"),
            "filename": "Sample file",
        }
    else:
        # Add other types if needed
        raise ValueError(f"Unsupported message type: {message.message_type}")

    # ✅ Gupshup requires `message` as a JSON string
    payload["message"] = json.dumps(message_data)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",  # Gupshup requires this
        "apikey": GUPSHUP_API_KEY,
    }

    print("Sending to Gupshup:", payload)

    try:
        response = httpx.post(GUPSHUP_API_URL, data=payload, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Gupshup error: {e.response.text}")
