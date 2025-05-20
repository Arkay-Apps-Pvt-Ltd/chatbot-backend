from sqlalchemy.orm import Session
from models import Contact, Tag
from schemas import ContactCreate, ContactUpdate


def get_contact(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()


def get_all_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Contact).offset(skip).limit(limit).all()


def create_contact(db: Session, contact_in: ContactCreate):
    contact = Contact(**contact_in.dict())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, contact_id: int, contact_in: ContactUpdate):
    contact = get_contact(db, contact_id)
    if not contact:
        return None
    for field, value in contact_in.dict(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: int):
    contact = get_contact(db, contact_id)
    if contact:
        db.delete(contact)
        db.commit()
    return contact


def update_opted_in_status(db: Session, contact_id: int, status: bool):
    db_contact = get_contact(db, contact_id)
    db_contact.opted_in = status
    db.commit()
    db.refresh(db_contact)
    return db_contact
