import httpx
from fastapi import APIRouter, Request, Body, HTTPException
from typing import Dict, Any
from . import schemas

GLADIA_API_KEY = "27e7daf5-eef9-4150-99c3-dac275d7641e"

router = APIRouter(tags=["3. Gladia Transcription"])

@router.post(
    "/api/gladia/init",
    summary="Initialize Gladia Live Transcription",
    description="""Proxies a request to the Gladia API to initialize a live audio transcription session.
    The request body and response will match the format specified by the official Gladia API documentation.""",
    response_model=schemas.GladiaInitResponse,
    responses={
        502: {"model": schemas.ErrorResponse, "description": "Error communicating with the Gladia API."}
    }
)
async def gladia_api_init(
    request: Request,
    # We use a generic Dict here because it's a direct proxy.
    request_body: Dict[str, Any] = Body(
        ...,
        example={"sample_rate": 48000, "encoding": "WAV"}
    )
):
    headers = {'X-Gladia-Key': GLADIA_API_KEY, 'Content-Type': 'application/json'}
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.gladia.io/v2/live", headers=headers, json=body)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error from Gladia: {e.response.text}")