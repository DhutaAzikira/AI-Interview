import asyncio
import json
from typing import Dict
import httpx  # An async-friendly version of the requests library
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
import os
from dotenv import load_dotenv

load_dotenv()
# --- Configuration ---

N8N_START_INTERVIEW_URL = os.getenv("N8N_START_INTERVIEW_URL")
GLADIA_API_KEY = os.getenv("GLADIA_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_SERVER_URL = os.getenv("HEYGEN_SERVER_URL")

# --- Application Setup ---
app = FastAPI()

# Mount folders for static files (CSS, JS) and templates (HTML)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory storage (replaces the need for Redis for this simple case)
SESSIONS: Dict[str, Dict] = {}
active_connections: Dict[str, WebSocket] = {}

# --- Helper Functions ---
async def connect(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    print(f"WebSocket connected for session: {session_id}")

def disconnect(session_id: str):
    if session_id in active_connections:
        del active_connections[session_id]
    print(f"WebSocket disconnected for session: {session_id}")


async def send_personal_message(message: dict, session_id: str):
    # Check if a websocket connection exists for the given session_id
    if session_id in active_connections:
        websocket = active_connections[session_id]
        await websocket.send_json(message)
        # If successful, print a success message
        print(f"SUCCESS: Sent message to session '{session_id}': {message}")
    else:
        # If no connection is found, print a detailed error message
        print("--------------------------------------------------")
        print(f"ERROR: Could not find an active WebSocket connection for session_id: '{session_id}'")
        print(f"Currently active connections are for these session_ids: {list(active_connections.keys())}")
        print("--------------------------------------------------")

async def forward_answer_to_n8n(session_id: str, answer: str):
    session_data = SESSIONS.get(session_id)
    if not session_data or not session_data.get('resumeUrl'):
        print(f"Error: Could not find resumeUrl for session {session_id}")
        return

    resume_url = session_data['resumeUrl']
    print(f"Forwarding answer for session {session_id} to {resume_url}")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(resume_url, json={'sessionId': session_id, 'answer': answer})
        except httpx.RequestError as e:
            print(f"Error forwarding answer to n8n: {e}")

# --- Frontend Endpoint ---
@app.get("/")
async def get_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- API Endpoints ---
@app.post("/api/interview/start")
async def start_interview(request: Request):
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(N8N_START_INTERVIEW_URL, json=body, timeout=30.0)
            response.raise_for_status()
            n8n_data = response.json()

        session_id = n8n_data.get('sessionId')
        resume_url = n8n_data.get('resumeUrl')
        if not session_id or not resume_url:
            raise Exception('n8n did not return a valid sessionId and resumeUrl.')

        SESSIONS[session_id] = {'resumeUrl': resume_url}
        print(f"Started session {session_id}, resumeUrl: {resume_url}")
        return {"sessionId": session_id}
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/api/send-question")
async def send_question(request: Request):
    body = await request.json()
    session_id = body.get('sessionId')
    question_text = body.get('question')
    message = {'type': 'new_question', 'payload': {'text': question_text}}
    await send_personal_message(message, session_id)
    return {"status": "Question sent to client."}

@app.post("/api/interview/end")
async def end_interview(request: Request):
    body = await request.json()
    session_id = body.get('sessionId')
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    message = {'type': 'end_interview'}
    await send_personal_message(message, session_id)
    return {"status": "End interview command sent."}

# --- Proxy Endpoints for Security ---
@app.post("/api/gladia/init")
async def gladia_api_init(request: Request):
    headers = {'X-Gladia-Key': GLADIA_API_KEY, 'Content-Type': 'application/json'}
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.gladia.io/v2/live", headers=headers, json=await request.json())
        return response.json()

@app.post("/api/heygen/task")
async def heygen_api_task(request: Request):
    headers = {'Authorization': f"Bearer {HEYGEN_API_KEY}", 'Content-Type': 'application/json'}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.task"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=await request.json())
        return {"status": "ok"}, response.status_code

# --- WebSocket Endpoint ---
@app.websocket("/ws/interview/{session_id:path}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "user_answer":
                answer = data.get("payload", {}).get("answer")
                if answer:
                    # Pass the email (stored in session_id) to the n8n handler
                    await forward_answer_to_n8n(session_id, answer)
    except WebSocketDisconnect:
        disconnect(session_id)


# Add these new proxy endpoints for HeyGen session management

@app.post("/api/heygen/create_token")
async def heygen_create_token():
    headers = {'X-Api-Key': HEYGEN_API_KEY}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.create_token"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers)
        response.raise_for_status()
        return response.json()


# Replace the existing heygen_new_session function with this corrected version

@app.post("/api/heygen/new_session")
async def heygen_new_session(request: Request):
    try:
        body = await request.json()
        token = body.get("token")
        if not token:
            return JSONResponse(status_code=400, content={"error": "Session token is missing"})

        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.new"

        # --- THIS IS THE CORRECT, COMPLETE REQUEST BODY ---
        heygen_body = {
            "quality": "medium",
            "avatar_name": "Wayne_20240711",  # Or your preferred avatar ID
            "voice": {
                "rate": 1
            },
            "video_encoding": "VP8",
            "disable_idle_timeout": False,
            "version": "v2",
            "stt_settings": {
                "provider": "deepgram",
                "confidence": 0.55
            },
            "activity_idle_timeout": 120
        }
        # ----------------------------------------------------

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, json=heygen_body, timeout=30.0)

            # This print statement is still useful for debugging
            print("--- HEYGEN /new_session RESPONSE ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            print("------------------------------------")

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": "HeyGen API returned a non-200 status", "details": response.text}
                )

            response_data = response.json()

            if not response_data.get("data") or not response_data["data"].get("url"):
                print("ERROR: HeyGen returned a successful status but the response is missing the LiveKit URL.")
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "Could not establish a video stream with the avatar service. Please check API limits or status."}
                )

            return response_data

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/heygen/start_session")
async def heygen_start_session(request: Request):
    body = await request.json()
    token = body.get("token")
    session_id = body.get("session_id")
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.start"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json={"session_id": session_id})
        response.raise_for_status()
        return response.json()


@app.post("/api/heygen/stop_session")
async def heygen_stop_session(request: Request):
    body = await request.json()
    token = body.get("token")
    session_id = body.get("session_id")
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.stop"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json={"session_id": session_id})
        response.raise_for_status()
        return response.json()