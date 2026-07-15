"""Popula o AleroPrice com a operação do Bar da Vila.

Não é um seed genérico: são os pratos que o bar realmente vende (croquete,
costelinha com ora-pro-nóbis, frango a passarinho, carbonara), com insumos,
ficha técnica, custos indiretos e um histórico de vendas coerente com a casa —
quarta é o dia de pico (é o que o site anuncia), fim de semana tem samba.

Serve para dois fins:
  1. o Gustavo abrir o dashboard e ver o negócio dele, não "Demo Bistrô";
  2. a demo de venda ter números plausíveis.

Idempotente: roda quantas vezes quiser sem duplicar.

    python scripts/seed_bardavila.py            # tenant 'bar-da-vila'
    python scripts/seed_bardavila.py --slug X   # outro tenant
"""
import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models.modelo_custo import CustoIndireto
from app.models.modelo_estoque import EstoqueMovimentacao
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_previsao import HistoricoVendas
from app.models.modelo_produto import Produto
from app.models.modelo_promocao import Promocao
from app.models.modelo_restaurante import Restaurante


# --- fornecedores --------------------------------------------------------
FORNECEDORES = [
    ('34028316000103', 'Distribuidora Campinas Bebidas LTDA', 'CampBebidas'),
    ('47960950000121', 'Açougue Vila Lemos ME', 'Açougue do Vila'),
    ('61189288000189', 'Hortifruti Barão Distribuidora', 'Hortifruti Barão'),
    ('33041260065290', 'Atacadão Secos e Molhados', 'Atacadão'),
]

# --- insumos (nome, unidade, preço unitário, estoque atual, mínimo, categoria, idx fornecedor)
PRODUTOS = [
    ('Carne moída (patinho)',      'kg', '32.90',  8.0,  5.0,  'Carnes',      1),
    ('Costelinha suína',           'kg', '27.50', 14.0,  8.0,  'Carnes',      1),
    ('Frango (coxinha da asa)',    'kg', '18.90', 12.0,  6.0,  'Carnes',      1),
    ('Bacon em cubos',             'kg', '39.90',  3.5,  2.0,  'Carnes',      1),
    ('Linguiça calabresa',         'kg', '24.00',  5.0,  3.0,  'Carnes',      1),
    ('Hambúrguer artesanal 180g',  'un',  '6.80', 60.0, 30.0,  'Carnes',      1),

    ('Batata',                     'kg',  '5.40', 25.0, 10.0,  'Hortifruti',  2),
    ('Mandioca',                   'kg',  '4.20', 10.0,  5.0,  'Hortifruti',  2),
    ('Ora-pro-nóbis',              'kg', '18.00',  2.0,  1.0,  'Hortifruti',  2),
    ('Cebola',                     'kg',  '4.80',  8.0,  4.0,  'Hortifruti',  2),
    ('Alho',                       'kg', '22.00',  2.0,  1.0,  'Hortifruti',  2),
    ('Tomate',                     'kg',  '7.20',  6.0,  3.0,  'Hortifruti',  2),
    ('Alface',                     'un',  '2.50', 20.0, 10.0,  'Hortifruti',  2),

    ('Farinha de mandioca',        'kg',  '6.90',  9.0,  4.0,  'Secos',       3),
    ('Farinha de trigo',           'kg',  '4.50', 12.0,  5.0,  'Secos',       3),
    ('Farinha de rosca',           'kg',  '8.20',  5.0,  2.0,  'Secos',       3),
    ('Ovos (dúzia)',               'dz', '12.00', 10.0,  5.0,  'Secos',       3),
    ('Massa espaguete',            'kg',  '7.80',  8.0,  4.0,  'Secos',       3),
    ('Queijo parmesão ralado',     'kg', '48.00',  2.5,  1.0,  'Frios',       3),
    ('Queijo mussarela',           'kg', '38.00',  4.0,  2.0,  'Frios',       3),
    ('Creme de leite',             'l',  '11.50',  6.0,  3.0,  'Frios',       3),
    ('Pão de hambúrguer',          'un',  '1.90', 60.0, 30.0,  'Padaria',     3),
    ('Óleo de soja',               'l',   '7.90', 15.0,  8.0,  'Secos',       3),
    ('Sal',                        'kg',  '2.20',  5.0,  2.0,  'Secos',       3),
    ('Pimenta da casa (preparo)',  'kg', '15.00',  1.5,  0.5,  'Secos',       3),

    ('Cerveja long neck 355ml',    'un',  '4.20', 240.0, 96.0, 'Bebidas',     0),
    ('Chopp barril (litro)',       'l',   '9.80',  50.0, 30.0, 'Bebidas',     0),
    ('Refrigerante lata 350ml',    'un',  '2.80', 120.0, 48.0, 'Bebidas',     0),
    ('Cachaça artesanal (dose)',   'un',  '3.50',  80.0, 30.0, 'Bebidas',     0),
]

# --- pratos: (nome, categoria, preço venda, margem, porções, [(insumo, qtd por porção)])
PRATOS = [
    ('Croquete da Bruna (6 un)', 'Petiscos', '34.00', 55, 1, [
        ('Carne moída (patinho)', 0.180), ('Farinha de rosca', 0.060),
        ('Farinha de trigo', 0.040), ('Ovos (dúzia)', 0.08),
        ('Cebola', 0.030), ('Alho', 0.005), ('Óleo de soja', 0.080),
        ('Pimenta da casa (preparo)', 0.010), ('Sal', 0.003),
    ]),
    ('Costelinha com farofa e ora-pro-nóbis', 'Pratos', '58.00', 50, 1, [
        ('Costelinha suína', 0.400), ('Farinha de mandioca', 0.080),
        ('Ora-pro-nóbis', 0.060), ('Cebola', 0.040), ('Alho', 0.008),
        ('Óleo de soja', 0.030), ('Sal', 0.005),
    ]),
    ('Frango a passarinho', 'Petiscos', '42.00', 55, 1, [
        ('Frango (coxinha da asa)', 0.450), ('Alho', 0.015),
        ('Farinha de trigo', 0.050), ('Óleo de soja', 0.120), ('Sal', 0.005),
    ]),
    ('Porção de batata frita', 'Petiscos', '28.00', 60, 1, [
        ('Batata', 0.400), ('Óleo de soja', 0.100), ('Sal', 0.004),
    ]),
    ('Mandioca frita com bacon', 'Petiscos', '32.00', 58, 1, [
        ('Mandioca', 0.350), ('Bacon em cubos', 0.060),
        ('Óleo de soja', 0.100), ('Sal', 0.004),
    ]),
    ('Carbonara da casa', 'Pratos', '46.00', 52, 1, [
        ('Massa espaguete', 0.120), ('Bacon em cubos', 0.070),
        ('Ovos (dúzia)', 0.17), ('Queijo parmesão ralado', 0.040),
        ('Creme de leite', 0.050), ('Sal', 0.003),
    ]),
    ('Calabresa acebolada', 'Petiscos', '30.00', 57, 1, [
        ('Linguiça calabresa', 0.250), ('Cebola', 0.080), ('Óleo de soja', 0.020),
    ]),
    ('Prato do dia', 'Pratos', '26.00', 45, 1, [
        ('Frango (coxinha da asa)', 0.200), ('Batata', 0.100),
        ('Cebola', 0.030), ('Alho', 0.005), ('Óleo de soja', 0.030),
        ('Sal', 0.004), ('Tomate', 0.060),
    ]),
    # O lanche da promoção de quarta.
    ('Lanche da Vila', 'Lanches', '24.00', 50, 1, [
        ('Hambúrguer artesanal 180g', 1.0), ('Pão de hambúrguer', 1.0),
        ('Queijo mussarela', 0.040), ('Bacon em cubos', 0.030),
        ('Alface', 0.15), ('Tomate', 0.040), ('Cebola', 0.020),
    ]),
    ('Cerveja long neck', 'Bebidas', '10.00', 58, 1, [
        ('Cerveja long neck 355ml', 1.0),
    ]),
    ('Chopp (500ml)', 'Bebidas', '12.00', 55, 1, [
        ('Chopp barril (litro)', 0.5),
    ]),
    ('Refrigerante lata', 'Bebidas', '7.00', 60, 1, [
        ('Refrigerante lata 350ml', 1.0),
    ]),
]

CUSTOS_INDIRETOS = [
    ('Aluguel do ponto', '3800.00', 'aluguel'),
    ('Energia elétrica', '1250.00', 'energia'),
    ('Água', '320.00', 'agua'),
    ('Salários (2 funcionários)', '4400.00', 'salarios'),
    ('Gás (botijão P45)', '480.00', 'gas'),
    ('Contador', '550.00', 'contabilidade'),
    ('Samba ao vivo (cachê fim de semana)', '1600.00', 'atracoes'),
    ('Internet e telefone', '180.00', 'outros'),
]

# Peso de movimento por dia da semana (0=seg). Quarta é o pico — é o que o
# próprio site do bar anuncia. Segunda o bar fecha.
MOVIMENTO_SEMANA = {0: 0.0, 1: 0.55, 2: 1.30, 3: 0.70, 4: 1.15, 5: 1.45, 6: 0.85}

# Quantas porções/dia, em média, num dia de peso 1.0.
# Calibrado para um faturamento na casa dos R$ 60–70 mil/mês — plausível para um
# boteco de bairro com 2 funcionários e aluguel de R$ 3.800. Número inflado é
# pior que número nenhum: o dono bate o olho e percebe que é fake.
# Ajuste com --escala quando souber o movimento real da casa.
VOLUME_BASE = {
    'Croquete da Bruna (6 un)': 14, 'Costelinha com farofa e ora-pro-nóbis': 9,
    'Frango a passarinho': 11, 'Porção de batata frita': 16,
    'Mandioca frita com bacon': 8, 'Carbonara da casa': 5,
    'Calabresa acebolada': 7, 'Prato do dia': 18, 'Lanche da Vila': 6,
    'Cerveja long neck': 70, 'Chopp (500ml)': 40, 'Refrigerante lata': 22,
}
ESCALA_PADRAO = 0.55

DIAS_DE_HISTORICO = 180


def _dec(v):
    return Decimal(str(v))


def seed(slug, escala=ESCALA_PADRAO):
    rest = Restaurante.query.filter_by(slug=slug).first()
    if rest is None:
        rest = Restaurante.query.order_by(Restaurante.id).first()
    if rest is None:
        print('ERRO: nenhum restaurante no banco. Rode `flask create-tenant` antes.')
        return 1
    rid = rest.id
    print(f'Tenant: {rest.nome} (id={rid}, slug={rest.slug})')

    # --- fornecedores ---
    forns = []
    for cnpj, razao, fantasia in FORNECEDORES:
        f = Fornecedor.query.filter_by(cnpj=cnpj, restaurant_id=rid).first()
        if f is None:
            f = Fornecedor(cnpj=cnpj, razao_social=razao, nome_fantasia=fantasia,
                           cidade='Campinas', estado='SP', restaurant_id=rid)
            db.session.add(f)
        forns.append(f)
    db.session.commit()

    # --- produtos (insumos) ---
    produtos = {}
    for nome, unid, preco, estoque, minimo, categoria, idx_forn in PRODUTOS:
        p = Produto.query.filter_by(nome=nome, restaurant_id=rid).first()
        if p is None:
            # `codigo` é unique GLOBAL (dívida conhecida do schema): prefixa com o tenant.
            p = Produto(
                codigo=f'BDV{rid}-{len(produtos) + 1:03d}',
                nome=nome, unidade=unid, preco_unitario=_dec(preco),
                estoque_atual=estoque, estoque_minimo=minimo,
                categoria=categoria, fornecedor_id=forns[idx_forn].id,
                restaurant_id=rid,
            )
            db.session.add(p)
            db.session.flush()
            db.session.add(EstoqueMovimentacao(
                produto_id=p.id, quantidade=estoque, tipo='entrada',
                referencia='Seed — estoque inicial', valor_unitario=_dec(preco),
                restaurant_id=rid,
            ))
        produtos[nome] = p
    db.session.commit()
    print(f'  produtos: {len(produtos)}')

    # --- pratos + ficha técnica ---
    n_pratos = 0
    for nome, categoria, preco, margem, porcoes, insumos in PRATOS:
        prato = Prato.query.filter_by(nome=nome).first()   # nome é unique global
        if prato is None:
            prato = Prato(
                nome=nome, categoria=categoria, preco_venda=_dec(preco),
                margem=_dec(margem), rendimento=1.0, unidade_rendimento='porção',
                porcoes_rendimento=porcoes, tempo_preparo=15, restaurant_id=rid,
            )
            db.session.add(prato)
            db.session.flush()
            for ordem, (insumo, qtd) in enumerate(insumos, 1):
                db.session.add(PratoInsumo(
                    prato_id=prato.id, produto_id=produtos[insumo].id,
                    quantidade=qtd, ordem=ordem,
                ))
            n_pratos += 1
    db.session.commit()
    print(f'  pratos novos: {n_pratos}')

    # --- custos indiretos (mês corrente) ---
    ref = date.today().replace(day=1)
    for descricao, valor, tipo in CUSTOS_INDIRETOS:
        existe = CustoIndireto.query.filter_by(
            descricao=descricao, data_referencia=ref, restaurant_id=rid).first()
        if existe is None:
            db.session.add(CustoIndireto(
                descricao=descricao, valor=_dec(valor), data_referencia=ref,
                tipo=tipo, recorrente=True, restaurant_id=rid,
            ))
    db.session.commit()

    # --- histórico de vendas ---
    if HistoricoVendas.query.filter_by(restaurant_id=rid).count() == 0:
        rng = random.Random(42)   # determinístico: mesma demo toda vez
        pratos_db = {p.nome: p for p in Prato.query.filter_by(restaurant_id=rid).all()}
        hoje = date.today()
        linhas = 0

        for d in range(DIAS_DE_HISTORICO, 0, -1):
            dia = hoje - timedelta(days=d)
            peso = MOVIMENTO_SEMANA[dia.weekday()]
            if peso == 0.0:
                continue   # segunda: fechado
            # sazonalidade suave ao longo do ano + ruído do dia
            fator = peso * rng.uniform(0.82, 1.18)

            for nome, base in VOLUME_BASE.items():
                prato = pratos_db.get(nome)
                if prato is None:
                    continue
                qtd = max(0, int(round(base * escala * fator * rng.uniform(0.85, 1.15))))
                if qtd == 0:
                    continue
                preco = prato.preco_venda or _dec('0')
                db.session.add(HistoricoVendas(
                    data=dia, prato_id=prato.id, quantidade=qtd,
                    valor_unitario=preco, valor_total=preco * qtd,
                    dia_semana=dia.weekday(), mes=dia.month,
                    semana_mes=((dia.day - 1) // 7) + 1,
                    restaurant_id=rid,
                ))
                linhas += 1
            if linhas % 2000 < 15:
                db.session.commit()
        db.session.commit()
        print(f'  histórico de vendas: {linhas} linhas ({DIAS_DE_HISTORICO} dias)')
    else:
        print('  histórico de vendas: já existe, mantido')

    # --- promoções ---
    # Checa título a título: uma promoção antiga qualquer no tenant não pode
    # impedir o seed das outras (era o que acontecia com `count() == 0`).
    promocoes = [
        dict(titulo='Lanche de Quarta',
             descricao='Lanche da Vila + chopp por R$ 29. Toda quarta, das 18h até acabar. '
                       'É o dia mais cheio da casa — vem cedo.',
             dia_semana=2),          # quarta
        dict(titulo='Sexta do Chopp em Dobro',
             descricao='Pediu um chopp, leva dois. Das 17h às 20h.',
             dia_semana=4),          # sexta
        dict(titulo='Feijoada de Aniversário',
             descricao='A casa faz 8 anos. Feijoada completa com samba a tarde toda.',
             data_inicio=date.today() + timedelta(days=20),
             validade=date.today() + timedelta(days=21)),
    ]

    n_promo = 0
    for dados in promocoes:
        existe = Promocao.query.filter_by(
            titulo=dados['titulo'], restaurant_id=rid).first()
        if existe:
            continue
        db.session.add(Promocao(ativo=True, restaurant_id=rid, **dados))
        n_promo += 1

    db.session.commit()
    print(f'  promoções: {n_promo} novas, {len(promocoes) - n_promo} já existiam')

    print('\nPronto. Abra /app pra ver o dashboard do bar.')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', default='bar-da-vila')
    ap.add_argument('--escala', type=float, default=ESCALA_PADRAO,
                    help='Multiplicador do volume de vendas. Ajuste ao movimento real da casa.')
    args = ap.parse_args()

    app = create_app(os.environ.get('APP_ENV', 'development'))
    with app.app_context():
        sys.exit(seed(args.slug, args.escala))
