"""
ASSISTENTE CIDADÃO DF — Backend Principal
Para rodar: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers.webhook import router
from app.services.rag import load_tcu_documents
from app.core.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executado na inicialização do servidor."""
    print("🚀 Iniciando Assistente Cidadão DF...")
    print("📚 Carregando base de conhecimento do TCU...")
    load_tcu_documents()
    print("✅ Sistema pronto!")
    yield
    print("🛑 Encerrando servidor...")

app = FastAPI(
    title="Assistente Cidadão DF",
    description="Backend do assistente cidadão via WhatsApp para o Distrito Federal",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
