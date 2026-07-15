"""Catálogo do Bar do Zé — segundo tenant de demonstração.

Existe pra provar que o multi-tenant isola de verdade: outro cardápio, outros
insumos, outros fornecedores, outro dashboard. É de propósito um bar DIFERENTE
do Bar da Vila — boteco de espetinho, ticket menor, cozinha simples — para que
comparar os dois dashboards mostre dois negócios, não o mesmo bar duas vezes.

`Prato.nome` é unique GLOBAL no schema (dívida conhecida, ver CLAUDE.md), então
os pratos daqui não podem repetir nome de prato de outro tenant nem por acaso.

Uso:
    flask create-tenant --restaurante "Bar do Zé" --email ze@bardoze.com ...
    python scripts/seed_bardoze.py
    python scripts/seed_movimento.py --slug bar-do-ze --reset
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.extensions import db
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_produto import Produto
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig

SLUG = 'bar-do-ze'

FORNECEDORES = [
    ('11222333000144', 'Distribuidora de Bebidas Zona Leste', 'Bebidas'),
    ('22333444000155', 'Açougue do Bairro', 'Carnes'),
    ('33444555000166', 'Sacolão do Mercado', 'Hortifruti'),
    ('44555666000177', 'Atacado Secos e Molhados', 'Secos'),
]

# (codigo, nome, unidade, preco, estoque_minimo, categoria, indice_fornecedor)
PRODUTOS = [
    ('ZE-01', 'Carne bovina em cubos (alcatra)', 'kg', 38.90, 6, 'Carnes', 1),
    ('ZE-02', 'Frango em cubos (coxa/sobrecoxa)', 'kg', 16.50, 6, 'Carnes', 1),
    ('ZE-03', 'Queijo coalho em espeto', 'un', 2.30, 40, 'Frios', 1),
    ('ZE-04', 'Panceta suína', 'kg', 29.90, 5, 'Carnes', 1),
    ('ZE-05', 'Linguiça toscana', 'kg', 22.00, 4, 'Carnes', 1),
    ('ZE-06', 'Mocotó', 'kg', 14.00, 4, 'Carnes', 1),
    ('ZE-07', 'Carne moída (acém)', 'kg', 26.90, 4, 'Carnes', 1),
    ('ZE-08', 'Batata', 'kg', 5.40, 12, 'Hortifruti', 2),
    ('ZE-09', 'Cebola', 'kg', 4.80, 5, 'Hortifruti', 2),
    ('ZE-10', 'Alho', 'kg', 22.00, 1, 'Hortifruti', 2),
    ('ZE-11', 'Limão', 'kg', 5.90, 3, 'Hortifruti', 2),
    ('ZE-12', 'Cheiro-verde', 'kg', 12.00, 1, 'Hortifruti', 2),
    ('ZE-13', 'Mandioca', 'kg', 4.20, 6, 'Hortifruti', 2),
    ('ZE-14', 'Massa de pastel', 'kg', 9.80, 3, 'Secos', 3),
    ('ZE-15', 'Farinha de mandioca', 'kg', 6.90, 4, 'Secos', 3),
    ('ZE-16', 'Óleo de soja', 'l', 7.90, 10, 'Secos', 3),
    ('ZE-17', 'Sal grosso', 'kg', 2.80, 3, 'Secos', 3),
    ('ZE-18', 'Tempero da casa (preparo)', 'kg', 13.00, 1, 'Secos', 3),
    ('ZE-19', 'Cerveja lata 350ml', 'un', 3.10, 144, 'Bebidas', 0),
    ('ZE-20', 'Cerveja garrafa 600ml', 'un', 7.20, 72, 'Bebidas', 0),
    ('ZE-21', 'Refrigerante lata 350ml', 'un', 2.80, 48, 'Bebidas', 0),
    ('ZE-22', 'Cachaça (dose)', 'un', 2.40, 40, 'Bebidas', 0),
]

# (nome, preco_venda, porcoes, [(codigo_produto, quantidade_por_porcao)])
PRATOS = [
    ('Espetinho de carne', 9.00, [
        ('ZE-01', 0.12), ('ZE-17', 0.004), ('ZE-18', 0.004)]),
    ('Espetinho de frango', 7.00, [
        ('ZE-02', 0.13), ('ZE-17', 0.004), ('ZE-18', 0.004)]),
    ('Espetinho de queijo coalho', 8.00, [
        ('ZE-03', 1.0), ('ZE-18', 0.002)]),
    ('Espetinho de linguiça', 8.00, [
        ('ZE-05', 0.12), ('ZE-09', 0.02)]),
    ('Torresmo do Zé', 24.00, [
        ('ZE-04', 0.30), ('ZE-16', 0.08), ('ZE-17', 0.005), ('ZE-11', 0.03)]),
    ('Caldo de mocotó', 18.00, [
        ('ZE-06', 0.25), ('ZE-09', 0.04), ('ZE-10', 0.006), ('ZE-12', 0.01)]),
    ('Pastel de feira (carne)', 10.00, [
        ('ZE-14', 0.09), ('ZE-07', 0.07), ('ZE-09', 0.02), ('ZE-16', 0.06)]),
    ('Fritas do Zé', 22.00, [
        ('ZE-08', 0.35), ('ZE-16', 0.09), ('ZE-17', 0.004)]),
    ('Mandioca na manteiga', 20.00, [
        ('ZE-13', 0.35), ('ZE-16', 0.05), ('ZE-17', 0.004)]),
    ('Cerveja lata', 8.00, [('ZE-19', 1.0)]),
    ('Cerveja garrafa 600', 15.00, [('ZE-20', 1.0)]),
    ('Refri do Zé', 6.00, [('ZE-21', 1.0)]),
    ('Dose de pinga', 6.00, [('ZE-22', 1.0)]),
]

SITE = {
    'nome': 'Bar do Zé',
    'hero_linha1': 'Bar do',
    'hero_linha2': 'Zé',
    'kicker': 'BOTECO DE ESQUINA · CAMPINAS–SP',
    'tagline': 'Espetinho na brasa, cerveja trincando e torresmo que faz barulho. Sem frescura.',
    'subline': 'ESPETINHO · TORRESMO · CALDO DE MOCOTÓ',
    'selo_estrelas': '4,7 no Google · 112 avaliações',
    'cidade_uf': 'Campinas–SP',
    'horario': 'Terça a domingo, das 17h até tarde',
    'tema': 'noite',
}


def seed():
    rest = Restaurante.query.filter_by(slug=SLUG).first()
    if rest is None:
        print(f'ERRO: nenhum restaurante com slug "{SLUG}". Rode antes:\n'
              f'  flask create-tenant --restaurante "Bar do Zé" --email ze@bardoze.com')
        return 1
    rid = rest.id
    print(f'Tenant: {rest.nome} (id={rid}, slug={rest.slug})')

    fornecedores = []
    for cnpj, razao, _cat in FORNECEDORES:
        f = Fornecedor.query.filter_by(cnpj=cnpj, restaurant_id=rid).first()
        if f is None:
            f = Fornecedor(cnpj=cnpj, razao_social=razao, nome_fantasia=razao,
                           cidade='Campinas', estado='SP', restaurant_id=rid)
            db.session.add(f)
        fornecedores.append(f)
    db.session.flush()
    print(f'  fornecedores: {len(fornecedores)}')

    produtos = {}
    for codigo, nome, unidade, preco, minimo, categoria, idx in PRODUTOS:
        p = Produto.query.filter_by(codigo=codigo).first()
        if p is None:
            p = Produto(
                codigo=codigo, nome=nome, unidade=unidade, preco_unitario=preco,
                estoque_minimo=minimo, estoque_atual=minimo, categoria=categoria,
                fornecedor_id=fornecedores[idx].id, ativo=True, restaurant_id=rid,
            )
            db.session.add(p)
            db.session.flush()
        produtos[codigo] = p
    print(f'  produtos: {len(produtos)}')

    n_pratos = 0
    for nome, preco, insumos in PRATOS:
        prato = Prato.query.filter_by(nome=nome).first()
        if prato is not None:
            continue
        prato = Prato(
            nome=nome, preco_venda=preco, rendimento=1, unidade_rendimento='un',
            porcoes_rendimento=1, tempo_preparo=12, ativo=True, restaurant_id=rid,
        )
        db.session.add(prato)
        db.session.flush()
        for ordem, (codigo, qtd) in enumerate(insumos, start=1):
            db.session.add(PratoInsumo(
                prato_id=prato.id, produto_id=produtos[codigo].id,
                quantidade=qtd, ordem=ordem,
            ))
        n_pratos += 1
    print(f'  pratos novos: {n_pratos}')

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    if cfg is None:
        db.session.add(SiteConfig(restaurant_id=rid, **SITE))
        print('  site: SiteConfig criado')
    else:
        print('  site: SiteConfig já existia, mantido')

    db.session.commit()
    print(f'\nPronto. Catálogo no ar. Agora o movimento:\n'
          f'  python scripts/seed_movimento.py --slug {SLUG} --reset')
    return 0


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        sys.exit(seed())
