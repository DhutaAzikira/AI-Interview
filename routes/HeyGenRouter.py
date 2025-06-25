from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
import httpx
from starlette.responses import JSONResponse
from helper import send_personal_message, connect, disconnect, forward_answer_to_n8n, SESSIONS

HEYGEN_API_KEY = "MGQ3YjZhNmIxNjgyNGRlZGIwYTE3NjY5YzQzNjViZWUtMTc1MDY5MDM4OQ=="
HEYGEN_SERVER_URL = "https://api.heygen.com"

router = APIRouter()


@router.post("/api/heygen/create_token")
async def heygen_create_token():
    headers = {'X-Api-Key': HEYGEN_API_KEY}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.create_token"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers)
        response.raise_for_status()
        return response.json()


@router.post("/api/heygen/new_session")
async def heygen_new_session(request: Request):
    body = await request.json()
    print(f"body: {body}")
    try:
        body = await request.json()
        print(f"body: {body}")
        token = body.get("token")

        if not token:
            return JSONResponse(status_code=400, content={"error": "Session token is missing"})

        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
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


@router.post("/api/heygen/start_session")
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


@router.post("/api/heygen/stop_session")
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


@router.post("/api/heygen/task")
async def heygen_api_task(request: Request):
    body = await request.json()
    token = body.get("token")
    session_id = body.get("session_id")
    task_type = body.get("task_type")
    text = body.get("text")

    payload = {
        "session_id": session_id,
        "task_type": task_type,
        "text": text
    }

    headers = {'Authorization': f"Bearer {token}", 'Content-Type': 'application/json'}
    api_url = f"{HEYGEN_SERVER_URL}/v1/streaming.task"
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=payload)
        return {"status": "ok"}, response.status_code
