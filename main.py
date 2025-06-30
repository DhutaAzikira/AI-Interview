from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import StaticRouter, InterviewRouter, HeyGenRouter, GladiaRouter

# --- Application Setup ---
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(StaticRouter.router)
app.include_router(InterviewRouter.router)
app.include_router(HeyGenRouter.router)
app.include_router(GladiaRouter.router)

#test1