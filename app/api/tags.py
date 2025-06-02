from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi.responses import Response

from database import get_db
from models import Tag
from schemas import TagCreate, TagRead, TagUpdate

router = APIRouter(tags=["Tags"])


@router.get("/tags", response_model=list[TagRead])
def get_tags(
    skip: int = 0,
    limit: int = 100,
    app_id: int = Query(description="Filter by App ID"),
    db: Session = Depends(get_db),
):
    return db.query(Tag).filter(Tag.app_id == app_id).offset(skip).limit(limit).all()


@router.post("/tags", response_model=TagRead)
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Tag).filter(Tag.name == tag.name, Tag.app_id == tag.app_id).first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Tag with this name already exists for this app"
        )

    db_tag = Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.get("/tags/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.put("/tags/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, tag: TagCreate, db: Session = Depends(get_db)):
    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check for duplicate tag name within the same app_id if the name or app_id has changed
    if db_tag.name != tag.name or db_tag.app_id != tag.app_id:
        existing = (
            db.query(Tag).filter(Tag.name == tag.name, Tag.app_id == tag.app_id).first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Tag with this name already exists for this app"
            )

    db_tag.name = tag.name
    db_tag.status = tag.status
    db_tag.app_id = tag.app_id
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.get("/tags/{tag_id}/update-status")
def update_tag_status(
    tag_id: int,
    status: bool = Query(..., description="New status for the tag"),
    db: Session = Depends(get_db),
):
    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db_tag.status = status
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(tag)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
