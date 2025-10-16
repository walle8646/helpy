from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    password_md5: str = Field(nullable=False)
    confirmation_code: Optional[str] = Field(default=None, max_length=6)
    confirmed: int = Field(default=0)
    created_at: Optional[str] = Field(default=None)
