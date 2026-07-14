"""Regras de exibição da promoção.

O caso motivador é o "Lanche de Quarta": promoção que se repete toda semana.
Ela precisa aparecer no site a semana inteira (é anúncio — o cliente tem que
saber na segunda que quarta tem lanche) e só ganhar destaque no dia.
"""
from datetime import date, timedelta

import pytest

from app.models.modelo_promocao import Promocao


HOJE = date.today()


def _quarta_mais_proxima():
    return HOJE + timedelta(days=(2 - HOJE.weekday()) % 7)


def test_recorrente_aparece_todos_os_dias_da_semana():
    """Não some nos outros dias: quem entra no site na segunda precisa ver."""
    promo = Promocao(titulo='Lanche de Quarta', dia_semana=2, ativo=True)
    assert promo.vigente is True


def test_recorrente_destaca_apenas_no_dia():
    promo = Promocao(titulo='Lanche de Quarta', dia_semana=2, ativo=True)
    assert promo.acontece_hoje is (HOJE.weekday() == 2)


def test_recorrente_tem_rotulo_do_dia():
    assert Promocao(titulo='x', dia_semana=2, ativo=True).rotulo == 'TODA QUARTA'
    assert Promocao(titulo='x', dia_semana=4, ativo=True).rotulo == 'TODA SEXTA'


def test_inativa_nunca_aparece():
    promo = Promocao(titulo='x', dia_semana=2, ativo=False)
    assert promo.vigente is False
    assert promo.acontece_hoje is False


def test_agendada_nao_aparece_antes_de_comecar():
    promo = Promocao(titulo='Feijoada de aniversário', ativo=True,
                     data_inicio=HOJE + timedelta(days=10))
    assert promo.vigente is False
    assert promo.agendada is True


def test_agendada_aparece_quando_chega_a_data():
    promo = Promocao(titulo='x', ativo=True, data_inicio=HOJE)
    assert promo.vigente is True
    assert promo.agendada is False


def test_expirada_nao_aparece():
    promo = Promocao(titulo='x', ativo=True, validade=HOJE - timedelta(days=1))
    assert promo.vigente is False


def test_validade_hoje_ainda_vale():
    """Último dia é dia válido — não pode sumir de manhã."""
    assert Promocao(titulo='x', ativo=True, validade=HOJE).vigente is True


def test_recorrente_com_prazo_para_de_valer_depois_do_fim():
    """'Lanche de Quarta até dezembro': recorrência + janela juntas."""
    promo = Promocao(titulo='x', dia_semana=2, ativo=True,
                     validade=HOJE - timedelta(days=1))
    assert promo.vigente is False
    assert promo.acontece_hoje is False


def test_pontual_sem_datas_vale_sempre():
    promo = Promocao(titulo='x', ativo=True)
    assert promo.vigente is True
    assert promo.rotulo is None
