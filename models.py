from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)


# Association table for many-to-many Contact <-> Tag
contact_tags = Table(
    'contact_tags',
    Base.metadata,
    Column('contact_id', Integer, ForeignKey('contacts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    country_code = Column(String(20), nullable=False)
    mobile_number = Column(String(20), nullable=False, index=True)
    source = Column(String(50), nullable=True)
    status = Column(Boolean, default=True)
    last_active_at = Column(DateTime, nullable=True)
    incoming = Column(Boolean, default=True)
    opted_in = Column(Boolean, default=True)

    tags = relationship("Tag", secondary=contact_tags, back_populates="contacts")

    sent_messages = relationship("Message", foreign_keys='Message.sender_id', back_populates="sender")
    received_messages = relationship("Message", foreign_keys='Message.receiver_id', back_populates="receiver")


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    status = Column(Boolean, default=True)

    contacts = relationship("Contact", secondary=contact_tags, back_populates="tags")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # hashed password

    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    contact = relationship("Contact", backref="users")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("contacts.id"))
    receiver_id = Column(Integer, ForeignKey("contacts.id"))
    content = Column(Text, nullable=True)
    attachment_url = Column(String(255), nullable=True)
    is_delivered = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship("Contact", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("Contact", foreign_keys=[receiver_id], back_populates="received_messages")
