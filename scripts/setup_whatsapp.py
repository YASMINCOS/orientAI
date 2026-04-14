#!/usr/bin/env python3
"""
setup_whatsapp.py
Configura a instância do WhatsApp na Evolution API.
Execute UMA VEZ depois de subir o Docker.

Como usar:
  python setup_whatsapp.py
"""
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_KEY = os.getenv("EVOLUTION_API_KEY", "minha-chave-secreta-123")
INSTANCE = os.getenv("EVOLUTION_INSTANCE", "cidadao-df")
WEBHOOK_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")

HEADERS = {"apikey": EVOLUTION_KEY, "Content-Type": "application/json"}

def create_instance():
    print(f"📱 Criando instância '{INSTANCE}'...")
    r = httpx.post(
        f"{EVOLUTION_URL}/instance/create",
        headers=HEADERS,
        json={
            "instanceName": INSTANCE,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        },
    )
    print(f"   Status: {r.status_code}")
    if r.status_code in (200, 201):
        print("   ✅ Instância criada!")
    elif r.status_code == 409:
        print("   ℹ️  Instância já existe — continuando...")
    else:
        print(f"   ⚠️  Resposta: {r.text}")

def get_qrcode():
    print(f"\n📷 Buscando QR Code...")
    r = httpx.get(
        f"{EVOLUTION_URL}/instance/connect/{INSTANCE}",
        headers=HEADERS,
    )
    data = r.json()
    qr = data.get("qrcode", {}).get("base64") or data.get("base64")
    if qr:
        print("\n" + "="*60)
        print("ESCANEIE O QR CODE ABAIXO COM SEU WHATSAPP:")
        print("="*60)
        print(f"\n[QR Code em base64 disponível na Evolution API]")
        print(f"Acesse: {EVOLUTION_URL}/instance/qrcode/{INSTANCE}")
        print("\nOu use o endpoint:")
        print(f"GET {EVOLUTION_URL}/instance/connect/{INSTANCE}")
        print("="*60)
    else:
        print(f"   Resposta completa: {json.dumps(data, indent=2)}")

def configure_webhook():
    print(f"\n🔗 Configurando webhook para: {WEBHOOK_URL}/webhook")
    r = httpx.post(
        f"{EVOLUTION_URL}/webhook/set/{INSTANCE}",
        headers=HEADERS,
        json={
            "url": f"{WEBHOOK_URL}/webhook",
            "webhook_by_events": True,
            "webhook_base64": False,
            "events": [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "CONNECTION_UPDATE",
            ],
        },
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print("   ✅ Webhook configurado!")
    else:
        print(f"   ⚠️  {r.text}")

def check_connection():
    print(f"\n🔍 Verificando conexão...")
    r = httpx.get(
        f"{EVOLUTION_URL}/instance/connectionState/{INSTANCE}",
        headers=HEADERS,
    )
    data = r.json()
    state = data.get("instance", {}).get("state", "desconhecido")
    print(f"   Estado: {state}")
    if state == "open":
        print("   ✅ WhatsApp conectado!")
    else:
        print("   ⏳ Aguardando conexão — escaneie o QR Code")

if __name__ == "__main__":
    print("🚀 Configurando WhatsApp — Assistente Cidadão DF\n")
    create_instance()
    configure_webhook()
    get_qrcode()
    check_connection()
    print("\n✅ Configuração concluída!")
    print("   Próximo passo: escaneie o QR Code com seu WhatsApp")
