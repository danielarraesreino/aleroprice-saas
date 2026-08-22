"""A landing serve dois casos opostos e não pode quebrar nenhum.

1. **Vitrine.** O Bar da Vila está no ar e é o caso de venda. Despersonalizar o
   template (tirar "croquete da Bruna", "4,9★ / 39 avaliações", "samba" de
   dentro do HTML) não pode mudar o site dele — os textos viraram a vibe
   `boteco` e os dados viraram campos do próprio bar.

2. **Bar recém-criado.** Sem conteúdo nenhum, o site não pode exibir título de
   seção com corpo vazio, nem herdar identidade de ninguém.
"""
from decimal import Decimal

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem
from app.utils.modelos import MODELOS


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
                   'Croquete da Bruna', '5519999779942'):
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


# ---------------------------------------------------------------------------
# Os invariantes acima valem pro clássico. Abaixo, valem pra TODOS os modelos.
#
# `modelos.MODELOS` é a fonte única: parametrizar pelas chaves faz o modelo que
# nascer amanhã já entrar aqui sozinho, sem ninguém lembrar de adicionar o
# teste. Um modelo bonito que vaza foto de outro bar, indexa prévia no Google
# ou mostra "Cardápio" no menu sem cardápio é pior que não ter modelo nenhum.
# ---------------------------------------------------------------------------

TODOS_OS_MODELOS = sorted(MODELOS)

# Seções que só existem se houver dado. Título sem corpo é o que denuncia site
# inacabado — e é o estado natural de toda prévia da campanha, que nasce vazia.
# (`clima`/`casa`/`aovivo` ficam de fora de propósito: são blocos de copy da
# vibe, têm corpo próprio e não dependem de cadastro.)
SECOES_COM_DADO = ('cardapio', 'avaliacoes', 'galeria', 'agenda', 'promocoes',
                   'historia')


def _secoes(corpo):
    import re
    return set(re.findall(r'<section[^>]*\bid="([^"]+)"', corpo))


def _tem_form_de_reserva(corpo):
    """O formulário que faz POST /reservar. Sem plano de reservas ele não pode
    existir: o cliente do bar preenche, envia e ninguém recebe.

    Procura a marcação do form, não o `function enviarReserva` — o helper de JS
    fica no rodapé de todos os modelos mesmo quando o form não sai.
    """
    return 'name="num_pessoas"' in corpo or 'onsubmit="return enviarReserva' in corpo


def _bar_do_modelo(session, modelo, *, slug, nome, demo=False, plano='site',
                   hero_foto='img/bar/capa-propria.jpg', conteudo=True,
                   preco=None):
    """Bar de teste rodando `modelo`.

    `conteudo=False` devolve o bar recém-criado da campanha: existe, tem
    modelo escolhido e nada mais.

    `preco=None` é o padrão de propósito: o cardápio sem preço é o estado em
    que quase todo bar entra, e é ele que não pode mostrar "R$ 0,00".
    """
    from datetime import date, timedelta
    from app.models.modelo_evento import Evento
    from app.models.modelo_promocao import Promocao

    r = Restaurante(nome=nome, slug=slug,
                    tipo_conta='demo' if demo else 'cliente',
                    subscription_tier=plano,
                    subscription_status='active' if plano != 'free' else 'free')
    session.add(r)
    session.commit()

    session.add(SiteConfig(restaurant_id=r.id, nome=nome, modelo=modelo,
                           whatsapp='5519911110000', vibe='boteco',
                           hero_foto=hero_foto if conteudo else None))
    if conteudo:
        session.add(DishCard(restaurant_id=r.id, nome='Bolinho de teste',
                             descricao='Só existe aqui.', imagem='img/bar/prato-proprio.jpg',
                             tag='★ TESTE', destaque=True, ordem=0, ativo=True,
                             preco=preco))
        session.add(Review(restaurant_id=r.id, autor='Cliente Fiel',
                           texto='Voltaria mil vezes.', estrelas=5, ordem=0, ativo=True))
        session.add(TeamMember(restaurant_id=r.id, nome='Chef Testeira',
                               papel='Cozinha', emoji='👩‍🍳', ordem=0, ativo=True))
        session.add(GalleryItem(restaurant_id=r.id, imagem='img/bar/galeria-propria.jpg',
                                ordem=0, ativo=True))
        session.add(Promocao(restaurant_id=r.id, titulo='Chope pela metade', ativo=True))
        session.add(Evento(restaurant_id=r.id, titulo='Roda de samba de teste',
                           data=date.today() + timedelta(days=5), ativo=True))
    session.commit()
    return r


@pytest.mark.parametrize('modelo', TODOS_OS_MODELOS)
class TestTodoModeloRespeitaOsInvariantes:
    """Cada modelo é uma landing inteira reescrita. Nenhum pode regredir os
    invariantes que o clássico já garante."""

    def test_renderiza_com_conteudo_completo(self, client, session, modelo):
        _bar_do_modelo(session, modelo, slug='bar-cheio', nome='Bar Cheio')

        resp = client.get('/bar/bar-cheio')
        corpo = resp.get_data(as_text=True)

        assert resp.status_code == 200, f'{modelo} quebrou com conteúdo completo'
        for trecho in ('Bar Cheio', 'Bolinho de teste', 'Cliente Fiel',
                       'Chef Testeira', 'galeria-propria.jpg',
                       'Roda de samba de teste', 'Chope pela metade'):
            assert trecho in corpo, f'{modelo} não renderizou: {trecho}'

    def test_bar_vazio_renderiza_sem_secao_orfa(self, client, session, modelo):
        _bar_do_modelo(session, modelo, slug='bar-vazio-m', nome='Bar Vazio',
                       conteudo=False)

        resp = client.get('/bar/bar-vazio-m')
        corpo = resp.get_data(as_text=True)

        assert resp.status_code == 200, f'{modelo} quebrou com bar vazio'
        assert 'Bar Vazio' in corpo
        orfas = sorted(_secoes(corpo) & set(SECOES_COM_DADO))
        assert orfas == [], f'{modelo} renderizou seção sem conteúdo: {orfas}'

    def test_demo_avisa_que_e_previa_e_nao_indexa(self, client, session, modelo):
        _bar_do_modelo(session, modelo, slug='bar-demo', nome='Bar Demo', demo=True)

        corpo = client.get('/bar/bar-demo').get_data(as_text=True)

        assert 'noindex' in corpo, f'{modelo} deixaria a prévia ser indexada'
        assert 'Prévia não oficial' in corpo, f'{modelo} não avisa que é prévia'

    def test_cliente_nao_e_marcado_como_previa(self, client, session, modelo):
        _bar_do_modelo(session, modelo, slug='bar-cliente', nome='Bar Cliente')

        corpo = client.get('/bar/bar-cliente').get_data(as_text=True)

        assert 'noindex' not in corpo, f'{modelo} sumiu com o site do cliente do Google'
        assert 'Prévia não oficial' not in corpo, f'{modelo} chama cliente de prévia'

    def test_menu_nao_aponta_pra_secao_inexistente(self, client, session, modelo):
        """Nos dois extremos: o bar cheio e o bar que acabou de nascer."""
        _bar_do_modelo(session, modelo, slug='bar-cheio', nome='Bar Cheio')
        _bar_do_modelo(session, modelo, slug='bar-vazio-m', nome='Bar Vazio',
                       conteudo=False)

        for slug in ('bar-cheio', 'bar-vazio-m'):
            corpo = client.get(f'/bar/{slug}').get_data(as_text=True)
            assert _links_quebrados(corpo) == [], f'{modelo} em /{slug}: link morto no menu'

    def test_sem_capa_propria_nao_ha_og_image(self, client, session, vitrine, modelo):
        """O card do WhatsApp com a foto de outro bar é o pior vazamento
        possível: sai da nossa tela e vira print no grupo do cliente.

        O Bar da Vila entra junto (fixture `vitrine`) justamente pra haver uma
        capa alheia disponível pra vazar.
        """
        _bar_do_modelo(session, modelo, slug='bar-sem-capa', nome='Bar Sem Capa',
                       hero_foto=None)

        corpo = client.get('/bar/bar-sem-capa').get_data(as_text=True)

        assert 'og:image' not in corpo, f'{modelo} anunciou og:image sem capa própria'
        assert 'twitter:image' not in corpo, f'{modelo} anunciou twitter:image sem capa'
        assert 'foto-18.jpg' not in corpo, f'{modelo} vazou a capa do Bar da Vila'

    def test_com_capa_propria_o_og_image_e_a_dele(self, client, session, vitrine, modelo):
        """Contraprova do teste acima: sem isto, bastaria nunca emitir og:image
        pra 'passar' — e todo bar perderia o card de compartilhamento."""
        _bar_do_modelo(session, modelo, slug='bar-com-capa', nome='Bar Com Capa',
                       hero_foto='img/bar/capa-propria.jpg')

        corpo = client.get('/bar/bar-com-capa').get_data(as_text=True)

        assert 'og:image' in corpo, f'{modelo} não emitiu og:image tendo capa'
        assert 'capa-propria.jpg' in corpo, f'{modelo} apontou og:image pra outra foto'
        assert 'foto-18.jpg' not in corpo, f'{modelo} vazou a capa do Bar da Vila'

    def test_preco_do_prato_aparece_no_cardapio(self, client, session, modelo):
        """A primeira pergunta de quem lê cardápio. Os 6 modelos respondem —
        em real brasileiro, com vírgula."""
        _bar_do_modelo(session, modelo, slug='bar-com-preco', nome='Bar Com Preço',
                       preco=Decimal('18.50'))

        corpo = client.get('/bar/bar-com-preco').get_data(as_text=True)

        assert 'R$ 18,50' in corpo, f'{modelo} não mostrou o preço do prato'
        # `tabular-nums` é o que mantém a coluna de preços reta quando os
        # números têm larguras diferentes. Sem isso o cardápio "dança".
        assert 'tabular-nums' in corpo, \
            f'{modelo} mostrou preço sem font-variant-numeric:tabular-nums'

    def test_preco_na_tela_e_no_json_ld_sao_o_mesmo_numero(self, client, session, modelo):
        """Vírgula pra pessoa, ponto pro Google — a partir do mesmo valor.

        Divergir aqui é o pior tipo de erro: o cliente lê um preço no site e o
        Google anuncia outro no resultado de busca.
        """
        _bar_do_modelo(session, modelo, slug='bar-preco-seo', nome='Bar SEO',
                       preco=Decimal('42.90'))

        corpo = client.get('/bar/bar-preco-seo').get_data(as_text=True)

        assert 'R$ 42,90' in corpo, f'{modelo} não mostrou o preço na tela'
        assert '"price":"42.90"' in corpo, f'{modelo} não emitiu offers no JSON-LD'
        assert '"priceCurrency":"BRL"' in corpo, f'{modelo} emitiu preço sem moeda'

    def test_prato_sem_preco_nao_mostra_simbolo_nenhum(self, client, session, modelo):
        """O invariante que protege o bar que ainda não precificou.

        `moeda_br` devolve "R$ 0,00" quando recebe None — se algum modelo
        aplicar o filtro sem checar antes, o cardápio inteiro anuncia comida
        de graça. Por isso a asserção é sobre o cifrão, não sobre o zero.
        """
        _bar_do_modelo(session, modelo, slug='bar-sem-preco', nome='Bar Sem Preço')

        corpo = client.get('/bar/bar-sem-preco').get_data(as_text=True)

        assert 'Bolinho de teste' in corpo, f'{modelo} perdeu o prato'
        assert 'R$' not in corpo, f'{modelo} mostrou cifrão em prato sem preço'
        assert 'R$ 0,00' not in corpo, f'{modelo} anunciou prato de graça'
        assert '"offers"' not in corpo, f'{modelo} emitiu Offer sem preço'

    def test_sem_plano_de_reservas_sobra_o_whatsapp(self, client, session, modelo):
        """Formulário que ninguém recebe é pior que não ter formulário. Sem o
        plano, o bar continua alcançável — pelo WhatsApp."""
        _bar_do_modelo(session, modelo, slug='bar-free', nome='Bar Free', plano='free')

        corpo = client.get('/bar/bar-free').get_data(as_text=True)

        assert not _tem_form_de_reserva(corpo), \
            f'{modelo} mostrou form de reserva sem plano de reservas'
        assert 'wa.me/5519911110000' in corpo, \
            f'{modelo} deixou o bar sem plano também sem WhatsApp'
