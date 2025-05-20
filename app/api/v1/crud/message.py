from sqlalchemy.orm import Session
from models import Message
from schemas import MessageCreate
from typing import List


def get_chat_messages(
    db: Session, user1_id: int, user2_id: int, skip: int = 0, limit: int = 50
) -> List[Message]:
    return (
        db.query(Message)
        .filter(
            ((Message.sender_id == user1_id) & (Message.receiver_id == user2_id))
            | ((Message.sender_id == user2_id) & (Message.receiver_id == user1_id))
        )
        .order_by(Message.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_message(db: Session, message: MessageCreate) -> Message:
    db_message = Message(
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content,
        attachment_url=message.attachment_url,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def mark_as_delivered(db: Session, msg_id: int) -> bool:
    msg = db.query(Message).filter(Message.id == msg_id).first()
    if not msg:
        return False
    msg.is_delivered = True
    db.commit()
    return True


def mark_as_read(db: Session, msg_id: int) -> bool:
    msg = db.query(Message).filter(Message.id == msg_id).first()
    if not msg:
        return False
    msg.is_read = True
    db.commit()
    return True
