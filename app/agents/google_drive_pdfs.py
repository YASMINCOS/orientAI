# app/agents/google_drive_pdfs.py

import httpx

# ID da pasta do Drive
DRIVE_FOLDER_ID = "1mYYKy4Gb36rVWnVWUppTt9BvuMZRjNYv"

# Mapeamento: chave do KNOWLEDGE_BASE → trecho do nome do arquivo no Drive
PDF_NAME_MAP = {
    "gov.br":              "govbr",
    "meu inss":            "inss",
    "carteira de trabalho":"carteira",
    "e-sus":               "esus",
    "assinatura":          "assinatura",   # ← NOVO: tutorial assinatura gov.br
}

async def get_pdf_url(topic_key: str, access_token: str) -> str | None:
    """
    Busca o PDF do Drive pelo nome do tema.
    Retorna o link de visualização pública (webViewLink) ou None.
    """
    keyword = PDF_NAME_MAP.get(topic_key)
    if not keyword:
        return None

    query = (
        f"'{DRIVE_FOLDER_ID}' in parents "
        f"and mimeType='application/pdf' "
        f"and name contains '{keyword}' "
        f"and trashed=false"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": query,
                "fields": "files(id, name, webViewLink, webContentLink)",
                "pageSize": 1,
            }
        )
        data = resp.json()
        files = data.get("files", [])
        if files:
            return files[0].get("webViewLink")
    return None