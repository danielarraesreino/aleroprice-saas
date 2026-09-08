"""Testes de integração do módulo de previsão (rotas atuais).

Cobrem: histórico de vendas, registro manual de venda, geração e visualização
de previsão, fatores de sazonalidade e importação de CSV (com baixa de estoque).
"""
import io
import pytest
from datetime import date, timedelta

from app.models.modelo_previsao import (
    HistoricoVendas,
    PrevisaoDemanda,
    FatorSazonalidade,
)
from app.models.modelo_prato import Prato


@pytest.fixture
def prato_ativo(session, restaurant):
    prato = Prato(
        nome='Arroz com Feijão',
        descricao='Prato tradicional',
        categoria='Pratos Principais',
        rendimento=1,
        unidade_rendimento='kg',
        porcoes_rendimento=1,
        preco_venda=15.0,
        ativo=True,
        restaurant_id=restaurant.id,
    )
    session.add(prato)
    session.commit()
    return prato


@pytest.fixture
def prato_com_historico(session, prato_ativo):
    """Prato + 30 dias de histórico (a rota de previsão exige >= 5 pontos)."""
    for i in range(30):
        session.add(HistoricoVendas(
            data=date.today() - timedelta(days=i),
            prato_id=prato_ativo.id,
            quantidade=10 + (i % 5),
            valor_unitario=15.0,
            valor_total=(10 + (i % 5)) * 15.0,
            restaurant_id=prato_ativo.restaurant_id,
        ))
    session.commit()
    return prato_ativo


def test_listar_historico(auth_client, session, prato_com_historico):
    resp = auth_client.get('/previsao/historico')
    assert resp.status_code == 200
    total = session.query(HistoricoVendas).filter_by(
        prato_id=prato_com_historico.id).count()
    assert total == 30


def test_registrar_venda(auth_client, session, prato_com_historico):
    antes = session.query(HistoricoVendas).filter_by(
        prato_id=prato_com_historico.id).count()
    resp = auth_client.post('/previsao/historico/registrar', data={
        'data': date.today().strftime('%Y-%m-%d'),
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'quantidade': 5,
        'valor_unitario': 15.0,
    }, follow_redirects=True)
    assert resp.status_code == 200
    depois = session.query(HistoricoVendas).filter_by(
        prato_id=prato_com_historico.id).count()
    assert depois == antes + 1


def test_gerar_e_visualizar_previsao(auth_client, session, prato_com_historico):
    resp = auth_client.post('/previsao/previsao/gerar', data={
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'data_inicio': date.today().strftime('%Y-%m-%d'),
        'data_fim': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
        'metodo': 'media_movel',
        'dias_projecao': 7,
    }, follow_redirects=True)
    assert resp.status_code == 200
    previsao = session.query(PrevisaoDemanda).filter_by(
        prato_id=prato_com_historico.id).first()
    assert previsao is not None

    resp = auth_client.get(f'/previsao/previsao/visualizar/{previsao.id}')
    assert resp.status_code == 200


def test_listar_previsoes(auth_client, session, prato_com_historico):
    auth_client.post('/previsao/previsao/gerar', data={
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'data_inicio': date.today().strftime('%Y-%m-%d'),
        'data_fim': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
        'metodo': 'media_movel',
        'dias_projecao': 7,
    }, follow_redirects=True)
    resp = auth_client.get('/previsao/previsoes')
    assert resp.status_code == 200


def test_criar_fator_sazonalidade(auth_client, session, prato_com_historico):
    resp = auth_client.post('/previsao/sazonalidade/criar', data={
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'tipo_sazonalidade': 'mes',
        'mes': 12,
        'fator': 1.2,
        'descricao': 'Dezembro',
    }, follow_redirects=True)
    assert resp.status_code == 200
    fator = session.query(FatorSazonalidade).filter_by(
        prato_id=prato_com_historico.id).first()
    assert fator is not None
    assert fator.fator == pytest.approx(1.2)


def test_importar_historico_csv(auth_client, session, prato_ativo):
    csv_content = 'data;produto;quantidade;valor\n'
    csv_content += f'{date.today().strftime("%Y-%m-%d")};Arroz com Feijão;5;15.00\n'
    data = {'arquivo_csv': (io.BytesIO(csv_content.encode('utf-8')), 'vendas.csv')}
    resp = auth_client.post('/previsao/historico/importar', data=data,
                            content_type='multipart/form-data',
                            follow_redirects=True)
    assert resp.status_code == 200
    venda = session.query(HistoricoVendas).filter_by(
        prato_id=prato_ativo.id).first()
    assert venda is not None


def test_editar_fator_sazonalidade(auth_client, session, prato_com_historico):
    """Edita um fator de sazonalidade via rota (GET form + POST update)."""
    auth_client.post('/previsao/sazonalidade/criar', data={
        'tipo_sazonalidade': 'mes',
        'mes': 12,
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'fator': 1.2,
        'descricao': 'Dezembro',
    }, follow_redirects=True)

    fator = session.query(FatorSazonalidade).filter_by(
        prato_id=prato_com_historico.id).first()
    assert fator is not None

    resp = auth_client.get(f'/previsao/sazonalidade/editar/{fator.id}')
    assert resp.status_code == 200

    resp = auth_client.post(f'/previsao/sazonalidade/editar/{fator.id}', data={
        'tipo_sazonalidade': 'evento',
        'evento': 'Natal',
        'tipo_item': 'prato',
        'item_id': prato_com_historico.id,
        'fator': 0.8,
        'descricao': 'Natal atualizado',
    }, follow_redirects=True)
    assert resp.status_code == 200

    session.expire_all()
    fator = session.query(FatorSazonalidade).filter_by(id=fator.id).first()
    assert fator.mes is None
    assert fator.evento == 'Natal'
    assert fator.fator == pytest.approx(0.8)
    assert fator.descricao == 'Natal atualizado'
