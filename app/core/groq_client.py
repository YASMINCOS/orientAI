import base64
from groq import Groq
from app.core.config import get_settings

settings = get_settings()
_client = Groq(api_key=settings.groq_api_key)

def chat(messages: list, system: str = "", temperature: float = 0.3) -> str:
    """
    Chama o Groq com Llama 3.3 70B.
    messages = lista de {"role": "user"/"assistant", "content": "..."}
    """
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = _client.chat.completions.create(
        model=settings.model_fast,
        messages=full_messages,
        temperature=temperature,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcreve áudio usando Groq Whisper.
    O WhatsApp manda áudio em OGG — funciona direto.
    """
    response = _client.audio.transcriptions.create(
        file=(filename, audio_bytes, "audio/ogg"),
        model=settings.model_whisper,
        language="pt",
    )
    return response.text

def analyze_image(image_bytes: bytes, question: str) -> str:
    """
    Analisa uma imagem (print de tela) e responde uma pergunta sobre ela.
    Usado no agente educativo para guiar o cidadão.
    """
    b64 = base64.b64encode(image_bytes).decode()
    response = _client.chat.completions.create(
        model=settings.model_vision,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
                {"type": "text", "text": question},
            ],
        }],
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()
