import os
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
from functools import lru_cache
from pathlib import Path

from flask import (
    Blueprint, render_template, request, jsonify, current_app, abort,
    redirect, url_for, flash, make_response, session,
)

from app.extensions import db
from app.models.modelo_reserva import Reserva
from app.models.modelo_restaurante import Restaurante

from . import bp
from app.utils.site_router import (
    _publicavel, eh_dominio_do_produto, slug_unico, tenant_por_host,
    tenant_por_slug, url_canonica, url_do_cardapio,
)
from app.utils import seo
from app.utils.vocabulario import tipo_do
from app.utils.temas import css_do_tema, cor_do_tema, tema_valido
from app.utils.copy_site import copy_da_vibe, vibe_valida
from app.utils.modelos import (
    MODELO_PADRAO, arquivo_do_modelo, modelo_valido,
    MODELO_ARTESAO_PADRAO, arquivo_do_modelo_artesao, modelo_artesao_valido,
    opcoes_de_modelo_artesao,
)
from app.utils.planos import pode, precos
from app.utils.tenant import limite_excedido


def _alerta_whatsapp(texto, phone=None, apikey=None):
    """Dispara alerta no WhatsApp do bar via CallMeBot (grátis).

    Usa o número e a apikey configurados no SiteConfig do bar (com fallback para env).
    Falha é silenciosa: nunca quebra a reserva — o botão wa.me segue como fallback pro cliente.
    """
    apikey = apikey or os.environ.get('CALLMEBOT_APIKEY')
    if not apikey or not phone:
        return
    params = urllib.parse.urlencode({'phone': phone, 'text': texto, 'apikey': apikey})
    url = 'https://api.callmebot.com/whatsapp.php?' + params
    try:
        urllib.request.urlopen(url, timeout=6)
        current_app.logger.info('CallMeBot: alerta de reserva enviado.')
    except Exception as e:  # noqa: BLE001 — alerta é best-effort
        current_app.logger.warning(f'CallMeBot falhou: {e}')


def _template_do_modelo(nome):
    """Arquivo do modelo, com rede de segurança pro template que ainda não existe.

    Os 6 modelos vivem em `app/utils/modelos.py`, mas os arquivos em
    `site/modelos/` entram um a um. Sem esse check, um `?modelo=` apontando pra
    template ainda não escrito derrubaria o site do bar com 500 — aqui ele só
    volta pro clássico, que sempre existe.
    """
    from jinja2 import TemplateNotFound
    arquivo = arquivo_do_modelo(nome)
    try:
        current_app.jinja_env.get_template(arquivo)
    except TemplateNotFound:
        current_app.logger.warning(f'Modelo {nome!r} sem template ({arquivo}); caindo no clássico.')
        return arquivo_do_modelo(MODELO_PADRAO)
    return arquivo


def _render_landing(rest):
    """Renderiza a landing pra um restaurante (tenant) qualquer."""
    from app.models.modelo_evento import Evento
    from app.models.modelo_promocao import Promocao

    _marcar_visita(rest)
    hoje = date.today()
    rid = rest.id if rest else None

    eventos_q = Evento.query.filter(Evento.ativo.is_(True), Evento.data >= hoje)
    promos_q = Promocao.query.filter(Promocao.ativo.is_(True))
    if rid is not None:
        eventos_q = eventos_q.filter(Evento.restaurant_id == rid)
        promos_q = promos_q.filter(Promocao.restaurant_id == rid)

    eventos = eventos_q.order_by(Evento.data.asc()).limit(6).all()
    promocoes = [p for p in promos_q.order_by(Promocao.data_cadastro.desc()).all() if p.vigente][:4]

    site = montar_site(rest)
    cfg = getattr(rest, 'site_config', None) if rest else None
    tema = getattr(cfg, 'tema', None) if cfg else None
    vibe = getattr(cfg, 'vibe', None) if cfg else None

    # Cor e tom também se espiam por querystring, igual ao modelo.
    #
    # O seletor do Modo Campo mostra a página mudando enquanto o dono escolhe,
    # e sem isto metade dos controles (cor, tom) não movia nada na prévia — o
    # vendedor tinha que salvar pra descobrir o resultado, no meio da conversa.
    # Mesma regra fechada de sempre: preset conhecido ou nada, e nunca grava.
    tema_espiado = (request.args.get('tema') or '').strip()
    vibe_espiada = (request.args.get('vibe') or '').strip()
    if tema_valido(tema_espiado):
        tema = tema_espiado
    if vibe_valida(vibe_espiada):
        vibe = vibe_espiada

    copy = copy_da_vibe(vibe, site.get('nome') or '')

    # Qual layout renderizar. `?modelo=<x>` é a prévia do vendedor: troca o
    # modelo só nesta resposta, sem gravar nada no banco — ele abre as opções
    # na frente do dono do bar e o site salvo continua o que era. Valor
    # desconhecido (na query ou no banco) cai no clássico, em silêncio.
    # Artesão tem o próprio catálogo de modelos (MODELOS_ARTESAO), com a mesma
    # regra: o salvo vale, `?modelo=` espia sem gravar, desconhecido cai no padrão.
    artesao = tipo_do(rest) == 'artesao'
    valido = modelo_artesao_valido if artesao else modelo_valido
    padrao = MODELO_ARTESAO_PADRAO if artesao else MODELO_PADRAO
    modelo_salvo = getattr(cfg, 'modelo', None) if cfg else None
    modelo_espiado = (request.args.get('modelo') or '').strip()
    previewando = valido(modelo_espiado)
    if previewando:
        modelo_atual = modelo_espiado
    else:
        modelo_atual = modelo_salvo if valido(modelo_salvo) else padrao

    # Claro ou escuro é escolha da casa, não do celular de quem visita.
    #
    # Todo modelo já sabe se pintar nos dois modos, mas quem decidia era o
    # sistema do visitante (`prefers-color-scheme`). Na demonstração isso é ruim
    # duas vezes: o vendedor não consegue mostrar "e no claro?" — que é metade
    # da conversa sobre visual — e o dono aprova um site que o cliente dele pode
    # ver de outro jeito.
    #
    # `auto` mantém o comportamento antigo (segue o aparelho + toggle da página).
    # `claro`/`escuro` fixam, e `?modo=` espia sem gravar, igual ao modelo.
    modo_salvo = getattr(cfg, 'tema_modo', None) if cfg else None
    modo_espiado = (request.args.get('modo') or '').strip()
    modo_atual = (modo_espiado if modo_espiado in ('claro', 'escuro', 'auto')
                  else (modo_salvo or 'auto'))
    if modo_espiado in ('claro', 'escuro', 'auto'):
        previewando = True
    # O template estampa isto no <html>; vazio = decide no navegador, como antes.
    tema_forcado = {'claro': 'light', 'escuro': 'dark'}.get(modo_atual, '')

    # Degradação por plano: quem não paga perde o controle do site, não o
    # endereço. Sem reservas online, o formulário vira botão de WhatsApp — o
    # cliente do bar nunca fica sem resposta.
    reservas_ativas = pode(rest, 'reservas')
    if not pode(rest, 'agenda'):
        eventos = []
    if not pode(rest, 'promocoes'):
        promocoes = []

    # Prévia sem agenda própria demonstra o recurso em vez de escondê-lo. É o que
    # o dono do bar mais quer ver ("quem toca sexta"), e evento futuro não existe
    # em dado público — sem isto, a seção some justamente na hora da venda.
    # Cada item vem marcado como exemplo e a página já é declaradamente prévia.
    if rest is not None and getattr(rest, 'eh_demo', False):
        from app.utils.vitrine import eventos_de_exemplo, promocoes_de_exemplo
        if not eventos:
            eventos = eventos_de_exemplo(vibe)
        if not promocoes:
            promocoes = promocoes_de_exemplo(vibe)

    conteudo = montar_conteudo(rest)

    # Dados estruturados: o mesmo grafo pra qualquer tenant, montado do que já
    # está nesta função — nenhuma query nova, nenhum dado inventado. É o que
    # faz o bar existir pro Google e pras IAs como fato (endereço, horário,
    # nota, cardápio) e não como imagem bonita. Ver app/utils/seo.py.
    #
    # A prévia comercial entra aqui igual ao cliente: ela já é `noindex` no
    # template, e `dados_estruturados` recusa por conta própria os itens de
    # demonstração (`exemplo=True`) — inclusive quando um dia a prévia deixar
    # de ser noindex.
    endereco_canonico = url_canonica(rest)
    json_ld = seo.serializar(seo.dados_estruturados(
        rest, site, conteudo['dishes'], conteudo['reviews'], eventos,
        endereco_canonico, url_do_cardapio(rest), produtos=conteudo['produtos'],
    ))
    meta_desc = seo.meta_descricao(site, rest)

    arquivo = (arquivo_do_modelo_artesao(modelo_atual) if artesao
               else _template_do_modelo(modelo_atual))
    resp = make_response(render_template(arquivo,
                           eventos=eventos, promocoes=promocoes,
                           site=site, tema_css=css_do_tema(tema),
                           tema_cor=cor_do_tema(tema), tenant=rest, copy=copy,
                           modelo_atual=modelo_atual, previewando=previewando,
                           modelos_artesao=opcoes_de_modelo_artesao() if artesao else None,
                           modo_atual=modo_atual, tema_forcado=tema_forcado,
                           reservas_ativas=reservas_ativas,
                           json_ld=json_ld, meta_desc=meta_desc,
                           bairro_titulo=seo.bairro_para_titulo(site),
                           url_canonica=endereco_canonico,
                           contato_vendas=os.environ.get('FEIRA_WHATSAPP', ''),
                           email_vendas=os.environ.get('FEIRA_EMAIL', 'contato@feiradebarao.com.br'),
                           # Selo do Caminhos: só para quem ligou no painel, e
                           # nunca na prévia — o bar que ainda não é cliente não
                           # declara apoio a nada em nome de ninguém.
                           apoia_caminhos=(bool(getattr(cfg, 'apoia_caminhos', False))
                                           and not getattr(rest, 'eh_demo', False)),
                           **conteudo))
    # Mesma regra da vitrine: visitante sem sessão recebe a cópia da borda da
    # Vercel e não espera cold start nem o banco acordar. A página não carrega
    # token de sessão (o formulário busca em /novidades/token na hora de
    # enviar). Prévia espiada (?modelo=, ?tema=) não entra no cache.
    if not previewando:
        _na_borda(resp)
    return resp


def _na_borda(resp):
    """Página igual para todo visitante sem sessão: sai da borda da Vercel."""
    if (current_app.config['SESSION_COOKIE_NAME'] not in request.cookies
            and not request.args):
        resp.headers['Cache-Control'] = 'public, s-maxage=300, stale-while-revalidate=86400'
        session.accessed = False
    return resp


@bp.route('/')
def landing():
    """Raiz: quem manda é o domínio da requisição.

    - bardavila.bar (Restaurante.dominio) -> site daquele bar
    - feiradebarao.com.br / localhost / preview -> landing do produto
    """
    host = request.host
    if not eh_dominio_do_produto(host):
        rest = tenant_por_host(host)
        if rest:
            return _render_landing(rest)
    resp = make_response(render_template('produto/landing.html', **_contexto_produto()))
    # A vitrine é igual para todo visitante (sem formulário com token, sem nada
    # de quem está logado), então a borda da Vercel pode servi-la pronta: o
    # visitante não espera o cold start da função (~9s) nem o banco acordar.
    # Depois de 5 min a borda segue entregando a cópia e renova em segundo
    # plano. Só para quem chega sem cookie de sessão, para nenhuma resposta com
    # sessão ir parar no cache.
    if current_app.config['SESSION_COOKIE_NAME'] not in request.cookies:
        resp.headers['Cache-Control'] = 'public, s-maxage=300, stale-while-revalidate=86400'
        # O context processor do Flask-Login lê a sessão em todo
        # render_template, e sessão lida faz o Flask mandar `Vary: Cookie` —
        # com isso a Vercel nunca guardava a vitrine (só MISS). Aqui não há
        # cookie e a página não depende de sessão: nada a variar.
        session.accessed = False
    return resp


def _bares_da_feira():
    """As barracas da feira: prévias de Barão Geraldo já montadas, lidas dos
    mesmos leads versionados que publicam cada /bar/<slug>.

    Nenhuma query e nenhum dado inventado — é o arquivo que o aplicador de
    demos usa como fonte da verdade. Barraca só entra com produto na banca:
    precisa de nota do Google, foto de capa e endereço em Barão. Ficam de fora
    o bar-vitrine fictício (fonte `vitrine-da-campanha`) e lead desativado.

    As fotos vêm de `img/feira/<slug>-{480,800}.jpg`: recortes 4:3 otimizados
    (≤ 50 KB) gerados a partir das capas das demos. Vivem numa pasta própria
    de propósito — dentro de `img/demo/<slug>/` o `fotos_do_bar()` as varreria
    pra dentro da galeria da prévia do bar no próximo `aplicar-demos`.
    """
    import yaml
    from app.utils.demos import listar_leads

    static_dir = os.path.join(current_app.root_path, 'static')
    bares = []
    for caminho in listar_leads():
        slug = os.path.splitext(os.path.basename(caminho))[0]
        try:
            with open(caminho, encoding='utf-8') as f:
                dados = yaml.safe_load(f) or {}
        except Exception:
            continue
        if not isinstance(dados, dict) or dados.get('ativo', True) is False:
            continue
        if (dados.get('demo') or {}).get('fonte') == 'vitrine-da-campanha':
            continue
        site = dados.get('site') or {}
        nota = str(site.get('nota_google') or '').strip()
        regiao = ' '.join(str(site.get(k) or '')
                          for k in ('endereco', 'cidade_uf', 'kicker'))
        if not nota or 'Barão' not in regiao:
            continue
        if not os.path.isfile(os.path.join(static_dir, 'img', 'demo', slug, 'capa.jpg')):
            continue

        thumb = f'img/feira/{slug}-480.jpg'
        grande = f'img/feira/{slug}-800.jpg'
        tem_thumb = os.path.isfile(os.path.join(static_dir, 'img', 'feira', f'{slug}-480.jpg'))
        bares.append({
            'slug': slug,
            'nome': (dados.get('nome') or slug).strip(),
            'nota': nota,
            'avaliacoes': site.get('qtd_avaliacoes'),
            'descritor': (site.get('descritor') or '').strip(),
            # Lead novo sem recorte gerado ainda: cai na capa original. Pesada,
            # mas a barraca aparece — gerar o recorte é otimização, não requisito.
            'foto_480': thumb if tem_thumb else f'img/demo/{slug}/capa.jpg',
            'foto_800': grande if (tem_thumb and os.path.isfile(
                os.path.join(static_dir, 'img', 'feira', f'{slug}-800.jpg'))) else None,
        })

    # Barraca só vai pra vitrine se o /bar/<slug> dela abre. O arquivo diz o
    # que existe; quem diz o que está no ar é o banco (`_publicavel`, que tira
    # prévia vencida). Sem este corte a home anunciava 23 barracas e todas
    # davam 404 assim que o prazo das demos passou.
    if bares:
        no_ar = {r.slug for r in _publicavel(
            Restaurante.query.filter(Restaurante.slug.in_([b['slug'] for b in bares]))
        )}
        bares = [b for b in bares if b['slug'] in no_ar]

    # Quem tem mais avaliação abre a feira: volume é o argumento (1.951 pesa
    # mais que qualquer adjetivo), e a ordem fica estável entre deploys.
    bares.sort(key=lambda b: (-(b['avaliacoes'] or 0), b['nome']))
    return bares


def _preco_publico():
    """O preço anunciado, num lugar só.

    A landing e o cadastro são a mesma venda em duas telas: quem clica em
    "montar sozinho" já leu o valor e precisa reencontrá-lo igual na hora de
    dar o e-mail. Escrever o número no template do cadastro criava a chance de
    a página prometer um preço e a outra cobrar outro.

    O valor vem de `planos.precos()`, que é quem o sistema usa pra cobrar.
    Antes esta função lia `FEIRA_PRECO` e `planos.precos()` lia
    `FEIRA_PRECO_SITE`: duas envs para o mesmo preço, e a vitrine anunciava um
    número enquanto a cobrança usava outro — a divergência exata que o docstring
    de `precos()` dizia ter resolvido. `FEIRA_PRECO` continua valendo como
    sobreposição só da vitrine, para testar discurso sem mexer na cobrança.
    """
    from app.utils.planos import precos
    return {
        'preco': os.environ.get('FEIRA_PRECO') or precos()['site'],
        'preco_periodo': os.environ.get('FEIRA_PRECO_PERIODO', 'por mês'),
        'preco_detalhe': os.environ.get(
            'FEIRA_PRECO_DETALHE',
            'Site no ar, reservas, cardápio digital e gestão.'
        ),
    }


# A feira em si. Dados confirmados pelo organizador em 18/10/2026; o resto
# (agenda, barracas físicas) entra quando ele mandar — não inventar.
FEIRA = {
    'local': 'Praça do Coco',
    'bairro': 'Barão Geraldo, Campinas – SP',
    'horarios': [
        {'dia': 'Sábado', 'schema': 'https://schema.org/Saturday', 'abre': '10:00', 'fecha': '16:00'},
        {'dia': 'Domingo', 'schema': 'https://schema.org/Sunday', 'abre': '10:00', 'fecha': '15:00'},
    ],
}


def _vitrine_de_expositores(limite=6):
    """Quem aparece na home: os que avisaram que estão hoje primeiro, depois os demais.

    A home nunca pode cair por causa disso: se a consulta falhar (coluna que
    ainda não existe, banco fora), a seção some e o resto da página segue.
    """
    try:
        from app.utils import feira as fe
        lista = fe.expositores()
    except Exception:
        db.session.rollback()
        return {'exp_vitrine': [], 'exp_total': 0, 'exp_hoje': 0}
    return {'exp_vitrine': lista[:limite], 'exp_total': len(lista),
            'exp_hoje': sum(1 for e in lista if e['hoje'])}


def _contexto_produto():
    """Dados comerciais da landing de venda. Vêm de env pra não versionar
    número de telefone nem preço — os dois mudam sem deploy."""
    zap = (os.environ.get('FEIRA_WHATSAPP') or '').strip()
    msg = urllib.parse.quote('Oi! Vi o Feira de Barão e quero saber como funciona pro meu bar.')

    bares = _bares_da_feira()
    com_nota = [float(b['nota'].replace(',', '.')) for b in bares]
    nota_media = (f"{sum(com_nota) / len(com_nota):.1f}".replace('.', ',')
                  if com_nota else None)

    from app.utils.modelos import opcoes_de_modelo
    from app.utils.planos import compra_do_site, taxa_de_instalacao, precos
    tab_precos = precos()
    return {
        **_vitrine_de_expositores(),
        'zap_url': f'https://wa.me/{zap}?text={msg}' if zap else '#preco',
        'taxa_setup': taxa_de_instalacao(),
        'compra': compra_do_site(),
        'precos': tab_precos,
        'preco_site': tab_precos['site'],
        'preco_pro': tab_precos['pro'],
        **_preco_publico(),
        'bares': bares,
        'total_bares': len(bares),
        'total_avaliacoes': sum(b['avaliacoes'] or 0 for b in bares),
        'nota_media': nota_media,
        'modelos': opcoes_de_modelo(),
        'feira': FEIRA,
        **_contexto_memoria(),
    }


def _contexto_memoria():
    """O mapa da memória na home: cartões, pinos e mural vêm dos verbetes."""
    from app.utils import memoria as mem
    return {
        'mem': mem,
        'memoria_capitulos': mem.capitulos(),
        'memoria_pontos': mem.pontos_do_mapa(
            lambda s: url_for('public.memoria_verbete', slug=s)),
        'memoria_mural': mem.mural()[:6],
        'zap_memoria': _zap_memoria(
            'Oi! Quero mandar uma memória/foto de Barão Geraldo para o Mural.\n\n'
            'Nome para o crédito:\nQuando foi:\nO que aconteceu:\n\n'
            'Autorizo publicar no feiradebarao.com.br com meu nome.'),
        'memoria_provocacoes': [
            (q, _zap_memoria(f'Oi! Sobre "{q}"\n\nO que eu tenho:\nNome para o crédito:\n\n'
                             'Autorizo publicar no feiradebarao.com.br com meu nome.'))
            for q in mem.PROVOCACOES],
    }


@bp.route('/feira')
def feira():
    """Expositores da Feira: mapa, lista e busca de produto.

    Sem parâmetro a página é igual para todo visitante e sai da borda da
    Vercel (`_na_borda`); com `?q=`/`?tipo=`/`?hoje=` é resposta própria.
    """
    from app.utils import feira as fe

    q = (request.args.get('q') or '').strip()[:60]
    tipo = request.args.get('tipo') if request.args.get('tipo') in fe.TIPOS else None
    so_hoje = request.args.get('hoje') == '1'

    lista = fe.expositores(tipo=tipo, so_hoje=so_hoje, q=q)
    pontos = [{'slug': e['slug'], 'nome': e['nome'], 'tipo': e['tipo'], 'url': e['url'], 'lat': e['lat'],
               'lng': e['lng'], 'ponto': e['ponto'], 'hoje': e['hoje']}
              for e in lista if e['lat'] is not None and e['lng'] is not None]
    resp = make_response(render_template(
        'produto/feira.html', expositores=lista, pontos=pontos,
        produtos=fe.buscar_produtos(q) if q else [],
        q=q, tipo=tipo, so_hoje=so_hoje,
        total_hoje=sum(1 for e in lista if e['hoje']),
        centro=fe.CENTRO, **_contexto_produto()))
    return _na_borda(resp)


@bp.route('/barao')
def barao():
    """Landing da campanha "Bares de Barão": a página que o vendedor manda no
    WhatsApp do dono de bar de Barão Geraldo e abre na mesa."""
    return render_template('produto/barao.html', campinas=False, **_contexto_produto())


# Perguntas da página indexável — só o que o produto faz hoje.
FAQ_PARA_BARES = [
    ('Precisa instalar aplicativo?',
     'Não. O cliente reserva pelo site e o aviso chega no WhatsApp do bar. Você edita o site pelo celular.'),
    ('Vocês cobram comissão por reserva ou pedido?',
     'Não. É uma mensalidade fixa, sem comissão por mesa.'),
    ('O perfil do Google continua sendo meu?',
     'Sim. A gente configura horário, fotos, cardápio e o link do site no seu Perfil da Empresa; o perfil segue no seu nome.'),
    ('Tem fidelidade?', 'Não. Se não servir, você cancela.'),
]


def _zap_memoria(texto):
    """WhatsApp da Feira (FEIRA_WHATSAPP) com a mensagem pronta. Sem número
    configurado, None — o template esconde o botão em vez de mandar a memória
    de alguém para o número errado."""
    zap = (os.environ.get('FEIRA_WHATSAPP') or '').strip()
    if not zap:
        return None
    return f'https://wa.me/{zap}?text={urllib.parse.quote(texto)}'


@bp.route('/memoria')
def memoria():
    """Memória Viva de Barão Geraldo: linha do tempo, lugares, pessoas, causos."""
    from app.utils import memoria as mem
    resp = make_response(render_template(
        'produto/memoria/hub.html', grupos=mem.por_categoria(),
        linha=mem.verbetes(), mural=mem.mural(), hall=mem.hall_da_memoria(),
        pontos=mem.pontos_do_mapa(lambda s: url_for('public.memoria_verbete', slug=s)),
        zap=_zap_memoria('Oi! Tenho uma memória/foto de Barão Geraldo pra mandar pro '
                         'Mural da Memória Viva.\n\nNome para o crédito:\nQuando foi:\n'
                         'O que aconteceu:\n\nAutorizo publicar no feiradebarao.com.br com meu nome.'),
        **_contexto_produto()))
    return _na_borda(resp)


@bp.route('/memoria/<slug>')
def memoria_verbete(slug):
    from app.utils import memoria as mem
    v = mem.verbete(slug)
    if v is None:
        abort(404)
    resp = make_response(render_template(
        'produto/memoria/verbete.html', v=v, relacionados=mem.relacionados(v),
        zap=_zap_memoria(f'Oi! Sobre "{v["titulo"]}" no site da Feira de Barão: tenho '
                         'uma foto/correção/história.\n\nNome para o crédito:\n\n'
                         'Autorizo publicar no feiradebarao.com.br com meu nome.'),
        **_contexto_produto()))
    return _na_borda(resp)


@bp.route('/site-para-bar-em-campinas')
def para_bares():
    """Mesma página de venda, indexável e para Campinas inteira: é a busca
    local sem concorrente ("site para bar em campinas", "cardápio no google
    maps"). /barao segue noindex, como link de campanha."""
    resp = make_response(render_template('produto/barao.html', campinas=True,
                                         faq=FAQ_PARA_BARES, **_contexto_produto()))
    return _na_borda(resp)


@bp.route('/robots.txt')
def robots():
    """O que o buscador não deve rastrear — e `/bar/` NÃO está nessa lista.

    Bloquear `/bar/` era duplamente errado. Primeiro porque `/bar/<slug>` é o
    endereço de todo cliente que ainda não comprou domínio próprio: o bar pagava
    por um site que o Google estava proibido de ler.

    Segundo porque não protegia a prévia — protegia menos. `Disallow` impede o
    rastreador de abrir a página, e é lá dentro que está o `noindex`. Sem poder
    ler, o Google pode manter a URL no índice sem conteúdo, que é exatamente o
    que se queria evitar. As duas diretivas se anulavam.

    Quem tira a prévia do índice é o `<meta name="robots" content="noindex">`
    que todo modelo emite quando `tenant.eh_demo` — e que some sozinho na
    conversão. O sitemap, por sua vez, lista só cliente.
    """
    from app.utils.site_router import dominio_do_produto

    corpo = (
        'User-agent: *\n'
        'Disallow: /cadastro\n'
        'Disallow: /app/\n'
        'Disallow: /campo/\n'
        'Disallow: /config-site/\n'
        'Disallow: /conteudo/\n'
        'Disallow: /campanha/\n'
        'Allow: /\n'
        'Allow: /llms.txt\n'
        'Allow: /llms-full.txt\n'
        f'\nSitemap: https://{request.host or dominio_do_produto()}/sitemap.xml\n'
    )
    return corpo, 200, {'Content-Type': 'text/plain; charset=utf-8'}


def _tenants_do_sitemap(dono_do_dominio):
    """Quem pode ser indexado neste domínio.

    Duas regras, uma consulta. `_publicavel` tira o tenant desligado (o mesmo
    filtro que decide se o site responde), e `Restaurante.clientes()` tira a
    prévia comercial: ela é `noindex` por definição — não é o site oficial do
    bar e não pode competir no Google com o negócio real do dono. Pedir
    indexação do que a própria página manda não indexar é contradição, e o
    Search Console reporta como erro.

    No domínio de um bar sobra só ele: sitemap de um host fala do próprio host,
    e o dono não hospeda a lista de clientes do produto no endereço dele.

    No domínio do produto, o inverso: bar com domínio próprio fica de fora. A
    URL dele é de outro host (o Google descarta), ele já tem o próprio sitemap,
    e cliente com domínio próprio não é barraca da feira — o Bar da Vila é um
    cliente da Vila Lemos, não de Barão Geraldo. Também fica de fora o tenant
    sem endereço no site: é conta de teste ou cadastro pela metade, e a página
    dele sairia vazia no Google.
    """
    consulta = _publicavel(Restaurante.clientes())
    if dono_do_dominio is not None:
        return consulta.filter(Restaurante.id == dono_do_dominio.id).all()
    consulta = consulta.filter(db.or_(Restaurante.dominio.is_(None),
                                      Restaurante.dominio == ''))
    return [t for t in consulta.order_by(Restaurante.id).all()
            if (getattr(getattr(t, 'site_config', None), 'endereco', None) or '').strip()]


@bp.route('/sitemap.xml')
def sitemap():
    """Mapa de indexação do domínio que fez a requisição.

    bardavila.bar/sitemap.xml  -> só o Bar da Vila
    feiradebarao.com.br/…      -> a home de venda + a home de cada cliente

    `lastmod` sai de `SiteConfig.data_atualizacao`, que é a data real da última
    edição do site. Não é enfeite: o Perplexity pesa frescor na hora de citar, e
    carimbar data falsa aqui é a maneira mais rápida de perder a confiança que
    justamente se quer ganhar. Bar que nunca foi editado sai sem `lastmod`.
    """
    from xml.sax.saxutils import escape
    from app.utils.site_router import dominio_do_produto

    paginas = []
    dono_do_dominio = tenant_por_host(request.host)
    if dono_do_dominio is None:
        # A landing de venda é a única página deste host que é nossa. Sitemap
        # sem nenhuma URL do próprio host é ignorado pelo Google.
        paginas.append((f'https://{dominio_do_produto()}/', None))
        paginas.append((f'https://{dominio_do_produto()}/site-para-bar-em-campinas', None))
        from app.utils.memoria import verbetes as _verbetes
        paginas.append((f'https://{dominio_do_produto()}/memoria', None))
        paginas.append((f'https://{dominio_do_produto()}/feira', None))
        for v in _verbetes():
            paginas.append((f"https://{dominio_do_produto()}/memoria/{v['slug']}", None))

    from app.models.modelo_sitecontent import DishCard
    for tenant in _tenants_do_sitemap(dono_do_dominio):
        cfg = getattr(tenant, 'site_config', None)
        atualizado = getattr(cfg, 'data_atualizacao', None)
        paginas.append((url_canonica(tenant), atualizado))
        # O cardápio é página própria (canonical e JSON-LD de Menu), mas só
        # existe com prato cadastrado — sem prato a rota dá 404.
        cardapio = url_do_cardapio(tenant)
        if cardapio and DishCard.query.filter_by(restaurant_id=tenant.id).first():
            paginas.append((cardapio, atualizado))

    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for endereco, atualizado in paginas:
        dia = atualizado.date() if isinstance(atualizado, datetime) else (
            atualizado if isinstance(atualizado, date) else None)
        linhas.append('  <url>')
        linhas.append(f'    <loc>{escape(endereco)}</loc>')
        if dia is not None:
            linhas.append(f'    <lastmod>{dia.isoformat()}</lastmod>')
        linhas.append('  </url>')
    linhas.append('</urlset>')

    return '\n'.join(linhas) + '\n', 200, {
        'Content-Type': 'application/xml; charset=utf-8'}


@bp.route('/llms.txt')
@bp.route('/llms-full.txt')
def llms_txt():
    """Gera resumo semântico no formato padrão llms.txt para consumo de LLMs e Search Engines de IA
    (Perplexity, ChatGPT Search, Gemini, Claude, Apple Intelligence).
    """
    from app.utils.site_router import dominio_do_produto, tenant_por_host
    from app.models.modelo_sitecontent import DishCard
    from app.models.modelo_restaurante import Restaurante

    dono_do_dominio = tenant_por_host(request.host)

    # 1. Se estiver no domínio de um bar específico (ex: bardavila.bar/llms.txt)
    if dono_do_dominio is not None:
        rest = dono_do_dominio
        cfg = getattr(rest, 'site_config', None)
        nome = rest.nome
        # Nada de "Barão Geraldo" carimbado: o bar com domínio próprio pode
        # estar em qualquer bairro (o Bar da Vila fica na Vila Lemos).
        local = (cfg.cidade_uf if cfg else None) or 'Campinas - SP'
        desc = (cfg.descritor if cfg else None) or (cfg.tagline if cfg else None) or f'Bar e restaurante em {local}'
        endereco = (cfg.endereco if cfg else None) or local
        horario = (cfg.horario if cfg else None) or 'Consulte o site oficial'
        whatsapp = (cfg.whatsapp if cfg else None) or (cfg.callmebot_phone if cfg else None) or ''
        
        pratos = DishCard.query.filter_by(restaurant_id=rest.id).order_by(DishCard.ordem.asc()).all()

        linhas = [
            f"# {nome} — {local}",
            "",
            f"> {desc}",
            "",
            "## Informações do Estabelecimento",
            f"- **Nome**: {nome}",
            f"- **Endereço**: {endereco}",
            f"- **Horário de Funcionamento**: {horario}",
            f"- **WhatsApp e Reservas**: {whatsapp}",
            f"- **Website Oficial**: {url_canonica(rest)}",
            "",
            "## Cardápio e Especialidades",
        ]
        if pratos:
            for p in pratos:
                preco_str = f" — R$ {p.preco}" if p.preco else ""
                linhas.append(f"- **{p.nome}**{preco_str}: {p.descricao or ''}")
        else:
            linhas.append("- Cardápio completo disponível diretamente no site oficial.")
        
        linhas.extend([
            "",
            "## Acesso e Reservas Online",
            f"Faça reservas de mesa e consulte o cardápio interativo em: {url_canonica(rest)}",
        ])
        return '\n'.join(linhas) + '\n', 200, {'Content-Type': 'text/markdown; charset=utf-8'}

    # 2. Se for no portal principal (feiradebarao.com.br/llms.txt)
    # Os mesmos do sitemap do portal: sem bar de domínio próprio (não é da
    # feira) e sem conta de teste.
    tenants = sorted(_tenants_do_sitemap(None), key=lambda t: t.nome or '')
    horarios = '; '.join(f"{h['dia']} das {h['abre'][:2]}h às {h['fecha'][:2]}h"
                         for h in FEIRA['horarios'])
    linhas = [
        "# Feira de Barão — Barão Geraldo, Campinas - SP",
        "",
        "> A Feira de Barão acontece na Praça do Coco, em Barão Geraldo (Campinas - SP), "
        "aos fins de semana. O portal reúne a memória do bairro e ajuda bares e "
        "restaurantes locais a serem encontrados no Google.",
        "",
        "## A feira",
        f"- **Onde**: {FEIRA['local']}, {FEIRA['bairro']}",
        f"- **Quando**: {horarios}",
        f"- **Site**: https://{dominio_do_produto()}/",
        "",
        "## Para donos de bar e restaurante",
        "- Site próprio, cardápio digital com QR, reserva com aviso no WhatsApp, "
        "pedido de avaliação no Google e perfil do Google Maps configurado.",
        f"- Planos e preços: https://{dominio_do_produto()}/#preco",
        "",
    ]
    from app.utils.memoria import verbetes as _verbetes
    if _verbetes():
        linhas += ["## Memória Viva de Barão Geraldo",
                   f"Hub: https://{dominio_do_produto()}/memoria "
                   "(fontes: blog História de Barão Geraldo, de Warney Smith, e Wikipédia)", ""]
        for v in _verbetes():
            linhas.append(f"- [{v['titulo']}](https://{dominio_do_produto()}/memoria/{v['slug']}) "
                          f"({v.get('periodo', '')}): {v.get('resumo', '')}")
        linhas.append("")
    if tenants:
        linhas.append("## Bares e restaurantes de Barão Geraldo na plataforma")

    for t in tenants:
        cfg = getattr(t, 'site_config', None)
        desc = (cfg.descritor if cfg else None) or (cfg.tagline if cfg else None) or 'Bar e Gastronomia'
        end = (cfg.endereco if cfg else None) or 'Barão Geraldo, Campinas - SP'
        linhas.append(f"### [{t.nome}]({url_canonica(t)})")
        linhas.append(f"- **Descrição**: {desc}")
        linhas.append(f"- **Endereço**: {end}")
        linhas.append(f"- **Cardápio Digital**: {url_canonica(t)}#cardapio")
        linhas.append("")

    linhas.extend([
        "## Links Úteis",
        f"- Portal: https://{dominio_do_produto()}/",
        f"- Cadastro de Estabelecimentos: https://{dominio_do_produto()}/cadastro",
        f"- Sitemap: https://{dominio_do_produto()}/sitemap.xml",
    ])

    return '\n'.join(linhas) + '\n', 200, {'Content-Type': 'text/markdown; charset=utf-8'}


def _marcar_visita(rest):
    """Conta abertura de prévia. A pergunta da campanha é 'o dono abriu?', e
    sem isso não há resposta — não existe analytics no projeto.

    Best-effort: falha aqui nunca pode derrubar o site do bar.
    """
    if not (rest and rest.eh_demo):
        return
    try:
        rest.demo_visitas = (rest.demo_visitas or 0) + 1
        if rest.demo_primeira_visita is None:
            rest.demo_primeira_visita = datetime.now()
            current_app.logger.info(
                f'Context: DEMO_ABERTA | {rest.slug} | fonte={rest.demo_fonte}')
        db.session.commit()
    except Exception:
        db.session.rollback()


@bp.route('/bar/<slug>')
def landing_slug(slug):
    """Site de um bar pelo slug. Sempre funciona, com ou sem domínio próprio —
    é o endereço das demos (ex.: /bar/bar-do-ze)."""
    rest = tenant_por_slug(slug)  # já filtra inativo
    if rest is None:
        abort(404)
    # Bar com domínio próprio não mora no portal da feira: no domínio do
    # produto, /bar/<slug> dele vira 301 para o endereço dele. Antes servia a
    # mesma página nos dois lugares (só o canonical apontava para o certo).
    if rest.dominio and eh_dominio_do_produto(request.host):
        return redirect(url_canonica(rest), code=301)
    return _render_landing(rest)


def _grupos_do_cardapio(dishes):
    """Divide o cardápio em blocos com título — sem inventar categoria.

    Não existe campo de categoria em `DishCard`, e chutar uma ("Entradas",
    "Pratos") seria escrever no cardápio do bar informação que o dono nunca
    deu. O que existe de verdade é `destaque`: o prato que a casa quer que
    apareça primeiro. Então é só isso que separa os dois blocos.

    O título só aparece quando há de fato dois blocos. Cardápio inteiro em
    destaque — ou nenhum — sai como lista única, sem cabeçalho enfeitando um
    grupo que não tem par: é a mesma regra da landing, onde seção sem conteúdo
    próprio não se anuncia.
    """
    destaques = [d for d in dishes if d.get('destaque')]
    demais = [d for d in dishes if not d.get('destaque')]
    if destaques and demais:
        return [{'titulo': 'Destaques da casa', 'itens': destaques},
                {'titulo': 'Também na cozinha', 'itens': demais}]
    return [{'titulo': None, 'itens': list(dishes)}]


def _render_cardapio(rest):
    """A página que abre da mesa: só o cardápio, o mais leve possível.

    Quem chega aqui apontou a câmera pro QR colado na mesa. Está sentado, com
    uma mão, no 4G do bar e quer uma coisa só — o que tem pra comer e quanto
    custa. Por isso esta página não carrega fonte de CDN, não anima nada e não
    repete hero, história, galeria nem formulário de reserva: tudo isso mora na
    landing, a um toque daqui.

    Read-only de propósito: não há carrinho, pedido nem pagamento. O QR na mesa
    substitui o cardápio plastificado, não o garçom.

    Sem plano nenhum no meio: cardápio é o que o bar imprimiu e colou na mesa.
    Um QR que para de abrir porque a mensalidade atrasou puniria o cliente do
    bar na frente do prato — o oposto da degradação descrita em `planos.py`.
    """
    site = montar_site(rest)
    dishes = montar_conteudo(rest)['dishes']

    # Bar sem prato cadastrado não tem cardápio — e página de cardápio vazia é
    # pior que 404: o cliente já está sentado, esperando ler alguma coisa.
    # Nada aponta pra cá nesse estado (o JSON-LD só publica `Menu.url` quando
    # há item, e o Modo Campo não oferece o QR).
    if not dishes:
        abort(404)

    cfg = getattr(rest, 'site_config', None)
    modo_salvo = getattr(cfg, 'tema_modo', None) if cfg else None
    # Claro/escuro é a escolha da casa, igual à landing. Sem escolha, escuro —
    # que é o default do site e o que o dono já viu ao aprovar.
    tema_forcado = {'claro': 'light', 'escuro': 'dark'}.get(modo_salvo or '', '')

    endereco_canonico = url_canonica(rest)
    endereco_cardapio = url_do_cardapio(rest) or f'{endereco_canonico}/cardapio'
    grafo = seo.cardapio_estruturado(rest, site, dishes, endereco_canonico,
                                     endereco_cardapio)

    # O cardápio é o QR da mesa: abre no 4G de quem acabou de sentar.
    return _na_borda(make_response(render_template(
        'site/cardapio.html',
        site=site, tenant=rest, grupos=_grupos_do_cardapio(dishes),
        copy=copy_da_vibe(getattr(cfg, 'vibe', None) if cfg else None,
                          site.get('nome') or ''),
        tema_css=css_do_tema(getattr(cfg, 'tema', None) if cfg else None),
        tema_cor=cor_do_tema(getattr(cfg, 'tema', None) if cfg else None),
        tema_forcado=tema_forcado,
        json_ld=seo.serializar(grafo) if grafo else None,
        url_canonica=endereco_cardapio,
        # Relativo de propósito: quem veio pelo QR está no domínio do bar e
        # continua nele ao tocar "ver o site".
        url_do_site=url_for('public.landing_slug', slug=rest.slug),
        email_vendas=os.environ.get('FEIRA_EMAIL', 'contato@feiradebarao.com.br'),
        contato_vendas=os.environ.get('FEIRA_WHATSAPP', ''),
    )))


@bp.route('/bar/<slug>/cardapio')
def cardapio(slug):
    """Cardápio digital do bar, o endereço que o QR da mesa carrega."""
    rest = tenant_por_slug(slug)  # já filtra inativo
    if rest is None:
        abort(404)
    return _render_cardapio(rest)


@bp.route('/kits')
@bp.route('/kits/')
@bp.route('/kits/index.html')
def kits_legado():
    """Endereço antigo do catálogo de kits (donaberga.com.br/kits/index.html).

    Está em posts e na bio do Instagram da Berga. Domínio de artesão leva à
    vitrine de produtos; qualquer outro host não tem /kits e dá 404.
    """
    rest = None if eh_dominio_do_produto(request.host) else tenant_por_host(request.host)
    if rest is None or tipo_do(rest) != 'artesao':
        abort(404)
    return redirect('/#produtos', code=301)


@bp.route('/s/<int:rid>')
def landing_tenant(rid):
    """Alias legado (preview por id). Mantido para não quebrar links já enviados."""
    rest = Restaurante.query.get_or_404(rid)
    # `is False` e não `not rest.ativo`: NULL (tenant antigo) conta como ativo.
    if rest.ativo is False:
        abort(404)
    return _render_landing(rest)


@bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Self-serve: cria o restaurante (tenant) + admin e já loga. Sem CLI."""
    from flask_login import login_user, current_user
    from app.models.usuario import Usuario
    from app.models.modelo_siteconfig import SiteConfig

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    from app.utils.planos import DIAS_DE_TRIAL

    def tela(**campos):
        """Todo render do cadastro passa por aqui.

        A página tinha a marca "Alero" e nenhuma palavra sobre preço, enquanto
        os dois CTAs que levam até ela dizem "Feira de Barão" e mostram o valor.
        Quem clicava trocava de empresa no meio da compra. O preço e o prazo
        agora acompanham o formulário, inclusive no re-render de erro — que é
        justamente quando a pessoa está decidindo se insiste.
        """
        return render_template('site/cadastro.html', dias_trial=DIAS_DE_TRIAL,
                               **_preco_publico(), **campos)

    dados = {'nome_bar': '', 'nome': '', 'email': ''}
    if request.method == 'POST':
        if limite_excedido(f'cadastro:{request.remote_addr}', maximo=5, janela_segundos=900):
            flash('Muitas tentativas de cadastro. Aguarde alguns minutos.', 'danger')
            return tela(**dados)
        nome_bar = (request.form.get('nome_bar') or '').strip()
        nome = (request.form.get('nome') or '').strip() or 'Responsável'
        email = (request.form.get('email') or '').strip().lower()
        senha = request.form.get('senha') or ''
        dados = {'nome_bar': nome_bar, 'nome': nome, 'email': email}

        erros = []
        if len(nome_bar) < 2:
            erros.append('Informe o nome do bar/restaurante.')
        if '@' not in email or '.' not in email:
            erros.append('E-mail inválido.')
        if len(senha) < 6:
            erros.append('A senha precisa de ao menos 6 caracteres.')
        if email and Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
            erros.append('Já existe uma conta com esse e-mail. Faça login.')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return tela(**dados)

        # Slug já no cadastro: é o endereço do site do bar (/bar/<slug>) antes
        # de ele ter domínio próprio. Sem isso o cliente sai do signup sem site.
        #
        # Commit único: restaurante, config e admin nascem juntos ou não nascem.
        # Antes eram dois commits, e uma falha no meio deixava um tenant órfão
        # (sem admin, mas consumindo o slug em slug_unico).
        try:
            # Nasce sem teste grátis (`FEIRA_DIAS_TRIAL=0`): a prévia já é o
            # teste — o bar vê o próprio site pronto antes de pagar. A conta
            # existe, o cardápio com QR funciona, e o que depende de plano
            # espera o pagamento, que é registrado no Modo Campo.
            from app.utils.planos import fim_do_trial
            rest = Restaurante(
                nome=nome_bar, slug=slug_unico(nome_bar),
                trial_termina_em=fim_do_trial(),
            )
            db.session.add(rest)
            db.session.flush()  # atribui rest.id sem fechar a transação
            db.session.add(SiteConfig(restaurant_id=rest.id, nome=nome_bar))
            admin = Usuario(nome=nome, email=email, senha=senha, tipo='admin',
                            restaurant_id=rest.id)
            db.session.add(admin)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception(f"Context: SIGNUP_FALHOU | {nome_bar} | {email}")
            flash('Não deu pra criar a conta agora. Tente de novo em instantes.', 'danger')
            return tela(**dados)

        login_user(admin)
        current_app.logger.info(f"Context: SIGNUP | {nome_bar} | {email} | rid={rest.id}")
        # Lead B2B no Brevo. Relação comercial iniciada por eles: sem dupla
        # confirmação. Falha (ou Brevo não configurado) não atrapalha o cadastro.
        from app.utils.email import salvar_contato
        salvar_contato(email, {'NOME': nome, 'BAR': nome_bar, 'ORIGEM': 'cadastro'},
                       'BREVO_LISTA_DONOS')
        flash('Conta criada! Personalize em Site e Conteúdo, depois veja seu site.', 'success')
        return redirect(url_for('dashboard.index'))

    return tela(**dados)


@bp.route('/bar/<slug>/avaliar')
def avaliar(slug):
    """Endereço curto do QR "avalie a gente": conta o clique e manda para a
    tela de escrever avaliação do Google. Sem place_id, cai no site do bar."""
    from app.models.modelo_siteconfig import SiteConfig

    rest = tenant_por_slug(slug)
    if rest is None:
        abort(404)
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first()
    if cfg is None or not cfg.google_place_id:
        return redirect(url_for('public.landing_slug', slug=rest.slug))
    # UPDATE atômico: dois cliques ao mesmo tempo não se perdem.
    SiteConfig.query.filter_by(id=cfg.id).update(
        {SiteConfig.cliques_avaliacao: db.func.coalesce(SiteConfig.cliques_avaliacao, 0) + 1},
        synchronize_session=False)
    db.session.commit()
    return redirect('https://search.google.com/local/writereview?placeid='
                    + urllib.parse.quote(cfg.google_place_id, safe=''))


@bp.route('/novidades/token')
def novidades_token():
    """Token de CSRF para o formulário de novidades.

    A home da Feira sai cacheada na borda, igual para todo visitante, então não
    pode carregar token de sessão no HTML. O formulário pede o token aqui, na
    hora de enviar — e esta resposta nunca é cacheada.
    """
    from flask_wtf.csrf import generate_csrf
    resp = jsonify(token=generate_csrf())
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@bp.route('/novidades', methods=['POST'])
def novidades():
    """Inscrição de morador/frequentador na lista "Comunidade Barão" do Brevo.

    Consentimento explícito (checkbox) + dupla confirmação por e-mail quando o
    template está configurado. `site` é um honeypot: robô preenche, gente não vê.
    """
    from app.utils.email import salvar_contato

    if request.form.get('site'):
        return jsonify(ok=True, msg='Pronto!')
    if limite_excedido(f'novidades:{request.remote_addr}', maximo=5, janela_segundos=900):
        return jsonify(ok=False, erro='Muitas tentativas. Tente de novo mais tarde.'), 429
    email = (request.form.get('email') or '').strip().lower()
    nome = (request.form.get('nome') or '').strip()[:80]
    telefone = (request.form.get('telefone') or '').strip()[:30]
    if '@' not in email or '.' not in email.split('@')[-1] or len(email) > 254:
        return jsonify(ok=False, erro='Confira o e-mail.'), 400
    if request.form.get('consentimento') != 'sim':
        return jsonify(ok=False, erro='Marque que aceita receber as novidades.'), 400

    # Origem só de um conjunto conhecido: "home" ou "bar:<slug existente>".
    origem = 'home'
    slug = (request.form.get('bar') or '').strip()
    bar = tenant_por_slug(slug) if slug else None
    if bar is not None:
        origem = f'bar:{bar.slug}'

    atributos = {'NOME': nome, 'ORIGEM': origem,
                 'CONSENTIMENTO': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    if telefone:
        atributos['TELEFONE'] = telefone
    if bar is not None:
        atributos['BAR'] = bar.nome
    salvar_contato(email, atributos, 'BREVO_LISTA_COMUNIDADE', dupla_confirmacao=True,
                   redirecionar=url_for('public.landing', _external=True))
    current_app.logger.info(f'Context: NOVIDADES | origem={origem}')
    # Mesma resposta se o Brevo falhar: quem se inscreve não tem o que fazer
    # com o erro, e o log já registrou.
    if os.environ.get('BREVO_TEMPLATE_DOI', '').isdigit():
        return jsonify(ok=True, msg='Pronto! Confira seu e-mail e clique no link para confirmar.')
    return jsonify(ok=True, msg='Pronto! Você vai receber as novidades da Feira.')


# Identidade/contato padrão (Bar da Vila) — fallback quando o tenant não configurou.
# Fallback NEUTRO. Antes, estes defaults eram a identidade do Bar da Vila
# (nome, endereço, Instagram e o WhatsApp do Gustavo) — o que fazia qualquer
# bar novo sem SiteConfig nascer como clone dele, com o telefone dele.
# A identidade do Bar da Vila agora vive na linha de SiteConfig dele, gravada
# pela migration `add_slug_dominio_tema`.
SITE_DEFAULTS = {
    'nome': None,               # cai pro Restaurante.nome em montar_site
    'hero_linha1': None,
    'hero_linha2': None,
    'kicker': None,
    'tagline': None,
    'subline': None,
    'selo_estrelas': None,
    'hero_foto': None,
    'logo': None,
    'whatsapp': None,
    'telefone_exibicao': None,
    'endereco': None,
    'cidade_uf': None,
    'horario': None,
    'ponto_na_feira': None,     # onde fica a barraca na feira (hotsite de artesão)
    'maps_query': None,
    'descritor': None,
    'servicos': None,
    'nota_google': None,
    'qtd_avaliacoes': None,
    'instagram_url': None,
    'facebook_url': None,
    'callmebot_phone': None,
    'callmebot_apikey': None,
}


def montar_site(rest):
    """Dict de identidade/contato do site: o que o tenant configurou.

    Campo vazio fica vazio — o template esconde a seção. Não existe mais
    fallback pra identidade de outro bar.
    """
    # Pelo relationship, não por query nova: `_render_landing` já toca em
    # `rest.site_config` logo depois, e a consulta explícita aqui fazia a mesma
    # linha ser buscada duas vezes na mesma requisição. Em produção cada ida ao
    # banco custa a latência da rede — a página do bar somava 11 consultas e
    # ~2s de TTFB, com 54ms de processamento.
    cfg = getattr(rest, 'site_config', None) if rest else None
    site = {}
    for chave, padrao in SITE_DEFAULTS.items():
        valor = getattr(cfg, chave, None) if cfg else None
        site[chave] = valor if (valor is not None and str(valor).strip() != '') else padrao

    if not site.get('nome') and rest is not None:
        site['nome'] = rest.nome
    return site


def _img(path):
    from flask import url_for
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return url_for('static', filename=path)


@lru_cache(maxsize=256)
def _proporcao(path):
    """largura/altura de uma imagem local em static (None se remota ou ilegível).

    O template usa para mostrar inteiro o cartaz vertical (9:16), que cortado como
    foto de produto perde o nome e a legenda.
    """
    if not path or path.startswith(('http://', 'https://')):
        return None
    try:
        from PIL import Image
        arquivo = Path(current_app.static_folder) / path
        with Image.open(arquivo) as im:
            return round(im.width / im.height, 3)
    except Exception:
        return None


def montar_conteudo(rest):
    """Listas das seções (cardápio, avaliações, equipe, galeria): do tenant ou padrão."""
    from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem, ProdutoSite
    rid = rest.id if rest else None

    def rows(model):
        if not rid:
            return []
        return model.query.filter_by(restaurant_id=rid, ativo=True).order_by(model.ordem, model.id).all()

    # Sem fallback pro conteúdo do Bar da Vila: um bar sem cardápio cadastrado
    # mostra a seção vazia, não o "Croquete da Bruna" e as avaliações reais dos
    # clientes de outro bar. Os dados do Bar da Vila foram persistidos como
    # linhas dele pela migration `add_slug_dominio_tema`.
    # `preco` viaja como Decimal (ou None) até o template e o JSON-LD: quem
    # formata é o filtro `moeda_br` na tela e `seo._preco_schema` no grafo —
    # vírgula pro cliente, ponto pro Google, um valor só na origem.
    dishes = [{'nome': d.nome, 'descricao': d.descricao, 'img': _img(d.imagem),
               'tag': d.tag, 'destaque': d.destaque, 'preco': d.preco}
              for d in rows(DishCard)]

    reviews = [{'autor': r.autor, 'texto': r.texto, 'estrelas': r.estrelas}
               for r in rows(Review)]

    team = [{'nome': t.nome, 'papel': t.papel, 'emoji': t.emoji}
            for t in rows(TeamMember)]

    gallery = [{'img': _img(g.imagem), 'legenda': g.legenda}
               for g in rows(GalleryItem)]

    # Produtos do hotsite de artesão. Bar não paga a query: só lê a tabela
    # quando o tenant é artesão.
    #
    # Só vai pra vitrine produto COM FOTO: card sem imagem não vende charcutaria
    # e deixa a grade com buracos. O produto sem foto continua no painel
    # (/conteudo/produtos) e aparece sozinho assim que ganhar a imagem. Filtra
    # aqui, e não no template, para o JSON-LD também não anunciar o que a
    # página não mostra.
    #
    # Exceção: quem não tem foto de produto nenhum (hotsite recém-montado, ainda
    # sem as fotos originais e a autorização de imagem) mostra o que faz em
    # texto, no lugar de uma vitrine vazia. Basta uma foto para voltar à regra.
    produtos = []
    if tipo_do(rest) == 'artesao':
        todos = rows(ProdutoSite)
        escolhidos = [p for p in todos if p.imagem] or todos
        produtos = [{'nome': p.nome, 'descricao': p.descricao, 'img': _img(p.imagem),
                     'categoria': p.categoria, 'preco': p.preco,
                     'sob_encomenda': bool(p.sob_encomenda), 'destaque': bool(p.destaque),
                     'ratio': _proporcao(p.imagem)}
                    for p in escolhidos]

    return {'dishes': dishes, 'reviews': reviews, 'team': team, 'gallery': gallery,
            'produtos': produtos}


@bp.route('/reservar', methods=['POST'])
def reservar():
    """Recebe uma reserva de mesa do formulário público da landing.

    Sem login (endpoint public.*). Grava no banco; o lojista vê/confirma no
    painel /reservas. Resolve o tenant pelo primeiro restaurante cadastrado
    (deploy single-tenant do Bar da Vila).
    """
    if limite_excedido(f'reservar:{request.remote_addr}', maximo=8, janela_segundos=300):
        return jsonify({'ok': False,
                        'erros': ['Muitas tentativas. Aguarde alguns minutos.']}), 429

    dados = request.form if request.form else (request.get_json(silent=True) or {})

    nome = (dados.get('nome') or '').strip()
    telefone = (dados.get('telefone') or '').strip()
    data_str = (dados.get('data') or '').strip()
    hora = (dados.get('hora') or '').strip()
    pessoas_str = str(dados.get('num_pessoas') or '').strip()
    observacao = (dados.get('observacao') or '').strip() or None

    erros = []
    if len(nome) < 2:
        erros.append('Informe seu nome.')
    if len(telefone) < 8:
        erros.append('Informe um telefone/WhatsApp válido.')

    data_reserva = None
    try:
        data_reserva = datetime.strptime(data_str, '%Y-%m-%d').date()
        if data_reserva < date.today():
            erros.append('A data da reserva não pode ser no passado.')
    except ValueError:
        erros.append('Escolha uma data válida.')

    try:
        datetime.strptime(hora, '%H:%M')
    except ValueError:
        erros.append('Escolha um horário válido.')

    num_pessoas = None
    try:
        num_pessoas = int(pessoas_str)
        if num_pessoas < 1 or num_pessoas > 50:
            raise ValueError
    except ValueError:
        erros.append('Número de pessoas inválido.')

    if erros:
        return jsonify({'ok': False, 'erros': erros}), 400

    # De qual bar é esta reserva? Pelo domínio (bardavila.bar) ou, quando o site
    # é servido em /bar/<slug>, pelo campo oculto que a landing envia.
    restaurante = tenant_por_host(request.host) or tenant_por_slug(dados.get('slug'))
    if restaurante is None:
        current_app.logger.error(
            f'Reserva sem tenant resolvível. host={request.host} slug={dados.get("slug")!r}'
        )
        return jsonify({'ok': False, 'erros': ['Não foi possível identificar o bar.']}), 400

    # Gate no servidor: esconder o formulário no template não impede um POST
    # direto. Sem o recurso, a reserva não entra e o cliente vai pro WhatsApp.
    if not pode(restaurante, 'reservas'):
        return jsonify({
            'ok': False,
            'erros': ['As reservas online deste bar estão desativadas. '
                      'Chame no WhatsApp.'],
            'wa_url': (f'https://wa.me/{restaurante.site_config.whatsapp}'
                       if getattr(restaurante, 'site_config', None)
                       and restaurante.site_config.whatsapp else None),
        }), 403

    reserva = Reserva(
        nome=nome,
        telefone=telefone,
        data=data_reserva,
        hora=hora,
        num_pessoas=num_pessoas,
        observacao=observacao,
        status='pendente',
        origem='site',
        restaurant_id=restaurante.id,
    )
    db.session.add(reserva)
    db.session.commit()

    current_app.logger.info(
        f"Context: RESERVA_SITE | tenant={restaurante.id} | {nome} | {telefone} | "
        f"{data_reserva} {hora} | {num_pessoas}p"
    )

    site = montar_site(restaurante)
    whatsapp = (site.get('whatsapp') or '').strip()

    # Alerta pro WhatsApp do bar: link pré-preenchido com os dados da reserva.
    linhas = [
        f'🍺 *Nova reserva pelo site do {site.get("nome") or restaurante.nome}!*',
        '',
        f'👤 {nome}',
        f'📞 {telefone}',
        f'📅 {data_reserva.strftime("%d/%m/%Y")} às {hora}',
        f'👥 {num_pessoas} pessoa(s)',
    ]
    if observacao:
        linhas.append(f'📝 {observacao}')
    texto = '\n'.join(linhas)

    # Alerta automático (CallMeBot, best-effort) + link wa.me como fallback.
    # Prioriza o número/apikey do CallMeBot configurados no painel pelo dono do bar.
    cfg = getattr(restaurante, 'site_config', None) if restaurante else None
    bot_phone = (getattr(cfg, 'callmebot_phone', None) or whatsapp) if cfg else whatsapp
    bot_apikey = getattr(cfg, 'callmebot_apikey', None) if cfg else None
    _alerta_whatsapp(texto, phone=bot_phone, apikey=bot_apikey)
    wa_url = ('https://wa.me/' + whatsapp + '?text=' + urllib.parse.quote(texto)) if whatsapp else None

    return jsonify({
        'ok': True,
        'mensagem': f'Reserva recebida, {nome.split()[0]}! Toque abaixo pra avisar o bar no WhatsApp. 🍺',
        'wa_url': wa_url,
    })


@bp.post('/api/concierge-voz')
def concierge_voz():
    """Concierge de IA por Voz: responde perguntas, lê cardápio e agenda reservas."""
    from app.utils.ai_copy import processar_voz_concierge
    from app.models.modelo_sitecontent import DishCard

    # Cada chamada gasta a cota de IA do projeto: limite por IP e texto curto.
    if limite_excedido(f'concierge:{request.remote_addr}', maximo=20, janela_segundos=300):
        return jsonify({'resposta': 'Muitas perguntas seguidas. Tente de novo em instantes.'}), 429
    dados = request.get_json(silent=True) or request.form
    texto = (dados.get('texto') or '').strip()[:300]
    slug = (dados.get('slug') or '').strip()

    rest = tenant_por_slug(slug) if slug else None
    site = montar_site(rest) if rest else {}
    nome_bar = site.get('nome') or (rest.nome if rest else 'Nosso Bar')

    pratos = []
    if rest:
        itens = DishCard.query.filter_by(restaurant_id=rest.id, ativo=True).limit(8).all()
        pratos = [{'nome': p.nome, 'preco': p.preco} for p in itens]

    info = {
        'whatsapp': site.get('whatsapp') or '',
        'endereco': site.get('endereco') or '',
        'horario': site.get('horario') or '',
    }

    resultado = processar_voz_concierge(texto, nome_bar=nome_bar, pratos=pratos, info=info)
    return jsonify(resultado)


