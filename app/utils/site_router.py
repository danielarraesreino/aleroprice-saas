"""Resolução do site público por domínio (Host header).

Um único app atende N bares. Quem decide o que a raiz `/` mostra é o domínio
da requisição:

    feiradebarao.com.br  -> landing do PRODUTO (venda)
    bardavila.bar        -> site do Bar da Vila (Restaurante.dominio)
    localhost / *.vercel.app / qualquer outro -> landing do PRODUTO

O site de um bar SEMPRE também responde em /bar/<slug>, mesmo sem domínio
próprio. É assim que uma demo (Bar do Zé) existe sem comprar domínio.

Isto substitui o `Restaurante.query.order_by(id).first()` que servia "o
primeiro bar do banco" na raiz — o que quebraria assim que houvesse 2 clientes.
"""
import os

from app.models.modelo_restaurante import Restaurante

# Domínio onde mora a landing de venda. Env para não travar o valor no código
# (preview da Vercel, staging, troca de marca).
DOMINIO_PRODUTO_PADRAO = 'feiradebarao.com.br'


def dominio_do_produto():
    return (os.environ.get('DOMINIO_PRODUTO') or DOMINIO_PRODUTO_PADRAO).lower()


def normalizar_host(host):
    """'BarDaVila.bar:5000' -> 'bardavila.bar'. Também tira o 'www.'."""
    if not host:
        return ''
    host = host.split(':', 1)[0].strip().lower().rstrip('.')
    if host.startswith('www.'):
        host = host[4:]
    return host


def eh_dominio_do_produto(host):
    return normalizar_host(host) == dominio_do_produto()


def tenant_por_host(host):
    """Restaurante dono deste domínio, ou None.

    None significa 'este Host não é o site de nenhum bar' — e aí a raiz mostra
    a landing do produto.
    """
    h = normalizar_host(host)
    if not h or h == dominio_do_produto():
        return None
    return Restaurante.query.filter(Restaurante.dominio == h).first()


def tenant_por_slug(slug):
    if not slug:
        return None
    return Restaurante.query.filter(Restaurante.slug == slug.strip().lower()).first()


def gerar_slug(nome):
    """Slug simples e estável a partir do nome do bar. Não garante unicidade —
    quem chama deve checar colisão (o banco tem unique)."""
    import re
    import unicodedata

    texto = unicodedata.normalize('NFKD', nome or '')
    texto = texto.encode('ascii', 'ignore').decode('ascii').lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto).strip('-')
    return texto[:60] or 'bar'
