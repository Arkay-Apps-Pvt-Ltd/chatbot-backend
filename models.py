from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Table,
    Enum,
    BigInteger,
    Double,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Association table for many-to-many relationship between Contact and Tag
contact_tags = Table(
    "contact_tags",
    Base.metadata,
    Column("contact_id", Integer, ForeignKey("contacts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False)
    whatsapp_number = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    is_whatsapp_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    status = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ✅ Define back relationship to Contact
    contacts = relationship("Contact", secondary=contact_tags, back_populates="tags")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False, index=True)
    country_code = Column(String(10), nullable=False)  # 📌 "91"
    mobile_number = Column(String(20), nullable=False)  # 📌 "7990152399"
    wa_id = Column(
        String(20), nullable=False, index=True
    )  # 📌 "917990152399" (country_code+mobile_number)
    name = Column(String(100), nullable=True)
    profile_name = Column(String(100), nullable=True)
    source = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    last_active_at = Column(DateTime, nullable=True)
    incoming = Column(Boolean, default=True)
    opted_in = Column(Boolean, default=True)
    language = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔥 Add this relationship
    tags = relationship("Tag", secondary=contact_tags, back_populates="contacts")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)

    # WhatsApp-specific fields
    # message_id = Column(String(100), nullable=False, unique=True)
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)

    message_type = Column(
        Enum(
            "text",
            "image",
            "video",
            "audio",
            "document",
            "location",
            "contacts",
            "sticker",
            "reaction",
            "system",
            name="message_type_enum",
        ),
        nullable=False,
    )

    payload = Column(JSON, nullable=False)  # Store full 'messages' JSON here

    direction = Column(
        Enum("inbound", "outbound", name="message_direction_enum"), nullable=False
    )
    status = Column(
        Enum("sent", "delivered", "read", "failed", name="message_status_enum"),
        nullable=False,
        server_default="sent",
    )

    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
