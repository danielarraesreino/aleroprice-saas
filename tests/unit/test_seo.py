"""Motor de dados estruturados: o que ele promete ao Google não pode ser falso.

Estes testes existem por um motivo só, e é o mesmo da regra de ouro do módulo:
schema.org é uma **declaração**. Emitir `telephone: ""`, `ratingValue: "None"` ou
um `Event` que ninguém vai tocar não é bug de formatação — é o site do cliente
afirmando ao Google algo que não é verdade, e a penalidade cai no bar, não em
nós. Por isso a cobertura aqui é menos sobre "montou o dict certo" e mais sobre
"não mentiu quando faltou dado".

Os horários e endereços usados são os **reais** dos leads em `app/data/leads/`.
Parser de horário de bar brasileiro não se testa com exemplo inventado: as
variações que quebram ("a partir das 18h", "Sex 11h30–14h e 18h–23h") só
aparecem no que os donos de bar realmente escreveram.
"""
from datetime import date, datetime

import pytest

from app.utils.seo import (
    abertura_schema, dados_estruturados, endereco_schema, horario_schema,
    meta_descricao, serializar,
)
from app.utils.vitrine import eventos_de_exemplo


URL = 'https://estacaobarao.bar/'


# --------------------------------------------------------------- ferramentas

def varrer(dados, caminho='raiz'):
    """Todo par (caminho, valor) folha do grafo. Usado pelas asserções de lixo."""
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            yield from varrer(valor, f'{caminho}.{chave}')
    elif isinstance(dados, list):
        for i, valor in enumerate(dados):
            yield from varrer(valor, f'{caminho}[{i}]')
    else:
        yield caminho, dados


def tipos(grafo):
    return [no['@type'] for no in grafo['@graph']]


def no_de(grafo, tipo):
    return next(no for no in grafo['@graph'] if no['@type'] == tipo)


class Evento:
    """Espelha o que o grafo lê de `app.models.modelo_evento.Evento`."""
    exemplo = False

    def __init__(self, **campos):
        self.__dict__.update(campos)


@pytest.fixture
def site_completo():
    """Estação Barão — o lead mais completo do banco (app/data/leads/)."""
    return {
        'nome': 'Estação Barão',
        'descritor': 'Bar e restaurante desde 1953 em Barão',
        'tagline': 'Setenta anos de balcão — a história do bairro passa por aqui.',
        'cidade_uf': 'Barão Geraldo, Campinas–SP',
        'endereco': 'R. Horácio Leonardi, 76 - Barão Geraldo, Campinas - SP, 13084-105',
        'horario': 'Seg–Qui 11h–00h · Sex–Sáb 11h–01h · Dom 11h–00h',
        'telefone_exibicao': '(19) 99109-1080',
        'whatsapp': '5519991091080',
        'maps_query': 'Estação Barão Bar e Restaurante Campinas',
        'instagram_url': 'https://www.instagram.com/estacao_bar/',
        'facebook_url': 'https://www.facebook.com/estacaobarao',
        'nota_google': '4,8',
        'qtd_avaliacoes': 26,
        'vibe': 'boteco',
        'hero_foto': 'img/demo/estacao-barao/capa.jpg',
        'servicos': 'Wi-Fi, Estacionamento',
        'data_atualizacao': datetime(2026, 8, 14, 10, 30, 0),
    }


@pytest.fixture
def dishes():
    return [
        {'nome': 'Porção de calabresa', 'descricao': 'Acebolada, na chapa.',
         'img': '/static/img/demo/estacao-barao/calabresa.jpg',
         'tag': '★ O MAIS PEDIDO', 'destaque': True},
        {'nome': 'Chope gelado', 'descricao': None, 'img': None,
         'tag': None, 'destaque': False},
    ]


@pytest.fixture
def reviews():
    return [{'autor': 'Ana Paula', 'texto': 'Melhor fim de tarde de Barão.',
             'estrelas': 5}]


# ------------------------------------------------------------- grafo completo

def test_bar_completo_gera_o_grafo_inteiro(site_completo, dishes, reviews):
    eventos = [Evento(titulo='Samba no salão', descricao='Roda de samba, entrada franca.',
                      data=date(2026, 9, 5), hora='20:00')]
    grafo = dados_estruturados(None, site_completo, dishes, reviews, eventos, URL)

    assert grafo['@context'] == 'https://schema.org'
    assert set(tipos(grafo)) == {
        'BarOrPub', 'Menu', 'Review', 'Event', 'BreadcrumbList', 'WebSite'}

    casa = no_de(grafo, 'BarOrPub')
    assert casa['name'] == 'Estação Barão'
    assert casa['telephone'] == '(19) 99109-1080'
    assert casa['servesCuisine'] == 'Brasileira'
    assert casa['address']['postalCode'] == '13084-105'
    assert casa['openingHours'] == ['Mo-Th 11:00-00:00', 'Fr-Sa 11:00-01:00',
                                    'Su 11:00-00:00']
    assert len(casa['sameAs']) == 2
    assert casa['hasMap'].startswith('https://www.google.com/maps/')
    # hasMenu é referência à página/âncora do cardápio, não o cardápio embutido.
    assert casa['hasMenu'] == {'@id': f'{URL}#cardapio'}

    cardapio = no_de(grafo, 'Menu')
    assert [i['name'] for i in cardapio['hasMenuItem']] == ['Porção de calabresa',
                                                            'Chope gelado']

    evento = no_de(grafo, 'Event')
    assert evento['startDate'] == '2026-09-05T20:00:00'
    assert evento['location'] == {'@id': f'{URL}#restaurante'}

    # Frescor: o Perplexity pesa data de modificação. Vai no WebSite porque
    # dateModified é propriedade de CreativeWork, não de LocalBusiness.
    assert no_de(grafo, 'WebSite')['dateModified'] == '2026-08-14T10:30:00'


def test_vibe_de_bar_vira_barorpub_e_o_resto_continua_restaurant(site_completo):
    for vibe, esperado in [('boteco', 'BarOrPub'), ('pub', 'BarOrPub'),
                           ('hamburgueria', 'Restaurant'), ('praia', 'Restaurant')]:
        site = dict(site_completo, vibe=vibe)
        grafo = dados_estruturados(None, site, [], [], [], URL)
        assert grafo['@graph'][0]['@type'] == esperado, vibe


def test_vibe_desconhecida_nao_inventa_cozinha(site_completo):
    """Vibe é escolha do dono. Sem ela não há de onde derivar servesCuisine."""
    grafo = dados_estruturados(None, dict(site_completo, vibe=None), [], [], [], URL)
    assert grafo['@graph'][0]['@type'] == 'Restaurant'
    assert 'servesCuisine' not in grafo['@graph'][0]


def test_cardapio_ausente_nao_promete_cardapio(site_completo):
    """`hasMenu` apontando pra seção que não existe manda o Google pra lugar nenhum."""
    grafo = dados_estruturados(None, site_completo, [], [], [], URL)
    assert 'hasMenu' not in grafo['@graph'][0]
    assert 'Menu' not in tipos(grafo)


# ------------------------------------------------------------ o bar sem dados

def test_bar_vazio_nao_emite_chave_vazia_nenhuma():
    """O caso que mais acontece: bar recém-cadastrado, só com o nome.

    Varre o grafo inteiro atrás de '', None e da string 'None' — o lixo que
    aparece quando alguém trata campo ausente como texto.
    """
    site = {chave: None for chave in (
        'nome', 'descritor', 'tagline', 'cidade_uf', 'endereco', 'horario',
        'telefone_exibicao', 'whatsapp', 'maps_query', 'instagram_url',
        'facebook_url', 'nota_google', 'qtd_avaliacoes', 'vibe', 'hero_foto',
        'servicos', 'data_atualizacao')}
    site['nome'] = 'Bar Recém-Nascido'

    grafo = dados_estruturados(None, site, [], [], [], 'https://feiradebarao.com.br/bar/novo')

    for caminho, valor in varrer(grafo):
        assert valor is not None, caminho
        assert valor != '', caminho
        assert valor != 'None', caminho

    casa = grafo['@graph'][0]
    for proibida in ('telephone', 'address', 'openingHours', 'sameAs', 'hasMap',
                     'aggregateRating', 'image', 'servesCuisine', 'priceRange',
                     'description', 'amenityFeature', 'hasMenu'):
        assert proibida not in casa, proibida
    assert 'dateModified' not in no_de(grafo, 'WebSite')


def test_string_none_no_banco_nao_vira_dado_estruturado():
    """Coluna que recebeu str(None) em algum caminho antigo não pode virar fato."""
    site = {'nome': 'Bar X', 'telefone_exibicao': 'None', 'endereco': '  ',
            'nota_google': 'None', 'tagline': ''}
    casa = dados_estruturados(None, site, [], [], [], URL)['@graph'][0]
    assert set(casa) == {'@type', '@id', 'name', 'url'}


def test_prato_sem_nome_nao_entra_no_cardapio(site_completo):
    grafo = dados_estruturados(
        None, site_completo,
        [{'nome': '', 'descricao': 'x'}, {'nome': 'Coxinha'}], [], [], URL)
    assert [i['name'] for i in no_de(grafo, 'Menu')['hasMenuItem']] == ['Coxinha']


def test_avaliacao_sem_autor_ou_texto_nao_vira_review(site_completo):
    reviews = [{'autor': 'Ana', 'texto': None, 'estrelas': 5},
               {'autor': None, 'texto': 'Ótimo', 'estrelas': 5},
               {'autor': 'João', 'texto': 'Ótimo', 'estrelas': None}]
    grafo = dados_estruturados(None, site_completo, [], reviews, [], URL)
    avaliacoes = [n for n in grafo['@graph'] if n['@type'] == 'Review']
    assert len(avaliacoes) == 1
    assert avaliacoes[0]['author']['name'] == 'João'
    assert 'reviewRating' not in avaliacoes[0]   # estrela ausente = chave ausente


# --------------------------------------------------------------- nota Google

@pytest.mark.parametrize('escrito, esperado', [
    ('4,7', 4.7), ('4.7', 4.7), ('5,0', 5.0), ('4', 4.0), (4.9, 4.9),
])
def test_nota_com_virgula_vira_float_com_ponto(escrito, esperado):
    site = {'nome': 'Bar X', 'nota_google': escrito, 'qtd_avaliacoes': 26}
    nota = dados_estruturados(None, site, [], [], [], URL)['@graph'][0]['aggregateRating']
    assert nota['ratingValue'] == esperado
    assert isinstance(nota['ratingValue'], float)
    assert nota['bestRating'] == 5
    assert nota['reviewCount'] == 26


def test_sem_nota_nao_existe_aggregate_rating():
    """Estrela no resultado do Google é o item mais cobiçado — e o mais
    perigoso de inventar."""
    site = {'nome': 'Bar X', 'qtd_avaliacoes': 26}
    assert 'aggregateRating' not in dados_estruturados(
        None, site, [], [], [], URL)['@graph'][0]


def test_nota_sem_quantidade_sai_sem_review_count():
    site = {'nome': 'Bar X', 'nota_google': '4,8'}
    nota = dados_estruturados(None, site, [], [], [], URL)['@graph'][0]['aggregateRating']
    assert 'reviewCount' not in nota


@pytest.mark.parametrize('lixo', ['', '  ', None, 'sem nota', '9,9', '0'])
def test_nota_impossivel_nao_vira_rating(lixo):
    site = {'nome': 'Bar X', 'nota_google': lixo, 'qtd_avaliacoes': 10}
    assert 'aggregateRating' not in dados_estruturados(
        None, site, [], [], [], URL)['@graph'][0]


# ------------------------------------------------------- eventos de exemplo

def test_evento_de_exemplo_nunca_entra_no_grafo(site_completo):
    """`vitrine.py` inventa agenda pra prévia comercial, com selo na tela.

    O Google não lê selo — lê `Event`. Publicar show que não vai acontecer é
    mentir em nome do bar, então a marca `exemplo=True` é barrada aqui.
    """
    real = Evento(titulo='Samba de verdade', data=date(2026, 9, 5), hora='20:00')
    eventos = eventos_de_exemplo('boteco') + [real]
    assert all(e.exemplo for e in eventos[:-1])   # o fixture ainda marca exemplo

    grafo = dados_estruturados(None, site_completo, [], [], eventos, URL)
    publicados = [n for n in grafo['@graph'] if n['@type'] == 'Event']

    assert [n['name'] for n in publicados] == ['Samba de verdade']
    assert 'Samba de roda' not in serializar(grafo)


def test_prévia_só_com_exemplos_nao_publica_evento_nenhum(site_completo):
    grafo = dados_estruturados(None, site_completo, [], [],
                               eventos_de_exemplo('pub'), URL)
    assert 'Event' not in tipos(grafo)


def test_evento_sem_hora_valida_fica_so_com_a_data(site_completo):
    """Hora fora de HH:MM ('20h', como escreve o exemplo) não vira horário chutado."""
    eventos = [Evento(titulo='Show', data=date(2026, 9, 5), hora='20h')]
    evento = no_de(dados_estruturados(None, site_completo, [], [], eventos, URL), 'Event')
    assert evento['startDate'] == '2026-09-05'


def test_evento_sem_data_nao_entra(site_completo):
    eventos = [Evento(titulo='Show sem data', data=None, hora='20:00')]
    assert 'Event' not in tipos(
        dados_estruturados(None, site_completo, [], [], eventos, URL))


# ------------------------------------------------------------------- horário

# Os nove horários que existem hoje em app/data/leads/*.yml, literais.
HORARIOS_REAIS = [
    ('Seg–Qui 11h–00h · Sex–Sáb 11h–01h · Dom 11h–00h',
     ['Mo-Th 11:00-00:00', 'Fr-Sa 11:00-01:00', 'Su 11:00-00:00']),
    ('Qua–Sex 17h–23h · Sáb e Dom 15h–00h',
     ['We-Fr 17:00-23:00', 'Sa,Su 15:00-00:00']),
    ('Qua–Sáb 18h–01h · Dom 18h–23h',
     ['We-Sa 18:00-01:00', 'Su 18:00-23:00']),
    ('Seg–Sex 16h–00h · Sáb 12h–00h · Dom 14h–00h',
     ['Mo-Fr 16:00-00:00', 'Sa 12:00-00:00', 'Su 14:00-00:00']),
    ('Ter, Qua e Sex 15h–00h · Qui 15h–22h · Sáb 11h–00h',
     ['Tu,We,Fr 15:00-00:00', 'Th 15:00-22:00', 'Sa 11:00-00:00']),
    ('Ter–Qui 17h–01h30 · Sex 17h–02h30 · Sáb 11h–02h30 · Dom 11h–01h30',
     ['Tu-Th 17:00-01:30', 'Fr 17:00-02:30', 'Sa 11:00-02:30', 'Su 11:00-01:30']),
    # Dois turnos no mesmo dia (almoço e jantar) viram duas faixas.
    ('Sex 11h30–14h e 18h–23h · Sáb 11h30–15h e 18h–00h · Dom 11h30–15h',
     ['Fr 11:30-14:00', 'Fr 18:00-23:00', 'Sa 11:30-15:00', 'Sa 18:00-00:00',
      'Su 11:30-15:00']),
    # Formato do EXEMPLO.yml.txt, que é o que o vendedor copia.
    ('Seg a sáb, 17h às 00h', ['Mo-Sa 17:00-00:00']),
]

# Estes dois também são reais — e não têm hora de fechar. Não dá pra converter
# sem inventar o fim do expediente, então não se converte.
HORARIOS_SEM_FIM = [
    'Qua, Qui, Sex e Dom a partir das 17h · Sáb a partir das 12h',
    'Qua–Sex a partir das 18h · Sáb e Dom a partir das 16h',
]


@pytest.mark.parametrize('texto, esperado', HORARIOS_REAIS)
def test_horario_real_de_lead_vira_opening_hours(texto, esperado):
    assert horario_schema(texto) == esperado


@pytest.mark.parametrize('texto', HORARIOS_SEM_FIM)
def test_horario_sem_hora_de_fechar_e_omitido(texto):
    assert horario_schema(texto) == []


def test_bloco_ilegivel_derruba_o_horario_inteiro():
    """Tudo ou nada. Publicar só a parte que parseou faria o Google anunciar
    'fechado' num dia em que o bar abre — e o cliente bate na porta trancada."""
    assert horario_schema('Seg–Qui 11h–00h · Sex quando der') == []


@pytest.mark.parametrize('texto', ['', '   ', None, 'consulte o Instagram'])
def test_horario_vazio_ou_sem_hora_nao_vira_nada(texto):
    assert horario_schema(texto) == []


def test_horario_aceita_variacoes_de_escrita():
    assert horario_schema('Todos os dias 11h–23h') == ['Mo-Su 11:00-23:00']
    assert horario_schema('Segunda-feira a sexta-feira 11h às 15h') == ['Mo-Fr 11:00-15:00']
    assert horario_schema('Sábado 12:00 - 23:00') == ['Sa 12:00-23:00']


def test_dia_escrito_por_extenso_nao_vira_intervalo_falso():
    """'sabado' contém um 'a' no meio: sem tratar dia inteiro primeiro, o parser
    leria 'sab' a 'do' e inventaria um intervalo."""
    assert horario_schema('Sábado 12h–23h') == ['Sa 12:00-23:00']


def test_hora_impossivel_nao_passa():
    assert horario_schema('Seg 25h–30h') == []


# ------------------------------------------------------------------ endereço

def test_endereco_completo_vira_postal_address_desmontado():
    endereco = endereco_schema(
        'Av. Santa Isabel, 57 - Barão Geraldo, Campinas - SP, 13084-012')
    assert endereco == {
        '@type': 'PostalAddress',
        'streetAddress': 'Av. Santa Isabel, 57 - Barão Geraldo',
        'addressLocality': 'Campinas',
        'addressRegion': 'SP',
        'addressCountry': 'BR',
        'postalCode': '13084-012',
    }


def test_endereco_sem_cep_parseia_o_resto_sem_inventar_cep():
    endereco = endereco_schema(
        'Avenida Santa Isabel, 462, em Barão Geraldo, Campinas (SP)')
    assert endereco['addressLocality'] == 'Campinas'
    assert endereco['addressRegion'] == 'SP'
    assert 'postalCode' not in endereco


@pytest.mark.parametrize('texto', [
    'Av. Prof. Atílio Martini, 940 — Barão Geraldo',
    'R. Ângelo Vicentim, 598 — Barão Geraldo',
    'R. Ana Maria de Souza, 26 — Barão Geraldo',
])
def test_endereco_so_com_bairro_vira_uma_linha_so(texto):
    """Bairro não é município. Chutar 'Campinas' aqui planta NAP errado, que é
    exatamente o que derruba ranking local."""
    assert endereco_schema(texto) == {'@type': 'PostalAddress',
                                      'streetAddress': texto}


def test_sigla_que_nao_e_uf_nao_vira_estado():
    texto = 'R. do Porto, 10 - Vila Nova, Centro - XX'
    assert endereco_schema(texto) == {'@type': 'PostalAddress',
                                      'streetAddress': texto}


@pytest.mark.parametrize('vazio', ['', '   ', None, 'None'])
def test_endereco_vazio_nao_vira_address(vazio):
    assert endereco_schema(vazio) is None


# ------------------------------------------------------------ meta descrição

def test_meta_de_bar_completo_cabe_na_faixa_do_google(site_completo):
    texto = meta_descricao(site_completo)
    assert 140 <= len(texto) <= 160, f'{len(texto)}: {texto}'
    assert texto.startswith('Estação Barão — Bar e restaurante desde 1953 em Barão.')
    assert 'a história do bairro passa por aqui' in texto
    assert 'Barão Geraldo, Campinas–SP' in texto     # intenção local
    assert 'None' not in texto


def test_prova_social_entra_quando_sobra_espaco():
    """A nota é o último a entrar de propósito: a estrela já aparece sozinha no
    resultado, vinda do AggregateRating. Aqui ela só ocupa o espaço que sobrou
    depois do que o Google não tem de outra fonte — quem é, e onde fica."""
    site = {'nome': 'Tatu Bola Bar', 'descritor': 'Boteco de esquina no Cambuí',
            'tagline': 'Mesa na calçada e chope gelado.',
            'cidade_uf': 'Cambuí, Campinas–SP',
            'nota_google': '4,8', 'qtd_avaliacoes': 312}
    texto = meta_descricao(site)
    assert 'Nota 4,8 no Google com 312 avaliações.' in texto
    assert len(texto) <= 160


def test_meta_nunca_passa_do_corte_do_google(site_completo):
    """Descrição cortada no meio da frase é pior que descrição curta."""
    esticado = dict(site_completo, tagline='x' * 400)
    assert len(meta_descricao(esticado)) <= 160


def test_meta_de_bar_sem_nada_e_none():
    assert meta_descricao({'nome': 'Bar Pelado'}) is None
    assert meta_descricao({}) is None
    assert meta_descricao(None) is None


def test_meta_cai_no_nome_do_restaurante_quando_o_site_nao_tem():
    class Rest:
        nome = 'Bar do Zé'
    assert meta_descricao({'descritor': 'Boteco em Barão'}, Rest()).startswith(
        'Bar do Zé — Boteco em Barão.')


def test_meta_nao_repete_a_cidade_que_ja_esta_no_descritor():
    site = {'nome': 'Tatu Bola', 'descritor': 'Bar de esquina no Cambuí',
            'cidade_uf': 'Cambuí'}
    assert meta_descricao(site).count('Cambuí') == 1


# ------------------------------------------------------------- serialização

def test_serializar_mantem_acento_e_neutraliza_fechamento_de_script():
    """Tagline é texto do dono do bar. Um '</script>' ali fecharia a tag e
    viraria XSS no site dele."""
    site = {'nome': 'Bar do Açaí', 'tagline': 'boa </script><script>alert(1)</script>'}
    texto = serializar(dados_estruturados(None, site, [], [], [], URL))

    assert 'Açaí' in texto            # ensure_ascii=False
    assert '</script>' not in texto
    assert '\\u003c' in texto


def test_serializar_gera_json_valido(site_completo, dishes, reviews):
    import json
    eventos = [Evento(titulo='Show', data=date(2026, 9, 5), hora='21:00')]
    grafo = dados_estruturados(None, site_completo, dishes, reviews, eventos, URL)
    assert json.loads(serializar(grafo)) == grafo


# --------------------------------------------------------------- imagens

def test_imagem_vira_url_absoluta_e_a_ausente_some(site_completo, dishes):
    imagens = dados_estruturados(
        None, site_completo, dishes, [], [], URL)['@graph'][0]['image']
    assert imagens == [
        'https://estacaobarao.bar/static/img/demo/estacao-barao/capa.jpg',
        'https://estacaobarao.bar/static/img/demo/estacao-barao/calabresa.jpg',
    ]


def test_url_de_imagem_ja_absoluta_passa_intacta(site_completo):
    site = dict(site_completo, hero_foto='https://blob.vercel-storage.com/capa.jpg')
    imagens = dados_estruturados(None, site, [], [], [], URL)['@graph'][0]['image']
    assert imagens == ['https://blob.vercel-storage.com/capa.jpg']


def test_bar_sem_foto_nao_empresta_a_capa_de_ninguem(site_completo):
    site = dict(site_completo, hero_foto=None)
    assert 'image' not in dados_estruturados(None, site, [], [], [], URL)['@graph'][0]


# ------------------------------------------------------------------ telefone

def test_whatsapp_vira_telefone_quando_nao_ha_numero_de_exibicao():
    site = {'nome': 'Bar X', 'whatsapp': '5519999779942'}
    assert dados_estruturados(
        None, site, [], [], [], URL)['@graph'][0]['telephone'] == '+5519999779942'


def test_whatsapp_sujo_nao_vira_telefone():
    """Coluna é 'só dígitos com DDI'. O que não for isso não vira E.164."""
    site = {'nome': 'Bar X', 'whatsapp': '(19) 99977-9942'}
    assert 'telephone' not in dados_estruturados(None, site, [], [], [], URL)['@graph'][0]


# ------------------------------------------- horário que só diz quando abre

def test_abertura_sem_fechamento_vira_specification():
    """Seis bares de Barão escrevem "a partir das 18h": a hora de fechar não é
    pública. Antes isso virava silêncio — o bar ficava sem horário nenhum no
    Google. `OpeningHoursSpecification` aceita `opens` sem `closes`."""
    spec = abertura_schema('Qua–Sex a partir das 18h · Sáb e Dom a partir das 16h')

    assert len(spec) == 2
    assert spec[0]['dayOfWeek'] == ['Wednesday', 'Thursday', 'Friday']
    assert spec[0]['opens'] == '18:00'
    assert 'closes' not in spec[0], 'hora de fechar nunca é estimada'
    assert spec[1]['dayOfWeek'] == ['Saturday', 'Sunday']
    assert spec[1]['opens'] == '16:00'


def test_abertura_com_meia_hora_e_todos_os_dias():
    spec = abertura_schema('Seg–Dom a partir das 16h30')

    assert len(spec) == 1
    assert len(spec[0]['dayOfWeek']) == 7
    assert spec[0]['opens'] == '16:30'


def test_intervalo_fechado_nao_vira_specification():
    """Quem tem hora de abrir E fechar é servido por `horario_schema`; emitir
    os dois seria dizer a mesma coisa duas vezes, em desacordo."""
    assert abertura_schema('Ter–Sáb 18h–01h') == []
    assert abertura_schema('Seg–Qui 11h30–15h e 18h–23h') == []


def test_horario_ilegivel_nao_vira_abertura():
    for lixo in ('', None, 'consulte nossas redes', 'todo dia até tarde'):
        assert abertura_schema(lixo) == []


def test_grafo_usa_specification_quando_so_ha_abertura():
    dados = dados_estruturados(
        None, {'nome': 'Bar X', 'horario': 'Qua–Sex a partir das 18h'},
        [], [], [], 'https://x.com.br/bar/x')
    lugar = next(n for n in dados['@graph']
                 if 'Bar' in str(n.get('@type')) or 'Restaurant' in str(n.get('@type')))

    assert 'openingHours' not in lugar
    assert lugar['openingHoursSpecification'][0]['opens'] == '18:00'
