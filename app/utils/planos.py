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
from datetime import date
import os

# Janela de teste grátis, contada a partir do cadastro ou da conversão
# demo->cliente. Um número, um lugar.
DIAS_DE_TRIAL = 14

def precos():
    """Preço de cada plano, de env. Um lugar só: a tela de planos e a landing
    de venda liam números diferentes (R$ 97 vs R$ 197) e divergiam sozinhas."""
    return {
        'site': os.environ.get('FEIRA_PRECO_SITE', 'R$ 129'),
        'pro': os.environ.get('FEIRA_PRECO_PRO', 'R$ 249'),
    }


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
