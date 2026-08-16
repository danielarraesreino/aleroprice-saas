import os
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta

from flask import (
    Blueprint, render_template, request, jsonify, current_app, abort,
    redirect, url_for, flash,
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
from app.utils.temas import css_do_tema, cor_do_tema, tema_valido
from app.utils.copy_site import copy_da_vibe, vibe_valida
from app.utils.modelos import MODELO_PADRAO, arquivo_do_modelo, modelo_valido
from app.utils.planos import pode, precos
from app.utils.tenant import limite_excedido


def _alerta_whatsapp(texto, phone=None):
    """Dispara alerta no WhatsApp do bar via CallMeBot (grátis).

    Só age se CALLMEBOT_APIKEY estiver configurado (env). Falha é silenciosa:
    nunca quebra a reserva — o botão wa.me segue como fallback pro cliente.

    `phone` vem do SiteConfig do tenant. Sem número configurado não há alerta:
    antes existia um fallback global pro celular do dono do Bar da Vila, o que
    faria a reserva de um bar novo tocar o telefone de outro cliente.
    """
    apikey = os.environ.get('CALLMEBOT_APIKEY')
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
    modelo_salvo = getattr(cfg, 'modelo', None) if cfg else None
    modelo_espiado = (request.args.get('modelo') or '').strip()
    previewando = modelo_valido(modelo_espiado)
    if previewando:
        modelo_atual = modelo_espiado
    else:
        modelo_atual = modelo_salvo if modelo_valido(modelo_salvo) else MODELO_PADRAO

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
        endereco_canonico, url_do_cardapio(rest),
    ))
    meta_desc = seo.meta_descricao(site, rest)

    return render_template(_template_do_modelo(modelo_atual),
                           eventos=eventos, promocoes=promocoes,
                           site=site, tema_css=css_do_tema(tema),
                           tema_cor=cor_do_tema(tema), tenant=rest, copy=copy,
                           modelo_atual=modelo_atual, previewando=previewando,
                           modo_atual=modo_atual, tema_forcado=tema_forcado,
                           reservas_ativas=reservas_ativas,
                           json_ld=json_ld, meta_desc=meta_desc,
                           url_canonica=endereco_canonico,
                           contato_vendas=os.environ.get('FEIRA_WHATSAPP', ''),
                           email_vendas=os.environ.get('FEIRA_EMAIL', 'contato@feiradebarao.com.br'),
                           **conteudo)


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
    return render_template('produto/landing.html', **_contexto_produto())


def _contexto_produto():
    """Dados comerciais da landing de venda. Vêm de env pra não versionar
    número de telefone nem preço — os dois mudam sem deploy."""
    zap = (os.environ.get('FEIRA_WHATSAPP') or '').strip()
    msg = urllib.parse.quote('Oi! Vi o Feira de Barão e quero saber como funciona pro meu bar.')
    return {
        'zap_url': f'https://wa.me/{zap}?text={msg}' if zap else '#preco',
        'preco': os.environ.get('FEIRA_PRECO', 'R$ 197'),
        'preco_periodo': os.environ.get('FEIRA_PRECO_PERIODO', 'por mês'),
        'preco_detalhe': os.environ.get(
            'FEIRA_PRECO_DETALHE',
            'Site no ar, reservas, cardápio digital e o sistema de custos completo. '
            'Sem taxa de setup e sem fidelidade — se não servir, você sai.'
        ),
    }


@bp.route('/barao')
def barao():
    """Landing da campanha "Bares de Barão": a página que o vendedor manda no
    WhatsApp do dono de bar de Barão Geraldo e abre na mesa.

    Público por ser `public.*` (allowlist do guard global). Contato e preços
    vêm de env — `_contexto_produto()` pro WhatsApp e `planos.precos()` pros
    dois planos (Site/Pro) — pra nada de comercial ficar hardcoded em template.
    """
    tabela = precos()
    return render_template('produto/barao.html',
                           preco_site=tabela['site'], preco_pro=tabela['pro'],
                           **_contexto_produto())


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
    """
    consulta = _publicavel(Restaurante.clientes())
    if dono_do_dominio is not None:
        consulta = consulta.filter(Restaurante.id == dono_do_dominio.id)
    return consulta.order_by(Restaurante.id).all()


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

    for tenant in _tenants_do_sitemap(dono_do_dominio):
        cfg = getattr(tenant, 'site_config', None)
        paginas.append((url_canonica(tenant), getattr(cfg, 'data_atualizacao', None)))

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

    return render_template(
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
    )


@bp.route('/bar/<slug>/cardapio')
def cardapio(slug):
    """Cardápio digital do bar, o endereço que o QR da mesa carrega."""
    rest = tenant_por_slug(slug)  # já filtra inativo
    if rest is None:
        abort(404)
    return _render_cardapio(rest)


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

    dados = {'nome_bar': '', 'nome': '', 'email': ''}
    if request.method == 'POST':
        if limite_excedido(f'cadastro:{request.remote_addr}', maximo=5, janela_segundos=900):
            flash('Muitas tentativas de cadastro. Aguarde alguns minutos.', 'danger')
            return render_template('site/cadastro.html', **dados)
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
            return render_template('site/cadastro.html', **dados)

        # Slug já no cadastro: é o endereço do site do bar (/bar/<slug>) antes
        # de ele ter domínio próprio. Sem isso o cliente sai do signup sem site.
        #
        # Commit único: restaurante, config e admin nascem juntos ou não nascem.
        # Antes eram dois commits, e uma falha no meio deixava um tenant órfão
        # (sem admin, mas consumindo o slug em slug_unico).
        try:
            # Nasce em teste grátis: sem isso a pessoa se cadastra e cai direto
            # no paywall, sem nunca ver o produto funcionando.
            from app.utils.planos import DIAS_DE_TRIAL
            rest = Restaurante(
                nome=nome_bar, slug=slug_unico(nome_bar),
                trial_termina_em=date.today() + timedelta(days=DIAS_DE_TRIAL),
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
            return render_template('site/cadastro.html', **dados)

        login_user(admin)
        current_app.logger.info(f"Context: SIGNUP | {nome_bar} | {email} | rid={rest.id}")
        flash('Conta criada! Personalize em Site e Conteúdo, depois veja seu site.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('site/cadastro.html', **dados)


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
    'whatsapp': None,
    'telefone_exibicao': None,
    'endereco': None,
    'cidade_uf': None,
    'horario': None,
    'maps_query': None,
    'descritor': None,
    'servicos': None,
    'nota_google': None,
    'qtd_avaliacoes': None,
    'instagram_url': None,
    'facebook_url': None,
}


def montar_site(rest):
    """Dict de identidade/contato do site: o que o tenant configurou.

    Campo vazio fica vazio — o template esconde a seção. Não existe mais
    fallback pra identidade de outro bar.
    """
    from app.models.modelo_siteconfig import SiteConfig
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first() if rest else None
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


def montar_conteudo(rest):
    """Listas das seções (cardápio, avaliações, equipe, galeria): do tenant ou padrão."""
    from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem
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

    return {'dishes': dishes, 'reviews': reviews, 'team': team, 'gallery': gallery}


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
    # Ambos usam o número DESTE bar — nunca um número global.
    _alerta_whatsapp(texto, phone=whatsapp)
    wa_url = ('https://wa.me/' + whatsapp + '?text=' + urllib.parse.quote(texto)) if whatsapp else None

    return jsonify({
        'ok': True,
        'mensagem': f'Reserva recebida, {nome.split()[0]}! Toque abaixo pra avisar o bar no WhatsApp. 🍺',
        'wa_url': wa_url,
    })


@bp.route('/calculadora-roi', methods=['GET', 'POST'])
def calculadora_roi():
    """Calculadora de ROI pública (Lead Magnet)"""
    resultado = None
    faturamento = None
    
    if request.method == 'POST':
        try:
            faturamento_str = request.form.get('faturamento_estimado', '0')
            # Limpar formatação de moeda se houver (R$, pontos, virgulas)
            faturamento_str = faturamento_str.replace('R$', '').replace('.', '').replace(',', '.')
            faturamento = float(faturamento_str)
            
            # Retention / Lead Capture
            email = request.form.get('email')
            if email:
                # Log for backend processing (Concierge / Marketing)
                # In production, this goes to Vercel Logs -> Datadog/Splunk or manually extracted
                from flask import current_app
                current_app.logger.info(f"Context: LEAD_CALCULADORA_ROI | Email: {email} | Faturamento: {faturamento}")
            
            # Estimativa de desperdício (10% - Dado de mercado Abrasel)
            desperdicio = faturamento * 0.10
            
            resultado = {
                'faturamento': faturamento,
                'desperdicio': desperdicio,
                'mensagem': f"Você pode estar perdendo R$ {desperdicio:,.2f} por mês em desperdício invisível."
            }
        except ValueError:
            resultado = {'erro': 'Por favor, insira um valor válido.'}
            
    return render_template('public/roi.html', resultado=resultado, faturamento=faturamento)
