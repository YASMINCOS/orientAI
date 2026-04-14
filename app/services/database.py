"""
Serviço de banco de dados — Supabase (PostgreSQL)
"""
from supabase import create_client
from app.core.config import get_settings

settings = get_settings()
_client = None

def get_db():
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client

async def save_complaint(record: dict) -> bool:
    """Salva denúncia no Supabase."""
    try:
        db = get_db()
        db.table("complaints").insert(record).execute()
        return True
    except Exception as e:
        print(f"Erro ao salvar denúncia: {e}")
        return False

async def get_complaints(status: str = None) -> list:
    """Busca denúncias (para painel público)."""
    try:
        db = get_db()
        query = db.table("complaints").select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("criado_em", desc=True).limit(100).execute()
        return result.data
    except Exception:
        return []

async def save_interaction(phone: str, agent: str, message: str, response: str):
    """Log de interações para análise posterior."""
    try:
        db = get_db()
        db.table("interactions").insert({
            "phone": phone,
            "agent": agent,
            "user_message": message[:500],
            "bot_response": response[:500],
        }).execute()
    except Exception:
        pass  # Não bloqueia o fluxo principal
