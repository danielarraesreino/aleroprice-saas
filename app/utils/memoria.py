"""Memória Viva de Barão Geraldo: verbetes e mural lidos de YAML versionado.

O conteúdo mora em `app/data/memoria/` (não no banco): é curadoria com fonte,
revisada antes de entrar, e cresce por commit. A memória que a comunidade
manda pelo WhatsApp entra no `mural.yml` depois de checada.

Fontes principais: blog "História de Barão Geraldo", de Warney Smith (uso
autorizado com crédito e link), e a Wikipédia (CC BY-SA, com atribuição).
"""
import os
from functools import lru_cache
from urllib.parse import quote

import yaml

DIR_MEMORIA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'memoria')

CATEGORIAS = {
    'linha-do-tempo': 'Linha do tempo',
    'lugar': 'Lugares',
    'pessoa-familia': 'Pessoas e famílias',
    'causo': 'Causos',
}

# Chamadas do Mural: cada uma abre o WhatsApp da Feira já com a pergunta.
PROVOCACOES = [
    'Tem foto da Praça do Coco antes de 2000?',
    'Seu avô ou sua avó trabalhou na Rhodia ou no Funilense?',
    'Qual foi o primeiro bar que você frequentou em Barão?',
    'Qual a foto mais antiga que você tem da Albino de Oliveira?',
]

FONTES = {
    'historiadebaraogeraldo.wordpress.com': 'Blog História de Barão Geraldo (Warney Smith)',
    'wikipedia.org': 'Wikipédia',
}


def fonte_rotulo(url):
    """Nome da fonte para a linha de crédito ("Fonte: …")."""
    return next((rotulo for dominio, rotulo in FONTES.items() if dominio in (url or '')), 'fonte')


def _ler(nome):
    caminho = os.path.join(DIR_MEMORIA, nome)
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding='utf-8') as f:
        return yaml.safe_load(f) or []


@lru_cache(maxsize=1)
def verbetes():
    """Todos os verbetes, em ordem cronológica."""
    return sorted(_ler('verbetes.yml'), key=lambda v: (v.get('ano') or 9999, v['titulo']))


def verbete(slug):
    return next((v for v in verbetes() if v['slug'] == slug), None)


def capitulos():
    """Os cartões do mapa da home, na ordem dos capítulos."""
    return sorted((v for v in verbetes() if v.get('capitulo')), key=lambda v: v['capitulo'])


def por_categoria():
    grupos = {c: [] for c in CATEGORIAS}
    for v in verbetes():
        grupos.setdefault(v.get('categoria') or 'causo', []).append(v)
    return [(c, CATEGORIAS.get(c, c), itens) for c, itens in grupos.items() if itens]


def relacionados(atual, limite=4):
    tags = set(atual.get('tags') or [])
    outros = [v for v in verbetes() if v['slug'] != atual['slug']]
    outros.sort(key=lambda v: -len(tags & set(v.get('tags') or [])))
    return [v for v in outros if tags & set(v.get('tags') or [])][:limite]


@lru_cache(maxsize=1)
def mural():
    return _ler('mural.yml')


def hall_da_memoria():
    """Quem mais mandou memória publicada, para o reconhecimento público."""
    contagem = {}
    for m in mural():
        nome = (m.get('nome') or '').strip()
        if nome and not m.get('fonte_url'):   # citação de fonte não é contribuição
            contagem[nome] = contagem.get(nome, 0) + 1
    return sorted(contagem.items(), key=lambda par: -par[1])


def link_mapa(lugar):
    return f"https://www.google.com/maps/search/?api=1&query={lugar['lat']},{lugar['lng']}"


def link_street_view(lugar):
    """Street View do ponto, sem chave de API (abre no Google Maps)."""
    return ('https://www.google.com/maps/@?api=1&map_action=pano'
            f"&viewpoint={lugar['lat']},{lugar['lng']}")


def embed_street_view(lugar):
    """Street View embutido: só com a env GOOGLE_MAPS_EMBED_KEY (Maps Embed API)."""
    chave = os.environ.get('GOOGLE_MAPS_EMBED_KEY')
    if not chave:
        return None
    return ('https://www.google.com/maps/embed/v1/streetview'
            f"?key={quote(chave)}&location={lugar['lat']},{lugar['lng']}&fov=80")


def pontos_do_mapa(url_de):
    """Pinos do mapa: todo verbete com lugar. `url_de(slug)` monta o link."""
    pontos = []
    for v in verbetes():
        lugar = v.get('lugar')
        if not lugar:
            continue
        pontos.append({
            'id': v['slug'], 'lat': lugar['lat'], 'lng': lugar['lng'],
            'nome': v['titulo'], 'desc': v.get('resumo', ''),
            'url': url_de(v['slug']), 'street_view': link_street_view(lugar),
            'aproximado': bool(lugar.get('aproximado')),
        })
    return pontos


def foto_url(foto, tamanho=800):
    """Caminho em static da versão WebP gerada para o verbete."""
    if not foto or not foto.get('webp'):
        return None
    return f"img/memoria/{foto['webp']}-{tamanho}.webp"
