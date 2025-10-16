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
    descrizione: Optional[str] = Field(default=None)  # NUOVO: descrizione biografica
    macro_aree: Optional[str] = Field(default=None)
    bollini: int = Field(default=0)
    consulenze_acquistate: int = Field(default=0)
    consulenze_vendute: int = Field(default=0)
    aree_interesse: Optional[str] = Field(default=None)
    prezzo_consulenza: Optional[int] = Field(default=150)  # NUOVO: prezzo in euro
    durata_consulenza: Optional[int] = Field(default=60)  # NUOVO: durata in minuti
