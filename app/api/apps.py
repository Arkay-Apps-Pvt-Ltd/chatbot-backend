from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from database import get_db
from models import App
from schemas import AppCreate, AppRead
from dependency import get_current_user

router = APIRouter(tags=["Apps"])


@router.get("/apps", response_model=list[AppRead])
def get_apps(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return db.query(App).filter(App.user_id == user.id).offset(skip).limit(limit).all()


@router.post("/apps", response_model=AppRead)
def create_app(
    app: AppCreate, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    existing = (
        db.query(App).filter(App.business_name == app.business_name, App.user_id == user.id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="App with this name already exists")

    # Convert Pydantic model to dict and include user_id
    db_app = App(**app.dict(), user_id=user.id)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.get("/apps/{app_id}", response_model=AppRead)
def get_app(app_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    app = db.query(App).filter(App.id == app_id, App.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.put("/apps/{app_id}", response_model=AppRead)
def update_app(
    app_id: int,
    app_update: AppCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_app = db.query(App).filter(App.id == app_id, App.user_id == user.id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="App not found")

    db_app.name = app_update.name
    db_app.status = app_update.status
    db.commit()
    db.refresh(db_app)
    return db_app


@router.delete("/apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_app(
    app_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    app = db.query(App).filter(App.id == app_id, App.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    db.delete(app)
    db.commit()
    # Return 204 No Content (no body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
