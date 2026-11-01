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
import os
import re
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app, url_for

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.utils import blob, categorias
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


# `foto.ab12cd34.jpg`: nome que `blob.enviar` dá no Blob, sempre com a
# miniatura ao lado. URL antiga (sufixo do próprio Blob) não tem.
_SUFIXO_BLOB = re.compile(r'\.[0-9a-f]{8}\.(jpe?g|png|webp)$')


def _miniatura(caminho):
    """Versão de 480 px (`<nome>-md.webp`) quando existe; senão a original.
    A vitrine mostra a foto em ~200 px: servir a de 800 px pesava 1 MiB na home.

    Local: confere no disco. URL: só as que `blob.enviar` nomeou, porque
    perguntar ao Blob se o arquivo existe custaria uma ida à rede por foto."""
    if not caminho:
        return None
    menor = blob.miniatura_de(caminho)
    if caminho.startswith(('http://', 'https://')):
        return menor if _SUFIXO_BLOB.search(caminho) else caminho
    if os.path.exists(os.path.join(current_app.static_folder, menor)):
        return _img(menor)
    return _img(caminho)


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
    """Link do expositor: domínio próprio quando existe (canônica, para o sinal
    de link ir ao site oficial e não à cópia em /expositor/<slug>); sem domínio,
    artesão abre dentro do portal para navegar pela Feira sem sair dele."""
    if getattr(r, 'tipo_negocio', 'bar') == 'artesao' and not (r.dominio or '').strip():
        return url_for('public.landing_expositor', slug=r.slug)
    return url_canonica(r)


# Categorias da Feira, com página própria (/feira/<slug>). As palavras são as
# mesmas que escolhem o ícone do pino no mapa (`produto/feira.html`, PALAVRAS):
# um expositor entra em todas as categorias em que o descritor ou as
# categorias dos produtos casarem. Ordem = ordem dos atalhos na página.
CATEGORIAS_DA_FEIRA = (
    ('comida-artesanal', 'Comida artesanal', ('pao', 'bolo', 'doce', 'queijo', 'geleia', 'compota',
     'biscoito', 'salgado', 'embutido', 'charcut', 'defumad', 'cafe', 'comida', 'molho',
     'tempero', 'mel', 'chopp', 'cerveja', 'bebida', 'vinho', 'pizza', 'empada', 'risot',
     'padaria', 'fermenta')),
    ('artesanato', 'Artesanato', ('ceramica', 'croche', 'trico', 'costura', 'bordado', 'madeira',
     'couro', 'vela', 'sabonete', 'artesanato', 'macrame', 'tecido', 'mosaico', 'vidro', 'wood')),
    ('plantas', 'Plantas e terrários', ('planta', 'flor', 'jardim', 'muda', 'suculenta',
     'orquidea', 'terrario', 'kokedama')),
    ('joias', 'Joias e bijuterias', ('joia', 'bijuteria', 'brinco', 'colar', 'pulseira', 'anel',
     'prata')),
    ('arte', 'Arte e bem-estar', ('arte$', 'artes$', 'artista', 'quadro', 'ilustra', 'pintura', 'livro', 'poster',
     'fotografia', 'tarot', 'taro', 'esoter', 'cristal', 'incenso', 'vintage')),
)


def _casa(palavra, chave):
    """Começo de palavra ('ceramica' casa 'ceramicas'); 'arte$' só a palavra
    inteira, senão 'arte' pegaria 'artesanato' e 'anel' pegaria 'canela'."""
    return palavra == chave[:-1] if chave.endswith('$') else palavra.startswith(chave)


def categorias_do_expositor(e):
    """Slugs de CATEGORIAS_DA_FEIRA para um item de `expositores()`.

    Palavra-chave no nome/descritor, ou categoria de produto que a taxonomia
    reconhece ("Bonecos e brinquedos" não tem palavra da lista, mas é artesanato)."""
    palavras = _norm(' '.join(filter(None, [e['nome'], e['descritor'],
                                            ' '.join(e['categorias'])]))).split()
    pela_taxonomia = {achado[0] for achado in map(categorias.subcategoria_de, e['categorias']) if achado}
    return [slug for slug, _, chaves in CATEGORIAS_DA_FEIRA
            if slug in pela_taxonomia or any(_casa(w, c) for w in palavras for c in chaves)]


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
            'foto': _img(c.hero_foto), 'foto_sm': _miniatura(c.hero_foto), 'url': _url_na_feira(r),
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
        achados.append(_item_produto(p, *pares[p.restaurant_id]))
        if len(achados) >= limite:
            break
    return achados


def _item_produto(p, r, c):
    return {
        'nome': p.nome, 'descricao': p.descricao, 'categoria': p.categoria,
        'img': _img(p.imagem), 'img_sm': _miniatura(p.imagem), 'preco': p.preco,
        'sob_encomenda': bool(p.sob_encomenda), 'slug': r.slug,
        'expositor': c.nome or r.nome, 'url': f'{_url_na_feira(r)}#produtos',
    }


def _produtos_de_artesao():
    """(produto, tenant, config) visíveis, só de artesão: é a vitrine da Feira."""
    pares = {r.id: (r, c) for r, c in _base_ativa().all()
             if getattr(r, 'tipo_negocio', None) == 'artesao'}
    return [(p, *pares[p.restaurant_id]) for p in _produtos_visiveis(list(pares))]


def subcategorias_com_produto():
    """{sub_slug: quantos produtos}, pela categoria que o expositor escreveu.
    Sem produto, a subcategoria não ganha página (seria conteúdo raso)."""
    contagem = {}
    for p, _, _ in _produtos_de_artesao():
        achado = categorias.subcategoria_de(p.categoria)
        if achado:
            contagem[achado[1]] = contagem.get(achado[1], 0) + 1
    return contagem


def produtos_da_subcategoria(sub, limite=96):
    """Produtos de todos os expositores cuja categoria cai em `sub`."""
    achados = []
    for p, r, c in _produtos_de_artesao():
        achado = categorias.subcategoria_de(p.categoria)
        if achado and achado[1] == sub:
            achados.append(_item_produto(p, r, c))
            if len(achados) >= limite:
                break
    return achados


def proximas_retiradas(hoje, antecedencia=2, quantas=6):
    """Próximos dias de feira (sábado e domingo) em que dá para retirar uma
    encomenda feita hoje, com `antecedencia` dias para produzir.

    Mesma regra do JS da sacola em `site/modelos/artesao/_base.html`; a página
    sai da borda da Vercel, então lá a conta é refeita no navegador.
    """
    dia = hoje + timedelta(days=max(antecedencia, 0))
    datas = []
    while len(datas) < quantas:
        if dia.weekday() in (5, 6):
            datas.append(dia)
        dia += timedelta(days=1)
    return datas


# (id, título, piso, teto). O id é também o caminho /presentes/<id>, que é o
# que a pessoa busca no Natal ("presente até 30 reais").
FAIXAS_DE_PRESENTE = (('ate-30', 'Até R$ 30', 0, 30), ('ate-60', 'De R$ 30 a R$ 60', 30, 60),
                      ('ate-120', 'De R$ 60 a R$ 120', 60, 120),
                      ('acima-120', 'Acima de R$ 120', 120, None))

# Cesta/kit sem coluna nova: o expositor já escreve "Cesta de Natal" ou
# "Kit café" no nome ou na categoria. Começo de palavra, então "caixinha" conta.
_PALAVRAS_CESTA = ('cesta', 'kit', 'box', 'caix')


def eh_cesta(produto):
    palavras = _norm(f'{produto.nome or ""} {produto.categoria or ""}').split()
    return any(w.startswith(p) for w in palavras for p in _PALAVRAS_CESTA)


def presentes():
    """Guia de Presentes: produtos com foto E preço de todos os expositores,
    por faixa de preço. Sem preço não entra: guia de presente é para decidir
    pelo quanto gastar."""
    pares = {r.id: (r, c) for r, c in _base_ativa().all()
             if getattr(r, 'tipo_negocio', 'bar') == 'artesao'}
    faixas = [{'id': i, 'titulo': t, 'itens': []} for i, t, _, _ in FAIXAS_DE_PRESENTE]
    for p in _produtos_visiveis(list(pares)):
        if not p.preco:
            continue
        r, c = pares[p.restaurant_id]
        item = {'nome': p.nome, 'img': _img(p.imagem), 'img_sm': _miniatura(p.imagem), 'preco': p.preco,
                'sob_encomenda': bool(p.sob_encomenda), 'cesta': eh_cesta(p),
                'expositor': c.nome or r.nome, 'url': f'{_url_na_feira(r)}#produtos'}
        # Faixas em ordem crescente: a primeira cujo teto cabe o preço.
        for faixa, (_, _, _, ate) in zip(faixas, FAIXAS_DE_PRESENTE):
            if ate is None or p.preco <= ate:
                faixa['itens'].append(item)
                break
    for f in faixas:
        f['itens'].sort(key=lambda i: i['preco'])
    return faixas
