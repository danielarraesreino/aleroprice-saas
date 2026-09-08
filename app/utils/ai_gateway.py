"""Fonte única de IA: gateway local OpenAI-compatible (freellmapi).

Centraliza as chamadas de IA em `OPENAI_BASE_URL` + `OPENAI_API_KEY` (o agregador
local em localhost:3001). Assim o app não depende mais de chaves soltas
espalhadas pelo sistema (~/.nvidia_key, ~/.deepseek_key): tudo fala com uma
porta só.

Cada chamada aqui retorna `None` quando o gateway não responde — e aí o caller
decide o fallback (ex.: NVIDIA NIM ou DeepSeek direto). Dessa forma o OCR de
nota e o agente Magneto continuam funcionando em produção mesmo se o gateway
local estiver fora do ar.
"""
import os
import json
import urllib.request
import urllib.error

# Nomes de modelo no agregador local. Podem ser sobrescritos por env.
GATEWAY_MODEL_VISION = os.environ.get('AI_VISION_MODEL', 'llama-3.2-11b-vision')
GATEWAY_MODEL_TEXT = os.environ.get('AI_TEXT_MODEL', 'llama-3.3-70b-instruct')
GATEWAY_MODEL_DEEPSEEK = os.environ.get('AI_DEEPSEEK_MODEL', 'deepseek-chat')


def _env(chave):
    valor = os.environ.get(chave)
    return valor.strip() if valor else None


def gateway_config():
    """Retorna (base_url, api_key) do gateway local, ou (None, None)."""
    return _env('OPENAI_BASE_URL'), _env('OPENAI_API_KEY')


def chat_completions(model, messages, temperature=0.2, max_tokens=1200, timeout=30):
    """Chama o gateway local (OpenAI-compatible) e retorna o texto, ou None.

    `messages` segue o formato OpenAI (inclusive o formato multimodal com
    ``content`` em lista de ``{type, text/image_url}``).
    """
    base, key = gateway_config()
    if not base or not key:
        return None

    url = base.rstrip('/') + '/chat/completions'
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {key}',
                'User-Agent': 'AleroSaas/1.0',
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content'].strip()
    except Exception:
        return None
