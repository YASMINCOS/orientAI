"""
RAG — Recuperação de conhecimento com normas do TCU
Usa ChromaDB local + Groq para classificar denúncias

Como funciona:
1. Na primeira execução, carrega os documentos do TCU (pasta data/tcu_docs)
2. Gera embeddings e salva no ChromaDB (persiste em disco)
3. Na classificação, busca trechos relevantes e passa para o LLM
"""
import os
import json
import chromadb
from chromadb.utils import embedding_functions
from app.core.groq_client import chat
from app.core.config import get_settings

settings = get_settings()

# ChromaDB persiste em disco — não perde ao reiniciar
CHROMA_PATH = "./data/chroma_db"
COLLECTION_NAME = "tcu_norms"

# Usa embeddings gratuitos da Sentence Transformers (roda local, sem API)
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"},
    )

def load_tcu_documents():
    """
    Carrega documentos do TCU na base vetorial.
    Execute isso UMA VEZ antes de iniciar o sistema.
    Os documentos ficam em: data/tcu_docs/
    """
    collection = _get_collection()

    # Verifica se já tem documentos
    if collection.count() > 0:
        print(f"✅ RAG já carregado: {collection.count()} chunks")
        return

    # Carrega os textos do TCU (incluídos na pasta data/tcu_docs)
    docs_path = "./data/tcu_docs"
    if not os.path.exists(docs_path):
        print("⚠️  Pasta data/tcu_docs não encontrada. Usando base de fallback.")
        _load_fallback_knowledge(collection)
        return

    documents = []
    ids = []
    metadatas = []

    for i, filename in enumerate(os.listdir(docs_path)):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_path, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Divide em chunks de ~500 caracteres com overlap
            chunks = _chunk_text(content, chunk_size=500, overlap=50)
            for j, chunk in enumerate(chunks):
                doc_id = f"{filename}_{j}"
                documents.append(chunk)
                ids.append(doc_id)
                metadatas.append({"source": filename, "chunk": j})

    if documents:
        collection.add(documents=documents, ids=ids, metadatas=metadatas)
        print(f"✅ RAG carregado: {len(documents)} chunks de {docs_path}")
    else:
        _load_fallback_knowledge(collection)

def _load_fallback_knowledge(collection):
    """
    Base de conhecimento mínima embutida no código.
    Baseada nas categorias do Fala.BR e diretrizes do TCU.
    """
    fallback_docs = [
        {
            "id": "tcu_001",
            "text": """Irregularidade administrativa segundo o TCU inclui: desvio de recursos públicos,
nepotismo (contratação de parentes), licitação irregular, superfaturamento de contratos,
dispensa indevida de licitação, pagamento por serviço não prestado, fraude em concurso público.""",
        },
        {
            "id": "tcu_002",
            "text": """Infraestrutura pública: problemas como buraco em via pública, falta de iluminação,
vazamento de água, esgoto a céu aberto, coleta de lixo irregular são responsabilidade
das secretarias municipais e distritais. No DF: NOVACAP (obras), CAESB (água/esgoto),
SLU (limpeza urbana), SEMOB (transporte).""",
        },
        {
            "id": "tcu_003",
            "text": """Saúde pública no DF: problemas em UPAs, UBSs, hospitais públicos
são responsabilidade da SES-DF (Secretaria de Estado de Saúde) e do IGES-DF.
Irregularidades incluem: falta de medicamentos, mau atendimento, demora excessiva,
falta de profissionais, equipamentos quebrados.""",
        },
        {
            "id": "tcu_004",
            "text": """Educação pública: problemas em escolas públicas do DF são responsabilidade
da SEEDF (Secretaria de Educação). Inclui: falta de professores, estrutura precária,
merenda escolar inadequada, violência na escola, irregularidades em contratos de fornecimento.""",
        },
        {
            "id": "tcu_005",
            "text": """Atendimento ao cidadão: mau atendimento por servidores públicos,
demora injustificada, recusa em atender, cobranças indevidas são passíveis de denúncia
ao órgão corregedor ou à ouvidoria. No DF: Ouvidoria do GDF recebe essas demandas.""",
        },
        {
            "id": "tcu_006",
            "text": """Gravidade das irregularidades: ALTA = envolve risco à vida ou desvio
significativo de recursos públicos. MÉDIA = impacta serviço público essencial mas sem
risco imediato. BAIXA = afeta qualidade do serviço mas não causa dano grave imediato.""",
        },
    ]

    collection.add(
        documents=[d["text"] for d in fallback_docs],
        ids=[d["id"] for d in fallback_docs],
        metadatas=[{"source": "fallback", "chunk": 0}] * len(fallback_docs),
    )
    print(f"✅ RAG fallback carregado: {len(fallback_docs)} documentos")

async def classify_complaint(description: str, organ: str, location: str) -> dict:
    """
    Classifica uma denúncia usando RAG com normas do TCU.
    1. Busca documentos relevantes no ChromaDB
    2. Passa contexto + denúncia para o Groq
    3. Retorna classificação estruturada
    """
    collection = _get_collection()

    # Busca os 3 trechos mais relevantes
    query = f"{description} {organ} {location}"
    try:
        results = collection.query(query_texts=[query], n_results=3)
        context_docs = results["documents"][0] if results["documents"] else []
        rag_context = "\n---\n".join(context_docs)
    except Exception:
        rag_context = "Base de normas não disponível."

    system = f"""Você é especialista em controle público e normas do TCU.
Use o contexto abaixo das normas do TCU para apoiar sua classificação.

CONTEXTO DAS NORMAS:
{rag_context}

Classifique a denúncia em JSON com este formato exato:
{{
  "categoria": "SAUDE_PUBLICA|EDUCACAO|INFRAESTRUTURA|IRREGULARIDADE_ADMINISTRATIVA|ATENDIMENTO|OUTROS",
  "subcategoria": "descrição curta do problema específico",
  "gravidade": "ALTA|MEDIA|BAIXA",
  "orgao_sugerido": "nome do órgão responsável no DF",
  "confianca": 0.85,
  "justificativa": "uma frase explicando a classificação"
}}

Responda APENAS com o JSON válido, sem texto adicional."""

    raw = chat(
        messages=[{
            "role": "user",
            "content": f"Denúncia:\nDescrição: {description}\nÓrgão: {organ}\nLocal: {location}",
        }],
        system=system,
        temperature=0.1,
    )

    try:
        # Remove possíveis markdown code blocks
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception:
        return {
            "categoria": "OUTROS",
            "subcategoria": "Não classificado automaticamente",
            "gravidade": "MEDIA",
            "orgao_sugerido": "Ouvidoria do GDF",
            "confianca": 0.0,
            "justificativa": "Erro na classificação automática — revisão manual necessária",
        }

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Divide texto em chunks com overlap para melhor recuperação."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]
