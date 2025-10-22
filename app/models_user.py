from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_md5: str
    confirmation_code: Optional[str] = Field(default=None, max_length=6)
    confirmed: int = Field(default=0)
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Campi profilo
    nome: Optional[str] = Field(default=None)
    professione: Optional[str] = Field(default=None)
    descrizione: Optional[str] = Field(default=None)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    bollini: int = Field(default=0)
    consulenze_acquistate: int = Field(default=0)
    consulenze_vendute: int = Field(default=0)
    aree_interesse: Optional[str] = Field(default=None)
    prezzo_consulenza: Optional[int] = Field(default=150)
    durata_consulenza: Optional[int] = Field(default=60)
    profile_picture: Optional[str] = None  # 🔥 AGGIUNGI QUESTA RIGA
