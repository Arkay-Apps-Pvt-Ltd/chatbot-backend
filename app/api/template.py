from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(tags=["Templates"])

GUPSHUP_API_URL = (
    "https://api.gupshup.io/wa/app/ebcc2fdf-3327-4056-9de6-655eaacf3e17/template"
)
HEADERS = {
    "apikey": "awdxg2aymfgsjcrrrufuvu5y4u1hd5xi",  # replace with your actual API key
    "Content-Type": "application/x-www-form-urlencoded",
}


@router.get("/templates")
async def get_templates():
    async with httpx.AsyncClient() as client:
        response = await client.get(GUPSHUP_API_URL, headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


@router.get("/templates/{template_id}")
async def get_template_by_id(template_id: str):
    url = f"{GUPSHUP_API_URL}/{template_id}"  # Assuming Gupshup supports fetching by template ID
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()



@router.get("/templates/{template_id}")
async def get_template_by_id(template_id: str):
    url = f"{GUPSHUP_API_URL}/{template_id}"  # Assuming Gupshup supports fetching by template ID
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()