"""Fotos recebidas dos expositores: só com autorização e só em tamanho de produção."""
import yaml
from PIL import Image

from app.scripts import receber_fotos as rf


def _img(caminho, w, h, cor=(200, 90, 40)):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (w, h), cor).save(caminho, 'JPEG')


def _lead(dir_leads, slug='fermentei'):
    dir_leads.mkdir(parents=True, exist_ok=True)
    (dir_leads / f'{slug}.yml').write_text(yaml.safe_dump(
        {'nome': 'Fermentei', 'tipo_negocio': 'artesao',
         'produtos': [{'nome': 'Pães de fermentação natural'}, {'nome': 'Panetone'}]},
        allow_unicode=True), encoding='utf-8')


def test_sem_autorizacao_a_pasta_e_ignorada(tmp_path):
    _img(tmp_path / 'in' / 'fermentei' / 'capa.jpg', 2000, 1500)
    r = rf.receber(tmp_path / 'in', destino_fotos=tmp_path / 'out', dir_leads=tmp_path / 'l')[0]
    assert 'AUTORIZADO' in r['status'] and not (tmp_path / 'out').exists()


def test_autorizacao_vazia_tambem_nao_vale(tmp_path):
    _img(tmp_path / 'in' / 'x' / 'capa.jpg', 2000, 1500)
    (tmp_path / 'in' / 'x' / 'AUTORIZADO.txt').write_text('  \n')
    assert 'AUTORIZADO' in rf.receber(tmp_path / 'in', destino_fotos=tmp_path / 'o', dir_leads=tmp_path / 'l')[0]['status']


def test_foto_pequena_e_recusada_e_grande_e_otimizada(tmp_path):
    pasta = tmp_path / 'in' / 'fermentei'
    (pasta).mkdir(parents=True)
    (pasta / 'AUTORIZADO.txt').write_text('Autorizado por Fulana no WhatsApp em 21/10')
    _img(pasta / 'capa.jpg', 4000, 3000)
    _img(pasta / 'outra.jpg', 230, 310)                  # captura de tela do Instagram
    r = rf.receber(tmp_path / 'in', destino_fotos=tmp_path / 'out', dir_leads=tmp_path / 'l')[0]
    assert any('pequena' in x for x in r['recusados'])
    capa = Image.open(tmp_path / 'out' / 'fermentei' / 'capa.jpg')
    assert max(capa.size) == 1600
    assert not (tmp_path / 'out' / 'fermentei' / 'galeria-01.jpg').exists()


def test_logo_vira_quadrado_512(tmp_path):
    pasta = tmp_path / 'in' / 'x'
    pasta.mkdir(parents=True)
    (pasta / 'AUTORIZADO.txt').write_text('ok, por WhatsApp')
    _img(pasta / 'logo.jpg', 900, 600)
    rf.receber(tmp_path / 'in', destino_fotos=tmp_path / 'out', dir_leads=tmp_path / 'l')
    assert Image.open(tmp_path / 'out' / 'x' / 'logo.jpg').size == (512, 512)


def test_produto_casa_com_o_do_yml_e_sem_par_vira_novo(tmp_path):
    pasta = tmp_path / 'in' / 'fermentei'
    pasta.mkdir(parents=True)
    (pasta / 'AUTORIZADO.txt').write_text('ok, por WhatsApp')
    _img(pasta / 'produto-panetone.jpg', 1200, 1200)
    _img(pasta / 'produto-focaccia.jpg', 1200, 1200)
    _lead(tmp_path / 'leads')
    rf.receber(tmp_path / 'in', destino_fotos=tmp_path / 'out', dir_leads=tmp_path / 'leads')
    lead = yaml.safe_load((tmp_path / 'leads' / 'fermentei.yml').read_text(encoding='utf-8'))
    por_nome = {p['nome']: p for p in lead['produtos']}
    assert por_nome['Panetone']['imagem'] == 'img/demo/fermentei/produto-panetone.jpg'
    assert 'Focaccia' in por_nome and por_nome['Focaccia']['imagem'].endswith('produto-focaccia.jpg')
    assert 'imagem' not in por_nome['Pães de fermentação natural']


def test_dry_run_nao_grava_nada(tmp_path):
    pasta = tmp_path / 'in' / 'fermentei'
    pasta.mkdir(parents=True)
    (pasta / 'AUTORIZADO.txt').write_text('ok, por WhatsApp')
    _img(pasta / 'capa.jpg', 2000, 1500)
    _lead(tmp_path / 'leads')
    antes = (tmp_path / 'leads' / 'fermentei.yml').read_text(encoding='utf-8')
    r = rf.receber(tmp_path / 'in', dry_run=True, destino_fotos=tmp_path / 'out', dir_leads=tmp_path / 'leads')[0]
    assert r['feitos'] and not (tmp_path / 'out').exists()
    assert (tmp_path / 'leads' / 'fermentei.yml').read_text(encoding='utf-8') == antes
