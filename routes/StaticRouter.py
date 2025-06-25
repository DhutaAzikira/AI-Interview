from fastapi import APIRouter, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/")
async def get_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})