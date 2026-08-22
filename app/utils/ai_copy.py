"""Gerador de Copy Gastronômico com IA (NVIDIA NIM / Llama 3.3 / Fallback).

Gera descrições apetitosas e títulos gourmet para pratos de cardápio em menos
de 1 segundo. Se a API estiver offline ou sem chave, utiliza fallback heurístico
especializado em gastronomia brasileira.
"""
import os
import json
import urllib.request
import urllib.error

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

FALLBACK_TEMPLATES = [
    "Receita artesanal da casa, preparada com ingredientes selecionados e tempero exclusivo. Porção perfeita para compartilhar.",
    "Clássico do nosso cardápio, feito na hora com sabor marcante e apresentação impecável. Acompanha o melhor chope da casa.",
    "Feito com paixão e os melhores insumos locais. Uma explosão de sabor e textura que é tradição em Barão Geraldo.",
]

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

def gerar_descricao_prato(nome_prato, vibe="boteco", detalhes=""):
    """Gera uma descrição curta e vendedora (1-2 frases) para o prato."""
    if not nome_prato or not nome_prato.strip():
        return ""

    api_key = _obter_chave_nvidia()
    if api_key:
        prompt = (
            f"Escreva uma descrição irresistível e curta (máximo 2 frases, ~30 palavras) "
            f"para o prato '{nome_prato}' em um cardápio de bar/restaurante ({vibe}). "
            f"Detalhes adicionais: {detalhes}. Não use aspas, nem introduções, responda direto o texto do cardápio."
        )
        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [
                {"role": "system", "content": "Você é um redator especialista em cardápios gastronômicos de alta conversão."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6,
            "max_tokens": 120,
            "stream": False
        }
        try:
            req = urllib.request.Request(
                NVIDIA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "AleroSaas/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                texto = data["choices"][0]["message"]["content"].strip()
                if texto:
                    return texto.strip('"').strip("'")
        except Exception:
            pass

    # Fallback elegante baseado no nome do prato
    n_lower = nome_prato.lower()
    if any(k in n_lower for k in ["chope", "cerveja", "ipa", "pilsen", "lager", "tap"]):
        return f"{nome_prato.strip()} servido estupidamente gelado na pressão, com colarinho cremoso e aroma fresco."
    if any(k in n_lower for k in ["porção", "croquete", "coxinha", "pastel", "batata", "torresmo"]):
        return f"Porção generosa e crocante por fora, suculenta por dentro. Perfeita para beliscar com uma cerveja gelada."
    if any(k in n_lower for k in ["picanha", "espeto", "parrilla", "costela", "hambúrguer", "burger"]):
        return f"Carne nobre grelhada no ponto certo, com sabor defumado marcante e suculência incomparável."

    import random
    return random.choice(FALLBACK_TEMPLATES)
