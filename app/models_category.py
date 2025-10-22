from sqlmodel import SQLModel, Field
from typing import Optional

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    icon: Optional[str] = Field(default="🎯")
    description: Optional[str] = Field(default=None)
    target: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default="#4CAF50")