"""
AGENTE DE OUVIDORIA
- Coleta estruturada da denúncia (conversa guiada)
- RAG com normas do TCU para classificação
- Salva no Supabase
- Gera protocolo único
- NÃO permite anônimo (precisa de contato para retorno)
"""
import uuid
from datetime import datetime
from app.core.groq_client import chat
from app.services.rag import classify_complaint
from app.services.database import save_complaint

START_TEXT = """📢 *Ouvidoria — Relatar Problema*

Aqui você pode registrar denúncias, reclamações ou sugestões sobre serviços públicos do DF.

⚠️ *Importante:*
• Seu nome e contato serão registrados para retorno
• Dados protegidos por lei (LGPD)
• Denúncias falsas são de responsabilidade do autor

Vamos começar. *Descreva o problema que você quer relatar:*

(Digite livremente — pode ser em áudio também)
Digite *0* para cancelar."""

CLASSIFY_SYSTEM = """Você é um especialista em controle público baseado nas normas do TCU.
Com base na descrição e no contexto do RAG fornecido, classifique a denúncia:

CATEGORIAS POSSÍVEIS:
- SAUDE_PUBLICA: problemas em serviços de saúde do DF
- EDUCACAO: problemas em escolas ou serviços educacionais
- INFRAESTRUTURA: buraco, iluminação, água, esgoto, lixo
- IRREGULARIDADE_ADMINISTRATIVA: desvio de verba, nepotismo, licitação irregular
- ATENDIMENTO: mau atendimento de servidor público
- OUTROS: não se encaixa nas categorias acima

Responda em JSON com este formato exato:
{
  "categoria": "CATEGORIA",
  "subcategoria": "descrição curta",
  "gravidade": "ALTA|MEDIA|BAIXA",
  "orgao_sugerido": "nome do órgão responsável",
  "confianca": 0.85,
  "justificativa": "motivo da classificação em 1 frase"
}"""

STEPS = [
    ("complaint_desc",    "Descreva o problema que você quer relatar:"),
    ("complaint_location","Em qual local ocorreu? (endereço, bairro ou RA do DF)"),
    ("complaint_date",    "Quando aconteceu? (data aproximada, ex: 10/04/2025 ou 'essa semana')"),
    ("complaint_organ",   "Qual órgão ou serviço está envolvido? (ex: SES, DER, GDF, escola...)"),
    ("complaint_evidence","Você tem foto ou documento como evidência?\n• Mande a imagem agora\n• Ou digite *não* para continuar sem"),
]

async def handle(ctx: dict, message: str, media_bytes: bytes = None) -> tuple[dict, str]:
    step = ctx.get("current_step", "complaint_start")
    draft = ctx.get("complaint_draft", {})
    phone = ctx["phone"]
    name = ctx.get("name", "Cidadão")
    location = ctx.get("location", "DF")

    if message.strip() == "0":
        ctx["current_agent"] = "orchestrator"
        ctx["current_step"] = "menu"
        ctx["complaint_draft"] = {}
        from app.agents.orchestrator import MENU_TEXT
        return ctx, MENU_TEXT.format(name=name)

    # ── INÍCIO ──
    if step == "complaint_start":
        ctx["current_step"] = "complaint_desc"
        ctx["complaint_draft"] = {"location_user": location}
        return ctx, STEPS[0][1]

    # ── COLETA SEQUENCIAL ──
    step_order = [s[0] for s in STEPS]

    if step in step_order:
        idx = step_order.index(step)
        field = step

        # Evidência: aceita imagem
        if field == "complaint_evidence":
            if media_bytes:
                draft["has_evidence"] = True
                draft["evidence_note"] = "imagem enviada pelo usuário"
                # Em produção: salvar no Supabase Storage
            else:
                draft["has_evidence"] = False

        else:
            draft[field] = message.strip()

        ctx["complaint_draft"] = draft

        # Próximo passo
        if idx + 1 < len(STEPS):
            next_step, next_question = STEPS[idx + 1]
            ctx["current_step"] = next_step
            return ctx, next_question

        # ── TODOS OS DADOS COLETADOS → CLASSIFICA E SALVA ──
        ctx["current_step"] = "complaint_confirm"
        return ctx, await _build_summary(ctx)

    # ── CONFIRMAÇÃO ──
    if step == "complaint_confirm":
        answer = message.lower().strip()
        if answer in ("sim", "s", "1", "confirmar", "confirmo"):
            result = await _finalize(ctx)
            ctx["current_agent"] = "orchestrator"
            ctx["current_step"] = "menu"
            ctx["complaint_draft"] = {}
            return ctx, result
        else:
            ctx["current_agent"] = "orchestrator"
            ctx["current_step"] = "menu"
            ctx["complaint_draft"] = {}
            return ctx, "Denúncia cancelada. Digite *menu* para voltar ao início."

    return ctx, START_TEXT


async def _build_summary(ctx: dict) -> str:
    draft = ctx["complaint_draft"]
    classification = await classify_complaint(
        description=draft.get("complaint_desc", ""),
        organ=draft.get("complaint_organ", ""),
        location=draft.get("complaint_location", ""),
    )
    ctx["complaint_draft"]["classification"] = classification

    return (
        f"📋 *Resumo da sua denúncia*\n\n"
        f"📝 Descrição: {draft.get('complaint_desc', '')[:200]}\n"
        f"📍 Local: {draft.get('complaint_location', '')}\n"
        f"📅 Data: {draft.get('complaint_date', '')}\n"
        f"🏛️ Órgão: {draft.get('complaint_organ', '')}\n"
        f"📎 Evidência: {'Sim' if draft.get('has_evidence') else 'Não'}\n\n"
        f"🤖 *Classificação sugerida pela IA:*\n"
        f"• Categoria: {classification.get('categoria', '—')}\n"
        f"• Gravidade: {classification.get('gravidade', '—')}\n"
        f"• Órgão responsável: {classification.get('orgao_sugerido', '—')}\n\n"
        f"⚠️ A classificação é uma sugestão — revisada por humanos.\n\n"
        f"Confirma o envio? (sim/não)"
    )


async def _finalize(ctx: dict) -> str:
    draft = ctx["complaint_draft"]
    classification = draft.get("classification", {})
    protocol_id = str(uuid.uuid4())[:8].upper()

    record = {
        "id": protocol_id,
        "nome": ctx.get("name", "Não informado"),
        "contato": ctx["phone"],
        "descricao": draft.get("complaint_desc", ""),
        "localidade": draft.get("complaint_location", ctx.get("location", "")),
        "data_ocorrido": draft.get("complaint_date", ""),
        "orgao_relacionado": draft.get("complaint_organ", ""),
        "categoria_sugerida": classification.get("categoria", "OUTROS"),
        "subcategoria": classification.get("subcategoria", ""),
        "gravidade": classification.get("gravidade", "MEDIA"),
        "tem_evidencia": draft.get("has_evidence", False),
        "status": "PENDENTE",
        "classificacao_ia": classification,
        "confianca_ia": classification.get("confianca", 0.0),
        "criado_em": datetime.utcnow().isoformat(),
    }

    await save_complaint(record)

    return (
        f"✅ *Denúncia registrada com sucesso!*\n\n"
        f"🔖 Protocolo: *{protocol_id}*\n\n"
        f"Guarde este número para acompanhar sua denúncia.\n\n"
        f"Os dados foram encaminhados para análise.\n"
        f"Em breve você poderá receber retorno por este número.\n\n"
        f"Digite *menu* para voltar ao início."
    )
