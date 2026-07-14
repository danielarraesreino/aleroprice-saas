"""
Comandos de linha de comando (Flask CLI).

Como não há UI de signup, o provisionamento de um novo cliente (tenant) e do
seu usuário administrador é feito por aqui:

    flask create-tenant --restaurante "Bar da Vila" \
        --email dono@bardavila.com --senha "SENHA_FORTE" --nome "Responsável"

Idempotente no e-mail: se o usuário já existir, aborta sem duplicar.
"""
import re
import secrets
import string
import unicodedata

import click

from app import db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario


def _gerar_senha(tamanho=14):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


def _slugificar(nome):
    sem_acento = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', sem_acento.lower())).strip('-')[:60]


def register_cli(app):
    @app.cli.command('create-tenant')
    @click.option('--restaurante', required=True, help='Nome do restaurante (tenant).')
    @click.option('--email', required=True, help='E-mail de login do administrador.')
    @click.option('--senha', default=None, help='Senha do admin. Se omitida, uma é gerada.')
    @click.option('--nome', default='Administrador', help='Nome do usuário admin.')
    @click.option('--cnpj', default=None, help='CNPJ do restaurante (opcional).')
    @click.option('--slug', default=None,
                  help='Slug do tenant (/bar/<slug>). Derivado do nome se omitido.')
    @click.option('--dominio', default=None,
                  help='Domínio próprio do cliente (ex.: bardavila.bar). Opcional.')
    def create_tenant(restaurante, email, senha, nome, cnpj, slug, dominio):
        """Cria um restaurante (tenant) e seu usuário administrador."""
        email = email.strip().lower()

        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            click.echo(
                f'ABORTADO: já existe usuário {email} '
                f'(restaurant_id={existente.restaurant_id}).'
            )
            raise SystemExit(1)

        slug = _slugificar(slug or restaurante)
        conflito = Restaurante.query.filter_by(slug=slug).first()
        if conflito:
            click.echo(
                f"ABORTADO: slug '{slug}' já é do restaurante "
                f'{conflito.nome} (id={conflito.id}). Passe --slug com outro valor.'
            )
            raise SystemExit(1)

        if dominio:
            dominio = dominio.strip().lower().removeprefix('www.')
            conflito = Restaurante.query.filter_by(dominio=dominio).first()
            if conflito:
                click.echo(
                    f"ABORTADO: domínio '{dominio}' já é do restaurante "
                    f'{conflito.nome} (id={conflito.id}).'
                )
                raise SystemExit(1)

        senha_gerada = None
        if not senha:
            senha = _gerar_senha()
            senha_gerada = senha

        restaurante_obj = Restaurante(nome=restaurante, cnpj=cnpj, slug=slug, dominio=dominio)
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
        click.echo(f'  Slug        : {slug}')
        click.echo(f'  Domínio     : {dominio or "(nenhum — só /bar/%s)" % slug}')
        click.echo(f'  Admin       : {email}')
        if senha_gerada:
            click.echo(f'  Senha       : {senha_gerada}   (anote — não será mostrada de novo)')
