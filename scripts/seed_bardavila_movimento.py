"""Um mês de operação do Bar da Vila.

Gera movimento coerente de ponta a ponta, na ordem em que a coisa acontece no
bar de verdade:

    cardápio → vendas do dia → consumo da ficha técnica → compra (NF-e) → desperdício

O saldo de estoque no fim é o resultado do razão (entradas - saídas), não um
número chutado: as compras são dimensionadas a partir do consumo real do
período, com folga de segurança.

Uso:
    python scripts/seed_bardavila_movimento.py                 # últimos 30 dias
    python scripts/seed_bardavila_movimento.py --dias 60
    python scripts/seed_bardavila_movimento.py --reset         # limpa o período antes

Assume que `scripts/seed_bardavila.py` já rodou (pratos, insumos, fornecedores).
"""
import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.modelo_cardapio import Cardapio, CardapioItem, CardapioSecao
from app.models.modelo_desperdicio import CategoriaDesperdicio, RegistroDesperdicio
from app.models.modelo_estoque import EstoqueMovimentacao
from app.models.modelo_nfe import NFItem, NFNota
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_previsao import HistoricoVendas
from app.models.modelo_produto import Produto
from app.models.modelo_restaurante import Restaurante

SEED = 20260714
DIAS_PADRAO = 30

# Fecha segunda. Pico quinta-sábado, domingo de almoço em família.
# 0=seg ... 6=dom
FATOR_DIA = {0: 0.0, 1: 0.70, 2: 0.85, 3: 1.05, 4: 1.50, 5: 1.70, 6: 1.15}

# Movimento típico de um dia normal (unidades vendidas), por nome de prato.
# É o que sustenta o bar: bebida em volume, petisco em margem, almoço em giro.
MIX_BASE = {
    'Croquete da Bruna (6 un)': 12,
    'Costelinha com farofa e ora-pro-nóbis': 8,
    'Frango a passarinho': 10,
    'Porção de batata frita': 14,
    'Mandioca frita com bacon': 7,
    'Carbonara da casa': 5,
    'Calabresa acebolada': 9,
    'Prato do dia': 22,
    'Lanche da Vila': 11,
    'Cerveja long neck': 60,
    'Chopp (500ml)': 40,
    'Refrigerante lata': 18,
}

# Prato do dia é almoço; o resto é bar à noite.
PERIODO = {'Prato do dia': 'tarde'}

SECOES = [
    ('Petiscos e Porções', 1, [
        'Croquete da Bruna (6 un)', 'Frango a passarinho', 'Porção de batata frita',
        'Mandioca frita com bacon', 'Calabresa acebolada',
    ]),
    ('Pratos', 2, [
        'Costelinha com farofa e ora-pro-nóbis', 'Carbonara da casa', 'Prato do dia',
    ]),
    ('Lanches', 3, ['Lanche da Vila']),
    ('Bebidas', 4, ['Cerveja long neck', 'Chopp (500ml)', 'Refrigerante lata']),
]

DESTAQUES = {'Croquete da Bruna (6 un)', 'Costelinha com farofa e ora-pro-nóbis'}

CATEGORIAS_DESPERDICIO = [
    ('Sobras de Preparo', 'Aparas e sobras da mise en place', '#F59E0B'),
    ('Estragado', 'Produto vencido ou deteriorado no estoque', '#EF4444'),
    ('Sobras de Clientes', 'Comida devolvida no prato', '#6366F1'),
    ('Erro de Preparo', 'Prato refeito por erro na cozinha', '#EC4899'),
    ('Quebra e Perda', 'Copo quebrado, chopp perdido na troca de barril', '#14B8A6'),
]

# Compras: perecível chega toda terça e sexta; seco e bebida, uma vez por semana.
# (categoria do produto -> dias da semana em que o fornecedor entrega)
DIAS_DE_COMPRA = {
    'Carnes': {1, 4},
    'Hortifruti': {1, 4},
    'Frios': {1},
    'Padaria': {1, 4},
    'Secos': {2},
    'Bebidas': {2},
}
# Cada entrega cobre o consumo até a próxima, com folga — descontando o que já
# está em casa, senão o estoque só cresce e o saldo final vira ficção.
FOLGA_COMPRA = 1.25

RESPONSAVEIS = ['Bruna', 'Gustavo', 'Márcia', 'Tiago']
LOCAIS = ['Cozinha', 'Estoque', 'Salão', 'Bar']


def _dec(v):
    return Decimal(str(round(float(v), 2)))


def _quantidade_do_dia(base, dia, rnd):
    """Vendas de um prato num dia: sazonalidade + promoção + clima + ruído."""
    fator = FATOR_DIA[dia.weekday()]
    if fator == 0:
        return 0
    return max(0, int(round(base * fator * rnd.uniform(0.88, 1.12))))


def limpar_periodo(rid, inicio, fim):
    """Apaga o movimento do tenant dentro da janela (idempotência do --reset)."""
    ini_dt = datetime.combine(inicio, time.min)
    fim_dt = datetime.combine(fim, time.max)

    HistoricoVendas.query.filter(
        HistoricoVendas.restaurant_id == rid,
        HistoricoVendas.data >= inicio,
        HistoricoVendas.data <= fim,
    ).delete(synchronize_session=False)

    EstoqueMovimentacao.query.filter(
        EstoqueMovimentacao.restaurant_id == rid,
        EstoqueMovimentacao.data_movimentacao >= ini_dt,
        EstoqueMovimentacao.data_movimentacao <= fim_dt,
    ).delete(synchronize_session=False)

    RegistroDesperdicio.query.filter(
        RegistroDesperdicio.restaurant_id == rid,
        RegistroDesperdicio.data_registro >= ini_dt,
        RegistroDesperdicio.data_registro <= fim_dt,
    ).delete(synchronize_session=False)

    notas = NFNota.query.filter(
        NFNota.restaurant_id == rid,
        NFNota.data_emissao >= ini_dt,
        NFNota.data_emissao <= fim_dt,
    ).all()
    for nota in notas:
        NFItem.query.filter_by(nf_nota_id=nota.id).delete(synchronize_session=False)
        db.session.delete(nota)

    db.session.flush()


def montar_cardapio(rid, pratos, inicio):
    """Cardápio ativo com as seções do bar. Devolve {nome_prato: CardapioItem}."""
    cardapio = Cardapio.query.filter_by(restaurant_id=rid, ativo=True).first()
    if cardapio is None:
        cardapio = Cardapio(
            nome='Cardápio do Bar da Vila',
            descricao='Cardápio da casa: petiscos, pratos, lanches e bebidas.',
            data_inicio=inicio, ativo=True, tipo='diário', restaurant_id=rid,
        )
        db.session.add(cardapio)
        db.session.flush()

    itens = {}
    for nome_secao, ordem, nomes in SECOES:
        secao = CardapioSecao.query.filter_by(
            cardapio_id=cardapio.id, nome=nome_secao).first()
        if secao is None:
            secao = CardapioSecao(cardapio_id=cardapio.id, nome=nome_secao, ordem=ordem)
            db.session.add(secao)
            db.session.flush()

        for i, nome in enumerate(nomes, start=1):
            prato = pratos.get(nome)
            if prato is None:
                continue
            item = CardapioItem.query.filter_by(
                secao_id=secao.id, prato_id=prato.id).first()
            if item is None:
                item = CardapioItem(
                    secao_id=secao.id, prato_id=prato.id, ordem=i,
                    preco_venda=prato.preco_venda,
                    destaque=nome in DESTAQUES, disponivel=True,
                )
                db.session.add(item)
                db.session.flush()
            itens[nome] = item

    return cardapio, itens


def garantir_categorias_desperdicio(rid):
    cats = {}
    for nome, descricao, cor in CATEGORIAS_DESPERDICIO:
        # `nome` é unique global no modelo — reaproveita a categoria de outro
        # tenant se ela já existir, só cria se for realmente nova.
        cat = CategoriaDesperdicio.query.filter_by(nome=nome).first()
        if cat is None:
            cat = CategoriaDesperdicio(
                nome=nome, descricao=descricao, cor=cor, ativo=True, restaurant_id=rid)
            db.session.add(cat)
            db.session.flush()
        cats[nome] = cat
    return cats


def seed(slug, dias, reset):
    rnd = random.Random(SEED)

    rest = Restaurante.query.filter_by(slug=slug).first()
    if rest is None:
        print(f'ERRO: nenhum restaurante com slug "{slug}". Rode scripts/seed_bardavila.py antes.')
        return 1
    rid = rest.id
    print(f'Tenant: {rest.nome} (id={rid})')

    hoje = date.today()
    inicio = hoje - timedelta(days=dias - 1)
    print(f'Janela: {inicio:%d/%m/%Y} a {hoje:%d/%m/%Y} ({dias} dias)')

    pratos = {p.nome: p for p in Prato.query.filter_by(restaurant_id=rid).all()
              if p.nome in MIX_BASE}
    if len(pratos) < len(MIX_BASE):
        faltando = set(MIX_BASE) - set(pratos)
        print(f'ERRO: pratos faltando no tenant: {sorted(faltando)}')
        return 1

    produtos = {p.id: p for p in Produto.query.filter_by(restaurant_id=rid).all()}
    fichas = {}  # prato_id -> [(produto, qtd_por_porcao)]
    for nome, prato in pratos.items():
        insumos = PratoInsumo.query.filter_by(prato_id=prato.id).all()
        porcoes = max(1, prato.porcoes_rendimento or 1)
        fichas[prato.id] = [
            (produtos[i.produto_id], i.quantidade / porcoes)
            for i in insumos if i.produto_id in produtos
        ]

    if reset:
        limpar_periodo(rid, inicio, hoje)
        print('  período limpo (vendas, estoque, NF-e, desperdício)')

    cardapio, itens = montar_cardapio(rid, pratos, inicio)
    print(f'  cardápio: "{cardapio.nome}" com {len(itens)} itens em {len(SECOES)} seções')

    # ---- 1. Vendas do dia + consumo da ficha técnica --------------------
    consumo = {}       # data -> {produto_id: quantidade}
    vendas_por_dia = {}  # data -> {nome_prato: qtd}
    n_vendas = 0
    faturamento = Decimal('0')

    for i in range(dias):
        dia = inicio + timedelta(days=i)
        if FATOR_DIA[dia.weekday()] == 0:
            continue  # segunda: bar fechado

        chuva = rnd.random() < 0.20
        clima = 'chuvoso' if chuva else rnd.choice(['ensolarado', 'nublado'])
        temperatura = round(rnd.uniform(14, 24) if chuva else rnd.uniform(18, 31), 1)

        do_dia = {}
        for nome, base in MIX_BASE.items():
            qtd = _quantidade_do_dia(base, dia, rnd)

            # Promoções da casa mexem no mix, não só no preço.
            if dia.weekday() == 2 and nome == 'Lanche da Vila':
                qtd = int(qtd * 1.8)            # Lanche de Quarta
            if dia.weekday() == 4 and nome == 'Chopp (500ml)':
                qtd = int(qtd * 1.6)            # Chopp de Sexta
            if chuva and nome != 'Prato do dia':
                qtd = int(qtd * 0.85)           # chuva esvazia o salão à noite

            if qtd <= 0:
                continue

            prato = pratos[nome]
            preco = Decimal(str(prato.preco_venda or 0))
            total = preco * qtd

            db.session.add(HistoricoVendas(
                data=dia,
                cardapio_item_id=itens[nome].id if nome in itens else None,
                prato_id=prato.id,
                quantidade=qtd,
                valor_unitario=preco,
                valor_total=total,
                periodo_dia=PERIODO.get(nome, 'noite'),
                dia_semana=dia.weekday(),
                semana_mes=min(5, (dia.day - 1) // 7 + 1),
                mes=dia.month,
                feriado=False,
                clima=clima,
                temperatura=temperatura,
                restaurant_id=rid,
            ))
            n_vendas += 1
            faturamento += total
            do_dia[nome] = qtd

            for produto, por_porcao in fichas[prato.id]:
                consumo.setdefault(dia, {})
                consumo[dia][produto.id] = consumo[dia].get(produto.id, 0) + por_porcao * qtd

        vendas_por_dia[dia] = do_dia

    print(f'  vendas: {n_vendas} linhas, faturamento R$ {faturamento:,.2f}')

    # ---- 2. Compras (NF-e) dimensionadas pelo consumo -------------------
    # Abertura do período: o bar não começa com a despensa vazia. Entra como
    # movimentação pra o razão fechar com a simulação de compra lá embaixo.
    abertura = datetime.combine(inicio, time(6, 0))
    for produto in produtos.values():
        inicial = float(produto.estoque_minimo or 0)
        if inicial <= 0:
            continue
        db.session.add(EstoqueMovimentacao(
            produto_id=produto.id, quantidade=inicial, tipo='entrada',
            data_movimentacao=abertura, referencia='Saldo inicial',
            valor_unitario=produto.preco_unitario,
            observacao='Estoque em casa na abertura do período',
            restaurant_id=rid,
        ))

    # Cada entrega cobre o consumo até a próxima entrega do mesmo fornecedor.
    consumo_por_produto_dia = {}
    for dia, mapa in consumo.items():
        for pid, qtd in mapa.items():
            consumo_por_produto_dia.setdefault(pid, {})[dia] = qtd

    entregas = {}  # (data, fornecedor_id) -> [(produto, qtd, custo_unit)]
    for pid, por_dia in consumo_por_produto_dia.items():
        produto = produtos[pid]
        dias_entrega = DIAS_DE_COMPRA.get(produto.categoria, {2})

        datas_compra = [inicio + timedelta(days=i) for i in range(dias)
                        if (inicio + timedelta(days=i)).weekday() in dias_entrega]
        if not datas_compra:
            continue

        # Começa o mês com o estoque mínimo em casa e vai simulando o saldo:
        # a compra é só o buraco entre o que vai ser consumido e o que sobrou.
        saldo = float(produto.estoque_minimo or 0)
        seguranca = float(produto.estoque_minimo or 0) * 1.3

        for j, data_compra in enumerate(datas_compra):
            proxima = datas_compra[j + 1] if j + 1 < len(datas_compra) else hoje + timedelta(days=1)
            necessario = sum(q for d, q in por_dia.items() if data_compra <= d < proxima)
            if necessario <= 0:
                continue

            qtd = round(max(0.0, necessario * FOLGA_COMPRA + seguranca - saldo), 2)
            if produto.unidade in ('un', 'dz'):
                qtd = float(max(0, int(round(qtd))))
            if qtd <= 0:
                saldo -= necessario  # deu pra segurar com o que tinha
                continue
            saldo = saldo + qtd - necessario

            # Custo oscila: é o que alimenta o alerta de inflação de insumo.
            base = float(produto.preco_unitario or 0)
            custo = round(base * rnd.uniform(0.96, 1.06), 4)

            fid = produto.fornecedor_id
            if fid is None:
                continue
            entregas.setdefault((data_compra, fid), []).append((produto, qtd, custo))

    n_notas = 0
    n_itens = 0
    total_compras = Decimal('0')
    for (data_compra, fid), linhas in sorted(entregas.items()):
        emissao = datetime.combine(data_compra, time(rnd.randint(7, 10), rnd.randint(0, 59)))
        numero = f'{rnd.randint(10000, 99999)}'
        chave = f'{rnd.randint(10**43, 10**44 - 1)}'

        valor_produtos = sum(_dec(qtd * custo) for _, qtd, custo in linhas)
        nota = NFNota(
            chave_acesso=chave, numero=numero, serie='1',
            data_emissao=emissao, valor_total=valor_produtos,
            valor_produtos=valor_produtos, fornecedor_id=fid, restaurant_id=rid,
        )
        db.session.add(nota)
        db.session.flush()
        n_notas += 1
        total_compras += valor_produtos

        for num, (produto, qtd, custo) in enumerate(linhas, start=1):
            item = NFItem(
                nf_nota_id=nota.id, produto_id=produto.id, num_item=num,
                quantidade=qtd, valor_unitario=_dec(custo),
                valor_total=_dec(qtd * custo), unidade_medida=produto.unidade,
                cfop='5102',
            )
            db.session.add(item)
            db.session.flush()
            n_itens += 1

            db.session.add(EstoqueMovimentacao(
                produto_id=produto.id, quantidade=qtd, tipo='entrada',
                data_movimentacao=emissao, referencia=f'NF {numero}',
                ref_id=item.id, valor_unitario=_dec(custo), restaurant_id=rid,
            ))

    print(f'  compras: {n_notas} notas / {n_itens} itens, R$ {total_compras:,.2f}')

    # ---- 3. Baixa de estoque pelo consumo do dia ------------------------
    n_saidas = 0
    for dia in sorted(consumo):
        fechamento = datetime.combine(dia, time(23, 30))
        for pid, qtd in consumo[dia].items():
            produto = produtos[pid]
            qtd = round(qtd, 3)
            if qtd <= 0:
                continue
            db.session.add(EstoqueMovimentacao(
                produto_id=pid, quantidade=qtd, tipo='saída',
                data_movimentacao=fechamento, referencia='Consumo do dia',
                valor_unitario=produto.preco_unitario,
                observacao='Baixa automática pela ficha técnica dos pratos vendidos',
                restaurant_id=rid,
            ))
            n_saidas += 1
    print(f'  consumo: {n_saidas} baixas de estoque pela ficha técnica')

    # ---- 4. Desperdício -------------------------------------------------
    cats = garantir_categorias_desperdicio(rid)
    motivos = {
        'Sobras de Preparo': ('Aparas de limpeza da peça', 'Cozinha'),
        'Estragado': ('Passou do ponto na câmara', 'Estoque'),
        'Sobras de Clientes': ('Cliente não terminou a porção', 'Salão'),
        'Erro de Preparo': ('Fritura passou do ponto', 'Cozinha'),
        'Quebra e Perda': ('Perda na troca do barril', 'Bar'),
    }
    perecíveis = [p for p in produtos.values()
                  if p.categoria in ('Carnes', 'Hortifruti', 'Frios', 'Padaria')]

    n_desp = 0
    valor_desp = Decimal('0')
    for dia in sorted(vendas_por_dia):
        for _ in range(rnd.choice([1, 2, 2, 3, 4])):
            nome_cat = rnd.choices(
                list(cats), weights=[35, 15, 25, 15, 10], k=1)[0]
            cat = cats[nome_cat]

            if nome_cat == 'Quebra e Perda':
                produto = produtos.get(52)  # chopp barril
                if produto is None:
                    continue
            elif nome_cat == 'Estragado':
                # Perda de estoque: some a peça inteira, não um percentual da venda.
                produto = rnd.choice(perecíveis)
            else:
                produto = rnd.choice(perecíveis)

            consumido = consumo.get(dia, {}).get(produto.id, 0.0)
            if nome_cat == 'Estragado':
                qtd = round(max(0.3, float(produto.estoque_minimo or 1) * rnd.uniform(0.15, 0.4)), 3)
            else:
                qtd = round(max(0.1, consumido * rnd.uniform(0.05, 0.12)), 3)
            valor = _dec(qtd * float(produto.preco_unitario or 0))
            motivo, local = motivos[nome_cat]

            db.session.add(RegistroDesperdicio(
                data_registro=datetime.combine(dia, time(rnd.randint(15, 23), rnd.randint(0, 59))),
                categoria_id=cat.id, produto_id=produto.id,
                quantidade=qtd, unidade=produto.unidade, valor_estimado=valor,
                motivo=motivo, responsavel=rnd.choice(RESPONSAVEIS), local=local,
                restaurant_id=rid,
            ))
            n_desp += 1
            valor_desp += valor

            db.session.add(EstoqueMovimentacao(
                produto_id=produto.id, quantidade=qtd, tipo='saída',
                data_movimentacao=datetime.combine(dia, time(23, 40)),
                referencia='Desperdício', valor_unitario=produto.preco_unitario,
                restaurant_id=rid,
            ))

    pct = (valor_desp / total_compras * 100) if total_compras else 0
    print(f'  desperdício: {n_desp} registros, R$ {valor_desp:,.2f} ({pct:.1f}% das compras)')

    # ---- 5. Saldo de estoque = razão de movimentações -------------------
    db.session.flush()
    for produto in produtos.values():
        movs = EstoqueMovimentacao.query.filter_by(
            produto_id=produto.id, restaurant_id=rid).all()
        saldo = sum(m.quantidade if m.tipo == 'entrada' else -m.quantidade for m in movs)
        produto.estoque_atual = round(max(0.0, saldo), 3)

    db.session.commit()
    print(f'\nPronto. {dias} dias de operação do bar no ar — dashboard, estoque, '
          f'desperdício e previsão têm o que mastigar.')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', default='bar-da-vila')
    ap.add_argument('--dias', type=int, default=DIAS_PADRAO)
    ap.add_argument('--reset', action='store_true',
                    help='apaga o movimento do período antes de gerar')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        sys.exit(seed(args.slug, args.dias, args.reset))
