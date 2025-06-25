import httpx
from fastapi import APIRouter, Request

GLADIA_API_KEY = "27e7daf5-eef9-4150-99c3-dac275d7641e"

router = APIRouter()


@router.post("/api/gladia/init")
async def gladia_api_init(request: Request):
    headers = {'X-Gladia-Key': GLADIA_API_KEY, 'Content-Type': 'application/json'}
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.gladia.io/v2/live", headers=headers, json=await request.json())
        print(f"Gladia API init response: {response.json()}")
        return response.json()
