from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ImageLink(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    url: str
    name: str = Field(default="")
    description: str = Field(default="")

class Category(SQLModel, table=True):
    """Categoria di consulenza"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    description: Optional[str] = None

class User(SQLModel, table=True):
    """Modello utente/consulente"""
    __tablename__ = "user"  # Nome esplicito tabella
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password: str  # Hash bcrypt
    nome: str
    cognome: Optional[str] = None
    professione: Optional[str] = None
    
    # Relazione con categoria
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    # Profilo consulente
    profile_picture_url: Optional[str] = None
    prezzo_consulenza: Optional[int] = None  # in €
    consulenze_vendute: int = Field(default=0)
    rating: Optional[float] = None
    bollini: int = Field(default=0)
    descrizione: Optional[str] = None
    aree_interesse: Optional[str] = None  # JSON string
    
    # Status
    confirmed: bool = Field(default=False)
    disponibile: bool = Field(default=True)
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Consultation(SQLModel, table=True):
    """Prenotazione consulenza"""
    __tablename__ = "consultation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    consultant_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending")  # pending, confirmed, completed, cancelled
    scheduled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
