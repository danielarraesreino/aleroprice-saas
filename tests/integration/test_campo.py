"""Modo Campo: a visita ao bar, do login até a venda fechada.

Este arquivo existe porque a jornada só falha *inteira*. Cada peça passa
isolada e mesmo assim a visita fracassa se, por exemplo, a sessão morrer entre
a foto e o fechamento. O teste central aqui é `test_jornada_completa`.

O guard é `e_operador()` — quem opera a campanha mexe em tenant que não é o
seu, o que é o oposto da regra do resto do app. Por isso os testes de acesso
são tão importantes quanto os de funcionalidade.
"""
import io

import pytest
from werkzeug.datastructures import FileStorage  # noqa: F401  (documenta o tipo esperado)

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, GalleryItem
from app.models.usuario import Usuario


JPEG = b'\xff\xd8\xff\xe0' + b'conteudo' * 8


@pytest.fixture(autouse=True)
def disco_isolado(tmp_path, monkeypatch):
    """Sem BLOB_READ_WRITE_TOKEN o upload grava em disco — aqui, no tmp."""
    from app.utils import demos
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path))
    return tmp_path


@pytest.fixture
def operador(session):
    """O primeiro tenant é o operador da campanha — critério de `e_operador`."""
    rest = Restaurante(nome='Alero (operador)', slug='alero')
    session.add(rest)
    session.commit()
    usuario = Usuario(nome='Vendedor', email='vendedor@alero.com',
                      senha='segredo123', tipo='admin', restaurant_id=rest.id)
    session.add(usuario)
    session.commit()
    return usuario


@pytest.fixture
def demo(session, operador):
    """Prévia de um bar que ainda não é cliente."""
    rest = Restaurante(nome='Boteco do Teste', slug='boteco-do-teste',
                       tipo_conta='demo')
    session.add(rest)
    session.commit()
    session.add(SiteConfig(restaurant_id=rest.id, nome='Boteco do Teste'))
    session.commit()
    return rest


def entrar(client, email='vendedor@alero.com', senha='segredo123', lembrar='1'):
    dados = {'email': email, 'senha': senha}
    if lembrar:
        dados['lembrar'] = lembrar
    return client.post('/auth/login', data=dados, follow_redirects=False)


# --------------------------------------------------------------- sessão

def test_login_com_lembrar_deixa_cookie_persistente(client, operador):
    """Sem isto, trocar pro app da câmera desloga o vendedor no meio da visita."""
    resp = entrar(client)

    cookies = resp.headers.getlist('Set-Cookie')
    remember = [c for c in cookies if c.startswith('remember_token=')]
    assert remember, f'não veio remember_token: {cookies}'
    assert 'Expires=' in remember[0] or 'Max-Age=' in remember[0]


def test_sem_marcar_lembrar_nao_persiste(client, operador):
    resp = entrar(client, lembrar=None)
    assert not [c for c in resp.headers.getlist('Set-Cookie')
                if c.startswith('remember_token=')]


# --------------------------------------------------------------- acesso

def test_campo_exige_login(client, demo):
    resp = client.get('/campo/', follow_redirects=False)
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_quem_nao_e_operador_nem_sabe_que_existe(client, session, demo):
    """404 e não 403: painel interno não se anuncia pra cliente pagante."""
    outro = Restaurante(nome='Bar Alheio', slug='bar-alheio', tipo_conta='cliente')
    session.add(outro)
    session.commit()
    session.add(Usuario(nome='Dono', email='dono@alheio.com', senha='segredo123',
                        tipo='admin', restaurant_id=outro.id))
    session.commit()

    entrar(client, 'dono@alheio.com')

    assert client.get('/campo/').status_code == 404
    assert client.get('/campo/boteco-do-teste').status_code == 404
    assert client.post('/campo/boteco-do-teste/basico',
                       data={'nome': 'Invadido'}).status_code == 404


def test_bar_inexistente_da_404(client, operador):
    entrar(client)
    assert client.get('/campo/nao-existe').status_code == 404


# --------------------------------------------------------------- edição

def test_upload_de_capa_aparece_no_site(client, session, demo):
    entrar(client)

    resp = client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'capa',
        'imagem': (io.BytesIO(JPEG), 'capa.jpg'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 200
    caminho = resp.get_json()['url']
    assert caminho == 'img/demo/boteco-do-teste/capa.jpg'

    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    assert cfg.hero_foto == caminho
    assert caminho in client.get(f'/bar/{demo.slug}').get_data(as_text=True)


def test_prato_com_foto_entra_no_cardapio(client, session, demo):
    entrar(client)

    client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'prato', 'nome': 'Costela na brasa',
        'imagem': (io.BytesIO(JPEG), 'costela.jpg'),
    }, content_type='multipart/form-data')

    prato = DishCard.query.filter_by(restaurant_id=demo.id).one()
    assert prato.nome == 'Costela na brasa'
    assert prato.ativo is True

    corpo = client.get(f'/bar/{demo.slug}').get_data(as_text=True)
    assert 'Costela na brasa' in corpo
    # a seção de cardápio é guardada por `{% if dishes %}` — tem que ter voltado
    assert 'O QUE SAI DA COZINHA' in corpo


def test_arquivo_invalido_responde_erro_legivel(client, demo):
    entrar(client)

    resp = client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'capa', 'imagem': (io.BytesIO(b'PK\x03\x04'), 'planilha.xlsx'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 400
    assert 'JPG' in resp.get_json()['erro']


def test_basico_salva_e_renomeia_o_tenant(client, session, demo):
    entrar(client)

    client.post(f'/campo/{demo.slug}/basico', data={
        'nome': 'Boteco do Zé', 'whatsapp': '5519988887777',
        'descritor': 'Boteco de esquina em Barão Geraldo', 'endereco': 'Rua X, 10',
    })

    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    assert cfg.whatsapp == '5519988887777'
    assert Restaurante.query.get(demo.id).nome == 'Boteco do Zé'

    corpo = client.get(f'/bar/{demo.slug}').get_data(as_text=True)
    assert 'Boteco de esquina em Barão Geraldo' in corpo


def test_estilo_so_aceita_preset_conhecido(client, session, demo):
    """Cliente não escolhe CSS livre — presets fechados pra não feiar o site."""
    entrar(client)

    client.post(f'/campo/{demo.slug}/estilo', data={'tema': 'neon-noite',
                                                    'vibe': 'hamburgueria'})
    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    assert (cfg.tema, cfg.vibe) == ('neon-noite', 'hamburgueria')

    client.post(f'/campo/{demo.slug}/estilo', data={'tema': '"><script>',
                                                    'vibe': 'inventada'})
    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    assert (cfg.tema, cfg.vibe) == ('neon-noite', 'hamburgueria')


def test_remover_nao_alcanca_item_de_outro_bar(client, session, demo):
    """`id` sem `restaurant_id` no filtro apagaria conteúdo do bar errado."""
    vizinho = Restaurante(nome='Bar Vizinho', slug='bar-vizinho', tipo_conta='demo')
    session.add(vizinho)
    session.commit()
    alheio = GalleryItem(restaurant_id=vizinho.id, imagem='img/x.jpg',
                         ordem=0, ativo=True)
    session.add(alheio)
    session.commit()

    entrar(client)
    client.post(f'/campo/{demo.slug}/remover/galeria/{alheio.id}')

    assert GalleryItem.query.get(alheio.id) is not None


def test_qr_aponta_pro_site_do_bar(client, demo):
    entrar(client)
    resp = client.get(f'/campo/{demo.slug}/qr.svg')

    assert resp.status_code == 200
    assert resp.mimetype == 'image/svg+xml'
    assert b'<svg' in resp.data


# --------------------------------------------------------------- modelo do site

def test_visual_abre_com_a_previa_do_modelo_salvo(client, session, demo):
    """A tela é a prévia: sem o iframe apontando pro site do bar, não há o que
    mostrar ao dono."""
    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    cfg.modelo = 'craft'
    session.commit()

    entrar(client)
    resp = client.get(f'/campo/{demo.slug}/visual')

    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert f'/bar/{demo.slug}?modelo=craft' in corpo, 'iframe não abriu no modelo salvo'
    # os 6 cartões, com a frase que o vendedor lê em voz alta
    for esperado in ('Clássico', 'Craft', 'Brasa', 'Pra espetaria'):
        assert esperado in corpo, f'sumiu do seletor: {esperado}'


def test_visual_e_404_pra_quem_nao_e_operador(client, session, demo):
    """Mesma regra do resto do Modo Campo: quem não opera nem sabe que existe."""
    outro = Restaurante(nome='Bar Alheio 3', slug='bar-alheio-3', tipo_conta='cliente')
    session.add(outro)
    session.commit()
    session.add(Usuario(nome='Dono', email='dono3@alheio.com', senha='segredo123',
                        tipo='admin', restaurant_id=outro.id))
    session.commit()

    entrar(client, 'dono3@alheio.com')

    assert client.get(f'/campo/{demo.slug}/visual').status_code == 404
    assert client.post(f'/campo/{demo.slug}/visual',
                       data={'modelo': 'craft'}).status_code == 404


def test_usar_este_grava_e_troca_o_site(client, session, demo):
    """O botão da venda: o que estava só na prévia passa a ser o site de fato."""
    entrar(client)
    resp = client.post(f'/campo/{demo.slug}/visual', data={'modelo': 'craft'})

    assert resp.status_code == 302
    assert SiteConfig.query.filter_by(restaurant_id=demo.id).one().modelo == 'craft'

    # sem `?modelo=` na URL o visitante já vê o modelo escolhido
    salvo = client.get(f'/bar/{demo.slug}').get_data(as_text=True)
    espiado = client.get(f'/bar/{demo.slug}?modelo=craft').get_data(as_text=True)
    classico = client.get(f'/bar/{demo.slug}?modelo=classico').get_data(as_text=True)
    assert salvo == espiado, 'o site salvo não bate com a prévia que foi mostrada'
    assert salvo != classico, 'trocar o modelo não mudou nada no site'


def test_visual_recusa_modelo_inventado(client, session, demo):
    """Presets fechados, igual tema e vibe — modelo desconhecido não grava."""
    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    cfg.modelo = 'craft'
    session.commit()

    entrar(client)
    client.post(f'/campo/{demo.slug}/visual', data={'modelo': '"><script>'})

    assert SiteConfig.query.filter_by(restaurant_id=demo.id).one().modelo == 'craft'


def test_visual_tem_link_na_tela_de_edicao(client, demo):
    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}').get_data(as_text=True)
    assert f'/campo/{demo.slug}/visual' in corpo


# --------------------------------------------------------------- proposta

def test_proposta_abre_pro_operador_com_dados_do_bar(client, session, demo):
    """A proposta compõe o que o painel já sabe do bar — nome, endereço, zap —
    e o link da prévia, pronta pra mostrar na mesa."""
    entrar(client)
    client.post(f'/campo/{demo.slug}/basico', data={
        'nome': 'Boteco do Teste', 'whatsapp': '5519988887777',
        'descritor': 'Boteco de esquina em Barão Geraldo',
        'endereco': 'Av. Santa Isabel, 100',
    })

    resp = client.get(f'/campo/{demo.slug}/proposta')
    assert resp.status_code == 200

    corpo = resp.get_data(as_text=True)
    for esperado in ('Boteco do Teste', 'Av. Santa Isabel, 100',
                     '5519988887777', f'/bar/{demo.slug}',
                     'wa.me/5519988887777'):
        assert esperado in corpo, f'sumiu da proposta: {esperado}'
    # prévia expira — o prazo faz parte da proposta
    assert 'prévia' in corpo.lower()


def test_proposta_e_404_pra_quem_nao_e_operador(client, session, demo):
    """Mesma regra do resto do Modo Campo: quem não opera nem sabe que existe."""
    outro = Restaurante(nome='Bar Alheio', slug='bar-alheio', tipo_conta='cliente')
    session.add(outro)
    session.commit()
    session.add(Usuario(nome='Dono', email='dono@alheio.com', senha='segredo123',
                        tipo='admin', restaurant_id=outro.id))
    session.commit()

    entrar(client, 'dono@alheio.com')
    assert client.get(f'/campo/{demo.slug}/proposta').status_code == 404


def test_proposta_preco_vem_do_env(client, demo, monkeypatch):
    """Mesma fonte de `planos.precos()`: mudar o env muda a proposta, sem
    caçar número hardcoded em template."""
    monkeypatch.setenv('FEIRA_PRECO_SITE', 'R$ 777')
    monkeypatch.setenv('FEIRA_PRECO_PRO', 'R$ 999')

    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}/proposta').get_data(as_text=True)

    assert 'R$ 777' in corpo
    assert 'R$ 999' in corpo


def test_proposta_cai_no_yaml_do_lead_quando_o_painel_nao_tem(
        client, session, demo, tmp_path, monkeypatch):
    """O SiteConfig da prévia costuma estar magro; o que faltar vem do lead."""
    from app.utils import demos as mod
    (tmp_path / f'{demo.slug}.yml').write_text(
        'nome: "Boteco do Teste"\n'
        'site:\n'
        '  endereco: "R. Eduardo Modesto, 212"\n'
        '  horario: "qua-sáb 17h à 0h"\n'
        '  instagram_url: "https://instagram.com/botecodoteste"\n',
        encoding='utf-8')
    monkeypatch.setattr(mod, 'DIR_LEADS', str(tmp_path))

    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}/proposta').get_data(as_text=True)

    for esperado in ('R. Eduardo Modesto, 212', 'qua-sáb 17h à 0h',
                     'instagram.com/botecodoteste'):
        assert esperado in corpo, f'fallback do lead não entrou: {esperado}'


def test_proposta_mostra_nota_do_google(client, session, demo):
    """Nota e avaliações são argumento de venda: o dono vê que já é achado no
    Google — e a linha de fechamento diz onde o cliente decide entrar."""
    cfg = session.query(SiteConfig).filter_by(restaurant_id=demo.id).first()
    cfg.nota_google = '4,8'
    cfg.qtd_avaliacoes = 120
    session.commit()

    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}/proposta').get_data(as_text=True)

    assert '4,8' in corpo, 'nota do Google sumiu da proposta'
    assert '120 avaliações' in corpo, 'quantidade de avaliações sumiu'
    assert 'onde ele decide' in corpo, 'linha de venda do Google sumiu'


def test_proposta_tem_link_na_tela_de_edicao(client, demo):
    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}').get_data(as_text=True)
    assert f'/campo/{demo.slug}/proposta' in corpo


# --------------------------------------------------------------- venda

def test_converter_cria_a_conta_sem_refazer_o_site(client, session, demo):
    entrar(client)
    client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'prato', 'nome': 'Croquete',
        'imagem': (io.BytesIO(JPEG), 'croquete.jpg'),
    }, content_type='multipart/form-data')
    prato_id = DishCard.query.filter_by(restaurant_id=demo.id).one().id

    client.post(f'/campo/{demo.slug}/converter', data={
        'responsavel': 'Gustavo', 'email': 'gustavo@boteco.com',
        'senha': 'senha-forte-1',
    })

    rest = Restaurante.query.get(demo.id)
    assert rest.tipo_conta == 'cliente'
    assert rest.demo_expira_em is None
    assert rest.trial_termina_em is not None

    dono = Usuario.query.filter_by(email='gustavo@boteco.com').one()
    assert dono.restaurant_id == rest.id

    # mesma linha, mesmo id: o conteúdo montado na visita continua lá
    assert DishCard.query.filter_by(restaurant_id=rest.id).one().id == prato_id

    corpo = client.get(f'/bar/{demo.slug}').get_data(as_text=True)
    assert 'Prévia não oficial' not in corpo
    assert 'noindex' not in corpo


def test_email_ja_usado_recusa_antes_de_mexer_no_tenant(session, demo):
    """Duas contas com o mesmo e-mail quebrariam o login — e a recusa precisa
    vir *antes* de qualquer mutação, senão o bar fica meio-convertido."""
    from app.utils.demos import LeadInvalido, converter_demo

    session.add(Usuario(nome='Alguém', email='ocupado@x.com', senha='segredo123',
                        tipo='admin', restaurant_id=demo.id))
    session.commit()

    with pytest.raises(LeadInvalido, match='ocupado@x.com'):
        converter_demo(demo, 'ocupado@x.com', 'senha-forte-1')

    assert demo.tipo_conta == 'demo'
    assert demo.demo_expira_em is not None or demo.trial_termina_em is None


def test_dados_invalidos_nao_convertem(client, session, demo):
    entrar(client)
    for dados in ({'email': 'sem-arroba', 'senha': 'senha-forte-1'},
                  {'email': 'ok@x.com', 'senha': '123'}):
        client.post(f'/campo/{demo.slug}/converter', data=dados)

    assert Restaurante.query.get(demo.id).tipo_conta == 'demo'
    assert Usuario.query.filter_by(restaurant_id=demo.id).count() == 0


def test_jornada_completa(client, session, demo):
    """A visita inteira, na ordem em que acontece no bar."""
    entrar(client)

    assert client.get(f'/campo/{demo.slug}').status_code == 200

    client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'capa', 'imagem': (io.BytesIO(JPEG), 'capa.jpg'),
    }, content_type='multipart/form-data')
    client.post(f'/campo/{demo.slug}/basico', data={
        'nome': 'Boteco do Zé', 'whatsapp': '5519988887777',
        'descritor': 'Boteco de esquina em Barão Geraldo',
    })
    client.post(f'/campo/{demo.slug}/estilo', data={'tema': 'pub-escuro',
                                                    'vibe': 'pub'})
    client.post(f'/campo/{demo.slug}/foto', data={
        'alvo': 'prato', 'nome': 'Costela na brasa',
        'imagem': (io.BytesIO(JPEG), 'costela.jpg'),
    }, content_type='multipart/form-data')
    assert client.get(f'/campo/{demo.slug}/qr.svg').status_code == 200

    corpo = client.get(f'/bar/{demo.slug}').get_data(as_text=True)
    for esperado in ('Boteco do Zé', 'Costela na brasa', '5519988887777',
                     'img/demo/boteco-do-teste/capa.jpg'):
        assert esperado in corpo, f'sumiu do site: {esperado}'

    client.post(f'/campo/{demo.slug}/converter', data={
        'responsavel': 'Zé', 'email': 'ze@boteco.com', 'senha': 'senha-forte-1',
    })

    rest = Restaurante.query.get(demo.id)
    assert rest.tipo_conta == 'cliente'
    assert Usuario.query.filter_by(email='ze@boteco.com').count() == 1

    # o dono entra com o que foi combinado ali na mesa
    client.get('/auth/logout')
    assert entrar(client, 'ze@boteco.com', 'senha-forte-1').status_code == 302


# --------------------------------------------------------------- domínio

def test_proposta_mostra_dominio_livre(client, session, demo, monkeypatch):
    """Argumento que se prova na hora: o domínio do bar está livre."""
    import urllib.error
    from app.utils import dominios

    def livre(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, 'x', {}, None)
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', livre)

    entrar(client)
    corpo = client.get(f'/campo/{demo.slug}/proposta').get_data(as_text=True)

    assert 'botecodoteste.com.br' in corpo
    assert 'está livre agora' in corpo


def test_proposta_nao_promete_dominio_quando_rdap_falha(client, session, demo, monkeypatch):
    """RDAP fora do ar não pode virar 'está livre' — o vendedor repetiria na mesa."""
    import urllib.error
    from app.utils import dominios

    def explode(req, timeout=None):
        raise urllib.error.URLError('sem rede')
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', explode)

    entrar(client)
    resp = client.get(f'/campo/{demo.slug}/proposta')
    corpo = resp.get_data(as_text=True)

    assert resp.status_code == 200          # proposta não quebra
    assert 'está livre agora' not in corpo
    assert 'na hora' in corpo               # cai no texto de fallback


def test_taxa_de_instalacao_so_aparece_com_env(client, session, demo, monkeypatch):
    entrar(client)
    monkeypatch.delenv('FEIRA_TAXA_SETUP', raising=False)
    assert 'Instalação única' not in client.get(
        f'/campo/{demo.slug}/proposta').get_data(as_text=True)

    monkeypatch.setenv('FEIRA_TAXA_SETUP', 'R$ 97')
    corpo = client.get(f'/campo/{demo.slug}/proposta').get_data(as_text=True)
    assert 'Instalação única' in corpo and 'R$ 97' in corpo


def test_rota_de_dominio_responde_json_pro_operador(client, session, demo, monkeypatch):
    import urllib.error
    from app.utils import dominios

    def livre(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, 'x', {}, None)
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', livre)

    entrar(client)
    resp = client.get(f'/campo/{demo.slug}/dominio')

    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados['livre'] == 'botecodoteste.com.br'
    assert all(item['livre'] is True for item in dados['consulta'])


def test_rota_de_dominio_404_pra_quem_nao_e_operador(client, session, demo):
    from app.models.modelo_restaurante import Restaurante
    outro = Restaurante(nome='Bar Alheio 2', slug='bar-alheio-2', tipo_conta='cliente')
    session.add(outro)
    session.commit()
    session.add(Usuario(nome='Dono', email='dono2@alheio.com', senha='segredo123',
                        tipo='admin', restaurant_id=outro.id))
    session.commit()

    entrar(client, 'dono2@alheio.com')
    assert client.get(f'/campo/{demo.slug}/dominio').status_code == 404


# --------------------------------------------------------------- home de campo

def test_operador_cai_no_modo_campo_ao_entrar(client, operador):
    """Quem opera a campanha entra pelo celular, dentro de um bar. Mandá-lo pro
    painel de lucratividade (14 itens de menu, feito pra notebook) custa toques
    que não existem naquele momento."""
    resp = entrar(client)

    assert resp.headers['Location'] == '/campo/'


def test_dono_de_bar_continua_indo_pro_painel(client, session, operador):
    """O dashboard é o painel dele — não pode ser sequestrado pela ferramenta
    de venda do operador."""
    bar = Restaurante(nome='Bar Cliente', slug='bar-cliente', tipo_conta='cliente')
    session.add(bar)
    session.commit()
    session.add(Usuario(nome='Dono', email='dono@cliente.com', senha='segredo123',
                        tipo='admin', restaurant_id=bar.id))
    session.commit()

    resp = entrar(client, 'dono@cliente.com')

    assert '/campo' not in resp.headers['Location']
    assert '/app' in resp.headers['Location']


def test_home_de_campo_mostra_o_que_esta_pronto(client, session, demo):
    """Pronto = tem foto e tem nota. Sem os dois, a prévia parece um modelo com
    o nome trocado — e é isso que o placar responde antes de sair pra rua."""
    cfg = SiteConfig.query.filter_by(restaurant_id=demo.id).one()
    cfg.hero_foto = 'img/demo/boteco-do-teste/capa.jpg'
    cfg.nota_google = '4,7'
    session.commit()

    sem_nada = Restaurante(nome='Bar Cru', slug='bar-cru', tipo_conta='demo')
    session.add(sem_nada)
    session.commit()

    entrar(client)
    corpo = client.get('/campo/').get_data(as_text=True)

    assert '4,7 ★' in corpo, 'a nota tem que aparecer na lista'
    assert 'sem foto' in corpo, 'o que falta tem que estar visível'
    assert 'data-pronto="sim"' in corpo and 'data-pronto="nao"' in corpo
