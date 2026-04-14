from fastapi import APIRouter, Request, HTTPException
from app.core.context import get_context, save_context, add_to_history
from app.core.whatsapp import send_text, download_media
from app.core.groq_client import transcribe_audio
import app.agents.orchestrator as orchestrator
import app.agents.health as health
import app.agents.complaint as complaint
import app.agents.educational as educational
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()

async def get_real_phone(lid_jid: str) -> str:
    lid_id = lid_jid.replace("@lid", "")
    try:
        r = aioredis.from_url(settings.redis_url)
        cached = await r.get(f"lid:{lid_id}")
        await r.aclose()
        if cached:
            return cached.decode()
    except Exception as e:
        print(f"Erro Redis lid lookup: {e}")
    return lid_id

async def save_lid_mapping(lid_jid: str, real_phone: str):
    lid_id = lid_jid.replace("@lid", "")
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.set(f"lid:{lid_id}", real_phone, ex=86400*30)
        await r.aclose()
    except Exception as e:
        print(f"Erro ao salvar lid mapping: {e}")

@router.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event = body.get("event", "")
    if event not in ("messages.upsert", "message"):
        return {"status": "ignored"}

    data = body.get("data", {})
    key = data.get("key", {})
    print(f"DEBUG key: {key}")
    msg = data.get("message", {})

    if key.get("fromMe", False):
        return {"status": "ignored"}

    remote_jid = key.get("remoteJid", "")
    remote_jid_alt = key.get("remoteJidAlt", "")
    is_lid = "@lid" in remote_jid

    if is_lid:
        if remote_jid_alt and "@s.whatsapp.net" in remote_jid_alt:
            phone = remote_jid_alt.replace("@s.whatsapp.net", "")
            is_lid = False
            await save_lid_mapping(remote_jid, phone)
        else:
            # FALLBACK TEMPORÁRIO PARA TESTES
            phone = "5561982040839"
            is_lid = False
    elif "@g.us" in remote_jid:
        return {"status": "ignored"}
    else:
        phone = remote_jid.replace("@s.whatsapp.net", "")

    if not phone:
        return {"status": "ignored"}

    text = (
        msg.get("conversation")
        or msg.get("extendedTextMessage", {}).get("text", "")
        or ""
    )

    # tenta transcrever áudio se não tiver texto
    if not text:
        audio_msg = msg.get("audioMessage", {})
        print(f"DEBUG audioMessage keys: {list(audio_msg.keys())}")
        print(f"DEBUG media_key presente: {bool(audio_msg.get('mediaKey', ''))}")
        print(f"DEBUG base64 presente: {bool(audio_msg.get('base64', ''))}")
        print(f"DEBUG url presente: {bool(audio_msg.get('url', ''))}")
        media_key_b64 = audio_msg.get("mediaKey", "")
        audio_b64 = audio_msg.get("base64", "")
        audio_url = audio_msg.get("url", "")

        if media_key_b64 and (audio_b64 or audio_url):
            try:
                import base64 as b64lib
                import hmac
                import hashlib
                from Crypto.Cipher import AES

                if audio_b64:
                    encrypted = b64lib.b64decode(audio_b64)
                else:
                    encrypted = await download_media(audio_url)

                media_key = b64lib.b64decode(media_key_b64)

                def hkdf(key, length, app_info=b""):
                    # ✅ CORRETO: salt de 32 bytes zerados primeiro
                    key = hmac.new(b"\0" * 32, key, hashlib.sha256).digest()
                    key_stream = b""
                    key_block = b""
                    block_index = 1
                    while len(key_stream) < length:
                        key_block = hmac.new(
                            key,
                            msg=key_block + app_info + chr(block_index).encode("utf-8"),
                            digestmod=hashlib.sha256
                        ).digest()
                        block_index += 1
                        key_stream += key_block
                    return key_stream[:length]

                expanded = hkdf(media_key, 112, b"WhatsApp Audio Keys")
                iv = expanded[0:16]
                cipher_key = expanded[16:48]

                # remove MAC dos últimos 10 bytes
                ciphertext = encrypted[:-10]

                cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(ciphertext)
                # remove padding PKCS7
                pad_len = decrypted[-1]
                decrypted = decrypted[:-pad_len]

                with open("/tmp/audio_test.ogg", "wb") as f:
                    f.write(decrypted)
                print(f"DEBUG áudio salvo: {len(decrypted)} bytes")

                text = transcribe_audio(decrypted, filename="audio.ogg")
                print(f"Áudio transcrito: {text}")
            except Exception as e:
                print(f"Erro ao descriptografar/transcrever áudio: {e}")
                import traceback
                traceback.print_exc()

    if not text:
        return {"status": "ignored"}

    name = data.get("pushName", "Cidadão")
    print(f"Mensagem de {phone} ({name}) [lid={is_lid}]: {text}")

    ctx = await get_context(phone)

    if is_lid and ctx.get("lid_unresolved", True) and not ctx.get("real_phone"):
        import re
        numbers = re.findall(r'\d{10,13}', text.replace(" ", ""))
        if numbers:
            real_phone = numbers[0]
            if not real_phone.startswith("55"):
                real_phone = "55" + real_phone
            await save_lid_mapping(remote_jid, real_phone)
            ctx["real_phone"] = real_phone
            ctx["lid_unresolved"] = False
            ctx["phone_original"] = phone
            await save_context(phone, ctx)
            phone = real_phone
            await send_text(phone, "✅ Número registrado! Vamos começar.\n\n")
        else:
            if not ctx.get("asked_phone"):
                ctx["asked_phone"] = True
                await save_context(phone, ctx)
                await send_text(
                    remote_jid,
                    "👋 Olá! Para funcionar corretamente, preciso do seu número de WhatsApp.\n\nDigite seu número com DDD (ex: 61999998888):"
                )
            return {"status": "ok"}

    if ctx.get("real_phone"):
        phone = ctx["real_phone"]

    if not ctx.get("name"):
        ctx["name"] = name
    if not ctx.get("location"):
        ctx["location"] = "DF"

    ctx = add_to_history(ctx, "user", text)
    agent = ctx.get("current_agent", "orchestrator")

    try:
        if agent == "orchestrator":
            ctx, response_text = await orchestrator.handle(ctx, text)
        elif agent == "health":
            ctx, response_text = await health.handle(ctx, text)
        elif agent == "complaint":
            ctx, response_text = await complaint.handle(ctx, text, None)
        elif agent == "educational":
            ctx, response_text = await educational.handle(ctx, text, None)
        else:
            ctx, response_text = await orchestrator.handle(ctx, text)
    except Exception as e:
        print(f"Erro no agente {agent}: {e}")
        import traceback
        traceback.print_exc()
        response_text = "😕 Tive um problema técnico. Digite *menu* para recomeçar."

    ctx = add_to_history(ctx, "assistant", response_text)
    await save_context(phone, ctx)
    await send_text(phone, response_text)
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Assistente Cidadão DF rodando!"}

@router.post("/messages-upsert")
async def webhook_messages_upsert(request: Request):
    return await webhook(request)

@router.post("/")
async def webhook_root(request: Request):
    return await webhook(request)