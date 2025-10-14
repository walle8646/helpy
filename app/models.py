from sqlmodel import SQLModel, Field

class ImageLink(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    url: str
    name: str = Field(default="")
    description: str = Field(default="")
