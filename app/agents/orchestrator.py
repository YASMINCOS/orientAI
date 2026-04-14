"""
AGENTE ORQUESTRADOR
- Menu principal
- Identifica o que o usuário quer (texto livre ou número)
- Roteia para o agente correto
- Comandos globais: 'menu', 'sair', 'voltar'
"""
from app.core.groq_client import chat
from app.core.context import add_to_history

MENU_TEXT = """Olá, {name}! 👋

Sou o assistente do cidadão do DF. Como posso ajudar?

1️⃣ Saúde — orientação, filas de UPAs, unidades próximas
2️⃣ Denúncia — relatar problema a um órgão público
3️⃣ Ajuda com Gov.br / INSS / serviços digitais
4️⃣ Outros

Responda com o número ou descreva o que precisa."""

SYSTEM_ROUTER = """Você é um assistente do governo do Distrito Federal.
Analise a mensagem do usuário (pode ter gírias, erros de digitação, linguagem informal) e classifique em UMA das opções:
- SAUDE: saúde, UPA, UBS, hospital, fila, médico, passando mal, doença, dor, febre, sintoma, tô mal, tô ruim, mió, doend
- OUVIDORIA: denúncia, reclamação, problema, irregularidade, corrupção, buraco, lixo, obra, esgoto
- EDUCATIVO: gov.br, INSS, CPF, login, conta, senha, benefício, aposentadoria, aplicativo, site, carteira, e-sus
- MENU: menu, início, voltar, sair, opções, ajuda, oi, olá, oii
- INCERTO: não dá para classificar claramente

Responda APENAS com uma dessas palavras."""


async def handle(ctx: dict, message: str) -> tuple[dict, str]:
    name = ctx.get("name") or "cidadão"
    msg_lower = message.lower().strip()

    # Comandos globais
    if msg_lower in ("menu", "início", "inicio", "0", "voltar", "sair"):
        ctx["current_agent"] = "orchestrator"
        ctx["current_step"] = "menu"
        ctx["collected"] = {}
        ctx["complaint_draft"] = {}
        return ctx, MENU_TEXT.format(name=name)

    if ctx["current_step"] == "menu":
        # Número do menu
        if message.strip() == "1":
            ctx["current_agent"] = "health"
            ctx["current_step"] = "health_listen"
            return ctx, (
                f"Olá, {name}! 🩺\n\n"
                "Pode me contar o que está sentindo?\n"
                "Fique à vontade para descrever com suas próprias palavras — também entendo áudio!\n\n"
                "_(Digite *0* a qualquer hora para voltar ao menu)_"
            )

        if message.strip() == "2":
            ctx["current_agent"] = "complaint"
            ctx["current_step"] = "complaint_start"
            from app.agents.complaint import START_TEXT
            return ctx, START_TEXT

        if message.strip() == "3":
            ctx["current_agent"] = "educational"
            ctx["current_step"] = "educational_start"
            from app.agents.educational import START_TEXT as EDU_START
            return ctx, EDU_START

        if message.strip() == "4":
            return ctx, (
                "Para outros assuntos, entre em contato:\n\n"
                "📞 Central *156* — Governo do DF\n"
                "🌐 www.df.gov.br\n\n"
                "Digite *menu* para voltar ao início."
            )

        # Texto livre — IA classifica
        intent = chat(
            messages=[{"role": "user", "content": message}],
            system=SYSTEM_ROUTER,
            temperature=0.0,
        ).upper().strip()

        for valid in ["SAUDE", "OUVIDORIA", "EDUCATIVO", "MENU", "INCERTO"]:
            if valid in intent:
                intent = valid
                break

        if intent == "SAUDE":
            ctx["current_agent"] = "health"
            ctx["current_step"] = "health_listen"
            # Passa a mensagem original direto para o health começar a escuta
            from app.agents.health import handle as health_handle
            ctx["symptoms_initial"] = message
            ctx["current_step"] = "health_clarify"
            from app.core.groq_client import chat as llm
            LISTENING_SYSTEM = """Você é um assistente de saúde pública do DF, simpático e acolhedor.
O usuário acabou de descrever um problema de saúde.
Faça UMA pergunta de acompanhamento para entender melhor.
Use linguagem simples e acolhedora. Entenda gírias e linguagem informal.
Seja breve — máximo 2 frases."""
            followup = llm(
                messages=[{"role": "user", "content": f"Usuário disse: {message}"}],
                system=LISTENING_SYSTEM,
                temperature=0.3,
            )
            return ctx, followup + "\n\n_(Digite *0* a qualquer hora para voltar ao menu)_"

        if intent == "OUVIDORIA":
            ctx["current_agent"] = "complaint"
            ctx["current_step"] = "complaint_start"
            from app.agents.complaint import START_TEXT
            return ctx, START_TEXT

        if intent == "EDUCATIVO":
            ctx["current_agent"] = "educational"
            ctx["current_step"] = "educational_start"
            from app.agents.educational import START_TEXT as EDU_START
            return ctx, EDU_START

        # Incerto ou menu
        return ctx, (
            "Não entendi bem. Veja as opções disponíveis:\n\n"
            + MENU_TEXT.format(name=name)
        )

    return ctx, MENU_TEXT.format(name=name)
