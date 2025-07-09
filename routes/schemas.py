# schemas.py

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

# ===================================================================
# Generic Schemas
# ===================================================================

class StatusResponse(BaseModel):
    status: str

class ErrorResponse(BaseModel):
    detail: str

# ===================================================================
# Interview Schemas
# ===================================================================

class StartInterviewRequest(BaseModel):
    booking_code: str = Field(..., example="BKNG-12345", description="The unique booking code for the interview.")

class StartInterviewResponse(BaseModel):
    sessionId: str = Field(..., example="session_abc123", description="The unique session ID for this interview instance.")
    resumeUrl: str = Field(..., example="https://example.com/resumes/doc.pdf", description="A URL to the candidate's resume.")

class SendQuestionRequest(BaseModel):
    sessionId: str = Field(..., example="session_abc123")
    question: str = Field(..., example="Can you tell me about a time you faced a challenge?")

class EndInterviewRequest(BaseModel):
    sessionId: str = Field(..., example="session_abc123")


# ===================================================================
# HeyGen Schemas
# ===================================================================

class HeyGenNewSessionRequest(BaseModel):
    token: str = Field(..., example="tkn_xxxxxxxxxxxx", description="The temporary token from the /create_token endpoint.")

class HeyGenSessionRequest(BaseModel):
    token: str = Field(..., example="tkn_xxxxxxxxxxxx")
    session_id: str = Field(..., example="sid_xxxxxxxxxxxx", description="The unique ID of the active streaming session.")

class HeyGenTaskRequest(BaseModel):
    token: str = Field(..., example="tkn_xxxxxxxxxxxx")
    session_id: str = Field(..., example="sid_xxxxxxxxxxxx")
    task_type: str = Field("text", example="text", description="The type of task to perform.")
    text: str = Field(..., example="Hello, welcome to the interview.", description="The text for the avatar to speak.")

class HeyGenTaskResponse(BaseModel):
    status: str = "ok"
    heygen_status_code: int = Field(..., example=200)

class HeyGenSuccessData(BaseModel):
    # This schema can be expanded as you discover more fields from HeyGen
    session_id: Optional[str] = Field(None, example="sid_xxxxxxxxxxxx")
    url: Optional[str] = Field(None, example="wss://livekit.example.com/...")

class HeyGenSuccessResponse(BaseModel):
    data: Optional[HeyGenSuccessData] = None
    error: Any = None # Can be null or an object

# ===================================================================
# Gladia Schemas
# ===================================================================

class GladiaInitResponse(BaseModel):
    # Based on Gladia's likely response for initializing a live session
    id: str = Field(..., example="gladia_sid_123")
    url: str = Field(..., example="wss://livekit.gladia.io/...")

from pydantic import BaseModel

class LiveKitConnection(BaseModel):
    """Defines the structure for LiveKit connection details."""
    server_url: str
    token: str

class InitiateSessionResponse(BaseModel):
    """Defines the successful response structure for the initiate_session endpoint."""
    message: str
    token: str
    session_id: str
    livekit_connection: LiveKitConnection
