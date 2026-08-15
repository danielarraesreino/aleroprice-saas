"""A landing entrega o grafo pronto — pra qualquer tenant, sem exceção.

`app/utils/seo.py` tem os testes de unidade do que ele monta. Aqui a pergunta é
outra e é a que quebra na prática: o motor está **ligado** na única rota que
serve site de bar, e ligado com os dados daquele bar — não do primeiro do banco.

O contexto é capturado pelo sinal `template_rendered` em vez de procurar string
no HTML: os templates estão sendo mexidos em paralelo, e um teste que dependesse
da marcação de lá quebraria sem nada estar errado no motor.
"""
import json

import pytest
from flask import template_rendered

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard

PRODUTO = 'feiradebarao.com.br'


@pytest.fixture(autouse=True)
def dominio_do_produto(monkeypatch):
    monkeypatch.setenv('DOMINIO_PRODUTO', PRODUTO)


@pytest.fixture
def contexto(app):
    """Kwargs que a view passou pro template desta requisição."""
    capturado = {}

    def registrar(sender, template, context, **extra):
        capturado.update(context)

    template_rendered.connect(registrar, app)
    yield capturado
    template_rendered.disconnect(registrar, app)


@pytest.fixture
def bar(session):
    r = Restaurante(nome='Bar da Vila', slug='bar-da-vila',
                    dominio='bardavila.bar', tipo_conta='cliente')
    session.add(r)
    session.commit()
    session.add(SiteConfig(
        restaurant_id=r.id, nome='Bar da Vila', vibe='boteco',
        descritor='Boteco de família em Vila Lemos',
        tagline='Samba no fim de semana, comida de vó e cerveja gelada.',
        cidade_uf='Vila Lemos, Campinas–SP',
        endereco='R. Madalena B. Ferreira, 10 - Vila Lemos, Campinas - SP, 13070-000',
        horario='Ter–Qui 17h–01h30 · Sex 17h–02h30',
        telefone_exibicao='(19) 99977-9942',
        nota_google='4,9', qtd_avaliacoes=39))
    session.add(DishCard(restaurant_id=r.id, nome='Croquete da Bruna',
                         descricao='O mais pedido da casa.', ordem=1))
    session.commit()
    return r


def grafo_de(contexto):
    assert contexto.get('json_ld'), 'a landing não recebeu json_ld'
    return json.loads(contexto['json_ld'])


def test_landing_do_bar_recebe_o_grafo_com_os_dados_dele(client, bar, contexto):
    assert client.get('/bar/bar-da-vila').status_code == 200

    grafo = grafo_de(contexto)
    casa = grafo['@graph'][0]

    assert casa['@type'] == 'BarOrPub'
    assert casa['name'] == 'Bar da Vila'
    assert casa['telephone'] == '(19) 99977-9942'
    assert casa['address']['addressLocality'] == 'Campinas'
    assert casa['openingHours'] == ['Tu-Th 17:00-01:30', 'Fr 17:00-02:30']
    assert casa['aggregateRating']['ratingValue'] == 4.9
    assert casa['aggregateRating']['reviewCount'] == 39

    cardapio = next(n for n in grafo['@graph'] if n['@type'] == 'Menu')
    assert cardapio['hasMenuItem'][0]['name'] == 'Croquete da Bruna'


def test_url_canonica_e_o_dominio_do_bar_mesmo_servindo_por_slug(client, bar,
                                                                 contexto):
    """O bar responde em três endereços. O grafo tem que apontar sempre pro
    canônico, senão o mesmo bar vira três entidades no índice do Google."""
    client.get('/bar/bar-da-vila', headers={'Host': PRODUTO})

    assert contexto['url_canonica'] == 'https://bardavila.bar/'
    assert grafo_de(contexto)['@graph'][0]['@id'] == 'https://bardavila.bar/#restaurante'


def test_meta_descricao_chega_montada_do_dado_real(client, bar, contexto):
    client.get('/bar/bar-da-vila')

    meta = contexto['meta_desc']
    assert meta.startswith('Bar da Vila — Boteco de família em Vila Lemos.')
    assert len(meta) <= 160


def test_bar_sem_nada_configurado_recebe_grafo_verdadeiro(client, session,
                                                          contexto):
    """Tenant recém-criado: o motor não pode inventar nada pra preencher."""
    r = Restaurante(nome='Bar Recém-Nascido', slug='bar-novo', tipo_conta='cliente')
    session.add(r)
    session.commit()

    assert client.get('/bar/bar-novo').status_code == 200

    casa = grafo_de(contexto)['@graph'][0]
    assert casa == {'@type': 'Restaurant',
                    '@id': f'https://{PRODUTO}/bar/bar-novo#restaurante',
                    'name': 'Bar Recém-Nascido',
                    'url': f'https://{PRODUTO}/bar/bar-novo'}
    assert contexto['meta_desc'] is None


def test_previa_comercial_nao_publica_a_agenda_de_exemplo(client, session,
                                                          contexto):
    """A prévia mostra agenda de exemplo na tela (com selo) pra o vendedor
    demonstrar o recurso. Em JSON-LD isso viraria show inventado."""
    r = Restaurante(nome='Tatu Bola', slug='tatu-bola', tipo_conta='demo')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Tatu Bola', vibe='boteco'))
    session.commit()

    assert client.get('/bar/tatu-bola').status_code == 200

    # A tela recebeu os exemplos...
    assert contexto['eventos'] and all(e.exemplo for e in contexto['eventos'])
    # ...e o grafo, nenhum deles.
    assert 'Event' not in [n['@type'] for n in grafo_de(contexto)['@graph']]
