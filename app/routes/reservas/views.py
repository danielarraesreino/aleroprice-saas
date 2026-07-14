from datetime import date

from flask import render_template, redirect, url_for, flash, request, abort

from app.extensions import db
from app.models.modelo_reserva import Reserva
from app.routes.reservas import bp
from app.utils.tenant import get_current_restaurant_id


@bp.route('/')
@bp.route('/index')
def index():
    """Lista as reservas do restaurante (painel do lojista)."""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    status = request.args.get('status', 'ativas')  # ativas | todas | pendente | confirmada | cancelada

    q = Reserva.query.filter_by(restaurant_id=restaurant_id)
    if status == 'ativas':
        q = q.filter(Reserva.status.in_(['pendente', 'confirmada']))
    elif status in Reserva.STATUS_VALIDOS:
        q = q.filter_by(status=status)

    reservas = q.order_by(Reserva.data.asc(), Reserva.hora.asc()).all()

    contagem = {
        'pendente': Reserva.query.filter_by(restaurant_id=restaurant_id, status='pendente').count(),
        'confirmada': Reserva.query.filter_by(restaurant_id=restaurant_id, status='confirmada').count(),
    }
    return render_template('reservas/index.html', reservas=reservas, filtro=status,
                           contagem=contagem, hoje=date.today())


def _mudar_status(reserva_id, novo_status):
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
    reserva = Reserva.query.filter_by(id=reserva_id, restaurant_id=restaurant_id).first_or_404()
    reserva.status = novo_status
    db.session.commit()
    return reserva


@bp.route('/<int:reserva_id>/confirmar', methods=['POST'])
def confirmar(reserva_id):
    r = _mudar_status(reserva_id, 'confirmada')
    flash(f'Reserva de {r.nome} confirmada.', 'success')
    return redirect(request.referrer or url_for('reservas.index'))


@bp.route('/<int:reserva_id>/cancelar', methods=['POST'])
def cancelar(reserva_id):
    r = _mudar_status(reserva_id, 'cancelada')
    flash(f'Reserva de {r.nome} cancelada.', 'warning')
    return redirect(request.referrer or url_for('reservas.index'))
