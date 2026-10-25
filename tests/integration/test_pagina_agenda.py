"""/agenda: página, JSON-LD, sitemap, llms.txt e formulário de inscrição."""
import json
import re
from datetime import date, timedelta

from app.extensions import db
from app.models.modelo_evento import Evento
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig


def _bar(session, slug, cnpj, horario=None, demo=False):
    r = Restaurante(nome=f'Bar {slug}', cnpj=cnpj, slug=slug, subscription_tier='site',
                    tipo_negocio='bar')
    if demo:
        r.tipo_conta = 'demo'
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=r.nome, modelo='classico', horario=horario))
    session.commit()
    return r


def test_agenda_responde_e_mostra_a_feira_no_fim_de_semana(client, session):
    resp = client.get('/agenda')
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert 'O que abre hoje' in corpo and 'Próximos dias' in corpo
    assert 'None' not in corpo


def test_evento_cadastrado_pelo_bar_aparece_com_json_ld(client, session):
    r = _bar(session, 'bar-evento', '66666666000101')
    amanha = date.today() + timedelta(days=1)
    session.add(Evento(titulo='Roda de samba', data=amanha, hora='20:00', restaurant_id=r.id))
    session.add(Evento(titulo='Evento velho', data=date.today() - timedelta(days=2),
                       restaurant_id=r.id))
    session.add(Evento(titulo='Evento desligado', data=amanha, ativo=False, restaurant_id=r.id))
    session.commit()
    corpo = client.get('/agenda?v=1').get_data(as_text=True)
    assert 'Roda de samba' in corpo and 'Evento velho' not in corpo
    assert 'Evento desligado' not in corpo
    bruto = re.search(r'<script type="application/ld\+json">(.*?)</script>', corpo, re.S).group(1)
    nos = json.loads(bruto)['@graph']
    assert nos[0]['@type'] == 'Event' and nos[0]['startDate'].endswith('T20:00:00-03:00')


def test_previa_de_bar_nao_publica_evento(client, session):
    r = _bar(session, 'bar-previa', '66666666000102', demo=True)
    session.add(Evento(titulo='Evento de prévia', data=date.today() + timedelta(days=1),
                       restaurant_id=r.id))
    session.commit()
    assert 'Evento de prévia' not in client.get('/agenda?v=2').get_data(as_text=True)


def test_agenda_no_sitemap_e_no_llms(client, session):
    assert '/agenda' in client.get('/sitemap.xml').get_data(as_text=True)
    assert '/agenda' in client.get('/llms.txt').get_data(as_text=True)


def test_agenda_tem_formulario_da_feira_inteira(client, session):
    corpo = client.get('/agenda').get_data(as_text=True)
    assert 'name="fonte" value="agenda"' in corpo and 'name="perfil"' in corpo
    assert 'Receba a agenda da Feira de Barão' in corpo
