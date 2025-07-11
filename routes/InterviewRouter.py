import httpx
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Body, HTTPException
from . import schemas
from helper import send_personal_message, connect, disconnect, forward_answer_to_n8n, SESSIONS
import os
from dotenv import load_dotenv

load_dotenv()

N8N_START_INTERVIEW_URL = os.getenv("N8N_START_INTERVIEW_URL")

router = APIRouter(tags=["1. Interview Lifecycle"])

@router.post(
    "/api/interview/start",
    summary="Start a new interview session",
    description="Starts the interview process using a booking code, gets a session ID from the backend, and returns it.",
    response_model=schemas.StartInterviewResponse,
    responses={
        502: {"model": schemas.ErrorResponse, "description": "Error communicating with the backend workflow service (n8n)."}
    }
)
async def start_interview(
    request: Request,
    request_body: schemas.StartInterviewRequest = Body(...) # For documentation
):
    body = await request.json()
    booking_code = body.get('booking_code')
    print(f"Received request to start interview with booking code: {booking_code}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(N8N_START_INTERVIEW_URL, json={'booking_code': booking_code}, timeout=30.0)
            response.raise_for_status()
            n8n_data = response.json()

        session_id = n8n_data.get('sessionId')
        resume_url = n8n_data.get('resumeUrl')
        if not session_id or not resume_url:
            raise HTTPException(status_code=502, detail="Backend workflow did not return a valid session ID and resume URL.")

        SESSIONS[session_id] = {'resumeUrl': resume_url}
        print(f"Started session {session_id}, resumeUrl: {resume_url}")
        return {"sessionId": session_id, "resumeUrl": resume_url}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with n8n workflow: {e.response.text}")

@router.post(
    "/api/send-question",
    summary="Send a question to the user",
    description="Pushes a new question to the client via the active WebSocket connection. This is typically called by a backend service.",
    response_model=schemas.StatusResponse
)
async def send_question(
    request: Request,
    request_body: schemas.SendQuestionRequest = Body(...) # For documentation
):
    body = await request.json()
    session_id = body.get('sessionId')
    question_text = body.get('question')
    message = {'type': 'new_question', 'payload': {'text': question_text}}
    await send_personal_message(message, session_id)
    return {"status": "Question sent to client."}

@router.post(
    "/api/interview/end",
    summary="End the interview session",
    description="Sends an 'end_interview' command to the client via WebSocket and cleans up the session on the server.",
    response_model=schemas.StatusResponse
)
async def end_interview(
    request: Request,
    request_body: schemas.EndInterviewRequest = Body(...) # For documentation
):
    body = await request.json()
    session_id = body.get('sessionId')
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    message = {'type': 'end_interview'}
    await send_personal_message(message, session_id)
    return {"status": "End interview command sent."}

@router.websocket("/ws/interview/{session_id}/")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # WebSockets are not formally part of the OpenAPI spec,
    # so they won't appear in the docs. Their function is described
    # in the HTTP endpoints that use them.
    await connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "user_answer":
                answer = data.get("payload", {}).get("answer")
                print(f"Received answer from client: {answer}")
                if answer:
                    await forward_answer_to_n8n(session_id, answer)
    except WebSocketDisconnect:
        disconnect(session_id)