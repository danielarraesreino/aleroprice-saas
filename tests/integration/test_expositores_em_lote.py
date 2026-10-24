"""Escala: planilha do formulário -> lead .yml -> tenant artesão no ar.

Dados sintéticos (nenhuma resposta real entra nos testes).
"""
import csv

import pytest
import yaml

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import ProdutoSite
from app.scripts import importar_expositores as imp
from app.utils import demos

CABECALHO = ['Carimbo de data/hora', 'Nome do Expositor', 'Nome da Barraca', 'Dia de Atendimento',
             'Produtos - Liste os principais itens que você vende', 'Contato - Telefone',
             'Contato - WhatsApp', 'Breve Descritivo do que Faz', 'E-mail', 'Fotos', 'Instagram',
             'Facebook']


def _csv(tmp_path, *linhas):
    arq = tmp_path / 'respostas.csv'
    with open(arq, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(CABECALHO)
        w.writerows(linhas)
    return arq


LINHA_OK = ['21/10/2026 10:00', 'Maria da Silva', 'Ateliê da Maria', 'Sábado, Domingo',
            'Crochê, bolsas; cestos\nChaveiros, crochê', '(19) 3333-4444', '(19) 99999-1234',
            'Peças de crochê feitas à mão.', 'maria@exemplo.com', 'https://drive.google.com/x',
            '@ateliedamaria', 'facebook.com/ateliedamaria']


def test_cabecalho_truncado_do_forms_ainda_e_reconhecido():
    cols = imp.mapear_colunas(['Produtos - Liste os princ', 'Nome da Barraca', 'Contato - WhatsApp'])
    assert cols == {'produtos': 0, 'barraca': 1, 'whatsapp': 2}


@pytest.mark.parametrize('bruto,esperado', [
    ('(19) 99999-1234', '5519999991234'), ('19999991234', '5519999991234'),
    ('+55 19 99999-1234', '5519999991234'), ('1933334444', '551933334444'),
    ('12345', None), ('', None), (None, None)])
def test_whatsapp_so_digitos_com_ddi(bruto, esperado):
    assert imp.whatsapp_digitos(bruto) == esperado


def test_redes_e_horario_e_produtos():
    assert imp.url_instagram('@ateliedamaria') == 'https://www.instagram.com/ateliedamaria/'
    assert imp.url_instagram('https://instagram.com/x') == 'https://instagram.com/x'
    assert imp.url_instagram('nome com espaço!') is None
    assert imp.url_facebook('facebook.com/x') == 'https://facebook.com/x'
    assert imp.url_facebook('qualquer coisa') is None
    assert imp.horario_da_feira('Sábado, Domingo') == 'Sábados e domingos na Feira de Barão'
    assert imp.horario_da_feira('só domingo') == 'Domingos na Feira de Barão'
    assert imp.lista_de_produtos('Crochê, bolsas; cestos\nChaveiros, crochê') == [
        'Crochê', 'Bolsas', 'Cestos', 'Chaveiros']        # sem duplicata, na ordem


def test_importar_gera_yml_sem_dado_pessoal(tmp_path):
    saida = tmp_path / 'leads'
    r = imp.importar(_csv(tmp_path, LINHA_OK), destino=saida)
    assert r[0]['slug'] == 'atelie-da-maria' and r[0]['status'] == 'criado'
    texto = (saida / 'atelie-da-maria.yml').read_text(encoding='utf-8')
    assert 'maria@exemplo.com' not in texto and 'Maria da Silva' not in texto   # e-mail e pessoa ficam fora
    lead = yaml.safe_load(texto)
    assert lead['tipo_negocio'] == 'artesao'
    assert lead['site']['whatsapp'] == '5519999991234'
    assert lead['site']['vibe'] == 'artesanal'
    assert [p['nome'] for p in lead['produtos']] == ['Crochê', 'Bolsas', 'Cestos', 'Chaveiros']
    assert any('drive.google.com' in a for a in r[0]['avisos'])               # fotos viram tarefa


def test_dry_run_nao_grava_e_nao_sobrescreve_sem_force(tmp_path):
    saida = tmp_path / 'leads'
    arq = _csv(tmp_path, LINHA_OK)
    assert imp.importar(arq, dry_run=True, destino=saida)[0]['status'] == 'simulado'
    assert not saida.exists()
    imp.importar(arq, destino=saida)
    (saida / 'atelie-da-maria.yml').write_text('nome: editado à mão\n', encoding='utf-8')
    assert 'já existe' in imp.importar(arq, destino=saida)[0]['status']
    assert 'editado à mão' in (saida / 'atelie-da-maria.yml').read_text(encoding='utf-8')


def test_barracas_com_o_mesmo_nome_nao_se_sobrescrevem(tmp_path):
    outra = list(LINHA_OK)
    outra[1] = 'Outra Pessoa'
    r = imp.importar(_csv(tmp_path, LINHA_OK, outra), destino=tmp_path / 'leads')
    assert [x['slug'] for x in r] == ['atelie-da-maria', 'atelie-da-maria-2']


def test_linha_sem_nome_e_ignorada_e_planilha_sem_coluna_falha_claro(tmp_path):
    vazia = [''] * len(CABECALHO)
    assert imp.importar(_csv(tmp_path, vazia), destino=tmp_path / 'leads') == []
    arq = tmp_path / 'ruim.csv'
    arq.write_text('a,b\n1,2\n', encoding='utf-8')
    with pytest.raises(SystemExit):
        imp.importar(arq, destino=tmp_path / 'leads')


# ------------------------------------------------------------ pipeline

def test_lead_de_artesao_vira_tenant_com_produtos_e_vibe(session, tmp_path):
    saida = tmp_path / 'leads'
    imp.importar(_csv(tmp_path, LINHA_OK), destino=saida)
    rest, log = demos.aplicar_lead(str(saida / 'atelie-da-maria.yml'))
    session.commit()
    assert rest.tipo_negocio == 'artesao' and rest.tipo_conta == 'demo'
    assert rest.site_config.vibe == 'artesanal'
    assert {p.nome for p in ProdutoSite.query.filter_by(restaurant_id=rest.id)} == {
        'Crochê', 'Bolsas', 'Cestos', 'Chaveiros'}


def test_lead_com_tipo_invalido_falha_alto(session, tmp_path):
    arq = tmp_path / 'x.yml'
    arq.write_text('nome: X\ntipo_negocio: padaria\n', encoding='utf-8')
    with pytest.raises(demos.LeadInvalido, match='tipo_negocio'):
        demos.aplicar_lead(str(arq))


def test_fotos_da_pasta_viram_logo_e_produtos(session, tmp_path, monkeypatch):
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path / 'fotos'))
    pasta = tmp_path / 'fotos' / 'banca-foto'
    pasta.mkdir(parents=True)
    for nome in ('capa.jpg', 'logo.jpg', 'produto-bolsa-de-croche.jpg'):
        (pasta / nome).write_bytes(b'\xff\xd8\xff')
    arq = tmp_path / 'banca-foto.yml'
    arq.write_text('nome: Banca Foto\ntipo_negocio: artesao\n', encoding='utf-8')
    rest, _ = demos.aplicar_lead(str(arq))
    session.commit()
    assert rest.site_config.logo == 'img/demo/banca-foto/logo.jpg'
    assert rest.site_config.hero_foto == 'img/demo/banca-foto/capa.jpg'
    p = ProdutoSite.query.filter_by(restaurant_id=rest.id).one()
    assert p.nome == 'Bolsa de croche' and p.imagem.endswith('produto-bolsa-de-croche.jpg')


def test_bar_continua_igual_no_pipeline(session, tmp_path):
    arq = tmp_path / 'bar-x.yml'
    arq.write_text('nome: Bar X\n', encoding='utf-8')
    rest, _ = demos.aplicar_lead(str(arq))
    session.commit()
    assert rest.tipo_negocio == 'bar'
    assert ProdutoSite.query.filter_by(restaurant_id=rest.id).count() == 0


def test_do_formulario_ao_site_no_ar(client, session, tmp_path):
    """A jornada inteira: planilha -> yml -> tenant -> /bar/<slug> e /feira."""
    saida = tmp_path / 'leads'
    imp.importar(_csv(tmp_path, LINHA_OK), destino=saida)
    rest, _ = demos.aplicar_lead(str(saida / 'atelie-da-maria.yml'))
    session.commit()
    pagina = client.get(f'/bar/{rest.slug}').get_data(as_text=True)
    assert 'Ateliê da Maria' in pagina and 'wa.me/5519999991234' in pagina
    assert 'Catálogo em montagem' not in pagina        # sem foto nenhuma, o que faz aparece em texto
    assert 'sem-foto' in pagina
    assert 'content="index,follow"' in pagina and 'noindex' not in pagina   # prévia de artesão é indexável
    assert 'faixa-previa' in pagina                    # mas segue declarada como prévia
    assert 'Ateliê da Maria' in client.get('/feira').get_data(as_text=True)
