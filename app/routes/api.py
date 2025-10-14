from fastapi import APIRouter
from app.database import get_session
from sqlmodel import select

router = APIRouter(prefix="/api", tags=["api"])
