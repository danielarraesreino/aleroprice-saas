"""Catálogo do cliente no formato de feed da Meta (WhatsApp Business, Instagram e
Facebook).

O site é a fonte da verdade: o expositor cadastra o produto uma vez no painel,
e o Commerce Manager da Meta busca este feed no horário agendado e atualiza o
catálogo conectado ao WhatsApp Business dele. O caminho inverso não existe: o
catálogo feito à mão no app do WhatsApp não tem exportação pública.

A Meta recusa o item sem preço ou sem imagem, então esses ficam de fora do feed
(e continuam no site). Colunas e valores seguem o modelo de planilha do
Commerce Manager.
"""
import csv
import io

from flask import url_for

from app.models.modelo_sitecontent import DishCard, ProdutoSite
from app.utils.site_router import dominio_do_produto, url_canonica
from app.utils.vocabulario import tipo_do

COLUNAS = ('id', 'title', 'description', 'availability', 'condition', 'price',
           'link', 'image_link', 'brand')


def _imagem_absoluta(caminho):
    if caminho.startswith(('http://', 'https://')):
        return caminho
    return f'https://{dominio_do_produto()}' + url_for('static', filename=caminho)


def itens(rest, nome_marca=None):
    """Linhas do feed (dicts com `COLUNAS`) e quantos produtos ficaram de fora."""
    artesao = tipo_do(rest) == 'artesao'
    modelo = ProdutoSite if artesao else DishCard
    produtos = (modelo.query.filter_by(restaurant_id=rest.id, ativo=True)
                .order_by(modelo.ordem, modelo.id).all())
    link = url_canonica(rest)
    marca = (nome_marca or rest.nome)[:100]
    linhas, fora = [], 0
    for p in produtos:
        if not p.preco or not p.imagem:
            fora += 1
            continue
        encomenda = artesao and bool(p.sob_encomenda)
        linhas.append({
            # Prefixo do tipo: id de produto e de prato vêm de tabelas diferentes.
            'id': f'{"p" if artesao else "d"}{p.id}',
            'title': p.nome[:150],
            'description': ((p.descricao or '').strip() or p.nome)[:5000],
            'availability': 'available for order' if encomenda else 'in stock',
            'condition': 'new',
            'price': f'{p.preco:.2f} BRL',
            'link': link,
            'image_link': _imagem_absoluta(p.imagem),
            'brand': marca,
        })
    return linhas, fora


def csv_do_feed(linhas):
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS, lineterminator='\n')
    escritor.writeheader()
    escritor.writerows(linhas)
    return saida.getvalue()
