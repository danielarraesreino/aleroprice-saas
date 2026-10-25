"""Agenda de Barão: o que abre hoje e os eventos. Nada de dado velho nem inventado."""
from datetime import date, datetime

import pytest

from app.utils import agenda as ag

FUSO = ag.FUSO
SABADO = datetime(2026, 10, 31, 11, 0, tzinfo=FUSO)       # 31/10/2026 é sábado
TERCA = datetime(2026, 10, 27, 11, 0, tzinfo=FUSO)
HOJE = date(2026, 10, 27)


def test_evento_passado_some_e_campo_vazio_nao_vira_none():
    assert ag.evento('Samba', date(2026, 10, 26), HOJE) is None
    ev = ag.evento('Samba', '2026-10-28', HOJE, hora=None, local=None, link='None')
    assert ev['local'] == '' and ev['hora'] == '' and ev['link'] == ''
    assert ev['rotulo'] == 'Amanhã'
    assert all(v != 'None' for v in ev.values() if isinstance(v, str))


def test_evento_sem_titulo_ou_com_data_invalida_e_descartado():
    assert ag.evento('', '2026-10-28', HOJE) is None
    assert ag.evento('Samba', 'amanhã', HOJE) is None
    assert ag.evento('Samba', '2026-10-28', HOJE, tipo='qualquer')['tipo'] == 'cultura'


def test_link_so_http_ou_relativo():
    assert ag.evento('A', '2026-10-28', HOJE, link='javascript:alert(1)')['link'] == ''
    assert ag.evento('A', '2026-10-28', HOJE, link='https://x.com')['link'] == 'https://x.com'


def test_arquivo_sem_verificado_em_nao_entra(tmp_path):
    (tmp_path / '2026-10.yml').write_text(
        'eventos:\n'
        '  - {titulo: Com conferência, data: 2026-10-28, verificado_em: 2026-10-25}\n'
        '  - {titulo: Sem conferência, data: 2026-10-28}\n'
        '  - {titulo: Passado, data: 2026-10-01, verificado_em: 2026-10-25}\n'
        '  - texto solto\n', encoding='utf-8')
    (tmp_path / 'quebrado.yml').write_text('eventos: [\n', encoding='utf-8')
    titulos = [e['titulo'] for e in ag.eventos_do_arquivo(HOJE, pasta=str(tmp_path))]
    assert titulos == ['Com conferência']


def test_proximos_ordena_e_corta_pela_janela():
    painel = [('Show', date(2026, 10, 29), '21:00', 'Bar A', 'https://a.bar'),
              ('Longe', date(2026, 12, 1), '', 'Bar A', 'https://a.bar'),
              ('Cedo', date(2026, 10, 29), '18:00', 'Bar B', 'https://b.bar')]
    lista = ag.proximos(HOJE, do_painel=painel, do_arquivo=[])
    assert [e['titulo'] for e in lista] == ['Cedo', 'Show']


@pytest.mark.parametrize('hora,esperado', [
    (9, 'abre'), (10, 'aberto'), (15, 'aberto'), (16, 'encerrado')])
def test_feira_no_sabado(hora, esperado):
    agora = SABADO.replace(hour=hora, minute=30 if hora == 15 else 0)
    feira = ag.abre_hoje(agora)[0]
    assert feira['nome'] == 'Feira de Barão' and feira['estado'] == esperado


def test_feira_nao_aparece_na_terca():
    assert ag.abre_hoje(TERCA) == []


def test_bar_com_horario_lido_entra_e_ilegivel_fica_de_fora():
    bares = [{'nome': 'Bar Lido', 'url': '/bar/lido', 'horario': 'Seg–Sáb 11h–23h'},
             {'nome': 'Bar Confuso', 'url': '/bar/confuso', 'horario': 'quando dá'},
             {'nome': 'Bar Vazio', 'url': '/bar/vazio', 'horario': None}]
    nomes = [b['nome'] for b in ag.abre_hoje(TERCA, bares)]
    assert nomes == ['Bar Lido']
    lido = ag.abre_hoje(TERCA, bares)[0]
    assert lido['estado'] == 'aberto' and lido['texto'] == 'aberto até 23h'


def test_horario_que_passa_da_meia_noite():
    espec = [{'dayOfWeek': ['Tuesday'], 'opens': '18:00', 'closes': '01:00'}]
    assert ag.status_do_dia(espec, TERCA.replace(hour=23))[0] == 'aberto'
    assert ag.status_do_dia(espec, TERCA.replace(hour=17))[0] == 'abre'


def test_so_abertura_nao_inventa_fechamento():
    estado, texto = ag.status_do_dia(
        [{'dayOfWeek': ['Tuesday'], 'opens': '18:00'}], TERCA.replace(hour=20))
    assert (estado, texto) == ('aberto', 'aberto agora')


def test_json_ld_so_com_o_que_existe():
    ev = ag.evento('Samba', '2026-10-28', HOJE, hora='20:00', local='Bar A', link='/bar/a')
    no = ag.json_ld([ev], 'https://feiradebarao.com.br')[0]
    assert no['startDate'] == '2026-10-28T20:00:00-03:00'
    assert no['url'] == 'https://feiradebarao.com.br/bar/a'
    assert 'offers' not in no
    sem_local = ag.json_ld([ag.evento('X', '2026-10-28', HOJE)], 'https://x')[0]
    assert 'location' not in sem_local and sem_local['startDate'] == '2026-10-28'
