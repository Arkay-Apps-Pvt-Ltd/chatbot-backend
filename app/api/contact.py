from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas import ContactCreate, ContactUpdate, ContactRead
from app.crud import contacts as contact_crud


# Dependency to get DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(tags=["Contacts"])


@router.get("/contacts", response_model=list[ContactRead])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return contact_crud.get_all_contacts(db, skip=skip, limit=limit)


@router.post("/contacts", response_model=ContactRead)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    return contact_crud.create_contact(db, contact)


@router.get("/contacts/{contact_id}", response_model=ContactRead)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = contact_crud.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)
):
    updated = contact_crud.update_contact(db, contact_id, contact)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated


@router.get("/contacts/{contact_id}/opted-in")
def update_tag_status(
    contact_id: int,
    status: bool = Query(..., description="New status for the tag"),
    db: Session = Depends(get_db),
):
    contact = contact_crud.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db_tag = contact_crud.update_opted_in_status(db, contact_id, status)
    return db_tag


@router.delete("/contacts/{contact_id}", response_model=ContactRead)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    deleted = contact_crud.delete_contact(db, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return deleted
