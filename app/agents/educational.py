"""
AGENTE EDUCATIVO
- Ajuda o cidadão a usar sistemas digitais (Gov.br, Meu INSS, etc.)
- Aceita prints de tela e interpreta com visão do Groq
- Aceita áudio (transcrito pelo webhook antes de chegar aqui)
- Oferece orientação por: vídeo, PDF ou texto (escolha do usuário)
- Linguagem simples, passo a passo
"""
from app.core.groq_client import chat, analyze_image

START_TEXT = """📚 *Ajuda com serviços digitais*

Pode me contar o que está precisando! Fique à vontade pra descrever com suas palavras.

Posso te ajudar com:
• Gov.br — login, cadastro, serviços
• Meu INSS — benefícios, extrato, simulação
• Carteira de Trabalho Digital
• e-SUS / agendamento de saúde
• Assinatura digital Gov.br
• Outros aplicativos do governo

*Manda uma mensagem, um print da tela onde travou, ou um áudio* — do jeito que for mais fácil pra você! 🎤

Digite *0* para voltar ao menu."""

SYSTEM_GUIDE = """Você é um assistente que ajuda pessoas com pouca familiaridade digital a usar serviços do governo.
Use linguagem MUITO simples. Sem termos técnicos.
Entenda gírias, abreviações e erros de digitação (ex: "num consigo entrar", "tá dando erro", "não to conseguindo", "komo faz").
Dê instruções passo a passo numeradas.
Seja específico: "clique no botão azul escrito Entrar", "vá em Menu no canto superior esquerdo".
Máximo 5 passos por resposta. Se precisar de mais, diga que vai continuar.
Se não souber, diga honestamente e indique o telefone de suporte do serviço.
NÃO ofereça vídeo ou PDF no final da resposta. Isso será feito pelo sistema automaticamente."""

IMAGE_SYSTEM = """Você é um assistente que ajuda pessoas a usar aplicativos do governo.
Analise este print de tela e:
1. Identifique qual sistema/app está sendo usado
2. Identifique onde o usuário pode estar travado
3. Dê instruções simples e específicas do que fazer agora
Use linguagem muito simples, como se fosse explicar para um familiar mais velho."""

# ──────────────────────────────────────────────────────────────────────────────
# Base de conhecimento — PDFs como links diretos do Google Drive
# Para adicionar novo PDF: botão direito no Drive → Compartilhar → Copiar link
# ──────────────────────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = {
    "gov.br": {
        "phone": "0800 978 0001",
        "link": "gov.br",
        "videos": [
            {"titulo": "Como criar conta no Gov.br (passo a passo)", "url": "https://www.youtube.com/watch?v=3xmcgMH3gMo"},
            {"titulo": "Como fazer login no Gov.br pelo celular",     "url": "https://www.youtube.com/watch?v=R5xK2Kg9Pxc"},
            {"titulo": "Como aumentar o nível da sua conta Gov.br",   "url": "https://www.youtube.com/watch?v=GmXzP1dQfwk"},
        ],
        "pdf": None,  # cole o link do Drive aqui quando tiver
    },
    "meu inss": {
        "phone": "135",
        "link": "meu.inss.gov.br",
        "videos": [
            {"titulo": "Como usar o Meu INSS pelo celular",               "url": "https://www.youtube.com/watch?v=QcH0X1kGXpA"},
            {"titulo": "Como solicitar benefício pelo Meu INSS",          "url": "https://www.youtube.com/watch?v=zVpJr_-Vy0w"},
            {"titulo": "Como ver seu extrato de contribuição no INSS",    "url": "https://www.youtube.com/watch?v=Yw5r6UM2fUo"},
        ],
        "pdf": None,  # cole o link do Drive aqui quando tiver
    },
    "carteira de trabalho": {
        "phone": "158",
        "link": "empregabrasil.mte.gov.br",
        "videos": [
            {"titulo": "Como baixar a Carteira de Trabalho Digital",        "url": "https://www.youtube.com/watch?v=3Fv2P8QiNeU"},
            {"titulo": "Como consultar seu histórico de empregos pelo app", "url": "https://www.youtube.com/watch?v=Wk_HzUm4bCA"},
        ],
        "pdf": None,  # cole o link do Drive aqui quando tiver
    },
    "e-sus": {
        "phone": "136",
        "link": "sisab.saude.gov.br",
        "videos": [
            {"titulo": "Como agendar consulta pelo e-SUS", "url": "https://www.youtube.com/watch?v=YlXn-3eXgTg"},
        ],
        "pdf": None,  # cole o link do Drive aqui quando tiver
    },
    "assinatura": {
        "phone": "0800 978 0001",
        "link": "gov.br/assinatura-eletronica",
        "videos": [
            {"titulo": "Como assinar documentos pelo Gov.br", "url": "https://www.youtube.com/watch?v=3xmcgMH3gMo"},
        ],
        "pdf": "https://drive.google.com/file/d/18fGUYJB0aefUP9EZspi-RrTS2jBAYp5N/view?usp=drive_link",
    },
}

# Palavras-chave → chave do KNOWLEDGE_BASE
KEYWORD_ALIASES = {
    "assinatura":          "assinatura",
    "assinar":             "assinatura",
    "assinatura gov":      "assinatura",
    "assinatura digital":  "assinatura",
    "documento digital":   "assinatura",
    "gov.br":              "gov.br",
    "govbr":               "gov.br",
    "inss":                "meu inss",
    "meu inss":            "meu inss",
    "carteira de trabalho":"carteira de trabalho",
    "ctps":                "carteira de trabalho",
    "e-sus":               "e-sus",
    "esus":                "e-sus",
}

MENU_FORMATO = (
    "\n\n---\n"
    "Como prefere receber a orientação?\n"
    "1️⃣ 🎥 Vídeo\n"
    "2️⃣ 📄 PDF\n"
    "3️⃣ 💬 Continuar por texto\n\n"
    "_(ou é só continuar me perguntando!)_\n"
    "Digite *0* para voltar ao menu."
)


def _find_topic(message: str) -> tuple[str | None, dict | None]:
    msg_lower = message.lower()
    for alias, key in KEYWORD_ALIASES.items():
        if alias in msg_lower:
            return key, KNOWLEDGE_BASE.get(key)
    return None, None


def _format_videos(videos: list) -> str:
    lines = ["🎥 *Tutoriais em vídeo:*\n"]
    for i, v in enumerate(videos, 1):
        lines.append(f"{i}. {v['titulo']}\n   👉 {v['url']}")
    lines.append("\nEscolha o vídeo pelo número ou me conte se ficou alguma dúvida!\nDigite *0* para voltar.")
    return "\n".join(lines)


def _extra_contact(topic: dict | None) -> str:
    if not topic:
        return ""
    return f"\n\n📞 Suporte: *{topic['phone']}* | 🌐 {topic['link']}"


async def handle(ctx: dict, message: str, media_bytes: bytes = None) -> tuple[dict, str]:
    step    = ctx.get("current_step", "educational_start")
    name    = ctx.get("name", "cidadão")
    msg_raw = message.strip()
    msg_lower = msg_raw.lower()

    # ── Comandos globais ──────────────────────────────────────
    if msg_lower in ("0", "menu", "voltar", "sair", "início", "inicio"):
        ctx["current_agent"] = "orchestrator"
        ctx["current_step"]  = "menu"
        from app.agents.orchestrator import MENU_TEXT
        return ctx, MENU_TEXT.format(name=name)

    # ── Usuário mandou imagem (print de tela) ─────────────────
    if media_bytes:
        ctx["current_step"]    = "educational_format_choice"
        ctx["last_topic_key"]  = None
        ctx["last_topic_data"] = None
        try:
            analysis = analyze_image(
                media_bytes,
                question="Analise este print e me diga: qual sistema é esse e o que o usuário deve fazer agora?"
            )
            response = (
                f"Analisei sua tela! 👀\n\n{analysis}\n\n"
                "Tem mais alguma dúvida? Manda outro print ou descreve o problema.\n"
                "Digite *0* para voltar ao menu."
            )
        except Exception:
            response = (
                "Recebi sua imagem mas tive dificuldade em analisar.\n"
                "Descreva em texto o que está vendo na tela e vou te ajudar!\n"
                "Digite *0* para voltar ao menu."
            )
        return ctx, response

    # ── Escolha de formato ────────────────────────────────────
    if step == "educational_format_choice" and msg_raw in ("1", "2", "3"):
        topic_key = ctx.get("last_topic_key")
        topic     = ctx.get("last_topic_data")
        last_msg  = ctx.get("last_user_message", message)

        ctx["current_step"] = "educational_chat"  # sai do estado de escolha

        if msg_raw == "1":  # Vídeo
            if topic and topic.get("videos"):
                return ctx, _format_videos(topic["videos"])
            return ctx, (
                "🎥 Para encontrar tutoriais em vídeo, pesquise no YouTube:\n"
                f"*\"passo a passo {topic_key or 'gov.br'} tutorial\"*\n\n"
                "Quer que eu continue explicando por texto? Me diga!\n"
                "Digite *0* para voltar."
            )

        if msg_raw == "2":  # PDF
            pdf_url = topic.get("pdf") if topic else None
            if pdf_url:
                return ctx, (
                    f"📄 *Guia em PDF:*\n\n{pdf_url}\n\n"
                    "Abra o link acima para ver o passo a passo ilustrado.\n"
                    "Se precisar de mais ajuda, é só perguntar!\n"
                    "Digite *0* para voltar."
                )
            return ctx, (
                "😕 Ainda não temos um PDF para esse tema.\n"
                "Quer que eu explique por texto mesmo? É só perguntar!\n"
                "Digite *0* para voltar."
            )

        if msg_raw == "3":  # Texto
            history  = ctx.get("history", [])
            messages = history[-6:] + [{"role": "user", "content": last_msg}]
            response = chat(messages=messages, system=SYSTEM_GUIDE, temperature=0.2)
            extra    = _extra_contact(topic)
            return ctx, response + extra + "\n\nTem mais dúvidas? Pode perguntar!\nDigite *0* para voltar."

    # ── Conversa de texto livre ───────────────────────────────
    ctx["current_step"]    = "educational_format_choice"
    ctx["last_user_message"] = message

    history  = ctx.get("history", [])
    messages = history[-6:] + [{"role": "user", "content": message}]

    topic_key, topic = _find_topic(message)
    ctx["last_topic_key"]  = topic_key
    ctx["last_topic_data"] = topic

    response = chat(messages=messages, system=SYSTEM_GUIDE, temperature=0.2)
    extra    = _extra_contact(topic)

    return ctx, response + extra + MENU_FORMATO