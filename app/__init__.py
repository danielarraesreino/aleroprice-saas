# -*- coding: utf-8 -*-

from flask import Flask
from app.config import config
from app.extensions import db, migrate

import app.models # Importar todos os modelos para registro
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
    # - blueprint 'public': landing / calculadora de ROI (marketing)
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
