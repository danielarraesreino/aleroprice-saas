"""A Feira como um todo: quem expõe, onde fica e quem está hoje.

Alimenta a página `/feira` (mapa + lista + busca). Mora aqui, e não nas views,
porque a mesma lógica serve ao mapa, à lista e à busca de produto — e porque
"hoje" precisa ser o de São Paulo.

Por que o fuso importa
----------------------
A função roda em UTC. Sábado às 21h em Barão já é domingo para o servidor, e o
"estou na feira hoje" de sábado à noite viraria "hoje" do domingo. `hoje_br()`
é o único jeito de perguntar a data neste módulo.

Quem aparece
------------
Expositor da Feira = tenant ativo que é artesão OU que já tem ponto marcado no
mapa. Bar sem coordenada fica na vitrine da home, não aqui: lista de 80 casas
sem lugar no mapa não ajuda quem está andando na praça.
"""
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import url_for

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.utils.site_router import url_canonica

FUSO = ZoneInfo('America/Sao_Paulo')

# Caixa de Campinas e entorno. Coordenada fora daqui é GPS ruim (ou 0,0 de
# aparelho sem sinal) e jogaria o pino no meio do oceano: melhor recusar.
LAT_MIN, LAT_MAX = -23.20, -22.50
LNG_MIN, LNG_MAX = -47.40, -46.70

# Praça do Coco, onde a Feira acontece: centro do mapa quando não há pinos.
CENTRO = (-22.8226773, -47.0820887)

TIPOS = ('bar', 'artesao')
ROTULO_TIPO = {'bar': 'Bar', 'artesao': 'Artesão'}


def hoje_br(agora=None):
    """Data de hoje em São Paulo (e não em UTC)."""
    agora = agora or datetime.now(tz=FUSO)
    return agora.astimezone(FUSO).date()


def coordenada_valida(lat, lng):
    """(lat, lng) como float dentro de Campinas, ou None. Aceita string com vírgula."""
    try:
        la = float(str(lat).replace(',', '.'))
        ln = float(str(lng).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    if not (LAT_MIN <= la <= LAT_MAX and LNG_MIN <= ln <= LNG_MAX):
        return None
    return la, ln


def alternar_na_feira(cfg, hoje=None):
    """Liga/desliga o "estou na feira hoje". Devolve True se ficou ligado."""
    hoje = hoje or hoje_br()
    cfg.na_feira_em = None if cfg.na_feira_em == hoje else hoje
    return cfg.na_feira_em == hoje


def _norm(texto):
    """minúscula e sem acento: 'Linguiça' casa com 'linguica'."""
    base = unicodedata.normalize('NFKD', texto or '')
    return ''.join(c for c in base if not unicodedata.combining(c)).casefold()


def _img(caminho):
    if not caminho:
        return None
    if caminho.startswith(('http://', 'https://')):
        return caminho
    return url_for('static', filename=caminho)


def _base_ativa():
    """Pares (tenant, config) dos que podem aparecer. Uma query só: sem N+1."""
    return (db.session.query(Restaurante, SiteConfig)
            .join(SiteConfig, SiteConfig.restaurant_id == Restaurante.id)
            .filter(Restaurante.ativo.isnot(False)))


def _produtos_visiveis(ids=None):
    """Produtos que a vitrine mostra: ativos e COM foto (mesma regra da página)."""
    q = ProdutoSite.query.filter(ProdutoSite.ativo.isnot(False),
                                 ProdutoSite.imagem.isnot(None),
                                 ProdutoSite.imagem != '')
    if ids is not None:
        q = q.filter(ProdutoSite.restaurant_id.in_(ids))
    return q.order_by(ProdutoSite.restaurant_id, ProdutoSite.ordem, ProdutoSite.id).all()


def _url_na_feira(r):
    """Expositor artesão abre dentro do portal (/bar/<slug>) para o visitante
    navegar pela Feira sem sair do domínio; bar externo usa a URL canônica."""
    if getattr(r, 'tipo_negocio', 'bar') == 'artesao':
        return url_for('public.landing_slug', slug=r.slug)
    return url_canonica(r)


def expositores(tipo=None, so_hoje=False, q=None, hoje=None):
    """Lista de expositores da Feira, quem está hoje primeiro.

    `q` casa com nome, descritor, ponto, categorias e nomes de produto.
    """
    hoje = hoje or hoje_br()
    pares = [(r, c) for r, c in _base_ativa().all()
             if c.lat is not None or getattr(r, 'tipo_negocio', None) == 'artesao']
    ids = [r.id for r, _ in pares]
    por_tenant = {}
    for p in _produtos_visiveis(ids):
        por_tenant.setdefault(p.restaurant_id, []).append(p)

    termos = _norm(q).split() if q else []
    saida = []
    for r, c in pares:
        t = r.tipo_negocio if r.tipo_negocio in TIPOS else 'bar'
        if tipo and t != tipo:
            continue
        produtos = por_tenant.get(r.id, [])
        categorias = list(dict.fromkeys(p.categoria for p in produtos if p.categoria))
        esta_hoje = c.na_feira_em == hoje
        if so_hoje and not esta_hoje:
            continue
        if termos:
            palheiro = _norm(' '.join(filter(None, [
                c.nome or r.nome, c.descritor, c.ponto_na_feira, ' '.join(categorias),
                ' '.join(p.nome for p in produtos)])))
            if not all(termo in palheiro for termo in termos):
                continue
        saida.append({
            'slug': r.slug, 'nome': c.nome or r.nome, 'tipo': t,
            'tipo_rotulo': ROTULO_TIPO[t], 'descritor': c.descritor,
            'foto': _img(c.hero_foto), 'url': _url_na_feira(r),
            'lat': c.lat, 'lng': c.lng, 'ponto': c.ponto_na_feira,
            'hoje': esta_hoje, 'categorias': categorias[:4],
            'total_produtos': len(produtos),
        })
    saida.sort(key=lambda e: (not e['hoje'], _norm(e['nome'])))
    return saida


def buscar_produtos(q, limite=48):
    """Produtos de todos os expositores que casam com TODAS as palavras de `q`."""
    termos = _norm(q).split()
    if not termos:
        return []
    pares = {r.id: (r, c) for r, c in _base_ativa().all()}
    achados = []
    for p in _produtos_visiveis(list(pares)):
        palheiro = _norm(' '.join(filter(None, [p.nome, p.descricao, p.categoria])))
        if not all(termo in palheiro for termo in termos):
            continue
        r, c = pares[p.restaurant_id]
        achados.append({
            'nome': p.nome, 'descricao': p.descricao, 'categoria': p.categoria,
            'img': _img(p.imagem), 'preco': p.preco,
            'sob_encomenda': bool(p.sob_encomenda),
            'expositor': c.nome or r.nome, 'url': f'{_url_na_feira(r)}#produtos',
        })
        if len(achados) >= limite:
            break
    return achados
