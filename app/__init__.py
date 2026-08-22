# -*- coding: utf-8 -*-

from flask import Flask
from app.config import config
from app.extensions import db, migrate, csrf

import app.models # Importar todos os modelos para registro
import os
import locale

def create_app(config_name='default'):
    """
    Factory para criação da aplicação Flask
    :param config_name: Nome da configuração a ser usada
    :return: Instância da aplicação Flask
    """

    import os
    
    # Hack for Vercel Read-Only File System
    # Flask-SQLAlchemy tries to create the instance folder if it doesn't exist.
    # On Vercel, only /tmp is writable.
    params = {}
    if os.environ.get('VERCEL'):
        params['instance_path'] = '/tmp'
        
    app = Flask(__name__, **params)
    app.config.from_object(config[config_name])
    # Guardado para gates que dependem do ambiente (ex.: billing recusa o modo
    # mock em produção). Sem isso, não há como distinguir prod de dev em runtime.
    app.config['CONFIG_NAME'] = config_name

    # Monitoramento de erros (Sentry) — opcional.
    # Só ativa se SENTRY_DSN estiver definido; ausência = no-op silencioso.
    # Import protegido para não quebrar caso o pacote não esteja instalado.
    import os as _os
    _sentry_dsn = _os.environ.get('SENTRY_DSN')
    if _sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(
                dsn=_sentry_dsn,
                integrations=[FlaskIntegration()],
                environment=config_name,
                traces_sample_rate=float(_os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
                send_default_pii=False,
            )
        except Exception as exc:  # pacote ausente ou DSN inválido: não derruba o app
            print(f'Sentry não inicializado: {exc}')

    # Logging Configuration
    import logging
    if not app.debug and not app.testing:
        # StreamHandler for Vercel/Production logs
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('AleroPriceSaaS Startup')
    
    # Inicializa as extensões
    db.init_app(app)
    migrate.init_app(app, db)
    
    from app.extensions import login_manager
    login_manager.init_app(app)
    
    # Configura a localização brasileira
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except locale.Error:

                try:
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                except locale.Error:
                    app.logger.warning('Não foi possível configurar locale brasileiro. Usando padrão do sistema.')
                    pass
    
    # Registra os filtros de template para formatação brasileira
    from app.utils.template_filters import registrar_filtros
    registrar_filtros(app)

    # Disponível em todo template: o link do painel tem que sair do domínio do
    # bar e ir para o do produto (ver `sistema_fica_no_dominio_do_produto`).
    from app.utils.site_router import url_do_sistema
    app.jinja_env.globals['url_do_sistema'] = url_do_sistema

    # A marca, num lugar só.
    #
    # "AleroPrice" estava escrito à mão em 38 lugares e aparecia no título de
    # toda tela do painel — inclusive para o dono de bar que comprou pelo
    # feiradebarao.com.br e nunca ouviu esse nome. Quem entra em /app/index
    # depois de assinar precisa ver a mesma marca da página onde comprou; marca
    # trocando no meio do produto lê como sistema de outra empresa.
    app.jinja_env.globals['MARCA'] = os.environ.get('FEIRA_MARCA', 'Feira de Barão')

    def og_imagem(arquivo):
        """URL absoluta e em https de uma imagem de compartilhamento.

        `url_for(..., _external=True)` monta a partir do esquema da requisição,
        e atrás do proxy da Vercel isso chega como `http://`. WhatsApp e
        Facebook descartam og:image que não seja https, então o link voltaria a
        ser compartilhado sem imagem — que é justamente o que isto conserta.
        """
        from app.utils.site_router import dominio_do_produto
        return f'https://{dominio_do_produto()}/static/img/og/{arquivo}'

    app.jinja_env.globals['og_imagem'] = og_imagem

    @app.context_processor
    def recursos_do_plano():
        """`pode('gestao')` em qualquer template, para o tenant de quem está logado.

        O menu do painel listava os 14 itens para todo mundo. Quem assina o
        plano Site — que é o que se vende de porta em porta — via metade das
        abas levarem a "faça upgrade": Pratos, Estoque, Notas Fiscais, Previsão,
        Desperdício, Custos. O dono do bar não lê isso como "existe mais
        produto"; lê como "comprei algo pela metade", e é a primeira tela que
        ele vê depois de pagar.

        A regra de plano já existe em `planos.pode` — aqui ela só fica ao
        alcance do template, sem cada um refazer a conta do próprio jeito.
        """
        from flask_login import current_user
        from app.utils.planos import pode

        def _pode(recurso):
            if not current_user.is_authenticated:
                return False
            return pode(getattr(current_user, 'restaurante', None), recurso)

        return {'pode': _pode}
    
    # Registra os blueprints
    from app.routes.estoque import bp as estoque_bp
    from app.routes.fornecedores import bp as fornecedores_bp
    from app.routes.nfe import bp as nfe_bp
    from app.routes.pratos import bp as pratos_bp
    from app.routes.produtos import bp as produtos_bp
    from app.routes.cardapios import bp as cardapios_bp
    from app.routes.desperdicio import bp as desperdicio_bp
    from app.routes.previsao import bp as previsao_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.custos import bp as custos_bp
    from app.routes.reservas import bp as reservas_bp
    from app.routes.agenda import bp as agenda_bp
    from app.routes.promocoes import bp as promocoes_bp
    from app.routes.configsite import bp as configsite_bp
    from app.routes.conteudo import bp as conteudo_bp
    from app.routes.campanha import bp as campanha_bp
    from app.routes.campo import bp as campo_bp
    from app.routes.agentes import bp as agentes_bp

    app.register_blueprint(estoque_bp, url_prefix='/estoque')
    app.register_blueprint(fornecedores_bp, url_prefix='/fornecedores')
    app.register_blueprint(nfe_bp, url_prefix='/nfe')
    app.register_blueprint(pratos_bp, url_prefix='/pratos')
    app.register_blueprint(produtos_bp, url_prefix='/produtos')
    app.register_blueprint(cardapios_bp, url_prefix='/cardapios')
    app.register_blueprint(desperdicio_bp, url_prefix='/desperdicio')
    app.register_blueprint(previsao_bp, url_prefix='/previsao')
    app.register_blueprint(custos_bp, url_prefix='/custos')
    app.register_blueprint(reservas_bp, url_prefix='/reservas')
    app.register_blueprint(agenda_bp, url_prefix='/agenda')
    app.register_blueprint(promocoes_bp, url_prefix='/promocoes')
    app.register_blueprint(configsite_bp, url_prefix='/config-site')
    app.register_blueprint(conteudo_bp, url_prefix='/conteudo')
    app.register_blueprint(campanha_bp, url_prefix='/campanha')
    app.register_blueprint(agentes_bp, url_prefix='/agentes')
    # Ferramenta de venda presencial do operador, não feature de cliente.
    app.register_blueprint(campo_bp, url_prefix='/campo')
    # Sistema/dashboard fica ATRÁS do login, em /app. A landing pública ocupa '/'.
    app.register_blueprint(dashboard_bp, url_prefix='/app')
    
    from app.routes.billing import bp as billing_bp
    app.register_blueprint(billing_bp, url_prefix='/billing')
    
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.publico import bp as public_bp
    app.register_blueprint(public_bp, url_prefix='/')
    
    # Enforcement global de login.
    # Toda rota exige usuário autenticado, EXCETO os endpoints públicos abaixo:
    # - static: assets
    # - auth.login / auth.logout: fluxo de autenticação
    # - billing.webhook: chamado pelo Stripe sem sessão de usuário
    # - blueprint 'public': landing, cadastro, site do bar (marketing)
    # Substitui a necessidade de @login_required rota a rota e evita que
    # produtos/estoque/nfe/custos/etc. fiquem acessíveis sem login.
    from flask import request, redirect, url_for
    from flask_login import current_user

    # 'bootstrap_demo' (run.py) é gated por SEED_TOKEN — só existe quando a env
    # var está setada, e valida o token em tempo constante antes de escrever.
    PUBLIC_ENDPOINTS = {'static', 'auth.login', 'auth.logout', 'billing.webhook',
                        'bootstrap_demo'}

    # O domínio do cliente é dele: ali mora o site do bar e nada mais.
    #
    # Sem esta separação, bardavila.bar respondia /auth/login, /cadastro e o
    # painel inteiro — ou seja, o site do Gustavo servia o formulário de
    # cadastro dos concorrentes dele e expunha a administração do produto num
    # endereço que não é nosso. Também é o que permite, no dia em que um cliente
    # sair, que o domínio dele não carregue nenhum resto do sistema.
    #
    # O que continua respondendo no domínio do bar: o site, o POST de reserva
    # (é o formulário da própria página) e os dois arquivos que o buscador
    # busca na raiz — robots.txt e sitemap.xml. Sem o sitemap aqui, o
    # robots.txt do bar apontaria para um endereço que redireciona pro domínio
    # do produto, e o Google descartaria o sitemap por ser de outro host. Todo
    # o resto vai para o domínio do produto, preservando o caminho — quem
    # salvou bardavila.bar/app nos favoritos cai no lugar certo.
    ENDPOINTS_DO_TENANT = {
        'static',
        'public.landing', 'public.landing_slug', 'public.landing_tenant',
        'public.reservar', 'public.robots', 'public.sitemap',
        # O cardápio é o QR colado na mesa: tem que abrir no endereço do bar.
        # Fora daqui ele levava 302 pro domínio do produto — o cliente sentado
        # via a barra do navegador trocar de bardavila.bar pra feiradebarao, e
        # o `Menu.url` do JSON-LD (que aponta pro domínio do bar) virava um
        # redirecionamento pra outro host, que o Google trata como sinal fraco.
        'public.cardapio',
    }

    @app.before_request
    def sistema_fica_no_dominio_do_produto():
        from app.utils.site_router import (
            dominio_do_produto, eh_dominio_do_produto, normalizar_host,
        )

        # Interruptor obrigatório: enquanto o DNS do domínio do produto não
        # apontar pra cá, redirecionar o login pra lá deixa o operador sem
        # conseguir entrar em lugar nenhum. Ligar SEPARAR_DOMINIOS=1 só depois
        # de confirmar que o domínio responde.
        if os.environ.get('SEPARAR_DOMINIOS') != '1':
            return

        endpoint = request.endpoint
        if endpoint is None or endpoint in ENDPOINTS_DO_TENANT:
            return

        host = normalizar_host(request.host)
        # Localhost, preview da Vercel e o próprio domínio do produto servem
        # tudo: é onde se desenvolve e onde o sistema mora de verdade.
        if (not host or eh_dominio_do_produto(host)
                or host.startswith('localhost') or host.startswith('127.0.0.1')
                or host.endswith('.vercel.app')):
            return

        # Chegou aqui: é domínio de cliente pedindo rota de sistema.
        destino = f'https://{dominio_do_produto()}{request.full_path.rstrip("?")}'
        return redirect(destino, code=302)

    @app.before_request
    def require_login():
        endpoint = request.endpoint
        if endpoint is None:
            return  # deixa o 404 seguir o fluxo normal
        if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith('public.'):
            return
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.path))

    # CSRF depois do guard de login — a ordem é o comportamento.
    #
    # O before_request do CSRFProtect entra na fila no momento do init_app.
    # Inicializando aqui, `require_login` roda primeiro: quem tem a sessão
    # expirada (e portanto também o token expirado) volta pro login em vez de
    # levar um 400 seco no meio de um formulário preenchido.
    #
    # Sem isto, todo POST do painel e o formulário público de reserva aceitam
    # request forjado de outro site — o flask-wtf estava no requirements e o
    # TestingConfig já desligava a checagem, mas a proteção nunca foi ligada.
    # As duas exceções vivem onde a rota vive, marcadas com `@csrf.exempt`:
    # `billing.webhook` (app/routes/billing/views.py) e `bootstrap_demo`
    # (run.py). Ambas são chamadas de fora, sem sessão e sem token.
    csrf.init_app(app)

    # 404 próprio. /bar/<slug> é rota pública quente (é o endereço do site de
    # todo bar que ainda não tem domínio próprio), e um slug errado caía na
    # página branca do Werkzeug, que não diz o que fazer em seguida.
    from flask import render_template

    @app.errorhandler(404)
    def pagina_nao_encontrada(_erro):
        partes = request.path.strip('/').split('/')
        slug = partes[1] if len(partes) == 2 and partes[0] == 'bar' else None
        titulo = 'Esse bar não está aqui' if slug else 'Página não encontrada'
        return render_template('site/404.html', slug=slug, titulo=titulo), 404

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def erro_interno(erro):
        """Loga o traceback numa linha só, porque o log da Vercel corta.

        O traceback que o Flask imprime tem uma linha por quadro, e o coletor da
        Vercel entrega cada uma como evento separado — na prática só chegava o
        topo (`wsgi_app`, `full_dispatch_request`), que é igual em todo erro e
        não diz nada. Diagnosticar a página quebrada em produção virava
        adivinhação: reproduzir localmente dava 200, e o log não contava o resto.

        Aqui o traceback inteiro vai junto, com ` | ` no lugar da quebra, e
        prefixado por `Context:` como o resto dos logs do projeto — dá pra achar
        com `vercel logs | grep ERRO_500` e ler a última linha, que é a causa.
        """
        from werkzeug.exceptions import HTTPException
        if isinstance(erro, HTTPException) and erro.code != 500:
            return erro  # 404, 403, 405: seguem o fluxo normal

        import traceback
        linha = ' | '.join(l.strip() for l in
                           traceback.format_exc().strip().splitlines())
        app.logger.error(f'Context: ERRO_500 | {request.method} {request.path} '
                         f'| {linha}')
        return render_template('site/404.html', slug=None,
                               titulo='Deu erro do nosso lado'), 500


    # Registra comandos CLI (ex.: create-tenant para provisionar clientes)
    from app.cli import register_cli
    register_cli(app)

    # Registra shell context
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'migrate': migrate}
        
    # Setup user loader
    from app.models.usuario import Usuario
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    return app
