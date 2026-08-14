"""Quem opera a campanha — o dono do produto, não o dono do bar.

O painel de campanha e o Modo Campo mexem em tenant que não é o do usuário
logado (prévia de bar que ainda não é cliente). Isso é o oposto da regra geral
do app, onde tudo filtra por `restaurant_id`. A exceção fica isolada aqui, com
um critério só: **o primeiro tenant é o operador**.

É proposital que não seja uma coluna nem uma env var. Coluna daria pra flipar
sem querer; env var some num deploy. `min(Restaurante.id)` não muda.
"""
from flask_login import current_user

from app.models.modelo_restaurante import Restaurante


def e_operador(usuario=None):
    usuario = current_user if usuario is None else usuario
    rest = getattr(usuario, 'restaurante', None)
    if rest is None:
        return False
    primeiro = Restaurante.query.order_by(Restaurante.id).first()
    return primeiro is not None and rest.id == primeiro.id
