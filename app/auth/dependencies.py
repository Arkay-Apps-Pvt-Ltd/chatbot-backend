# app/auth/dependencies.py

from fastapi import Depends, WebSocket, HTTPException, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from models import User
from database import get_db
from config import config

bearer_scheme = HTTPBearer()

SECRET_KEY = config["secret_key"]
ALGORITHM = config["algorithm"]

# For HTTP routes
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode error")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# For WebSocket routes
async def get_current_user_ws(websocket: WebSocket, db: Session):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        raise WebSocketException(code=1008, reason="Missing token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=1008)
            raise WebSocketException(code=1008, reason="Invalid token payload")
    except JWTError:
        await websocket.close(code=1008)
        raise WebSocketException(code=1008, reason="Token decode error")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        await websocket.close(code=1008)
        raise WebSocketException(code=1008, reason="User not found")

    return user
