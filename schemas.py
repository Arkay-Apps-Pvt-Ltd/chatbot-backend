from typing import Union, Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, constr
import json

from typing import Any
from enum import Enum


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    user: UserOut


class AppCreate(BaseModel):
    business_name: str
    whatsapp_number: str
    status: bool | None = True


class AppRead(BaseModel):
    id: int
    business_name: str
    whatsapp_number: str
    is_active: bool
    is_whatsapp_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    app_id: int  # ✅ Linking tag to app
    name: str
    status: bool = True


class TagRead(BaseModel):
    id: int
    name: str
    status: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagUpdate(BaseModel):
    name: str
    status: bool = True


class TagStatusUpdate(BaseModel):
    status: bool


class ContactBase(BaseModel):
    name: str
    app_id: int
    profile_name: Optional[str] = None
    country_code: constr(strip_whitespace=True, min_length=1)
    mobile_number: constr(strip_whitespace=True, min_length=5)
    source: Optional[str] = None
    is_active: Optional[bool] = True
    last_active_at: Optional[datetime] = None
    incoming: Optional[bool] = True
    opted_in: Optional[bool] = True

    class Config:
        from_attributes = True


class ContactCreate(ContactBase):
    tag_ids: Optional[List[str]] = []


class ContactUpdate(ContactBase):
    tag_ids: Optional[List[str]] = []


class ContactRead(ContactBase):
    id: int
    wa_id: str
    created_at: datetime
    updated_at: datetime
    tags: List[TagRead] = []

    class Config:
        from_attributes = True


class MessageType(str, Enum):
    text = "text"
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"
    location = "location"
    contacts = "contacts"
    sticker = "sticker"
    reaction = "reaction"
    system = "system"

class MessageCreate(BaseModel):
    app_id: int
    to_number: str
    message_type: MessageType
    payload: Union[Dict[str, Any], List[Any]]