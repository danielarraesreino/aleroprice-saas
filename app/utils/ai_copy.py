"""Gerador de Copy Gastronômico, Assistente de Voz Concierge e Peças de Marketing com IA.

Utiliza NVIDIA NIM (Llama 3.3 70B) com a chave do usuário e fallback heurístico
robusto para gastronomia e bares de Barão Geraldo / Campinas.
"""
import os
import json
import re
import urllib.parse
import urllib.request
import urllib.error

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

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
    # Fallback seguro para runtime de produção
    return "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"

def _chamar_nvidia(prompt, system="Você é um assistente especialista em gastronomia e marketing de bares.", max_tokens=600):
    api_key = _obter_chave_nvidia()
    if not api_key:
        return None

    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": max_tokens,
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
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def gerar_descricao_prato(nome_prato, vibe="boteco", detalhes=""):
    """Gera uma descrição curta e vendedora (1-2 frases) para o prato."""
    if not nome_prato or not nome_prato.strip():
        return ""

    prompt = (
        f"Escreva uma descrição irresistível e curta (máximo 2 frases, ~30 palavras) "
        f"para o prato '{nome_prato}' em um cardápio de bar/restaurante ({vibe}). "
        f"Detalhes adicionais: {detalhes}. Não use aspas, nem introduções, responda direto o texto do cardápio."
    )
    texto = _chamar_nvidia(prompt, max_tokens=100)
    if texto:
        return texto.strip('"').strip("'")

    # Fallback elegante
    n_lower = nome_prato.lower()
    if any(k in n_lower for k in ["chope", "cerveja", "ipa", "pilsen", "lager", "tap"]):
        return f"{nome_prato.strip()} servido estupidamente gelado na pressão, com colarinho cremoso e aroma fresco."
    if any(k in n_lower for k in ["porção", "croquete", "coxinha", "pastel", "batata", "torresmo"]):
        return f"Porção generosa e crocante por fora, suculenta por dentro. Perfeita para beliscar com uma cerveja gelada."
    if any(k in n_lower for k in ["picanha", "espeto", "parrilla", "costela", "hambúrguer", "burger"]):
        return f"Carne nobre grelhada no ponto certo, com sabor defumado marcante e suculência incomparável."

    return "Receita artesanal da casa, preparada com ingredientes selecionados e tempero exclusivo. Porção perfeita para compartilhar."

def processar_voz_concierge(texto_ouvida, nome_bar="Nosso Bar", pratos=None, info=None):
    """Processa o áudio/texto falado pelo cliente e responde como Concierge de IA."""
    pratos = pratos or []
    info = info or {}
    zap = info.get("whatsapp") or ""
    nomes_pratos = [p.get("nome", "") for p in pratos[:5] if p.get("nome")]
    pratos_str = ", ".join(nomes_pratos) if nomes_pratos else "porções artesanais e chopes gelados"

    t_lower = (texto_ouvida or "").lower()

    # Tentativa com IA
    prompt = (
        f"Você é a voz do concierge virtual do bar '{nome_bar}'. O cliente acabou de falar: '{texto_ouvida}'.\n"
        f"Pratos da casa: {pratos_str}.\n"
        f"Endereço: {info.get('endereco', 'Barão Geraldo')}. Horário: {info.get('horario', 'Terça a Domingo a partir das 18h')}.\n"
        f"Gere uma resposta falada acolhedora, concisa (1 a 2 frases) para responder ao cliente em voz alta.\n"
        f"Classifique a intenção entre: 'reserva', 'cardapio', 'info'.\n"
        f"Responda EXCLUSIVAMENTE em formato JSON puro: "
        f'{{"intencao": "reserva|cardapio|info", "resposta_fala": "sua resposta em 1-2 frases", "resumo": "detalhes"}}'
    )
    res_ai = _chamar_nvidia(prompt, system="Você é um assistente de voz para bares que responde sempre em JSON válido.", max_tokens=250)
    if res_ai:
        try:
            # Extrai o bloco json
            m = re.search(r'\{.*\}', res_ai, re.DOTALL)
            if m:
                dados = json.loads(m.group(0))
                intencao = dados.get("intencao", "geral")
                resposta_fala = dados.get("resposta_fala", "")
                link_zap = ""
                if intencao == "reserva" and zap:
                    msg = f"Olá! Quero confirmar a reserva no {nome_bar}: {texto_ouvida}"
                    link_zap = f"https://wa.me/{zap}?text={urllib.parse.quote(msg)}"
                return {
                    "ok": True,
                    "intencao": intencao,
                    "resposta_fala": resposta_fala,
                    "link_whatsapp": link_zap,
                    "texto_original": texto_ouvida
                }
        except Exception:
            pass

    # Fallback heurístico inteligente
    if any(w in t_lower for w in ["reserva", "mesa", "lugares", "reservar", "aniversário", "sábado", "sexta", "amanhã"]):
        resposta = f"Com certeza! Preparei seu pedido de reserva no {nome_bar}. Basta confirmar no WhatsApp com 1 toque."
        msg = f"Olá! Gostaria de reservar uma mesa no {nome_bar}: '{texto_ouvida}'"
        link_zap = f"https://wa.me/{zap}?text={urllib.parse.quote(msg)}" if zap else ""
        return {
            "ok": True,
            "intencao": "reserva",
            "resposta_fala": resposta,
            "link_whatsapp": link_zap,
            "texto_original": texto_ouvida
        }

    if any(w in t_lower for w in ["cardápio", "prato", "comida", "comer", "beber", "chope", "cerveja", "porção", "preço"]):
        resposta = f"Aqui no {nome_bar} nossos destaques são: {pratos_str}. Todos preparados na hora e servidos estupidamente gelados!"
        return {
            "ok": True,
            "intencao": "cardapio",
            "resposta_fala": resposta,
            "link_whatsapp": "",
            "texto_original": texto_ouvida
        }

    # Info geral
    horario = info.get("horario") or "de terça a domingo a partir das 18h"
    endereco = info.get("endereco") or "em Barão Geraldo"
    resposta = f"Estamos abertos {horario}, localizados {endereco}. Venha aproveitar a noite conosco!"
    return {
        "ok": True,
        "intencao": "info",
        "resposta_fala": resposta,
        "link_whatsapp": "",
        "texto_original": texto_ouvida
    }

def gerar_pecas_marketing(nome_bar="Nosso Bar", pratos=None, vibe="boteco"):
    """Gera 3 peças publicitárias e posts de alta conversão para o bar."""
    pratos = pratos or []
    nomes_pratos = [p.get("nome", "") for p in pratos[:4] if p.get("nome")]
    pratos_str = ", ".join(nomes_pratos) if nomes_pratos else "nossas porções exclusivas e chope artesanal"

    prompt = (
        f"Gere 3 peças publicitárias prontas para o Instagram do bar '{nome_bar}' em Barão Geraldo (vibe: {vibe}).\n"
        f"Pratos em destaque: {pratos_str}.\n"
        f"Peça 1: Post de Sexta-Feira / Happy Hour (Chamada irresistível + hashtags locais).\n"
        f"Peça 2: Destaque Gastronômico (Foto do prato principal + copy apetitosa).\n"
        f"Peça 3: Story Interativo (Enquete / Pergunta com alto engajamento).\n"
        f"Responda em formato JSON com a estrutura:\n"
        f'[{{"tipo": "Happy Hour Sexta", "titulo": "...", "copy": "...", "hashtags": "#baraogeraldo #campinas ...", "sugestao_visual": "..."}}, ...]'
    )

    res_ai = _chamar_nvidia(prompt, system="Você é um diretor de marketing digital para gastronomia.", max_tokens=700)
    if res_ai:
        try:
            m = re.search(r'\[.*\]', res_ai, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception:
            pass

    # Fallback estruturado
    return [
        {
            "tipo": "Happy Hour & Sexta-Feira",
            "titulo": f"Sextou com Chope Trincando no {nome_bar}! 🍻",
            "copy": f"A melhor hora da semana chegou! Mesa posta, chope artesanal na pressão e {pratos_str} saindo fumegando da cozinha. Marque aqui quem vai pagar a primeira rodada com você hoje! 👇",
            "hashtags": "#BaraoGeraldo #Campinas #HappyHourCampinas #BarCampinas #ChopeArtesanal",
            "sugestao_visual": "Foto em close da torneira de chope enchendo a taça com colarinho cremoso ao fundo da casa cheia."
        },
        {
            "tipo": "Destaque Gastronômico",
            "titulo": f"O Sabor que é Tradição em Barão Geraldo 🔥",
            "copy": f"Feito com tempero de verdade e ingredientes de primeira: conheça nossos pratos mais pedidos. Peça direto na mesa pelo nosso cardápio digital oficial!",
            "hashtags": "#GastronomiaCampinas #ComidaDeBoteco #Petiscos #BaraoGeraldoSP",
            "sugestao_visual": "Foto aérea em alta resolução da porção com molho artesanal e fumaça saindo."
        },
        {
            "tipo": "Story Interativo",
            "titulo": "Enquete da Noite: Qual o seu Combo Perfeito? 🗳️",
            "copy": f"Qual você escolhe para abrir a noite no {nome_bar}?\n🅰️ Chope Pilsen + Porção Crocante\n🅱️ IPA Artesanal + Petisco Especial\nVota na enquete!",
            "hashtags": "#Enquete #Stories #BarDaVila #BaraoGeraldo",
            "sugestao_visual": "Story com fundo escuro, duas fotos lado a lado e adesivo de enquete no centro."
        }
    ]
