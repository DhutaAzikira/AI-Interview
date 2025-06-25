from fastapi import WebSocket
from typing import Dict
import httpx

SESSIONS: Dict[str, Dict] = {}
active_connections: Dict[str, WebSocket] = {}


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
