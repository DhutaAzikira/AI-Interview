import httpx
from fastapi import APIRouter, Request, Body, HTTPException
from typing import Dict, Any
from . import schemas
from dotenv import load_dotenv
import os

load_dotenv()

GLADIA_API_KEY = os.getenv("GLADIA_API_KEY")

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
):
    headers = {'X-Gladia-Key': GLADIA_API_KEY, 'Content-Type': 'application/json'}
    try:
        body = {
            "encoding": "wav/pcm",
            "sample_rate": 16000,
            'model': "solaria-1",
            "endpointing": 2,
            "language_config": {
                "languages": ["id"],
                "code_switching": False,
            },
            "maximum_duration_without_endpointing": 60,
            "realtime_processing": {
                "translation": False,
            },
            "pre_processing": {
                "audio_enhancer": False,
                "speech_threshold": 0.6
            },
        }


        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.gladia.io/v2/live", headers=headers, json=body)
            print("Response from Gladia:", response.json())
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error from Gladia: {e.response.text}")