"""Pagamento recebido fora do sistema.

A cobrança automática está desligada por decisão ("fecho manual"), então esta
função é o único caminho entre o dinheiro entrar e o site continuar no ar.
"""
from datetime import date, timedelta

import pytest

from app.models.modelo_restaurante import Restaurante
from app.utils.planos import (
    PagamentoInvalido, _soma_meses, plano_efetivo, registrar_pagamento,
)


def bar(**kw):
    r = Restaurante(nome='Bar X', slug='bar-x')
    r.tipo_conta = kw.pop('tipo_conta', 'cliente')
    for k, v in kw.items():
        setattr(r, k, v)
    return r


class TestSomaMeses:
    def test_dia_que_nao_existe_no_mes_seguinte_encurta(self):
        # 31/01 + 1 mês não é 03/03: o dono lê a data e conta os dias.
        assert _soma_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
        assert _soma_meses(date(2028, 1, 31), 1) == date(2028, 2, 29)

    def test_atravessa_o_ano(self):
        assert _soma_meses(date(2026, 12, 15), 1) == date(2027, 1, 15)
        assert _soma_meses(date(2026, 11, 30), 13) == date(2027, 12, 30)

    def test_mes_de_31_dias_preserva_o_dia(self):
        assert _soma_meses(date(2026, 3, 31), 2) == date(2026, 5, 31)

    def test_dezembro_nao_estoura(self):
        # `mes + 1` daria 13 e o date() levantaria ValueError.
        assert _soma_meses(date(2026, 11, 30), 1) == date(2026, 12, 30)
        assert _soma_meses(date(2026, 6, 30), 6) == date(2026, 12, 30)


class TestRegistrarPagamento:
    def test_marca_a_data_e_ativa(self):
        r = bar()
        ate = registrar_pagamento(r, meses=1, plano='site',
                                  hoje=date(2026, 8, 15))
        assert ate == date(2026, 9, 15)
        assert r.plano_ate == date(2026, 9, 15)
        assert r.subscription_tier == 'site'
        assert r.subscription_status == 'active'

    def test_renovar_antes_de_vencer_soma(self):
        # Quem paga adiantado não pode perder os dias já comprados.
        r = bar(plano_ate=date(2026, 9, 15))
        ate = registrar_pagamento(r, meses=1, hoje=date(2026, 8, 15))
        assert ate == date(2026, 10, 15)

    def test_vencido_recomeca_de_hoje(self):
        # Somar sobre uma data velha venderia um período que já passou.
        r = bar(plano_ate=date(2026, 1, 10))
        ate = registrar_pagamento(r, meses=1, hoje=date(2026, 8, 15))
        assert ate == date(2026, 9, 15)

    def test_pagar_limpa_cancelamento(self):
        # plano_efetivo trata 'canceled' como vencido mesmo com data no futuro.
        r = bar(subscription_status='canceled')
        registrar_pagamento(r, meses=1, hoje=date(2026, 8, 15))
        assert plano_efetivo(r) == 'site'

    def test_pagar_encerra_o_trial(self):
        r = bar(trial_termina_em=date(2026, 8, 20))
        registrar_pagamento(r, meses=1, hoje=date(2026, 8, 15))
        assert r.trial_termina_em is None
        assert plano_efetivo(r) == 'site'

    def test_previa_precisa_ser_convertida_antes(self):
        r = bar(tipo_conta='demo')
        with pytest.raises(PagamentoInvalido, match='prévia'):
            registrar_pagamento(r, meses=1)

    @pytest.mark.parametrize('meses', [0, -1, 25, 'tres', None])
    def test_meses_fora_da_faixa_recusa(self, meses):
        with pytest.raises(PagamentoInvalido):
            registrar_pagamento(bar(), meses=meses)

    def test_plano_desconhecido_recusa(self):
        with pytest.raises(PagamentoInvalido, match='site ou pro'):
            registrar_pagamento(bar(), meses=1, plano='premium')

    def test_pago_sobrevive_ao_fim_do_trial(self):
        """O caso que motivou a função: pagou, trial acabou, site congelou."""
        r = bar(trial_termina_em=date(2026, 8, 1),
                plano_ate=None, subscription_tier='free')
        assert plano_efetivo(r) == 'free'  # antes de anotar o pagamento
        registrar_pagamento(r, meses=12, hoje=date(2026, 8, 15))
        assert plano_efetivo(r) == 'site'
        assert r.plano_ate == date(2027, 8, 15)


class TestConversaoNaoDaPlanoDeGraca:
    """`converter_demo` gravava tier='site' com `plano_ate` nulo.

    `plano_efetivo` lê data nula como "sem corte conhecido, vale o tier", então
    toda conversão saía com plano Site vitalício e os 14 dias de trial nunca
    valiam nada. Sem este teste, a regressão é invisível: tudo funciona, só não
    cobra.
    """

    def test_convertido_nao_nasce_com_tier_pago(self, app, session):
        from app.utils.demos import converter_demo
        r = Restaurante(nome='Bar Novo', slug='bar-novo')
        r.tipo_conta = 'demo'
        session.add(r)
        session.commit()

        converter_demo(r, 'dono@barnovo.com.br', 'senha-boa-123')
        session.commit()

        assert r.subscription_tier == 'free'
        assert r.plano_ate is None
        # Sem teste grátis (`FEIRA_DIAS_TRIAL=0`), a conversão nasce em free e
        # o acesso vem do pagamento. Com teste aberto, o acesso viria de
        # `trial_termina_em` — nunca do tier, que é o furo do plano vitalício.
        assert plano_efetivo(r) == 'free'
        assert r.trial_termina_em is None

    def test_passado_o_trial_sem_pagar_cai_para_free(self, app, session):
        from app.utils.demos import converter_demo
        r = Restaurante(nome='Bar Sumiu', slug='bar-sumiu')
        r.tipo_conta = 'demo'
        session.add(r)
        session.commit()

        converter_demo(r, 'dono@barsumiu.com.br', 'senha-boa-123')
        r.trial_termina_em = date.today() - timedelta(days=1)
        session.commit()

        assert plano_efetivo(r) == 'free'


class TestExpiracaoDaPrevia:
    """O prazo da prévia era escrito e nunca lido — ver `_publicavel`."""

    def test_demo_vencida_some_do_site_publico(self, app, session):
        from app.utils.site_router import tenant_por_slug
        ontem = date.today() - timedelta(days=1)
        r = Restaurante(nome='Bar Vencido', slug='bar-vencido')
        r.tipo_conta = 'demo'
        r.demo_expira_em = ontem
        session.add(r)
        session.commit()
        assert tenant_por_slug('bar-vencido') is None

    def test_demo_no_prazo_continua(self, app, session):
        from app.utils.site_router import tenant_por_slug
        r = Restaurante(nome='Bar No Prazo', slug='bar-no-prazo')
        r.tipo_conta = 'demo'
        r.demo_expira_em = date.today() + timedelta(days=5)
        session.add(r)
        session.commit()
        assert tenant_por_slug('bar-no-prazo') is not None

    def test_demo_que_vence_hoje_ainda_esta_no_ar(self, app, session):
        # O bar visitado hoje não pode sair do ar durante a conversa.
        from app.utils.site_router import tenant_por_slug
        r = Restaurante(nome='Bar Hoje', slug='bar-hoje')
        r.tipo_conta = 'demo'
        r.demo_expira_em = date.today()
        session.add(r)
        session.commit()
        assert tenant_por_slug('bar-hoje') is not None

    def test_cliente_com_data_velha_nao_e_afetado(self, app, session):
        # converter_demo zera a data, mas um registro antigo pode ter sobrado.
        from app.utils.site_router import tenant_por_slug
        r = Restaurante(nome='Bar Cliente', slug='bar-cliente')
        r.tipo_conta = 'cliente'
        r.demo_expira_em = date.today() - timedelta(days=90)
        session.add(r)
        session.commit()
        assert tenant_por_slug('bar-cliente') is not None

    def test_demo_sem_prazo_continua(self, app, session):
        from app.utils.site_router import tenant_por_slug
        r = Restaurante(nome='Bar Sem Prazo', slug='bar-sem-prazo')
        r.tipo_conta = 'demo'
        r.demo_expira_em = None
        session.add(r)
        session.commit()
        assert tenant_por_slug('bar-sem-prazo') is not None
