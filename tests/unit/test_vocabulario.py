"""Vocabulário por tipo de negócio: bar não muda, artesão ganha seus rótulos."""
from types import SimpleNamespace

import pytest

from app.utils.vocabulario import rotulo, tipo_do, tipo_schema


@pytest.mark.parametrize('valor', [None, '', 'bar', 'qualquer-coisa'])
def test_tipo_ausente_ou_desconhecido_vale_bar(valor):
    assert tipo_do(SimpleNamespace(tipo_negocio=valor)) == 'bar'
    assert rotulo(SimpleNamespace(tipo_negocio=valor), 'cardapio') == 'Cardápio'


def test_artesao_tem_rotulos_proprios():
    rest = SimpleNamespace(tipo_negocio='artesao')
    assert rotulo(rest, 'cardapio') == 'Produtos'
    assert rotulo(rest, 'barraca') == 'Ateliê'
    assert rotulo('artesao', 'item') == 'Peça'


def test_schema_bar_preserva_o_tipo_da_vibe_e_artesao_vira_store():
    assert tipo_schema(None, 'BarOrPub') == 'BarOrPub'
    assert tipo_schema('bar', 'Restaurant') == 'Restaurant'
    assert tipo_schema('artesao', 'Restaurant') == 'Store'
