"""Leitor de Cupons e Notas Fiscais por Foto / OCR (Visão).

Fonte primária: gateway local OpenAI-compatible (freellmapi via localhost:3001),
modelo de visão (llama-3.2-11b-vision). Fallback: NVIDIA NIM direto, para quando
o gateway local estiver fora do ar.
"""
import os
import json
import re
import base64
import urllib.request
import urllib.error

from app.utils import ai_gateway

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

_PROMPT_OCR = (
    "Você é um sistema OCR especialista em documentos fiscais e cupons de compras para restaurantes.\n"
    "Analise a imagem da nota fiscal/recibo em anexo e extraia os dados em formato JSON puro:\n"
    "{\n"
    '  "fornecedor": "Nome da empresa/fornecedor",\n'
    '  "cnpj": "CNPJ se visível ou vazio",\n'
    '  "numero_nota": "Número do cupom/nota ou 0",\n'
    '  "data_emissao": "YYYY-MM-DD (ou data atual)",\n'
    '  "valor_total": 0.0,\n'
    '  "itens": [\n'
    "    {\n"
    '      "codigo": "1",\n'
    '      "descricao": "Nome do produto/insumo",\n'
    '      "quantidade": 1.0,\n'
    '      "unidade": "UN|KG|L|CX|PC",\n'
    '      "valor_unitario": 0.0,\n'
    '      "valor_total": 0.0\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Importante: Extraia todos os produtos listados. Se algum valor não for legível, estime com base no contexto. "
    "Responda EXCLUSIVAMENTE o bloco JSON, sem explicações em texto."
)


def _obter_chave_nvidia():
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key.strip()
    key_file = os.path.expanduser("~/.nvidia_key")
    if os.path.exists(key_file):
        try:
            with open(key_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return None


def _extrair_json(texto):
    m = re.search(r'\{.*\}', texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _ocr_via_nvidia(data_uri):
    """Fallback: chama a NVIDIA NIM direto (visão)."""
    api_key = _obter_chave_nvidia()
    if not api_key:
        return {"ok": False, "erro": "Chave da NVIDIA não configurada para OCR."}

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT_OCR},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "stream": False
    }

    try:
        req = urllib.request.Request(
            NVIDIA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "AleroSaas-OCR/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            texto_resp = data["choices"][0]["message"]["content"].strip()
            resultado = _extrair_json(texto_resp)
            if resultado:
                resultado["ok"] = True
                return resultado
            return {"ok": False, "erro": "A IA não conseguiu interpretar o formato do documento."}
    except Exception as e:
        return {"ok": False, "erro": f"Falha na comunicação com NVIDIA Vision: {str(e)}"}


def processar_foto_nfe(imagem_bytes, content_type="image/jpeg"):
    """Envia a imagem da nota fiscal para o modelo de visão e extrai JSON."""
    b64_img = base64.b64encode(imagem_bytes).decode("utf-8")
    data_uri = f"data:{content_type};base64,{b64_img}"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _PROMPT_OCR},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]
        }
    ]

    # 1) Gateway local (fonte única)
    texto = ai_gateway.chat_completions(
        ai_gateway.GATEWAY_MODEL_VISION,
        messages,
        temperature=0.2,
        max_tokens=1200,
    )
    if texto:
        resultado = _extrair_json(texto)
        if resultado:
            resultado["ok"] = True
            return resultado

    # 2) Fallback: NVIDIA NIM direto
    return _ocr_via_nvidia(data_uri)
