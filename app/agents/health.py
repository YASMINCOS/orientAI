"""
AGENTE DE SAÚDE
- Usuário fala primeiro (não recebe menu de cara)
- Triagem leve inspirada no Protocolo de Manchester
- Entende linguagem informal (gírias, abreviações)
- Dados mockados de UPAs, UBSs e Hospitais do DF
- Explica diferença entre UPA / UBS / Hospital
- Fluxo especial para picadas de animais peçonhentos (escorpião, cobra, aranha)

⚠️ NÃO faz diagnóstico. NÃO substitui médico.
⚠️ NUNCA diz para o usuário esperar ou que pode aguardar em caso de picada.
"""
from app.core.groq_client import chat
from app.services.health_data import get_upa_queues, get_nearest_units, get_unit_type_info

# ─── SISTEMA DE TRIAGEM ──────────────────────────────────────
TRIAGE_SYSTEM = """Você é um assistente de saúde pública do Distrito Federal.
Analise o que o usuário escreveu (pode ser linguagem informal, gírias, abreviações, erros de digitação)
e classifique a URGÊNCIA em:

- EMERGENCIA: risco imediato de vida → SAMU 192
- URGENTE: precisa de UPA hoje (dor forte, febre alta, vômito intenso, pressão, corte profundo, etc)
- MODERADO: pode ir a UBS, mas não pode esperar muito
- LEVE: pode agendar na UBS, sem urgência
- PECONHENTO: menção a picada/mordida de escorpião, cobra, aranha, abelha (enxame), lagartixa venenosa

Responda APENAS com uma dessas palavras: EMERGENCIA, URGENTE, MODERADO, LEVE, PECONHENTO
Nunca faça diagnóstico. Apenas classifique urgência."""

LISTENING_SYSTEM = """Você é um assistente de saúde pública do DF, simpático e acolhedor.
O usuário acabou de descrever um problema de saúde.

Sua tarefa:
1. Faça UMA pergunta de acompanhamento para entender melhor (ex: tempo, intensidade, outros sintomas)
2. Use linguagem muito simples e acolhedora, como se fosse conversar com um familiar
3. Entenda gírias e linguagem informal brasileira (tô, tá, mió, véio, etc)
4. Seja breve — máximo 2 frases

NÃO faça triagem ainda. Apenas mostre que entendeu e faça UMA pergunta."""

PECONHENTO_SYSTEM = """Você é um assistente de saúde pública do DF.
O usuário foi picado ou mordido por um animal peçonhento (escorpião, cobra ou aranha).

Sua tarefa:
1. Identifique qual animal pelo texto do usuário
2. Pergunte: consegue descrever o animal? há quanto tempo foi a picada? tem sintomas como dor, inchaço, tontura, vômito?
3. Seja MUITO acolhedor e calmo — não cause pânico, mas transmita urgência
4. Use linguagem simples
5. Máximo 3 frases

NÃO diga para o usuário esperar, repousar em casa ou que pode ser leve. NUNCA minimize a situação."""

# ─── BASE DE UNIDADES COM SORO ANTIPEÇONHENTO NO DF ─────────
# Fonte: Secretaria de Saúde do DF / CIEVS-DF (base mockada realista)
# Atualizar conforme dados oficiais da SES-DF
UNIDADES_SORO = {
    "escorpiao": [
        {
            "name": "Hospital de Base do DF (HBDF)",
            "tipo": "Hospital",
            "soros": ["antiescorpiônico", "antibotrópico", "antiloxoscélico"],
            "endereco": "SMHS Área Especial, Brasília",
            "phone": "(61) 3315-1600",
            "funciona": "24h",
            "obs": "Centro de referência para acidentes com animais peçonhentos no DF",
        },
        {
            "name": "UPA Norte (Sobradinho)",
            "tipo": "UPA",
            "soros": ["antiescorpiônico"],
            "endereco": "Sobradinho I, Brasília",
            "phone": "(61) 3486-0400",
            "funciona": "24h",
            "obs": "Atende picadas leves a moderadas de escorpião",
        },
        {
            "name": "UPA Sul (Gama)",
            "tipo": "UPA",
            "soros": ["antiescorpiônico"],
            "endereco": "Setor Central, Gama",
            "phone": "(61) 3388-0300",
            "funciona": "24h",
            "obs": "Atende picadas leves a moderadas de escorpião",
        },
        {
            "name": "Hospital Regional de Taguatinga (HRT)",
            "tipo": "Hospital",
            "soros": ["antiescorpiônico", "antibotrópico"],
            "endereco": "QSD 21 Área Especial, Taguatinga",
            "phone": "(61) 3451-0100",
            "funciona": "24h",
            "obs": "Referência para região oeste do DF",
        },
        {
            "name": "Hospital Regional de Ceilândia (HRC)",
            "tipo": "Hospital",
            "soros": ["antiescorpiônico"],
            "endereco": "QNM 28, Ceilândia",
            "phone": "(61) 3471-9600",
            "funciona": "24h",
            "obs": "Referência para Ceilândia e região",
        },
    ],
    "cobra": [
        {
            "name": "Hospital de Base do DF (HBDF)",
            "tipo": "Hospital",
            "soros": ["antibotrópico", "anticrotálico", "antilaquético", "antielapídico"],
            "endereco": "SMHS Área Especial, Brasília",
            "phone": "(61) 3315-1600",
            "funciona": "24h",
            "obs": "⭐ Principal referência para mordida de cobra no DF — maior variedade de soros",
        },
        {
            "name": "Hospital Regional de Taguatinga (HRT)",
            "tipo": "Hospital",
            "soros": ["antibotrópico", "anticrotálico"],
            "endereco": "QSD 21 Área Especial, Taguatinga",
            "phone": "(61) 3451-0100",
            "funciona": "24h",
            "obs": "Referência para região oeste",
        },
        {
            "name": "Hospital Regional de Sobradinho (HRS)",
            "tipo": "Hospital",
            "soros": ["antibotrópico"],
            "endereco": "Quadra 7, Sobradinho",
            "phone": "(61) 3486-0100",
            "funciona": "24h",
            "obs": "Referência para região norte do DF",
        },
    ],
    "aranha": [
        {
            "name": "Hospital de Base do DF (HBDF)",
            "tipo": "Hospital",
            "soros": ["antiloxoscélico", "antilatrodectus", "antifones"],
            "endereco": "SMHS Área Especial, Brasília",
            "phone": "(61) 3315-1600",
            "funciona": "24h",
            "obs": "⭐ Referência principal para picada de aranha — aranha-marrom, viúva-negra e caranguejeira",
        },
        {
            "name": "Hospital Regional de Taguatinga (HRT)",
            "tipo": "Hospital",
            "soros": ["antiloxoscélico"],
            "endereco": "QSD 21 Área Especial, Taguatinga",
            "phone": "(61) 3451-0100",
            "funciona": "24h",
            "obs": "Atende picada de aranha-marrom",
        },
        {
            "name": "UPA Norte (Sobradinho)",
            "tipo": "UPA",
            "soros": ["antiloxoscélico"],
            "endereco": "Sobradinho I, Brasília",
            "phone": "(61) 3486-0400",
            "funciona": "24h",
            "obs": "Atende casos leves de picada de aranha",
        },
    ],
}

# Aliases para detectar o animal pelo texto do usuário
ANIMAL_ALIASES = {
    "escorpiao": [
        "escorpião", "escorpiao", "lacraia", "escorpiã", "escorpião",
        "picado escorpião", "picou escorpião", "ferroada",
    ],
    "cobra": [
        "cobra", "serpente", "cascavel", "jararaca", "sucuri",
        "mordida cobra", "cobra mordeu", "picada cobra",
    ],
    "aranha": [
        "aranha", "aranha-marrom", "viúva negra", "viuva negra",
        "caranguejeira", "picada aranha", "aranha picou",
    ],
}


def _detectar_animal(texto: str) -> str | None:
    """Retorna 'escorpiao', 'cobra', 'aranha' ou None."""
    t = texto.lower()
    for animal, aliases in ANIMAL_ALIASES.items():
        for alias in aliases:
            if alias in t:
                return animal
    return None


def _montar_resposta_peconhento(animal: str) -> str:
    unidades = UNIDADES_SORO.get(animal, [])
    nomes = {
        "escorpiao": "escorpião 🦂",
        "cobra":     "cobra 🐍",
        "aranha":    "aranha 🕷️",
    }
    label = nomes.get(animal, "animal peçonhento")

    aviso = (
        f"🚨 *Picada de {label} — vá imediatamente a uma das unidades abaixo!*\n\n"
        "⚠️ *Não espere os sintomas piorarem.* O soro é mais eficaz quanto antes for aplicado.\n"
        "Se tiver tontura, falta de ar, vômito ou convulsão: *ligue agora para o SAMU — 192*\n\n"
        "🏥 *Unidades com soro disponível no DF:*\n"
    )

    linhas = []
    for u in unidades:
        soros_str = ", ".join(u["soros"])
        linhas.append(
            f"• *{u['name']}* ({u['tipo']})\n"
            f"  📍 {u['endereco']}\n"
            f"  📞 {u['phone']} — {u['funciona']}\n"
            f"  💉 Soros: {soros_str}\n"
            f"  ℹ️ {u['obs']}"
        )

    rodape = (
        "\n\n_⚠️ Dados de referência — ligue antes para confirmar disponibilidade do soro._\n"
        "_🚑 SAMU: 192 | CVT-DF (Centro de Vigilância Toxicológica): (61) 3325-1313_\n\n"
        "Digite *0* para voltar ao menu."
    )

    return aviso + "\n\n".join(linhas) + rodape


async def handle(ctx: dict, message: str) -> tuple[dict, str]:
    step     = ctx.get("current_step", "health_listen")
    location = ctx.get("location", "DF")
    name     = ctx.get("name", "cidadão")
    msg_lower = message.lower().strip()

    # ── Comandos globais ──────────────────────────────────────
    if msg_lower in ("0", "menu", "voltar", "sair", "início", "inicio"):
        ctx["current_agent"] = "orchestrator"
        ctx["current_step"]  = "menu"
        from app.agents.orchestrator import MENU_TEXT
        return ctx, MENU_TEXT.format(name=name)

    # ── Detecta animal peçonhento em QUALQUER etapa ───────────
    # Tem prioridade sobre qualquer outro fluxo
    animal = _detectar_animal(message)
    if animal:
        ctx["current_step"]    = "health_peconhento"
        ctx["animal_picada"]   = animal
        ctx["symptoms_initial"] = message

        # Faz uma pergunta rápida de acompanhamento antes de mostrar unidades
        followup = chat(
            messages=[{"role": "user", "content": f"Usuário disse: {message}"}],
            system=PECONHENTO_SYSTEM,
            temperature=0.2,
        )
        return ctx, (
            followup + "\n\n"
            "_(Responda rapidamente — assim que puder me dar essas informações, "
            "vou te mostrar onde encontrar o soro mais próximo.)_\n\n"
            "Digite *0* para voltar ao menu."
        )

    # ── Fluxo pós-pergunta de peçonhento ─────────────────────
    if step == "health_peconhento":
        animal = ctx.get("animal_picada", "escorpiao")
        ctx["current_step"] = "health_options"
        return ctx, _montar_resposta_peconhento(animal)

    # ── ETAPA 1: Escuta ativa ─────────────────────────────────
    if step == "health_listen":
        ctx["current_step"]     = "health_clarify"
        ctx["symptoms_initial"] = message

        followup = chat(
            messages=[{"role": "user", "content": f"Usuário disse: {message}"}],
            system=LISTENING_SYSTEM,
            temperature=0.3,
        )
        return ctx, followup + "\n\n_(Digite *0* a qualquer hora para voltar ao menu)_"

    # ── ETAPA 2: Classifica urgência ──────────────────────────
    if step == "health_clarify":
        initial  = ctx.get("symptoms_initial", "")
        full_desc = f"Sintoma inicial: {initial}\nDetalhes: {message}"
        ctx["symptoms_full"] = full_desc

        urgency = chat(
            messages=[{"role": "user", "content": full_desc}],
            system=TRIAGE_SYSTEM,
            temperature=0.0,
        ).strip().upper()

        for u in ["EMERGENCIA", "URGENTE", "MODERADO", "LEVE", "PECONHENTO"]:
            if u in urgency:
                urgency = u
                break

        # Se o modelo classificou como PECONHENTO na triagem
        if urgency == "PECONHENTO":
            animal = _detectar_animal(full_desc) or "escorpiao"
            ctx["animal_picada"] = animal
            ctx["current_step"]  = "health_options"
            return ctx, _montar_resposta_peconhento(animal)

        ctx["current_step"] = "health_options"
        ctx["last_urgency"] = urgency
        return ctx, _build_triage_result(urgency)

    # ── ETAPA 3: Opções pós-triagem ───────────────────────────
    if step == "health_options":
        if message.strip() == "1":
            ctx["current_step"] = "health_options"
            return ctx, await _show_queues()

        if message.strip() == "2":
            ctx["current_step"] = "health_find_unit"
            return ctx, (
                "Que tipo de unidade você quer encontrar?\n\n"
                "1️⃣ UPA (urgência, 24h)\n"
                "2️⃣ UBS (consulta, horário comercial)\n"
                "3️⃣ Hospital\n\n"
                "_(Digite o número)_"
            )

        if message.strip() == "3":
            ctx["current_step"] = "health_options"
            return ctx, _explain_units()

        if message.strip() == "4":
            ctx["current_agent"] = "orchestrator"
            ctx["current_step"]  = "menu"
            from app.agents.orchestrator import MENU_TEXT
            return ctx, MENU_TEXT.format(name=name)

        ctx["current_step"] = "health_options"
        return ctx, _post_triage_menu(ctx.get("last_urgency", "LEVE"))

    # ── ETAPA 3b: Encontrar unidade ───────────────────────────
    if step == "health_find_unit":
        unit_map  = {"1": "UPA", "2": "UBS", "3": "HOSPITAL"}
        unit_type = unit_map.get(message.strip())

        if unit_type:
            units_text = await _show_nearest(location, unit_type)
            info_text  = get_unit_type_info(unit_type)
            ctx["current_step"] = "health_options"
            return ctx, f"{info_text}\n\n{units_text}"

        ctx["current_step"] = "health_options"
        return ctx, _post_triage_menu(ctx.get("last_urgency", "LEVE"))

    # Fallback
    ctx["current_step"] = "health_listen"
    return ctx, (
        f"Olá, {name}! Pode me contar o que está sentindo? "
        "Fique à vontade para descrever com suas próprias palavras. 🩺\n\n"
        "_(Digite *0* para voltar ao menu)_"
    )


# ─── HELPERS ─────────────────────────────────────────────────

def _build_triage_result(urgency: str) -> str:
    if urgency == "EMERGENCIA":
        return (
            "🚨 *ATENÇÃO — Emergência!*\n\n"
            "Pelo que você descreveu, *ligue agora para o SAMU: 192*\n\n"
            "Não espere. O SAMU vai ao seu endereço.\n\n"
            "⚠️ Isso não é diagnóstico médico.\n\n"
            "O que deseja fazer agora?\n"
            "1️⃣ Ver filas das UPAs\n"
            "2️⃣ Encontrar unidade próxima\n"
            "3️⃣ Entender UPA, UBS e Hospital\n"
            "4️⃣ Voltar ao menu"
        )
    if urgency == "URGENTE":
        return (
            "🟠 *Recomendo que você vá a uma UPA hoje.*\n\n"
            "Os sintomas que você descreveu precisam de avaliação médica em breve.\n"
            "A UPA funciona 24 horas e não precisa de agendamento.\n\n"
            "⚠️ Isso não é diagnóstico médico.\n\n"
            "O que deseja fazer agora?\n"
            "1️⃣ Ver filas das UPAs (menor espera)\n"
            "2️⃣ Encontrar unidade próxima\n"
            "3️⃣ Entender UPA, UBS e Hospital\n"
            "4️⃣ Voltar ao menu"
        )
    if urgency == "MODERADO":
        return (
            "🟡 *Você pode ir a uma UBS (Unidade Básica de Saúde).*\n\n"
            "Seus sintomas merecem atenção, mas não parecem ser emergência.\n"
            "A UBS funciona seg-sex, 7h às 19h. Se piorar, vá à UPA.\n\n"
            "⚠️ Isso não é diagnóstico médico.\n\n"
            "O que deseja fazer agora?\n"
            "1️⃣ Ver filas das UPAs\n"
            "2️⃣ Encontrar UBS próxima\n"
            "3️⃣ Entender UPA, UBS e Hospital\n"
            "4️⃣ Voltar ao menu"
        )
    return (
        "🟢 *Seus sintomas parecem leves por enquanto.*\n\n"
        "Você pode agendar uma consulta na UBS do seu bairro.\n"
        "Se piorar (febre alta, dor intensa), procure uma UPA.\n\n"
        "⚠️ Isso não é diagnóstico médico.\n\n"
        "O que deseja fazer agora?\n"
        "1️⃣ Ver filas das UPAs\n"
        "2️⃣ Encontrar UBS próxima\n"
        "3️⃣ Entender UPA, UBS e Hospital\n"
        "4️⃣ Voltar ao menu"
    )


def _post_triage_menu(urgency: str) -> str:
    return (
        "O que deseja fazer?\n\n"
        "1️⃣ Ver filas das UPAs\n"
        "2️⃣ Encontrar unidade próxima\n"
        "3️⃣ Entender UPA, UBS e Hospital\n"
        "4️⃣ Voltar ao menu"
    )


def _explain_units() -> str:
    return (
        "📋 *Diferença entre UPA, UBS e Hospital*\n\n"
        "🔴 *UPA — 24 horas*\n"
        "Urgências e emergências: febre alta, dor forte, cortes, fraturas, vômito intenso, pressão alta.\n\n"
        "🟡 *UBS — Seg-Sex, 7h-19h*\n"
        "Consultas de rotina, vacinação, pré-natal, receitas, diabetes, hipertensão, saúde mental leve.\n\n"
        "🔵 *Hospital*\n"
        "Cirurgias, internações, UTI, especialidades. Acesso por encaminhamento ou SAMU (192).\n\n"
        "🚨 *SAMU: 192* — emergências que correm risco de vida\n\n"
        "O que deseja fazer?\n"
        "1️⃣ Ver filas das UPAs\n"
        "2️⃣ Encontrar unidade próxima\n"
        "4️⃣ Voltar ao menu"
    )


async def _show_queues() -> str:
    queues = await get_upa_queues()
    if not queues:
        return (
            "😕 Não consegui carregar as filas agora.\n\n"
            "Consulte diretamente: *indicadores.igesdf.org.br*\n\n"
            "Digite *menu* para voltar."
        )

    lines = [
        "🏥 *Filas UPAs do DF* _(dados estimados — demo)_\n"
        "⏰ Ordenadas da menor para a maior fila\n"
    ]
    for u in queues[:8]:
        emoji = "🟢" if u["waiting"] < 10 else ("🟡" if u["waiting"] < 25 else "🔴")
        lines.append(
            f"{emoji} *{u['name']}*\n"
            f"   👥 {u['waiting']} aguardando | ⏱ ~{u['wait_min']} min\n"
            f"   📞 {u['phone']}"
        )
    lines.append(
        "\n_ℹ️ Dados de demonstração. Consulte indicadores.igesdf.org.br para dados em tempo real._\n"
        "Digite *menu* para voltar."
    )
    return "\n\n".join(lines)


async def _show_nearest(location: str, unit_type: str = None) -> str:
    units = await get_nearest_units(location, unit_type)
    if not units:
        return (
            "😕 Não encontrei unidades para sua região.\n\n"
            "Consulte: *cnes.datasus.gov.br*\n"
            "Digite *menu* para voltar."
        )

    tipo_label = {"UPA": "UPAs (24h)", "UBS": "UBSs", "HOSPITAL": "Hospitais"}.get(unit_type or "", "Unidades")
    lines = [f"📍 *{tipo_label} próximas de {location}*\n"]
    for u in units[:5]:
        lines.append(
            f"• *{u['name']}* ({u['type']})\n"
            f"  📞 {u['phone']}\n"
            f"  ℹ️ {u.get('descricao', '')}"
        )
    lines.append("\nFonte: CNES/DataSUS | Digite *menu* para voltar.")
    return "\n\n".join(lines)