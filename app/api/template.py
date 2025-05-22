from fastapi import APIRouter
import httpx

router = APIRouter(tags=["Templates"])

GUPSHUP_API_URL = "https://api.gupshup.io/wa/app/0f11ed72-2d2a-4f38-b522-2d2267e6ce57/template"
HEADERS = {
    "apikey": "awdxg2aymfgsjcrrrufuvu5y4u1hd5xi",  # replace with your actual API key
    "Content-Type": "application/x-www-form-urlencoded"
}

@router.get("/templates")
async def get_templates():
    async with httpx.AsyncClient() as client:
        response = await client.get(GUPSHUP_API_URL, headers=HEADERS)
        return response.json()
