import uuid
from sqlalchemy.orm import Session
from src.database.models import User, Conversation, Message


def create_user(db: Session) -> User:
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_conversation(db: Session, user_id: uuid.UUID = None, title: str = None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: uuid.UUID) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def add_message(db: Session, conversation_id: uuid.UUID, role: str, content: str,
                 sources: list = None, category_filter: str = None) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        category_filter=category_filter,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_conversations(db: Session, user_id: uuid.UUID = None) -> list[Conversation]:
    query = db.query(Conversation)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    return query.order_by(Conversation.created_at.desc()).all()