import uuid
from sqlalchemy.orm import Session
from src.database.models import User, Conversation, Message
from src.core.hashing import hash_password, verify_password


# ---------- Users ----------
def get_user(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == uuid.UUID(user_id)).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def create_user(db: Session, email: str, password: str, full_name: str = None) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


# ---------- Conversations ----------
def create_conversation(db: Session, user_id: uuid.UUID, title: str = None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID = None) -> Conversation | None:
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    return query.first()


def list_conversations(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


# ---------- Messages ----------
def add_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    sources: list = None,
    category_filter: str = None,
    document_id_filter: str = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        category_filter=category_filter,
        document_id_filter=document_id_filter,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message