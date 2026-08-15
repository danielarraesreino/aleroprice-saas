"""Qual plano vale para este bar, agora.

Único lugar do código que combina tier + datas + status do Stripe. Não compare
`trial_termina_em` nem `plano_ate` espalhado por view: sempre pergunte aqui.

Planos
------
demo      prévia comercial; acesso amplo, sem cobrança, marcada como não oficial
trial     14 dias após a conversão — vale como `pro`, porque esconder o produto
          na janela em que a pessoa está decidindo é o oposto de vender
site      o site do bar (R$129): domínio próprio, CMS, reservas, agenda, promoções
pro       site + gestão (R$249): ficha técnica, estoque, NF-e, previsão, relatórios
free      pós-trial sem pagar: o site continua no ar, mas congelado

Degradação, não desligamento
----------------------------
Bar imprime QR e põe o link no Instagram. Derrubar o site pune o cliente do bar,
não o bar — e vira dano à nossa reputação. Quem não paga perde o *controle* do
site (não edita, não recebe reserva), nunca o endereço. Ver `RECURSOS_POR_PLANO`.
"""
from datetime import date, timedelta
import os

# Janela de teste grátis, contada a partir do cadastro ou da conversão
# demo->cliente. Um número, um lugar.
DIAS_DE_TRIAL = 14

def precos():
    """Preço de cada plano, de env. Um lugar só: a tela de planos e a landing
    de venda liam números diferentes (R$ 97 vs R$ 197) e divergiam sozinhas.

    O piso de mercado (pesquisa de agosto/2026): site institucional custa R$
    2.500-7.000 só para fazer, mais R$ 100-500/mês de manutenção e R$ 30-150/mês
    de hospedagem; plataforma de cardápio cobra mensalidade E R$ 400-2.000 de
    instalação. A mensalidade daqui fica abaixo da manutenção sozinha — e ainda
    inclui o site, o domínio e as atualizações.
    """
    return {
        'site': os.environ.get('FEIRA_PRECO_SITE', 'R$ 197'),
        'pro': os.environ.get('FEIRA_PRECO_PRO', 'R$ 347'),
    }


def taxa_de_instalacao():
    """Cobrança única de registrar o domínio, montar com as fotos e publicar.

    Sem a env a linha some da proposta — dá para testar o discurso antes de
    fixar o valor, como já se faz com a mensalidade.
    """
    return (os.environ.get('FEIRA_TAXA_SETUP') or '').strip() or None


# Convite de fundador: o desconto que o vendedor concede na mesa.
#
# Existe como objeto, e não como preço menor na tabela, por um motivo comercial:
# preço baixo na vitrine vira o valor do produto e não volta mais. Concedido por
# código, com prazo e número de vagas, ele continua sendo um favor — "as três
# primeiras casas de Barão viram meu portfólio" — e o preço cheio segue de pé
# para todo mundo depois.
#
# FEIRA_CONVITE define o código; sem ele nada disso aparece em lugar nenhum.
def convite():
    codigo = (os.environ.get('FEIRA_CONVITE') or '').strip()
    if not codigo:
        return None
    return {
        'codigo': codigo.upper(),
        'preco_site': os.environ.get('FEIRA_CONVITE_PRECO_SITE', 'R$ 129'),
        'preco_pro': os.environ.get('FEIRA_CONVITE_PRECO_PRO', 'R$ 249'),
        'vagas': os.environ.get('FEIRA_CONVITE_VAGAS', '5'),
        'rotulo': os.environ.get('FEIRA_CONVITE_ROTULO', 'Casa fundadora'),
    }


def conferir_convite(codigo):
    """O código digitado vale? Devolve o convite ou None.

    Comparação sem diferenciar maiúscula e espaço: o vendedor dita o código em
    voz alta dentro de um bar barulhento, e o dono digita como ouviu.
    """
    convidado = convite()
    if not convidado or not codigo:
        return None
    return convidado if (codigo or '').strip().upper() == convidado['codigo'] else None


# Ordem de poder. Usada por `plano_minimo` para comparar.
ESCALA = ('free', 'site', 'pro')

# O que cada plano libera. `demo` e `trial` são resolvidos como `pro`.
RECURSOS_POR_PLANO = {
    'free': set(),
    'site': {'cms', 'reservas', 'agenda', 'promocoes', 'temas', 'dominio'},
    'pro': {'cms', 'reservas', 'agenda', 'promocoes', 'temas', 'dominio',
            'gestao', 'relatorios'},
}

# Teto de itens de conteúdo no plano free. Não é punição: é o suficiente pra
# manter um site honesto no ar depois que o trial acaba.
LIMITES_FREE = {'cardapio': 5, 'galeria': 3, 'avaliacoes': 3, 'equipe': 3,
                'diferenciais': 3}


def plano_efetivo(rest):
    """Plano que vale hoje pra este restaurante.

    Devolve um de: 'demo', 'trial', 'free', 'site', 'pro'.
    """
    if rest is None:
        return 'free'

    if getattr(rest, 'tipo_conta', None) == 'demo':
        return 'demo'

    hoje = date.today()
    tier = (rest.subscription_tier or 'free').lower()
    status = (rest.subscription_status or '').lower()

    # Assinatura em dia. `plano_ate` nulo = sem data de corte conhecida (é o
    # caso dos tenants criados antes do campo existir) — vale o tier.
    if tier in ('site', 'pro'):
        vencido = rest.plano_ate is not None and hoje > rest.plano_ate
        cancelado = status in ('canceled', 'past_due')
        if not vencido and not cancelado:
            return tier

    # Trial vale como pro: mostra o produto inteiro enquanto a pessoa decide.
    if rest.trial_termina_em and hoje <= rest.trial_termina_em:
        return 'trial'

    return 'free'


def _recursos(plano):
    if plano in ('demo', 'trial'):
        return RECURSOS_POR_PLANO['pro']
    return RECURSOS_POR_PLANO.get(plano, set())


def pode(rest, recurso):
    """Este bar tem direito a este recurso hoje?"""
    return recurso in _recursos(plano_efetivo(rest))


def nivel(plano):
    """Posição na escala free < site < pro. demo/trial contam como pro."""
    if plano in ('demo', 'trial'):
        return ESCALA.index('pro')
    return ESCALA.index(plano) if plano in ESCALA else 0


def atende(rest, minimo):
    """O plano do bar alcança pelo menos `minimo` ('site' ou 'pro')?"""
    return nivel(plano_efetivo(rest)) >= nivel(minimo)


def limite(rest, tipo):
    """Quantos itens deste tipo de conteúdo o bar pode ter. None = ilimitado."""
    if atende(rest, 'site'):
        return None
    return LIMITES_FREE.get(tipo)


class PagamentoInvalido(Exception):
    """Recusa de registro de pagamento. Mensagem é pra ler em pé, no bar."""


def _soma_meses(quando, meses):
    """Mesmo dia, N meses à frente, encurtando quando o mês não tem o dia.

    31/01 + 1 mês = 28/02 (ou 29 em bissexto). Sem isto, o dia 31 estouraria e
    a alternativa comum — somar 30 dias — faz a data do bar andar para trás
    todo mês, e o dono percebe.
    """
    total = (quando.month - 1) + meses
    ano = quando.year + total // 12
    mes = total % 12 + 1
    ultimo = 31 if mes == 12 else (date(ano, mes + 1, 1) - timedelta(days=1)).day
    return date(ano, mes, min(quando.day, ultimo))


def registrar_pagamento(rest, meses=1, plano='site', hoje=None):
    """Dinheiro que entrou fora do sistema: PIX, maquininha, transferência.

    A cobrança automática foi abortada de propósito ("fecho manual"), e sem esta
    função não havia caminho nenhum: `plano_ate` só era escrito pelo webhook do
    Stripe. Na prática, o bar que pagava no PIX seguia contando os 14 dias de
    trial e caía em `free` — o dono paga e o site congela.

    Renovar antes de vencer **soma**, não substitui: a base é o vencimento atual
    quando ele está no futuro, senão hoje. Quem paga adiantado não perde os dias
    que já comprou, e quem some por dois meses recomeça de hoje em vez de comprar
    um período que já passou.

    `subscription_status` volta pra 'active' porque `plano_efetivo` trata
    'canceled'/'past_due' como vencido — pagar de novo tem que limpar o estado
    anterior, ou o bar continua degradado com a data certa.
    """
    if rest is None:
        raise PagamentoInvalido('bar não encontrado')
    if plano not in ('site', 'pro'):
        raise PagamentoInvalido(f'plano "{plano}" não existe — use site ou pro')
    try:
        meses = int(meses)
    except (TypeError, ValueError):
        raise PagamentoInvalido('quantidade de meses inválida')
    if not 1 <= meses <= 24:
        raise PagamentoInvalido('meses tem que ficar entre 1 e 24')
    if getattr(rest, 'tipo_conta', None) == 'demo':
        raise PagamentoInvalido(
            'esta ainda é uma prévia. Converta em conta do dono antes de '
            'registrar o pagamento.')

    hoje = hoje or date.today()
    base = rest.plano_ate if rest.plano_ate and rest.plano_ate > hoje else hoje

    rest.plano_ate = _soma_meses(base, meses)
    rest.subscription_tier = plano
    rest.subscription_status = 'active'
    # O trial deixa de importar assim que há pagamento; zerar evita que
    # `dias_de_trial_restantes` mostre "faltam 3 dias" pra quem já pagou.
    rest.trial_termina_em = None
    return rest.plano_ate


def dias_de_trial_restantes(rest):
    """Para o aviso no painel. None quando não está em trial."""
    if rest is None or not rest.trial_termina_em:
        return None
    if plano_efetivo(rest) != 'trial':
        return None
    return (rest.trial_termina_em - date.today()).days


def rotulo(plano):
    return {
        'demo': 'Prévia',
        'trial': 'Teste grátis',
        'free': 'Gratuito',
        'site': 'Site',
        'pro': 'Pro',
    }.get(plano, plano)
