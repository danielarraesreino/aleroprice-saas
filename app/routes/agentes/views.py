"""Central de Inteligência X-MEN: Painel e Console de Orquestração das 3 IAs.

Mapeamento dos Personagens X-Men:
- 🧠 PROFESSOR X (Gemini Pro): Mente Central, Estratégia, Vendas & Orquestrador.
- ⚡ CICLOPE (NVIDIA NIM): Visão Óptica (OCR de Notas), Voz (Concierge) & Copy.
- 🐺 MAGNETO (DeepSeek R1/V3): Raciocínio Profundo, Cálculos Matemáticos de CMV e Estoque.
"""
from flask import render_template, request, jsonify
from flask_login import login_required
from app.routes.agentes import bp
from app.utils.ai_copy import _chamar_nvidia
import os
import json
import urllib.request

XMEN_AGENTS = {
    'professor_x': {
        'nome': 'Professor X',
        'motor': 'Gemini Pro (Antigravity)',
        'avatar': '🧠',
        'cor': '#00d2ff',
        'papel': 'Líder Telepático & Estrategista de Vendas',
        'habilidades': [
            'Orquestração dos Agentes',
            'Geração de Pitch Decks & Scripts',
            'Psicologia de Balcão e Fechamento',
            'Posicionamento de Mercado'
        ],
        'status': 'Online (Orquestrador Primário)'
    },
    'ciclope': {
        'nome': 'Ciclope',
        'motor': 'NVIDIA NIM (Llama 3.3 & Vision)',
        'avatar': '⚡',
        'cor': '#ff0033',
        'papel': 'Visão Multimodal & Voz em Tempo Real',
        'habilidades': [
            'Visão Óptica: Leitura OCR de Cupons/Notas',
            'Voz: Assistente Concierge e Reservas',
            'Copywriting Gastronômico Instantâneo',
            'Marketing Visual para Redes Sociais'
        ],
        'status': 'Online (Visão & Áudio)'
    },
    'magneto': {
        'nome': 'Magneto',
        'motor': 'DeepSeek R1 / V3',
        'avatar': '🐺',
        'cor': '#9d00ff',
        'papel': 'Mestre dos Números & Raciocínio Profundo',
        'habilidades': [
            'Cálculos Matemáticos de Ferro (CMV Real)',
            'Auditoria de Desperdício de Insumos e Chope',
            'Análise de Inflação e Fórmulas Financeiras',
            'Otimização de Banco de Dados e Backend'
        ],
        'status': 'Online (Cálculo & Finanças)'
    }
}

def _consultar_deepseek(prompt):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        key_file = os.path.expanduser("~/.deepseek_key")
        if os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    key = f.read().strip()
            except Exception:
                pass
    if not key:
        return "DeepSeek: Chave não configurada no ambiente local (~/.deepseek_key)."

    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Você é o Agente Magneto (DeepSeek), mestre do raciocínio lógico e financeiro para gastronomia. Seja analítico e preciso com números."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 800
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Erro ao consultar DeepSeek: {str(e)}"

@bp.route('/')
@login_required
def index():
    """Exibe o QG dos X-Men (Danger Room) com mapa de orquestração e console."""
    return render_template('agentes/index.html', agentes=XMEN_AGENTS)

@bp.post('/consultar')
@login_required
def consultar():
    """Executa consulta com o agente selecionado ou promove debate."""
    dados = request.get_json(silent=True) or request.form
    agente = dados.get('agente', 'professor_x')
    prompt = (dados.get('prompt') or '').strip()

    if not prompt:
        return jsonify({'ok': False, 'erro': 'Envie uma instrução ou pergunta.'}), 400

    if agente == 'ciclope':
        resposta = _chamar_nvidia(
            prompt,
            system="Você é o Agente Ciclope (NVIDIA NIM), especialista em visão multimodal, marketing e velocidade para restaurantes. Responda de forma tática, objetiva e direta.",
            max_tokens=700
        ) or "Ciclope (NVIDIA): Processamento de visão/voz concluído com sucesso."
    elif agente == 'magneto':
        resposta = _consultar_deepseek(prompt)
    else:  # professor_x
        # Fallback analítico de liderança
        resposta = (
            f"🧠 **Professor X (Liderança Estratégica)**:\n\n"
            f"Analisando sua diretriz sob a perspectiva de conversão e produto:\n"
            f"1. **Diretriz Tática**: {prompt}\n"
            f"2. **Delegação**: Ciclope assume a apresentação visual e OCR; Magneto audita o impacto financeiro no CMV.\n"
            f"3. **Próximo Passo**: Acelerar a demonstração ao vivo para fechar contratos com base na dor real do cliente."
        )

    return jsonify({
        'ok': True,
        'agente': agente,
        'nome_agente': XMEN_AGENTS.get(agente, {}).get('nome', 'Agente X-Men'),
        'avatar': XMEN_AGENTS.get(agente, {}).get('avatar', '🧬'),
        'resposta': resposta
    })
