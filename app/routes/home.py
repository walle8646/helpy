from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import get_session
from app.models import ImageLink
from sqlmodel import select
from app.logger_config import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    image_names = [
        "home_pricipal_image",
        "sara",
        "mic",
        "david",
        "amily"
    ]
    urls = {name: "" for name in image_names}
    with get_session() as session:
        statement = select(ImageLink).where(ImageLink.name.in_(image_names))
        results = session.exec(statement).all()
        for img in results:
            urls[img.name] = img.url
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "hero_img_url": urls["home_pricipal_image"],
            "sara_img_url": urls["sara"],
            "mic_img_url": urls["mic"],
            "david_img_url": urls["david"],
            "amily_img_url": urls["amily"],
            "title": "Helpy - Home"
        }
    )
