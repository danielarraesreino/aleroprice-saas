"""Testes de integração do módulo de desperdício (rotas atuais).

Cobrem o fluxo real: criar categoria, registrar desperdício, listar, criar e
visualizar metas e gerar relatórios/exportação. Usam `auth_client` (login como
admin do restaurante de teste) e as rotas registradas em `/desperdicio`.
"""
import pytest
from datetime import date, timedelta

from app.models.modelo_desperdicio import (
    CategoriaDesperdicio,
    RegistroDesperdicio,
    MetaDesperdicio,
)
from app.models.modelo_produto import Produto


@pytest.fixture
def categoria(session, restaurant):
    cat = CategoriaDesperdicio(
        nome='Vencimento',
        descricao='Produtos vencidos',
        cor='#FF0000',
        ativo=True,
        restaurant_id=restaurant.id,
    )
    session.add(cat)
    session.commit()
    return cat


@pytest.fixture
def produto(session, restaurant):
    prod = Produto(
        nome='Arroz',
        descricao='Arroz branco',
        unidade='kg',
        preco_unitario=5.0,
        estoque_minimo=10.0,
        estoque_atual=50.0,
        categoria='Grãos',
        restaurant_id=restaurant.id,
    )
    session.add(prod)
    session.commit()
    return prod


@pytest.fixture
def registro(session, categoria, produto):
    reg = RegistroDesperdicio(
        categoria_id=categoria.id,
        produto_id=produto.id,
        quantidade=2.5,
        unidade='kg',
        valor_estimado=12.5,
        motivo='Vencido',
        responsavel='QA',
        local='Estoque',
        restaurant_id=produto.restaurant_id,
    )
    session.add(reg)
    session.commit()
    return reg


def test_criar_categoria(auth_client, session, restaurant):
    resp = auth_client.post('/desperdicio/categoria/criar', data={
        'nome': 'Sobra de produção',
        'descricao': 'Sobra de preparo',
        'cor': '#FFA500',
    }, follow_redirects=True)
    assert resp.status_code == 200
    cat = session.query(CategoriaDesperdicio).filter_by(
        nome='Sobra de produção', restaurant_id=restaurant.id).first()
    assert cat is not None


def test_registrar_desperdicio(auth_client, session, categoria, produto):
    resp = auth_client.post('/desperdicio/registro/criar', data={
        'categoria_id': categoria.id,
        'tipo_item': 'produto',
        'item_id': produto.id,
        'quantidade': 1.5,
        'unidade': 'kg',
        'valor_estimado': 7.5,
        'motivo': 'Vencido',
        'responsavel': 'QA',
        'local': 'Estoque',
    }, follow_redirects=True)
    assert resp.status_code == 200
    reg = session.query(RegistroDesperdicio).filter_by(
        produto_id=produto.id, restaurant_id=produto.restaurant_id).first()
    assert reg is not None
    assert reg.quantidade == 1.5


def test_listar_registros(auth_client, registro):
    resp = auth_client.get('/desperdicio/registros')
    assert resp.status_code == 200


def test_criar_meta(auth_client, session, categoria):
    resp = auth_client.post('/desperdicio/meta/criar', data={
        'descricao': 'Reduzir vencidos',
        'data_inicio': date.today().strftime('%Y-%m-%d'),
        'data_fim': (date.today() + timedelta(days=60)).strftime('%Y-%m-%d'),
        'categoria_id': categoria.id,
        'valor_inicial': 500.0,
        'meta_reducao_percentual': 20.0,
        'responsavel': 'QA',
    }, follow_redirects=True)
    assert resp.status_code == 200
    meta = session.query(MetaDesperdicio).filter_by(
        descricao='Reduzir vencidos', restaurant_id=categoria.restaurant_id).first()
    assert meta is not None
    # valor_meta é derivado: 500 * (1 - 0.20)
    assert meta.valor_meta == pytest.approx(400.0)


def test_listar_e_visualizar_meta(auth_client, session, categoria):
    meta = MetaDesperdicio(
        descricao='Meta QA',
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=30),
        categoria_id=categoria.id,
        valor_inicial=100.0,
        valor_meta=80.0,
        meta_reducao_percentual=20.0,
        restaurant_id=categoria.restaurant_id,
    )
    session.add(meta)
    session.commit()

    resp = auth_client.get('/desperdicio/metas')
    assert resp.status_code == 200

    resp = auth_client.get(f'/desperdicio/meta/visualizar/{meta.id}')
    assert resp.status_code == 200


def test_relatorios_e_exportacao(auth_client, registro):
    resp = auth_client.get('/desperdicio/relatorios')
    assert resp.status_code == 200

    resp = auth_client.get('/desperdicio/exportar/registros')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
