"""Resolução de plano: tier × datas × status, num lugar só.

Estas regras decidem quem paga e o que cada um vê. Antes existia só
`subscription_tier != 'pro'` espalhado em 3 rotas, sem trial e sem data.
"""
from datetime import date, timedelta

import pytest

from app.models.modelo_restaurante import Restaurante
from app.utils.planos import (
    atende, dias_de_trial_restantes, limite, plano_efetivo, pode,
)

HOJE = date.today()
ONTEM = HOJE - timedelta(days=1)
AMANHA = HOJE + timedelta(days=1)


def bar(**kwargs):
    """Restaurante solto (sem banco) — plano_efetivo é função pura."""
    r = Restaurante(nome='Bar X')
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


@pytest.mark.parametrize('atributos,esperado', [
    # prévia comercial ganha antes de tudo
    ({'tipo_conta': 'demo'}, 'demo'),
    ({'tipo_conta': 'demo', 'subscription_tier': 'free'}, 'demo'),

    # assinatura em dia
    ({'subscription_tier': 'site'}, 'site'),
    ({'subscription_tier': 'pro'}, 'pro'),
    ({'subscription_tier': 'pro', 'plano_ate': AMANHA}, 'pro'),

    # assinatura vencida ou cancelada cai pra free
    ({'subscription_tier': 'pro', 'plano_ate': ONTEM}, 'free'),
    ({'subscription_tier': 'pro', 'subscription_status': 'canceled'}, 'free'),
    ({'subscription_tier': 'site', 'subscription_status': 'past_due'}, 'free'),

    # trial
    ({'trial_termina_em': AMANHA}, 'trial'),
    ({'trial_termina_em': HOJE}, 'trial'),          # último dia ainda vale
    ({'trial_termina_em': ONTEM}, 'free'),

    # pagante vencido com trial ainda válido volta pro trial, não pro free
    ({'subscription_tier': 'pro', 'plano_ate': ONTEM,
      'trial_termina_em': AMANHA}, 'trial'),

    # sem nada
    ({}, 'free'),
])
def test_plano_efetivo(atributos, esperado):
    assert plano_efetivo(bar(**atributos)) == esperado


def test_sem_restaurante_e_free():
    assert plano_efetivo(None) == 'free'


def test_tenant_antigo_sem_plano_ate_continua_valendo():
    """Campo nasceu por ALTER TABLE: quem já pagava tem plano_ate nulo e não
    pode ser rebaixado por isso."""
    assert plano_efetivo(bar(subscription_tier='pro', plano_ate=None)) == 'pro'


def test_trial_da_acesso_de_pro():
    """Esconder o produto durante a decisão é o oposto de vender."""
    r = bar(trial_termina_em=AMANHA)
    assert pode(r, 'gestao')
    assert pode(r, 'reservas')
    assert atende(r, 'pro')


def test_free_nao_edita_mas_o_site_fica_no_ar():
    r = bar(trial_termina_em=ONTEM)
    assert not pode(r, 'cms')
    assert not pode(r, 'reservas')
    assert not atende(r, 'site')


def test_site_nao_alcanca_gestao():
    r = bar(subscription_tier='site')
    assert pode(r, 'reservas')
    assert not pode(r, 'gestao')
    assert atende(r, 'site')
    assert not atende(r, 'pro')


def test_limite_de_conteudo_so_no_free():
    assert limite(bar(subscription_tier='site'), 'cardapio') is None
    assert limite(bar(trial_termina_em=AMANHA), 'cardapio') is None
    assert limite(bar(), 'cardapio') == 5
    assert limite(bar(), 'galeria') == 3
    assert limite(bar(), 'tipo-que-nao-existe') is None


def test_dias_de_trial_restantes():
    assert dias_de_trial_restantes(bar(trial_termina_em=HOJE + timedelta(days=3))) == 3
    assert dias_de_trial_restantes(bar(trial_termina_em=ONTEM)) is None   # já era
    assert dias_de_trial_restantes(bar(subscription_tier='pro')) is None  # não é trial
    assert dias_de_trial_restantes(None) is None


def test_rate_limit_conta_janela(app):
    """Contenção de script bobo em /reservar e /cadastro.

    Roda com TESTING desligado de propósito: o helper é inerte sob TESTING
    (o contador é global do processo e vazaria entre testes), então testá-lo
    dentro do app de teste não exercitaria nada.
    """
    from app.utils.tenant import limite_excedido, _ACESSOS

    app.config['TESTING'] = False
    try:
        _ACESSOS.clear()
        chave = 'teste:1.2.3.4'
        assert all(not limite_excedido(chave, maximo=3, janela_segundos=60)
                   for _ in range(3))
        assert limite_excedido(chave, maximo=3, janela_segundos=60)

        # chave diferente não é afetada
        assert not limite_excedido('teste:5.6.7.8', maximo=3, janela_segundos=60)
    finally:
        app.config['TESTING'] = True
        _ACESSOS.clear()
