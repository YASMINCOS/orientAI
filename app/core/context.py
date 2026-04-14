import json
import redis.asyncio as redis
from app.core.config import get_settings

settings = get_settings()

# Cada conversa dura 30 minutos sem atividade
TTL_SECONDS = 1800

async def get_redis():
    return redis.from_url(settings.redis_url, decode_responses=True)

async def get_context(phone: str) -> dict:
    """
    Busca o contexto atual da conversa de um usuário.
    O contexto guarda: nome, localização, agente atual, histórico, dados coletados.
    """
    r = await get_redis()
    data = await r.get(f"ctx:{phone}")
    await r.aclose()
    if data:
        return json.loads(data)
    return {
        "phone": phone,
        "name": None,
        "location": None,
        "current_agent": "orchestrator",
        "current_step": "menu",
        "history": [],          # últimas mensagens
        "collected": {},        # dados coletados no fluxo atual
        "complaint_draft": {},  # rascunho de denúncia
    }

async def save_context(phone: str, ctx: dict):
    """Salva o contexto atualizado com TTL."""
    r = await get_redis()
    await r.setex(f"ctx:{phone}", TTL_SECONDS, json.dumps(ctx, ensure_ascii=False))
    await r.aclose()

async def clear_context(phone: str):
    """Limpa o contexto — usado quando usuário digita 'menu' ou 'sair'."""
    r = await get_redis()
    await r.delete(f"ctx:{phone}")
    await r.aclose()

def add_to_history(ctx: dict, role: str, content: str) -> dict:
    """Adiciona mensagem ao histórico, mantendo só as últimas 10."""
    ctx["history"].append({"role": role, "content": content})
    ctx["history"] = ctx["history"][-10:]
    return ctx
