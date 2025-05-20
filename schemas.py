from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    first_name: str
    last_name: str | None = None
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    first_name: str
    last_name: str | None = None
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


class MessageCreate(BaseModel):
    sender_id: int | None = None
    receiver_id: int
    content: str
    attachment_url: str | None = None


class TagBase(BaseModel):
    name: str
    status: bool


class TagCreate(TagBase):
    pass

class TagStatusUpdate(BaseModel):
    status: bool

class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ContactBase(BaseModel):
    name: str
    country_code: str = None
    mobile_number: str
    source: Optional[str] = None
    status: Optional[bool] = True
    last_active_at: Optional[datetime] = None
    incoming: Optional[bool] = True
    opted_in: Optional[bool] = True

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    pass

class ContactRead(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagRead] = []

    class Config:
        from_attributes = True

class ChatItemSchema(BaseModel):
    contact_id: int
    name: str
    avatar: Optional[str]
    lastMessage: Optional[str]
    time: Optional[str]
    unread: int
    online: bool