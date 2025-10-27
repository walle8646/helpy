from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class ImageLink(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    url: str
    name: str = Field(default="")
    description: str = Field(default="")

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    icon: Optional[str] = Field(default="🎯")
    description: Optional[str] = Field(default=None)
    target: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default="#4CAF50")

class User(SQLModel, table=True):
    """Modello utente/consulente"""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_md5: str
    nome: Optional[str] = None
    cognome: Optional[str] = None
    professione: Optional[str] = None
    
    # Relazione con categoria
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    # Profilo consulente
    profile_picture: Optional[str] = None
    prezzo_consulenza: Optional[int] = None
    consulenze_vendute: int = Field(default=0)
    consulenze_acquistate: int = Field(default=0)
    bollini: int = Field(default=0)
    descrizione: Optional[str] = None
    aree_interesse: Optional[str] = None
    
    # Status
    confirmed: int = Field(default=0)
    confirmation_code: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Consultation(SQLModel, table=True):
    """Prenotazione consulenza"""
    __tablename__ = "consultation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    consultant_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending")
    scheduled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ========== MESSAGGISTICA MODELS ==========

class Conversation(SQLModel, table=True):
    """Conversazioni tra utenti (normalizzate: user1_id < user2_id)"""
    __tablename__ = "conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user1_id: int = Field(foreign_key="user.id", index=True)
    user2_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ✅ Relationship con Message
    messages: List["Message"] = Relationship(back_populates="conversation")

class Message(SQLModel, table=True):
    """Messaggi nelle conversazioni"""
    __tablename__ = "messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    sender_id: int = Field(foreign_key="user.id", index=True)
    content: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)  # ✅ AGGIUNTO
    
    # ✅ Relationship con Conversation
    conversation: Optional[Conversation] = Relationship(back_populates="messages")