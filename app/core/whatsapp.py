import httpx
from app.core.config import get_settings

settings = get_settings()
HEADERS = {"Content-Type": "application/json", "apikey": settings.evolution_api_key}
BASE = f"{settings.evolution_api_url}/message"
INSTANCE = settings.evolution_instance

async def send_text(phone: str, text: str):
    # phone pode ser numero real ou @lid
    number = phone.replace("@s.whatsapp.net", "").replace("@lid", "")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{BASE}/sendText/{INSTANCE}",
            headers=HEADERS,
            json={"number": number, "textMessage": {"text": text}},
        )
        print(f"Envio para {number}: {r.status_code}")

async def download_media(media_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(media_url, headers=HEADERS)
        return r.content
