from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.logger_config import logger
from app.database import create_db_and_tables
from app.routes import home, api
from fastapi import APIRouter
from app.models import ImageLink
from app.database import get_session
from sqlmodel import select

app = FastAPI(title="helpy")

app.include_router(home.router)
app.include_router(api.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/imagelinks", response_model=list[ImageLink])
def get_image_links():
    with get_session() as session:
        return session.exec(select(ImageLink)).all()

@router.post("/imagelinks", response_model=ImageLink)
def create_image_link(link: ImageLink):
    with get_session() as session:
        session.add(link)
        session.commit()
        session.refresh(link)
        return link
