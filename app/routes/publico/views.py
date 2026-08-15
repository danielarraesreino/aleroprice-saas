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
    eh_dominio_do_produto, slug_unico, tenant_por_host, tenant_por_slug,
)
from app.utils.temas import css_do_tema, cor_do_tema
from app.utils.copy_site import copy_da_vibe
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

    return render_template(_template_do_modelo(modelo_atual),
                           eventos=eventos, promocoes=promocoes,
                           site=site, tema_css=css_do_tema(tema),
                           tema_cor=cor_do_tema(tema), tenant=rest, copy=copy,
                           modelo_atual=modelo_atual, previewando=previewando,
                           modo_atual=modo_atual, tema_forcado=tema_forcado,
                           reservas_ativas=reservas_ativas,
                           contato_vendas=os.environ.get('FEIRA_WHATSAPP', ''),
                           email_vendas=os.environ.get('FEIRA_EMAIL', 'contato@feiradebarao.com.br'),
                           **montar_conteudo(rest))


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
    """Segunda camada de proteção das prévias (a primeira é o meta noindex).

    Bloqueia /bar/ inteiro em vez de listar as demos: listar entregaria a lista
    de prospecção pra qualquer um, e cliente convertido usa domínio próprio.
    """
    corpo = (
        'User-agent: *\n'
        'Disallow: /bar/\n'
        'Disallow: /s/\n'
        'Disallow: /cadastro\n'
        'Disallow: /app/\n'
        'Allow: /\n'
    )
    return corpo, 200, {'Content-Type': 'text/plain; charset=utf-8'}


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
    dishes = [{'nome': d.nome, 'descricao': d.descricao, 'img': _img(d.imagem),
               'tag': d.tag, 'destaque': d.destaque} for d in rows(DishCard)]

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
