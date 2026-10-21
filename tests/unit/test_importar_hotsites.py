"""Pacote de hotsites (expositores.json) -> leads."""
import json

import yaml

from app.scripts import importar_hotsites as ih


def _e(**kw):
    base = {'slug': 'x', 'nome': 'Ateliê X', 'cat': 'Crochê e amigurumi', 'bio': 'Feito à mão.',
            'vende': ['Amigurumis (bichinhos, bonecas)', 'Tricô'], 'whatsapp': '5519999991234',
            'instagram_url': 'https://instagram.com/x', 'dias': 'Sábado e domingo', 'fotos': ['a.jpg']}
    base.update(kw)
    return base


def test_converte_modelo_pela_categoria_vibe_neutra_e_produto_com_descricao():
    slug, lead, avisos = ih.converter(_e())
    assert slug == 'x' and lead['tipo_negocio'] == 'artesao'
    assert lead['site']['modelo'] == 'atelie' and lead['site']['vibe'] == 'artesanal-feira'
    assert lead['produtos'][0] == {'nome': 'Amigurumis', 'descricao': 'Bichinhos, bonecas'}
    assert lead['site']['whatsapp'] == '5519999991234'
    assert lead['site']['horario'] == 'Sábados e domingos na Feira de Barão'
    assert lead['demo']['expira_em']                       # prévia expira se ninguém converter


def test_fotos_do_pacote_nao_entram_e_isso_e_avisado():
    _, lead, avisos = ih.converter(_e())
    assert 'imagem' not in json.dumps(lead) and 'foto' not in json.dumps(lead['site'])
    assert any('NÃO usadas' in a for a in avisos)


def test_sem_whatsapp_avisa_e_nao_inventa():
    _, lead, avisos = ih.converter(_e(whatsapp=''))
    assert 'whatsapp' not in lead['site'] and any('Instagram' in a for a in avisos)


def test_dois_numeros_no_pacote_omite_o_whatsapp_ate_validar():
    _, lead, avisos = ih.converter(_e(obs='ATENÇÃO: bio diz 19 1; Linktree diz 19 2. Validar qual é o certo.'))
    assert 'whatsapp' not in lead['site'] and any('OMITIDO' in a for a in avisos)


def test_nao_vaza_email_nem_pessoa_e_pula_quem_ja_tem_site(tmp_path):
    arq = tmp_path / 'p.json'
    arq.write_text(json.dumps([_e(obs='Dona: perfil pessoal @fulana'), _e(slug='dona-berga', nome='Dona Berga')]),
                   encoding='utf-8')
    res = ih.importar(arq, destino=tmp_path / 'leads')
    assert [r['status'] for r in res] == ['criado', 'pulado (já tem site)']
    texto = (tmp_path / 'leads' / 'x.yml').read_text(encoding='utf-8')
    assert 'fulana' not in texto and '@' not in yaml.safe_load(texto)['nome']
    assert not (tmp_path / 'leads' / 'dona-berga.yml').exists()


def test_nao_sobrescreve_sem_force(tmp_path):
    arq = tmp_path / 'p.json'
    arq.write_text(json.dumps([_e()]), encoding='utf-8')
    ih.importar(arq, destino=tmp_path / 'l')
    assert ih.importar(arq, destino=tmp_path / 'l')[0]['status'].startswith('já existe')
    assert ih.importar(arq, destino=tmp_path / 'l', force=True)[0]['status'] == 'criado'
