"""Prévias comerciais a partir de arquivo de lead.

Dois requisitos não-óbvios estão travados aqui:

1. **Idempotência.** O aplicador roda por HTTP (`/bootstrap-demo?action=demos`),
   que pode dar timeout no meio e ser reexecutado. Reaplicar tem que atualizar,
   nunca duplicar.
2. **`noindex`.** A prévia é montada com o nome e as fotos de um bar que não
   pediu nada. Se ela indexar, compete no Google com o negócio real de alguém.
   O teste de `noindex` é o que impede isso de regredir.
"""
import textwrap

import pytest

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, Review, GalleryItem
from app.utils import demos


LEAD = textwrap.dedent("""
    nome: Boteco do Teste
    tema: pub-escuro
    site:
      descritor: Boteco de esquina em Campinas
      tagline: Chope gelado e porção farta.
      whatsapp: '5519988887777'
      hero_foto: img/bar/foto-18.jpg
    cardapio:
      - nome: Calabresa acebolada
        descricao: Na chapa.
        imagem: img/bar/foto-5.jpg
        tag: "★ O MAIS PEDIDO"
        destaque: true
      - nome: Chope
        descricao: Bem tirado.
    avaliacoes:
      - autor: Cliente Fulano
        texto: Melhor da regiao.
        estrelas: 5
    galeria:
      - img/bar/foto-3.jpg
      - img/bar/foto-6.jpg
    demo:
      fonte: relatorio-rmc
""")


@pytest.fixture
def lead(tmp_path, monkeypatch):
    """Diretório de leads isolado, com um arquivo válido."""
    (tmp_path / 'boteco-do-teste.yml').write_text(LEAD, encoding='utf-8')
    monkeypatch.setattr(demos, 'DIR_LEADS', str(tmp_path))
    return tmp_path


def test_aplica_lead_e_publica_site(client, session, lead):
    resultado = demos.aplicar_todos()
    assert resultado['erros'] == []

    rest = Restaurante.query.filter_by(slug='boteco-do-teste').one()
    assert rest.tipo_conta == 'demo'
    assert rest.demo_expira_em is not None          # prévia sempre tem prazo

    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).one()
    assert cfg.tema == 'pub-escuro'
    assert cfg.whatsapp == '5519988887777'

    assert DishCard.query.filter_by(restaurant_id=rest.id).count() == 2
    assert Review.query.filter_by(restaurant_id=rest.id).count() == 1
    assert GalleryItem.query.filter_by(restaurant_id=rest.id).count() == 2

    resp = client.get('/bar/boteco-do-teste')
    assert resp.status_code == 200
    assert 'Boteco do Teste' in resp.get_data(as_text=True)


def test_demo_nao_e_indexavel(client, session, lead):
    """Assert jurídico: prévia não autorizada não pode ir pro Google.

    Quem faz isso é o `noindex` da própria página — e só ele. O `Disallow:
    /bar/` que existia aqui atrapalhava duas vezes: bloqueava o site do cliente
    pagante (que também mora em /bar/<slug>) e impedia o rastreador de abrir a
    página pra ler justamente este noindex.
    """
    demos.aplicar_todos()
    corpo = client.get('/bar/boteco-do-teste').get_data(as_text=True)

    assert 'noindex' in corpo
    assert 'Prévia não oficial' in corpo


def test_robots_nao_bloqueia_o_site_do_cliente(client, session, lead):
    """`/bar/<slug>` é o endereço de todo bar sem domínio próprio: bloqueá-lo é
    vender um site que o Google não pode ler."""
    robots = client.get('/robots.txt').get_data(as_text=True)

    assert 'Disallow: /bar/' not in robots
    assert 'Disallow: /s/' not in robots
    # o que continua fora do índice é o sistema, não o site de ninguém
    for interno in ('/app/', '/campo/', '/cadastro'):
        assert f'Disallow: {interno}' in robots


def test_reaplicar_nao_duplica(client, session, lead):
    demos.aplicar_todos()
    demos.aplicar_todos()
    demos.aplicar_todos()

    assert Restaurante.query.filter_by(slug='boteco-do-teste').count() == 1
    rid = Restaurante.query.filter_by(slug='boteco-do-teste').one().id
    assert SiteConfig.query.filter_by(restaurant_id=rid).count() == 1
    assert DishCard.query.filter_by(restaurant_id=rid).count() == 2
    assert GalleryItem.query.filter_by(restaurant_id=rid).count() == 2


def test_demo_nao_cria_usuario(session, lead):
    """Demo não tem dono — é isso que faz a conversão ser 'adicionar', não
    'migrar'. Todo o conteúdo curado fica no mesmo restaurant_id."""
    from app.models.usuario import Usuario
    demos.aplicar_todos()
    rest = Restaurante.query.filter_by(slug='boteco-do-teste').one()
    assert Usuario.query.filter_by(restaurant_id=rest.id).count() == 0


def test_recusa_sobrescrever_cliente_pagante(session, lead):
    demos.aplicar_todos()
    rest = Restaurante.query.filter_by(slug='boteco-do-teste').one()
    rest.tipo_conta = 'cliente'
    session.commit()

    resultado = demos.aplicar_todos()

    assert resultado['ok'] == []
    assert 'cliente' in resultado['erros'][0]['erro']


def test_campo_desconhecido_falha_alto(session, tmp_path, monkeypatch):
    """Typo no .yml vira erro visível, não campo silenciosamente ignorado."""
    (tmp_path / 'bar-x.yml').write_text(
        'nome: Bar X\nsite:\n  whatsap: "5519999999999"\n', encoding='utf-8')
    monkeypatch.setattr(demos, 'DIR_LEADS', str(tmp_path))

    resultado = demos.aplicar_todos()

    assert resultado['ok'] == []
    assert 'whatsap' in resultado['erros'][0]['erro']
    assert Restaurante.query.filter_by(slug='bar-x').first() is None


def test_conversao_preserva_conteudo(client, session, lead):
    demos.aplicar_todos()
    rest = Restaurante.query.filter_by(slug='boteco-do-teste').one()
    pratos_antes = DishCard.query.filter_by(restaurant_id=rest.id).count()

    admin = demos.converter_demo(rest, 'dono@boteco.com', 'segredo123')
    db.session.commit()

    assert rest.tipo_conta == 'cliente'
    assert rest.demo_expira_em is None
    assert rest.trial_termina_em is not None
    assert admin.restaurant_id == rest.id
    # mesmo restaurant_id, mesmas linhas: nada foi recriado
    assert DishCard.query.filter_by(restaurant_id=rest.id).count() == pratos_antes

    # virou cliente: sai o aviso de prévia e volta a ser indexável
    corpo = client.get('/bar/boteco-do-teste').get_data(as_text=True)
    assert 'noindex' not in corpo
    assert 'Prévia não oficial' not in corpo


def test_demo_nao_conta_como_cliente(session, lead):
    """Métrica comercial não pode inflar com prévia."""
    demos.aplicar_todos()
    assert Restaurante.clientes().filter_by(slug='boteco-do-teste').count() == 0


def test_fotos_da_pasta_montam_o_site(client, session, tmp_path, monkeypatch):
    """Fluxo de campo: o dono manda as fotos, você joga na pasta e roda o
    comando — sem editar YAML na frente dele."""
    from PIL import Image

    (tmp_path / 'leads').mkdir()
    (tmp_path / 'leads' / 'boteco-do-teste.yml').write_text(
        'nome: Boteco do Teste\nsite:\n  tagline: Teste.\n', encoding='utf-8')
    monkeypatch.setattr(demos, 'DIR_LEADS', str(tmp_path / 'leads'))

    pasta = tmp_path / 'fotos' / 'boteco-do-teste'
    pasta.mkdir(parents=True)
    for nome in ('capa.jpg', 'prato-costela-na-brasa.jpg', 'ambiente-1.jpg'):
        Image.new('RGB', (8, 8), (120, 80, 40)).save(pasta / nome)
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path / 'fotos'))

    demos.aplicar_todos()

    rest = Restaurante.query.filter_by(slug='boteco-do-teste').one()
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).one()

    assert cfg.hero_foto == 'img/demo/boteco-do-teste/capa.jpg'
    pratos = DishCard.query.filter_by(restaurant_id=rest.id).all()
    assert [p.nome for p in pratos] == ['Costela na brasa']   # nome vem do arquivo
    assert GalleryItem.query.filter_by(restaurant_id=rest.id).count() == 1

    corpo = client.get('/bar/boteco-do-teste').get_data(as_text=True)
    assert 'Costela na brasa' in corpo
    assert 'capa.jpg' in corpo


def test_yaml_tem_prioridade_sobre_a_pasta(session, tmp_path, monkeypatch):
    """Quem escreveu no arquivo decidiu — a pasta só preenche o que falta."""
    from PIL import Image

    (tmp_path / 'leads').mkdir()
    (tmp_path / 'leads' / 'bar-x.yml').write_text(
        'nome: Bar X\nsite:\n  hero_foto: img/bar/foto-18.jpg\n', encoding='utf-8')
    monkeypatch.setattr(demos, 'DIR_LEADS', str(tmp_path / 'leads'))

    pasta = tmp_path / 'fotos' / 'bar-x'
    pasta.mkdir(parents=True)
    Image.new('RGB', (8, 8)).save(pasta / 'capa.jpg')
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path / 'fotos'))

    demos.aplicar_todos()

    rest = Restaurante.query.filter_by(slug='bar-x').one()
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).one()
    assert cfg.hero_foto == 'img/bar/foto-18.jpg'


def test_casa_fechada_fica_fora_do_ar_mesmo_reaplicando(client, session, tmp_path, monkeypatch):
    """`ativo: false` no lead tira a prévia do ar — e a mantém fora.

    Sem isso o aplicador reativava tudo a cada rodada, e casa que fechou (o
    Google marca "permanentemente fechado") voltava a ter site publicado no nome
    dela, além de reentrar no roteiro e custar um deslocamento à toa. Apagar o
    lead não serve: a próxima varredura o recriaria.
    """
    (tmp_path / 'bar-que-fechou.yml').write_text(
        'nome: Bar Que Fechou\nativo: false\nsite:\n  tagline: Fechou.\n',
        encoding='utf-8')
    monkeypatch.setattr(demos, 'DIR_LEADS', str(tmp_path))

    demos.aplicar_todos()
    rest = Restaurante.query.filter_by(slug='bar-que-fechou').one()
    assert rest.ativo is False
    assert client.get('/bar/bar-que-fechou').status_code == 404

    # a reaplicação é rotina (roda a cada deploy) e não pode ressuscitar a casa
    demos.aplicar_todos()
    session.expire_all()
    assert Restaurante.query.filter_by(slug='bar-que-fechou').one().ativo is False
    assert client.get('/bar/bar-que-fechou').status_code == 404


def test_lead_sem_ativo_continua_publicando(client, session, lead):
    """O padrão não muda: quem não declara `ativo` vai pro ar como sempre."""
    demos.aplicar_todos()
    assert Restaurante.query.filter_by(slug='boteco-do-teste').one().ativo is True
    assert client.get('/bar/boteco-do-teste').status_code == 200
