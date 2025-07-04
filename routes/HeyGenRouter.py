from fastapi import APIRouter, Request, Body, HTTPException
import httpx
from . import schemas
import os
from dotenv import load_dotenv

load_dotenv()

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_SERVER_URL = os.getenv("HEYGEN_SERVER_URL")

router = APIRouter(tags=["2. HeyGen Streaming"])

@router.post(
    "/api/heygen/create_token",
    summary="Create HeyGen Streaming Token",
    description="Retrieves a temporary API token from HeyGen to initialize a streaming session.",
)
async def heygen_create_token():
    headers = {'X-Api-Key': HEYGEN_API_KEY}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.create_token"

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers)

        response.raise_for_status()
        return response.json()

@router.post(
    "/api/heygen/new_session",
    summary="Create a new HeyGen streaming session",
    description="Initializes a new streaming session with the HeyGen avatar service using a valid token.",
    responses={
        400: {"model": schemas.ErrorResponse, "description": "Session token is missing."},
        502: {"model": schemas.ErrorResponse, "description": "Could not establish a video stream with HeyGen."}
    }
)
async def heygen_new_session(
    request: Request,
    request_body: schemas.HeyGenNewSessionRequest = Body(...) # For documentation
):
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Session token is missing")

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.new"

    heygen_body = {
        "quality": "medium",
        "avatar_name": "Wayne_20240711",
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

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=heygen_body, timeout=30.0)
        response.raise_for_status()
        response_data = response.json()
        if not response_data.get("data") or not response_data["data"].get("url"):
            raise HTTPException(status_code=502, detail="HeyGen response is missing the LiveKit URL.")
        return response_data

@router.post(
    "/api/heygen/start_session",
    summary="Start an existing HeyGen session",
    description="Starts the video stream for a previously created but inactive session. This makes the avatar active and ready to receive tasks.",
    tags=["2. HeyGen Streaming"],
    responses={
        404: {"model": schemas.ErrorResponse, "description": "Session ID not found by HeyGen."},
        502: {"model": schemas.ErrorResponse, "description": "Error communicating with HeyGen API."}
    }
)
async def heygen_start_session(
    request: Request,
    request_body: schemas.HeyGenSessionRequest = Body(...) # For documentation
):
    """Starts the video stream for a previously created session."""
    body = await request.json()
    token = body.get("token")
    session_id = body.get("session_id")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.start"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, json={"session_id": session_id})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Handle specific errors like 404 Not Found from HeyGen
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"HeyGen session not found: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"Error from HeyGen: {e.response.text}")

@router.post(
    "/api/heygen/stop_session",
    summary="Stop an active HeyGen session",
)
async def heygen_stop_session(
    request: Request,
    request_body: schemas.HeyGenSessionRequest = Body(...)
):
    body = await request.json()
    token, session_id = body.get("token"), body.get("session_id")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.stop"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json={"session_id": session_id})
        response.raise_for_status()
        return response.json()

@router.post(
    "/api/heygen/task",
    summary="Send a TTS task to HeyGen",
    description="Sends a text prompt for the avatar to speak during the session."
)
async def heygen_api_task(
    request: Request,
    request_body: schemas.HeyGenTaskRequest = Body(...) # For documentation
):
    body = await request.json()
    token = body.get("token")
    session_id = body.get("session_id")
    text = body.get("text")
    task_type = body.get("task_type", "text")

    payload = {
        "session_id": session_id,
        "task_type": task_type,
        "text": text
    }
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.task"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=payload)
        return {"status": "ok", "heygen_status_code": response.status_code}

