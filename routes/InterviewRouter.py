import httpx
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from starlette.responses import JSONResponse
from helper import send_personal_message, connect, disconnect, forward_answer_to_n8n, SESSIONS

N8N_START_INTERVIEW_URL = "http://localhost:5678/webhook-test/starts-interview"

router = APIRouter()


@router.post("/api/interview/start")  ##OK
async def start_interview(request: Request):
    request = await request.json()
    print(f"Received request to start interview with booking code: {request}")

    if 'booking_code' not in request:
        return JSONResponse(status_code=400, content={"error": "Booking is required."})

    n8n_data_payload = {
        'booking_code': request['booking_code'],
    }

    print(f"Received n8n data: {n8n_data_payload}")

    try:

        async with httpx.AsyncClient() as client:  ##POST TO n8n
            response = await client.post(
                N8N_START_INTERVIEW_URL,
                json=n8n_data_payload,
                timeout=30.0)

            response.raise_for_status()
            n8n_data = response.json()

        session_id = n8n_data.get('sessionId')
        resume_url = n8n_data.get('resumeUrl')

        if not session_id or not resume_url:
            raise Exception('n8n did not return a valid sessionId and resumeUrl.')

        SESSIONS[session_id] = {'resumeUrl': resume_url}
        print(f"Started session {session_id}, resumeUrl: {resume_url}")
        return {"sessionId": session_id, "resumeUrl": resume_url}

    except Exception as e:
        print(f"Error starting interview: {e}")


# --- WebSocket Endpoint ---
@router.websocket("/ws/interview/{session_id}/")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "user_answer":
                answer = data.get("payload", {}).get("answer")
                if answer:
                    await forward_answer_to_n8n(session_id, answer)
    except WebSocketDisconnect:
        disconnect(session_id)


@router.post("/api/send-question")
async def send_question(request: Request):
    body = await request.json()
    session_id = body.get('sessionId')
    question_text = body.get('question')
    message = {'type': 'new_question', 'payload': {'text': question_text}}
    await send_personal_message(message, session_id)
    return {"status": "Question sent to client."}


@router.post("/api/interview/end")
async def end_interview(request: Request):
    body = await request.json()
    session_id = body.get('sessionId')
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    message = {'type': 'end_interview'}
    await send_personal_message(message, session_id)
    return {"status": "End interview command sent."}
