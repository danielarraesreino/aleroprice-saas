"""Hotsite da Dona Berga Charcutaria Artesanal (primeiro tenant `artesao`).

Conteúdo tirado das legendas do Instagram @donaberga_produtosartesanais
(coleta de 18/10/2026). Só entra o que está escrito lá: sem preço (nenhuma
legenda traz). Fotos: as 48 que a Berga aprovou em 20/10/2026 (copiadas e
otimizadas para app/static/img/berga/).

Idempotente: cria o que falta e nunca sobrescreve o que o dono já editou.
O tenant nasce INATIVO (`ativo=False`): `tenant_por_host`/`tenant_por_slug`
não servem site de tenant inativo, então nada vai ao ar por acidente. Para
publicar, depois da aprovação das fotos:

    python -m app.scripts.seed_berga --no-ar
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import GalleryItem, ProdutoSite

SLUG = 'dona-berga'
DOMINIO = 'donaberga.com.br'

SITE = {
    'nome': 'Dona Berga',
    'hero_linha1': 'Dona',
    'hero_linha2': 'Berga',
    'kicker': 'CHARCUTARIA ARTESANAL · FEIRA DE BARÃO · CAMPINAS–SP',
    'tagline': 'Charcutaria artesanal familiar: defumados, maturados e conservas '
               'feitos sem química, com técnica e cuidado.',
    'subline': 'DEFUMADOS · MATURADOS · CONSERVAS',
    'hero_foto': 'img/berga/hero.jpg',
    'logo': 'img/berga/logo.jpg',
    'whatsapp': '5519991563362',
    'telefone_exibicao': '(19) 99156-3362',
    'cidade_uf': 'Barão Geraldo, Campinas–SP',
    'horario': 'Sábados e domingos na Feira de Barão',
    'maps_query': 'Feira de Barão Geraldo Campinas',
    'instagram_url': 'https://www.instagram.com/donaberga_produtosartesanais/',
    'descritor': 'Charcutaria artesanal em Barão Geraldo',
    'tema': 'boteco-ambar',
    'vibe': 'artesanal',
    'tema_modo': 'auto',
}

# (nome, descricao, categoria, sob_encomenda, destaque) — descrições só com o
# que as legendas afirmam.
PRODUTOS = [
    ('Tender', 'Sabor festivo, levemente adocicado. Estrela da ceia de Natal.', 'Defumados', False, True),
    ('Copa Lombo (Coppa)', 'Marmoreio nobre e cura lenta.', 'Defumados', False, True),
    ('Picanha Suína', 'Corte nobre com a capa de gordura natural que garante suculência.', 'Defumados', False, False),
    ('Lombo Defumado', 'Boa opção para quem prefere carne mais magra: só uma fina capa de gordura.', 'Defumados', False, False),
    ('Lombo Italiano Defumado', 'Sabor sutil e agradável, defumado em serragem de abacateiro.', 'Defumados', False, False),
    ('Presunto Defumado Artesanal', 'Sem químicas e sem conservantes.', 'Defumados', False, False),
    ('Bacon Defumado', None, 'Defumados', False, False),
    ('Pastrami de Cupim', None, 'Defumados', False, False),
    ('Chorizo Espanhol', None, 'Defumados', False, False),
    ('Joelho Defumado', None, 'Defumados', False, False),

    ('Linguiça Defumada Caipira', 'Também na versão apimentada e com pimenta biquinho.', 'Linguiças', False, True),
    ('Linguiça Defumada com Queijo Coalho', 'Muito queijo.', 'Linguiças', False, False),
    ('Linguiça Calabresa com Parmesão', 'Petisco em poucas unidades.', 'Linguiças', False, False),
    ('Linguiça Defumada Premium', 'Seis horas de defumação a quente com lenhas frutíferas.', 'Linguiças', False, False),
    ('Linguiça de Rúcula com Tomate Seco', None, 'Linguiças', False, False),

    ('Lonzino Maturado', None, 'Maturados', False, False),
    ('Fiocco de Culatello', None, 'Maturados', False, False),
    ('Lombo Curado', None, 'Maturados', False, False),
    ('Linguiças Curadas', None, 'Maturados', False, False),

    ('Molho Old Chilli', None, 'Molhos e geleias', False, False),
    ('Molho Brazilian Smoke', None, 'Molhos e geleias', False, False),
    ('Molhos de Pimenta', 'Dedo-de-moça, habanero e americana defumada.', 'Molhos e geleias', False, False),
    ('Geleia de Pimenta', 'Sabores equilibrados; harmoniza com carne suína e hambúrguer.', 'Molhos e geleias', False, False),
    ('Alho Crocante', None, 'Molhos e geleias', False, False),
    ('Malagueta Defumada no Azeite', None, 'Molhos e geleias', False, False),

    ('Picles Tradicional', None, 'Conservas', False, False),
    ('Picles Spice', None, 'Conservas', False, False),
    ('Seleta de Legumes', None, 'Conservas', False, False),
    ('Pimentas em Azeite', 'Em garrafa, com as pimentas e o azeite à vista.', 'Conservas', False, False),
    ('Pimentas em Conserva', None, 'Conservas', False, False),

    ('Kit Artesanal Personalizado', 'Você escolhe os itens e monta a caixa: do lombo defumado ao molho Old Chilli. '
     'Produção limitada.', 'Kits', True, True),
]


# Fotos aprovadas pela Berga (20/10/2026), em app/static/img/berga/.
IMAGENS = {
    'Tender': 'tender', 'Copa Lombo (Coppa)': 'copa-lombo', 'Picanha Suína': 'picanha-suina',
    'Lombo Defumado': 'lombo-defumado', 'Lombo Italiano Defumado': 'lombo-italiano',
    'Presunto Defumado Artesanal': 'presunto', 'Bacon Defumado': 'bacon',
    'Linguiça Defumada Caipira': 'linguica-caipira',
    'Linguiça Calabresa com Parmesão': 'linguica-parmesao', 'Lombo Curado': 'lombo-curado',
    'Geleia de Pimenta': 'geleia-pimenta', 'Molhos de Pimenta': 'molhos-pimenta',
    'Picles Tradicional': 'picles-tradicional', 'Picles Spice': 'picles-spice',
    'Seleta de Legumes': 'seleta-legumes', 'Pimentas em Azeite': 'pimentas-azeite',
    'Pimentas em Conserva': 'pimentas-conserva', 'Kit Artesanal Personalizado': 'kit',
}

GALERIA = [
    ('g-barraca', 'A barraca na Feira de Barão'),
    ('g-berga-na-barraca', 'Berga na barraca'),
    ('g-prateleira', 'Molhos, conservas e geleias na prateleira'),
    ('g-maturados', 'Peças em maturação'),
    ('g-linguicas', 'Linguiças embaladas'),
    ('g-lombo-e-conservas', 'Lombo fatiado e conservas'),
    ('g-equipe', 'A equipe da barraca'),
]


def semear(no_ar=False):
    """Cria/atualiza o tenant da Berga. Devolve (restaurante, produtos_novos)."""
    rest = Restaurante.query.filter_by(slug=SLUG).first()
    if rest is None:
        rest = Restaurante(nome='Dona Berga Charcutaria Artesanal', slug=SLUG,
                           dominio=DOMINIO, tipo_negocio='artesao',
                           tipo_conta='cliente', subscription_tier='site',
                           ativo=bool(no_ar))
        db.session.add(rest)
        db.session.flush()
    elif no_ar:
        rest.ativo = True

    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first()
    if cfg is None:
        db.session.add(SiteConfig(restaurant_id=rest.id, **SITE))
    else:
        # Só completa o que falta; o que o dono editou fica como está.
        for campo in ('hero_foto', 'logo'):
            if not getattr(cfg, campo):
                setattr(cfg, campo, SITE[campo])

    existentes = {p.nome: p for p in ProdutoSite.query.filter_by(restaurant_id=rest.id)}
    novos = 0
    for ordem, (nome, desc, cat, enc, dest) in enumerate(PRODUTOS):
        foto = f'img/berga/{IMAGENS[nome]}.jpg' if nome in IMAGENS else None
        if nome in existentes:
            # Só completa o que falta; o que o dono editou fica como está.
            if foto and not existentes[nome].imagem:
                existentes[nome].imagem = foto
            continue
        db.session.add(ProdutoSite(restaurant_id=rest.id, nome=nome, descricao=desc,
                                   categoria=cat, sob_encomenda=enc, destaque=dest,
                                   imagem=foto, ordem=ordem, ativo=True))
        novos += 1

    fotos = {g.imagem for g in GalleryItem.query.filter_by(restaurant_id=rest.id)}
    for ordem, (arq, legenda) in enumerate(GALERIA):
        caminho = f'img/berga/{arq}.jpg'
        if caminho not in fotos:
            db.session.add(GalleryItem(restaurant_id=rest.id, imagem=caminho,
                                       legenda=legenda, ordem=ordem, ativo=True))
    db.session.commit()
    return rest, novos


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        rest, novos = semear(no_ar='--no-ar' in sys.argv)
        print(f'{rest.nome}: ativo={rest.ativo} · {novos} produto(s) novo(s)')
