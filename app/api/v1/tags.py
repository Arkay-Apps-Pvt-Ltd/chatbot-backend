from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas import TagCreate, TagRead, TagStatusUpdate
from app.api.v1.crud import tags


# Dependency to get DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("/", response_model=list[TagRead])
def read_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return tags.get_all_tags(db, skip=skip, limit=limit)


@router.post("/", response_model=TagRead)
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    existing = tags.get_tag_by_name(db, tag.name)
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")
    return tags.create_tag(db, tag)


@router.get("/{tag_id}", response_model=TagRead)
def read_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = tags.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.put("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, tag: TagCreate, db: Session = Depends(get_db)):
    db_tag = tags.get_tag(db, tag_id)
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db_tag = tags.update_tag(db, tag_id, tag)
    return db_tag


@router.get("/{tag_id}/update-status")
def update_tag_status(
    tag_id: int,
    status: bool = Query(..., description="New status for the tag"),
    db: Session = Depends(get_db),
):
    db_tag = tags.get_tag(db, tag_id)
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db_tag = tags.update_tag_status(db, tag_id, status)
    return db_tag


@router.delete("/{tag_id}", response_model=TagRead)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = tags.delete_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag
