"""
Serviço de dados de saúde pública — DF
- Mock enriquecido para demo (UPAs, UBSs, Hospitais)
- Fallback para API CNES quando disponível

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O QUE CADA UNIDADE ATENDE:

🔴 UPA (Unidade de Pronto Atendimento) — 24h
   Urgências e emergências de MÉDIA complexidade.
   Ex: febre alta, cortes, fraturas simples, vômito intenso,
   dor forte, pressão alta, suspeita de dengue grave,
   pequenas cirurgias. Tem raio-x, exames laboratoriais.

🟡 UBS (Unidade Básica de Saúde) — horário comercial
   Atenção PRIMÁRIA — porta de entrada do SUS.
   Ex: consultas de rotina, vacinação, pré-natal,
   hipertensão, diabetes, saúde mental leve (ansiedade,
   depressão), agendamentos, renovação de receita.
   Funciona seg-sex, 7h-19h (maioria).

🔵 HOSPITAL — internação e alta complexidade
   Cirurgias, internações, UTI, especialidades complexas.
   Acesso geralmente via encaminhamento da UPA/UBS
   ou SAMU (192) para emergências graves.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import httpx
import random
from datetime import datetime

# ── UPAs do DF ───────────────────────────────────────────────
UPAS_DF = [
    {"name": "UPA Ceilândia",         "region": "Ceilândia",         "phone": "(61) 3471-7300", "address": "QNN 13 Área Especial, Ceilândia"},
    {"name": "UPA Samambaia",          "region": "Samambaia",         "phone": "(61) 3354-6100", "address": "QS 316 Conjunto 1, Samambaia"},
    {"name": "UPA Sobradinho",         "region": "Sobradinho",        "phone": "(61) 3486-3060", "address": "Q 14 Área Especial 1, Sobradinho"},
    {"name": "UPA Taguatinga",         "region": "Taguatinga",        "phone": "(61) 3352-3400", "address": "QSD 33 Área Especial, Taguatinga"},
    {"name": "UPA Planaltina",         "region": "Planaltina",        "phone": "(61) 3389-5600", "address": "Setor Tradicional, Planaltina"},
    {"name": "UPA Santa Maria",        "region": "Santa Maria",       "phone": "(61) 3344-5900", "address": "QR 204, Santa Maria"},
    {"name": "UPA Recanto das Emas",   "region": "Recanto das Emas",  "phone": "(61) 3348-4350", "address": "QD 407, Recanto das Emas"},
    {"name": "UPA Paranoá",            "region": "Paranoá",           "phone": "(61) 3468-5700", "address": "Quadra 2 AE, Paranoá"},
    {"name": "UPA Núcleo Bandeirante", "region": "Núcleo Bandeirante","phone": "(61) 3346-9100", "address": "Área Especial, Núcleo Bandeirante"},
    {"name": "UPA Gama",               "region": "Gama",              "phone": "(61) 3302-3700", "address": "Setor Leste, Gama"},
    {"name": "UPA Brazlândia",         "region": "Brazlândia",        "phone": "(61) 3476-5100", "address": "Setor Norte, Brazlândia"},
    {"name": "UPA São Sebastião",      "region": "São Sebastião",     "phone": "(61) 3350-5300", "address": "Trecho 2, São Sebastião"},
    {"name": "UPA Estrutural",         "region": "Estrutural",        "phone": "(61) 3902-1256", "address": "Setor de Chácara, Estrutural"},
]

# ── UBSs representativas do DF ────────────────────────────────
UBS_DF = [
    {"name": "UBS Asa Norte (CS 110)",      "region": "Asa Norte",       "phone": "(61) 3321-5480", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Asa Sul (CS 108)",        "region": "Asa Sul",         "phone": "(61) 3245-7800", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Taguatinga Centro",       "region": "Taguatinga",      "phone": "(61) 3352-3490", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Ceilândia Centro",        "region": "Ceilândia",       "phone": "(61) 3471-1400", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Gama Leste",              "region": "Gama",            "phone": "(61) 3302-3756", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Samambaia Norte",         "region": "Samambaia",       "phone": "(61) 3354-6160", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Santa Maria Centro",      "region": "Santa Maria",     "phone": "(61) 3344-5910", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Planaltina Norte",        "region": "Planaltina",      "phone": "(61) 3389-5610", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Sobradinho II",           "region": "Sobradinho",      "phone": "(61) 3486-3080", "horario": "Seg-Sex 7h-19h"},
    {"name": "UBS Recanto das Emas",        "region": "Recanto das Emas","phone": "(61) 3348-4360", "horario": "Seg-Sex 7h-19h"},
]

# ── Hospitais do DF ───────────────────────────────────────────
HOSPITAIS_DF = [
    {"name": "Hospital Regional de Taguatinga (HRT)", "region": "Taguatinga", "phone": "(61) 3451-0600", "especialidades": "Cirurgia, UTI, Maternidade"},
    {"name": "Hospital de Base do DF (HBDF)",          "region": "Asa Sul",    "phone": "(61) 3315-1600", "especialidades": "Alta complexidade, Trauma, Neurologia"},
    {"name": "Hospital Regional de Ceilândia (HRC)",   "region": "Ceilândia",  "phone": "(61) 3471-9400", "especialidades": "Cirurgia, Pediatria, Maternidade"},
    {"name": "Hospital Regional do Gama (HRGa)",       "region": "Gama",       "phone": "(61) 3302-5200", "especialidades": "Cirurgia, Obstetrícia, UTI"},
    {"name": "Hospital Regional de Sobradinho (HRS)",  "region": "Sobradinho", "phone": "(61) 3486-3400", "especialidades": "Cirurgia, Ortopedia, UTI"},
    {"name": "Hospital Regional de Planaltina (HRP)",  "region": "Planaltina", "phone": "(61) 3389-5700", "especialidades": "Clínica Médica, Maternidade"},
    {"name": "Hospital Regional de Santa Maria (HRSM)","region": "Santa Maria","phone": "(61) 3344-6100", "especialidades": "Clínica, Cirurgia, Maternidade"},
    {"name": "Hospital Regional do Paranoá (HRPa)",    "region": "Paranoá",    "phone": "(61) 3468-5900", "especialidades": "Clínica Médica, Obstetrícia"},
    {"name": "Hospital Regional de Samambaia (HRSam)", "region": "Samambaia",  "phone": "(61) 3354-6200", "especialidades": "Clínica, Cirurgia"},
    {"name": "Hospital Regional de Brazlândia (HRBr)", "region": "Brazlândia", "phone": "(61) 3476-5300", "especialidades": "Clínica Médica"},
]

CNES_API = "https://apidadosabertos.saude.gov.br/v1/cnes/estabelecimentos"


def _mock_queues() -> list[dict]:
    """
    Dados de demonstração com variação realista por horário.
    Em produção: substituir por scraping Playwright do indicadores.igesdf.org.br
    """
    hora = datetime.now().hour
    pico = hora in range(8, 12) or hora in range(17, 21)
    base_min, base_max = (15, 55) if pico else (3, 30)

    queues = []
    for upa in UPAS_DF:
        waiting = random.randint(base_min, base_max)
        wait_min = waiting * random.randint(2, 4)
        queues.append({
            "name": upa["name"],
            "region": upa["region"],
            "waiting": waiting,
            "wait_min": wait_min,
            "phone": upa["phone"],
            "source": "demo",
        })

    return sorted(queues, key=lambda x: x["waiting"])


async def get_upa_queues() -> list[dict]:
    """
    Tenta buscar filas do painel IGES-DF.
    O painel usa JS dinâmico — em produção usar Playwright.
    """
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            await client.get(
                "https://indicadores.igesdf.org.br/pagina-inicial/filasupa/",
                headers={"User-Agent": "Mozilla/5.0 (compatible; CidadaoDF/1.0)"},
                follow_redirects=True,
            )
        return _mock_queues()
    except Exception:
        return _mock_queues()


async def get_nearest_units(location: str, unit_type: str = None) -> list[dict]:
    """
    Tenta API CNES/DataSUS. Se falhar, usa dados estáticos do DF.
    unit_type: 'UPA', 'UBS', 'HOSPITAL' ou None
    """
    try:
        params = {"coUf": "53", "limit": 20}
        if unit_type == "UPA":
            params["dsTipoUnidade"] = "UNIDADE DE PRONTO ATENDIMENTO"
        elif unit_type == "UBS":
            params["dsTipoUnidade"] = "UNIDADE BASICA DE SAUDE"

        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(CNES_API, params=params)
            data = r.json()

        items = data.get("estabelecimentos", data.get("items", []))
        if not items:
            raise ValueError("API vazia")

        units = []
        for item in items[:10]:
            units.append({
                "name": item.get("nomeFantasia", item.get("nome", "")),
                "type": item.get("descricaoTipoUnidade", unit_type or "Unidade de Saúde"),
                "phone": item.get("telefone", "Não informado"),
                "address": item.get("logradouro", ""),
                "region": item.get("municipio", "DF"),
            })
        return units if units else _static_units(location, unit_type)

    except Exception:
        return _static_units(location, unit_type)


def _static_units(location: str, unit_type: str = None) -> list[dict]:
    """Fallback estático com dados reais do DF."""
    loc_lower = (location or "").lower()
    all_units = []

    if unit_type in (None, "UPA"):
        for u in UPAS_DF:
            all_units.append({
                "name": u["name"], "type": "UPA 24h",
                "phone": u["phone"], "region": u["region"],
                "descricao": "Urgências — funciona 24h",
            })

    if unit_type in (None, "UBS"):
        for u in UBS_DF:
            all_units.append({
                "name": u["name"], "type": "UBS",
                "phone": u["phone"], "region": u["region"],
                "descricao": f"Consultas/prevenção — {u.get('horario','Seg-Sex 7h-19h')}",
            })

    if unit_type in (None, "HOSPITAL"):
        for h in HOSPITAIS_DF:
            all_units.append({
                "name": h["name"], "type": "Hospital",
                "phone": h["phone"], "region": h["region"],
                "descricao": h.get("especialidades", ""),
            })

    if loc_lower:
        nearby = [u for u in all_units if loc_lower in u["region"].lower()]
        if nearby:
            return nearby[:5]

    return all_units[:5]


def get_unit_type_info(unit_type: str) -> str:
    """Explica o que cada tipo de unidade atende."""
    infos = {
        "UPA": (
            "🔴 *UPA — Unidade de Pronto Atendimento (24h)*\n"
            "Para urgências de média gravidade:\n"
            "• Febre alta persistente\n"
            "• Dor forte (cabeça, barriga, peito)\n"
            "• Cortes, fraturas, torções\n"
            "• Vômito ou diarreia intensa\n"
            "• Pressão alta descompensada\n"
            "• Crise asmática moderada\n"
            "• Suspeita de dengue com sinais de alerta\n\n"
            "🚨 Emergência grave (infarto, AVC, desmaio) → ligue *192 (SAMU)*"
        ),
        "UBS": (
            "🟡 *UBS — Unidade Básica de Saúde*\n"
            "Para cuidados de rotina e prevenção (seg-sex, 7h-19h):\n"
            "• Consultas gerais e renovação de receita\n"
            "• Vacinação e pré-natal\n"
            "• Controle de pressão e diabetes\n"
            "• Saúde bucal (odontologia)\n"
            "• Ansiedade e depressão leve\n"
            "• Agendamentos para especialistas"
        ),
        "HOSPITAL": (
            "🔵 *Hospital*\n"
            "Para casos de alta complexidade:\n"
            "• Cirurgias e internações\n"
            "• UTI e cuidados intensivos\n"
            "• Especialidades médicas complexas\n\n"
            "Acesso via encaminhamento da UPA/UBS ou pelo *SAMU (192)*."
        ),
    }
    return infos.get(unit_type.upper(), "")
