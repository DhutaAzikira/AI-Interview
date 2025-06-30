from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Frontend"])
templates = Jinja2Templates(directory="templates")

@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Serve Homepage",
    description="Serves the main `index.html` template which contains the frontend application."
)
async def get_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})