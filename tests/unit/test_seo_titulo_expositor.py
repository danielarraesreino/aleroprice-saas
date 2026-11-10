"""Título e descrição do hotsite de expositor: produto + bairro, sem inventar."""
from app.utils import seo


def _site(**campos):
    return {'nome': 'Barro Bom', 'ponto_na_feira': 'Praça do Coco', **campos}


def test_titulo_ganha_bairro_e_feira_quando_cabe():
    assert (seo.titulo_do_expositor(_site(descritor='Cerâmica'))
            == 'Barro Bom — Cerâmica em Barão Geraldo | Feira de Barão')


def test_titulo_longo_fica_com_o_bairro_e_perde_o_sufixo():
    titulo = seo.titulo_do_expositor(_site(nome='Lili Jolie Arte em Cerâmica',
                                           descritor='Cerâmica (colares e brincos)'))
    assert titulo == 'Lili Jolie Arte em Cerâmica — Cerâmica (colares e brincos) em Barão Geraldo'


def test_titulo_nao_repete_o_bairro_nem_a_feira():
    titulo = seo.titulo_do_expositor(_site(descritor='Pães de Barão Geraldo'))
    assert titulo.count('Barão Geraldo') == 1
    assert seo.titulo_do_expositor(_site(nome='Pão da Feira de Barão')).count('Feira de Barão') == 1


def test_titulo_ganha_bairro_mesmo_sem_ponto_na_feira():
    assert (seo.titulo_do_expositor({'nome': 'Barro Bom', 'descritor': 'Cerâmica'})
            == 'Barro Bom — Cerâmica em Barão Geraldo | Feira de Barão')
    assert seo.titulo_do_expositor({'descritor': 'Cerâmica'}) is None      # sem nome não há título


def test_descricao_do_expositor_diz_onde_antes_da_tagline():
    rest = {'tipo_negocio': 'artesao'}
    texto = seo.meta_descricao(_site(descritor='Cerâmica', tagline='Feito à mão. Peças leves.'), rest)
    assert texto == ('Barro Bom — Cerâmica. Na Feira de Barão, em Barão Geraldo (Campinas). '
                     'Feito à mão. Peças leves.')
    assert len(texto) <= seo.TAMANHO_META_MAX
    # Sem `ponto_na_feira` o lugar entra do mesmo jeito; em bar, não.
    sem_ponto = {'nome': 'Barro Bom', 'descritor': 'Cerâmica', 'tagline': 'Feito à mão.'}
    assert 'em Barão Geraldo (Campinas)' in seo.meta_descricao(sem_ponto, rest)
    assert 'Feira de Barão' not in seo.meta_descricao(sem_ponto, {'tipo_negocio': 'bar'})


def test_grafo_do_expositor_leva_o_que_vende_e_o_evento_da_feira():
    rest = {'tipo_negocio': 'artesao'}
    grafo = seo.dados_estruturados(
        rest, _site(), [], [], [], 'https://feiradebarao.com.br/expositor/barro-bom',
        produtos=[{'nome': 'Vaso', 'categoria': 'Cerâmica'}, {'nome': 'Prato', 'categoria': 'Cerâmica'}])
    loja = grafo['@graph'][0]
    assert loja['keywords'] == 'Cerâmica'
    assert loja['event']['@id'].endswith('/#feira')
