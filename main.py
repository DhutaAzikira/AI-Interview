from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routes import StaticRouter, InterviewRouter, HeyGenRouter, GladiaRouter

# --- Application Setup ---
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(StaticRouter.router)
app.include_router(InterviewRouter.router)
app.include_router(HeyGenRouter.router)
app.include_router(GladiaRouter.router)

#test2