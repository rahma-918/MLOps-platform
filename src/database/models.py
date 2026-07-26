"""
Modèles SQLAlchemy définissant le schéma de la base de données :
users -> conversations -> messages.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=True)  # ex: généré à partir de la 1ère question
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" ou "assistant"
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # liste des sources citées (pour les réponses assistant)
    category_filter = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")