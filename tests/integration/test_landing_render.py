"""A landing serve dois casos opostos e não pode quebrar nenhum.

1. **Vitrine.** O Bar da Vila está no ar e é o caso de venda. Despersonalizar o
   template (tirar "croquete da Bruna", "4,9★ / 39 avaliações", "samba" de
   dentro do HTML) não pode mudar o site dele — os textos viraram a vibe
   `boteco` e os dados viraram campos do próprio bar.

2. **Bar recém-criado.** Sem conteúdo nenhum, o site não pode exibir título de
   seção com corpo vazio, nem herdar identidade de ninguém.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem


@pytest.fixture
def vitrine(session):
    """Bar da Vila como está em produção."""
    r = Restaurante(nome='Bar da Vila', slug='bar-da-vila', dominio='bardavila.bar')
    session.add(r)
    session.commit()
    session.add(SiteConfig(
        restaurant_id=r.id, nome='Bar da Vila',
        hero_linha1='Bar da', hero_linha2='Vila',
        tagline='Buteco de família de verdade — comida de vó, cerveja gelada e samba.',
        subline='COSTELINHA · CROQUETE DA BRUNA · SAMBA AO VIVO',
        selo_estrelas='4,9 no Google · 39 avaliações',
        whatsapp='5519999779942', tema='boteco-ambar', vibe='boteco',
        descritor='Buteco de família em Campinas',
        nota_google='4,9', qtd_avaliacoes=39,
        servicos='Refeição no local · Drive-through',
        hero_foto='img/bar/foto-18.jpg',
    ))
    session.add(DishCard(restaurant_id=r.id, nome='Croquete da Bruna',
                         descricao='O xodó do bar.', imagem='img/bar/foto-5.jpg',
                         tag='★ O MAIS PEDIDO', destaque=True, ordem=0, ativo=True))
    session.add(Review(restaurant_id=r.id, autor='Rony Nunes',
                       texto='Autêntico bar raiz.', estrelas=5, ordem=0, ativo=True))
    session.add(TeamMember(restaurant_id=r.id, nome='Bruna',
                           papel='Cozinheira e anfitriã', emoji='👩‍🍳', ordem=0, ativo=True))
    session.add(GalleryItem(restaurant_id=r.id, imagem='img/bar/foto-3.jpg',
                            ordem=0, ativo=True))
    session.commit()
    return r


def test_vitrine_mantem_o_texto_original(client, vitrine):
    corpo = client.get('/bar/bar-da-vila').get_data(as_text=True)

    # Identidade e dados do bar
    for trecho in ('Bar da Vila', 'Buteco de família em Campinas',
                   'Croquete da Bruna', '5519999779942',
                   'Refeição no local · Drive-through'):
        assert trecho in corpo, f'sumiu da vitrine: {trecho}'

    # Nota real, que antes era 4,9/39 fixo no HTML
    assert '4,9' in corpo
    assert '39 AVALIAÇÕES' in corpo

    # Títulos que agora vêm da vibe `boteco` — devem ser os mesmos de antes
    for trecho in ('O QUE SAI DA COZINHA', 'Comida de <em>buteco</em>, feita com amor',
                   'A FAMÍLIA', 'QUEM VEM, VOLTA', 'O CLIMA DA CASA',
                   'Samba ao vivo', 'Cerveja gelada'):
        assert trecho in corpo, f'a vibe boteco perdeu: {trecho}'


def test_vitrine_nao_e_marcada_como_previa(client, vitrine):
    corpo = client.get('/bar/bar-da-vila').get_data(as_text=True)
    assert 'Prévia não oficial' not in corpo
    assert 'noindex' not in corpo


def test_bar_vazio_nao_mostra_secao_orfa(client, session):
    """Título de seção sem conteúdo embaixo é o que denuncia site inacabado."""
    r = Restaurante(nome='Bar Novo', slug='bar-novo')
    session.add(r)
    session.commit()

    resp = client.get('/bar/bar-novo')
    corpo = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert 'Bar Novo' in corpo
    for titulo in ('O QUE SAI DA COZINHA', 'QUEM VEM, VOLTA', 'A FAMÍLIA', 'DÁ UMA OLHADA'):
        assert titulo not in corpo, f'seção vazia renderizou: {titulo}'


def test_bar_vazio_nao_herda_nota_de_ninguem(client, session, vitrine):
    """O 4,9/39 do Bar da Vila não pode aparecer no site de outro bar."""
    r = Restaurante(nome='Bar Novo', slug='bar-novo')
    session.add(r)
    session.commit()

    corpo = client.get('/bar/bar-novo').get_data(as_text=True)

    assert '39 AVALIAÇÕES' not in corpo
    assert 'Croquete da Bruna' not in corpo
    assert '5519999779942' not in corpo


def test_vibe_troca_o_tom_do_site(client, session):
    """Uma hamburgueria não pode receber um site falando de samba."""
    r = Restaurante(nome='Smash Vinhedo', slug='smash-vinhedo')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Smash Vinhedo',
                           vibe='hamburgueria', tema='neon-noite'))
    session.add(DishCard(restaurant_id=r.id, nome='Smash duplo',
                         ordem=0, ativo=True))
    session.commit()

    corpo = client.get('/bar/smash-vinhedo').get_data(as_text=True)

    assert 'O QUE SAI DA CHAPA' in corpo
    assert 'Samba ao vivo' not in corpo
    assert 'O QUE SAI DA COZINHA' not in corpo


def test_vibe_cobre_os_ultimos_textos_que_eram_fixos(client, session):
    """Promoções, agenda, CTA e reserva eram hardcoded com texto de boteco.

    "A cerveja tá gelando" no site de uma hamburgueria denuncia template.
    Plano 'site' + promoção + evento pra renderizar os quatro blocos de uma vez.
    """
    from datetime import date, timedelta
    from app.models.modelo_evento import Evento
    from app.models.modelo_promocao import Promocao

    r = Restaurante(nome='Chapa Quente', slug='chapa-quente',
                    subscription_tier='site', subscription_status='active')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Chapa Quente',
                           vibe='hamburgueria', tema='neon-noite'))
    session.add(Promocao(restaurant_id=r.id, titulo='Dobro de cheddar', ativo=True))
    session.add(Evento(restaurant_id=r.id, titulo='Noite do smash',
                       data=date.today() + timedelta(days=3), ativo=True))
    session.commit()

    corpo = client.get('/bar/chapa-quente').get_data(as_text=True)

    # Nada de boteco vazando nos blocos que eram fixos
    for trecho in ('A cerveja tá gelando', 'Promoções da casa',
                   'Promoções da <em>casa</em>', 'TÁ ROLANDO AGORA',
                   'MARCA NA AGENDA', 'Marque na agenda',
                   'Bateu a fome?', 'Reservar mesa 🍺', 'Avisar o bar no WhatsApp'):
        assert trecho not in corpo, f'texto de boteco vazou na hamburgueria: {trecho}'

    # E a copy da hamburgueria assume os quatro blocos
    for trecho in ('SAINDO DA CHAPA', 'Promoções do <em>dia</em>',      # promoções
                   'SE PROGRAMA', 'O que vem <em>por aí</em>',          # agenda
                   'Bateu a larica?', 'A chapa tá quente.',             # cta de contato
                   'Reservar mesa 🍔',                                  # form de reserva
                   'Avisar a hamburgueria no WhatsApp'):
        assert trecho in corpo, f'faltou a copy da hamburgueria: {trecho}'


def _links_quebrados(corpo):
    """Âncoras do menu que não têm seção correspondente na página."""
    import re
    ancoras = set(re.findall(r'href="#([a-z]+)"', corpo))
    secoes = set(re.findall(r'<section class="sec" id="([^"]+)"', corpo))
    secoes.add('topo')            # o header usa id="topo"
    return sorted(ancoras - secoes)


def test_menu_nao_aponta_pra_secao_inexistente(client, session):
    """Bar sem conteúdo: o menu não pode listar Cardápio/Galeria se elas sumiram.

    Clicar num link que não vai a lugar nenhum faz o site parecer travado —
    foi exatamente o que aconteceu com as prévias da campanha, que nascem
    sem cardápio e sem foto.
    """
    r = Restaurante(nome='Bar Vazio', slug='bar-vazio')
    session.add(r)
    session.commit()

    corpo = client.get('/bar/bar-vazio').get_data(as_text=True)

    assert _links_quebrados(corpo) == []


def test_menu_completo_quando_ha_conteudo(client, vitrine):
    corpo = client.get('/bar/bar-da-vila').get_data(as_text=True)

    assert _links_quebrados(corpo) == []
    for ancora in ('#cardapio', '#avaliacoes', '#galeria', '#contato'):
        assert ancora in corpo, f'menu perdeu {ancora} mesmo tendo conteúdo'
