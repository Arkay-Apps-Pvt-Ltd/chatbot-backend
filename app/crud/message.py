from sqlalchemy.orm import Session
from models import Message
from schemas import MessageBase
from typing import List


def get_chat_messages(
    db: Session, sender_id: int, receiver_id: int, skip: int = 0, limit: int = 50
) -> List[Message]:
    return (
        db.query(Message)
        .filter(
            ((Message.sender_id == sender_id) & (Message.receiver_id == receiver_id))
            | ((Message.sender_id == receiver_id) & (Message.receiver_id == sender_id))
        )
        .order_by(Message.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_message(db: Session, message: MessageBase) -> Message:
    db_message = Message(
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content
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
