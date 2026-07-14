"""
Comandos de linha de comando (Flask CLI).

Como não há UI de signup, o provisionamento de um novo cliente (tenant) e do
seu usuário administrador é feito por aqui:

    flask create-tenant --restaurante "Bar da Vila" \
        --email dono@bardavila.com --senha "SENHA_FORTE" --nome "Responsável"

Idempotente no e-mail: se o usuário já existir, aborta sem duplicar.
"""
import secrets
import string

import click

from app import db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
from app.utils.site_router import slug_unico


def _gerar_senha(tamanho=14):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


def register_cli(app):
    @app.cli.command('create-tenant')
    @click.option('--restaurante', required=True, help='Nome do restaurante (tenant).')
    @click.option('--email', required=True, help='E-mail de login do administrador.')
    @click.option('--senha', default=None, help='Senha do admin. Se omitida, uma é gerada.')
    @click.option('--nome', default='Administrador', help='Nome do usuário admin.')
    @click.option('--cnpj', default=None, help='CNPJ do restaurante (opcional).')
    def create_tenant(restaurante, email, senha, nome, cnpj):
        """Cria um restaurante (tenant) e seu usuário administrador."""
        email = email.strip().lower()

        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            click.echo(
                f'ABORTADO: já existe usuário {email} '
                f'(restaurant_id={existente.restaurant_id}).'
            )
            raise SystemExit(1)

        senha_gerada = None
        if not senha:
            senha = _gerar_senha()
            senha_gerada = senha

        # Sem slug o bar não tem endereço em /bar/<slug> e o site dele nasce
        # inacessível.
        restaurante_obj = Restaurante(
            nome=restaurante, cnpj=cnpj, slug=slug_unico(restaurante))
        db.session.add(restaurante_obj)
        db.session.commit()

        admin = Usuario(
            nome=nome,
            email=email,
            senha=senha,
            tipo='admin',
            restaurant_id=restaurante_obj.id,
        )
        db.session.add(admin)
        db.session.commit()

        click.echo('Tenant provisionado com sucesso.')
        click.echo(f'  Restaurante : {restaurante} (id={restaurante_obj.id})')
        click.echo(f'  Site        : /bar/{restaurante_obj.slug}')
        click.echo(f'  Admin       : {email}')
        if senha_gerada:
            click.echo(f'  Senha       : {senha_gerada}   (anote — não será mostrada de novo)')
