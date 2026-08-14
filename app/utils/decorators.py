from functools import wraps

from flask import redirect, url_for, flash
from flask_login import current_user

from app.utils.planos import atende, plano_efetivo


def plano_minimo(minimo):
    """Exige plano >= `minimo` ('site' ou 'pro').

    Toda a decisão mora em `app/utils/planos.py`; aqui é só o desvio de rota.
    Trial e demo passam como pro — quem está decidindo precisa ver o produto.
    """
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            restaurante = current_user.restaurante
            if not atende(restaurante, minimo):
                if minimo == 'pro':
                    msg = ('Esta funcionalidade é do plano Pro. '
                           'Faça o upgrade para desbloquear a gestão completa.')
                else:
                    msg = ('Seu período de teste terminou. Escolha um plano para '
                           'voltar a editar o site — ele continua no ar.')
                flash(msg, 'warning')
                return redirect(url_for('dashboard.upgrade'))

            return f(*args, **kwargs)
        return wrapper
    return decorador


# Mantido para as rotas que já usavam: relatórios do dashboard.
pro_required = plano_minimo('pro')


__all__ = ['plano_minimo', 'pro_required', 'plano_efetivo']
