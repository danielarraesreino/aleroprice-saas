"""Textos do site do expositor: editáveis no painel e neutros por padrão.

Caso real (2/11): o Viaverde (madeira) mostrava "Ingrediente de verdade — Sem
atalho e sem aditivo" e "Feito em pequena escala, com ingrediente de verdade",
textos da Berga (comida) que o expositor não escreveu e não podia editar.
"""
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.models.usuario import Usuario
from app.utils.copy_site import opcoes_de_vibe


def _expositor(session, slug, **cfg):
    r = Restaurante(nome='Viaverde', slug=slug, subscription_tier='site',
                    subscription_status='active', tipo_negocio='artesao')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Viaverde', whatsapp='5519992359917', **cfg))
    session.add(ProdutoSite(restaurant_id=r.id, nome='Tábua', imagem='img/x.jpg', ativo=True))
    session.add(Usuario(nome='Dona', email=f'dona@{slug}.com', senha='senha-bem-longa',
                        tipo='admin', restaurant_id=r.id))
    session.commit()
    return r


def test_vibe_neutra_nao_fala_de_ingrediente(client, session):
    _expositor(session, 'madeira-neutra', vibe='artesanal-feira')
    html = client.get('/expositor/madeira-neutra').get_data(as_text=True)
    for frase in ('Ingrediente de verdade', 'sem aditivo', 'com ingrediente', 'Quer provar', 'QUEM PROVOU'):
        assert frase not in html
    assert 'Nossos <em>produtos</em>' in html


def test_dono_escreve_titulo_frase_e_destaques(client, session):
    _expositor(session, 'madeira-propria', vibe='artesanal-feira',
               secao_titulo='Peças em madeira', secao_lead='Feitas na minha oficina.',
               pilares='Feito à mão | Cada peça passa pelas minhas mãos\nMadeira certificada\n | sem titulo')
    html = client.get('/expositor/madeira-propria').get_data(as_text=True)
    assert 'Peças em madeira' in html and 'Feitas na minha oficina.' in html
    assert '<strong>Feito à mão</strong><span>Cada peça passa pelas minhas mãos</span>' in html
    assert '<strong>Madeira certificada</strong>' in html      # destaque sem frase também vale
    assert 'sem titulo' not in html                            # linha sem título é ignorada


def test_texto_do_dono_nao_injeta_html(client, session):
    _expositor(session, 'madeira-xss', vibe='artesanal-feira', secao_titulo='<script>alert(1)</script>')
    html = client.get('/expositor/madeira-xss').get_data(as_text=True)
    assert '<script>alert(1)</script>' not in html


def test_painel_do_expositor_edita_e_limita(client, session):
    r = _expositor(session, 'madeira-painel', vibe='artesanal-feira')
    with client.session_transaction() as s:
        s['_user_id'] = str(Usuario.query.filter_by(restaurant_id=r.id).one().id)
    html = client.get('/config-site/').get_data(as_text=True)
    assert 'Textos do seu site' in html and 'name="pilares"' in html
    client.post('/config-site/', data={'nome': 'Viaverde', 'secao_titulo': 'Peças ' * 40,
                                       'pilares': 'A | b\n' * 200})
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).one()
    assert len(cfg.secao_titulo) <= 120 and len(cfg.pilares) <= 600


def test_vibes_por_tipo():
    artesao = {v['valor'] for v in opcoes_de_vibe('artesao')}
    assert artesao == {'artesanal-feira'}
    assert 'artesanal' in {v['valor'] for v in opcoes_de_vibe('artesao', 'artesanal')}
    bar = {v['valor'] for v in opcoes_de_vibe('bar')}
    assert 'boteco' in bar and not bar & {'artesanal', 'artesanal-feira'}


def test_expositor_que_se_cadastra_nasce_com_vibe_neutra(client, session):
    client.post('/cadastro', data={'nome_bar': 'Madeiras do Zé', 'nome': 'Zé', 'tipo': 'artesao',
                                   'email': 'ze@madeira.com', 'senha': 'segredo123'})
    r = Restaurante.query.filter_by(nome='Madeiras do Zé').one()
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).one()
    assert cfg.vibe == 'artesanal-feira' and cfg.modelo != 'classico'
