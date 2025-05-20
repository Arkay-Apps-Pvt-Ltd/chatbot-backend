from sqlalchemy.orm import Session
from models import Tag
from schemas import TagCreate


def create_tag(db: Session, tag: TagCreate):
    db_tag = Tag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def get_tag(db: Session, tag_id: int):
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_tag_by_name(db: Session, name: str):
    return db.query(Tag).filter(Tag.name == name).first()


def get_all_tags(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Tag).offset(skip).limit(limit).all()


def update_tag(db: Session, tag_id: int, tag: TagCreate):
    db_tag = get_tag(db, tag_id)
    db_tag.name = tag.name
    db_tag.status = tag.status
    db.commit()
    db.refresh(db_tag)
    return db_tag


def update_tag_status(db: Session, tag_id: int, status: bool):
    db_tag = get_tag(db, tag_id)
    db_tag.status = status
    db.commit()
    db.refresh(db_tag)
    return db_tag


def delete_tag(db: Session, tag_id: int):
    tag = get_tag(db, tag_id)
    if tag:
        db.delete(tag)
        db.commit()
    return tag
