from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Contact, Tag
from schemas import ContactCreate, ContactUpdate, ContactRead

router = APIRouter(tags=["Contacts"])


@router.get("/contacts", response_model=List[ContactRead])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Contact).offset(skip).limit(limit).all()


@router.post("/contacts", response_model=ContactRead)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    contact_data = contact.dict(exclude={"tag_ids"})

    # Compute wa_id
    wa_id = f"{contact.country_code}{contact.mobile_number}"
    contact_data["wa_id"] = wa_id

    # Check for existing contact with same app_id + wa_id
    existing = (
        db.query(Contact)
        .filter(and_(Contact.app_id == contact.app_id, Contact.wa_id == wa_id))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A contact with this app_id and wa_id already exists.",
        )

    # Create contact
    db_contact = Contact(**contact_data)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)

    # Handle tag_ids (if provided)
    if contact.tag_ids:
        try:
            tag_ids = [int(tid) for tid in contact.tag_ids]
            db_tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            db_contact.tags.extend(db_tags)
            db.commit()
            db.refresh(db_contact)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid tag_ids format. Must be list of integers or strings of integers.",
            )

    return db_contact


@router.get("/contacts/{contact_id}", response_model=ContactRead)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)
):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = contact.dict(exclude_unset=True, exclude={"tag_ids"})

    # If country_code or mobile_number or app_id updated, recompute wa_id and check uniqueness
    country_code = update_data.get("country_code", db_contact.country_code)
    mobile_number = update_data.get("mobile_number", db_contact.mobile_number)
    app_id = update_data.get("app_id", db_contact.app_id)
    wa_id = f"{country_code}{mobile_number}"
    update_data["wa_id"] = wa_id

    existing = (
        db.query(Contact)
        .filter(
            and_(
                Contact.app_id == app_id,
                Contact.wa_id == wa_id,
                Contact.id != contact_id,
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Another contact with this app_id and wa_id already exists.",
        )

    for field, value in update_data.items():
        setattr(db_contact, field, value)

    # Handle tag_ids update if provided
    if contact.tag_ids is not None:
        try:
            tag_ids = [int(tid) for tid in contact.tag_ids]
            db_tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            db_contact.tags = db_tags
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid tag_ids format. Must be list of integers or strings of integers.",
            )

    db.commit()
    db.refresh(db_contact)
    return db_contact


@router.get("/contacts/{contact_id}/opted-in")
def update_opted_in_status(
    contact_id: int, status: bool = Query(...), db: Session = Depends(get_db)
):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db_contact.opted_in = status
    db.commit()
    db.refresh(db_contact)
    return db_contact


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
