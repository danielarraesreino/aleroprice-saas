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
    
    app.register_blueprint(estoque_bp, url_prefix='/estoque')
    app.register_blueprint(fornecedores_bp, url_prefix='/fornecedores')
    app.register_blueprint(nfe_bp, url_prefix='/nfe')
    app.register_blueprint(pratos_bp, url_prefix='/pratos')
    app.register_blueprint(produtos_bp, url_prefix='/produtos')
    app.register_blueprint(cardapios_bp, url_prefix='/cardapios')
    app.register_blueprint(desperdicio_bp, url_prefix='/desperdicio')
    app.register_blueprint(previsao_bp, url_prefix='/previsao')
    app.register_blueprint(custos_bp, url_prefix='/custos')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
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

    PUBLIC_ENDPOINTS = {'static', 'auth.login', 'auth.logout', 'billing.webhook'}

    @app.before_request
    def require_login():
        endpoint = request.endpoint
        if endpoint is None:
            return  # deixa o 404 seguir o fluxo normal
        if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith('public.'):
            return
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.path))

    # Registra o blueprint de erro (opcional)
    # from app.errors import bp as errors_bp
    # app.register_blueprint(errors_bp)
    
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
