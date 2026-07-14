from datetime import datetime, date

from flask import render_template, redirect, url_for, flash, request, abort

from app.extensions import db
from app.models.modelo_evento import Evento
from app.routes.agenda import bp
from app.utils.tenant import get_current_restaurant_id


def _rid():
    rid = get_current_restaurant_id()
    if not rid:
        abort(403)
    return rid


@bp.route('/')
@bp.route('/index')
def index():
    rid = get_current_restaurant_id()
    if not rid:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))
    eventos = Evento.query.filter_by(restaurant_id=rid).order_by(Evento.data.asc()).all()
    return render_template('agenda/index.html', eventos=eventos, hoje=date.today())


def _ler_form():
    titulo = (request.form.get('titulo') or '').strip()
    descricao = (request.form.get('descricao') or '').strip() or None
    data_str = (request.form.get('data') or '').strip()
    hora = (request.form.get('hora') or '').strip() or None
    ativo = request.form.get('ativo') == 'on'

    erros = []
    if len(titulo) < 2:
        erros.append('Informe o título do evento.')
    data_ev = None
    try:
        data_ev = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        erros.append('Escolha uma data válida.')
    return titulo, descricao, data_ev, hora, ativo, erros


@bp.route('/novo', methods=['GET', 'POST'])
def novo():
    rid = _rid()
    if request.method == 'POST':
        titulo, descricao, data_ev, hora, ativo, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('agenda/form.html', evento=None)
        db.session.add(Evento(titulo=titulo, descricao=descricao, data=data_ev,
                              hora=hora, ativo=ativo, restaurant_id=rid))
        db.session.commit()
        flash('Evento criado.', 'success')
        return redirect(url_for('agenda.index'))
    return render_template('agenda/form.html', evento=None)


@bp.route('/<int:evento_id>/editar', methods=['GET', 'POST'])
def editar(evento_id):
    rid = _rid()
    evento = Evento.query.filter_by(id=evento_id, restaurant_id=rid).first_or_404()
    if request.method == 'POST':
        titulo, descricao, data_ev, hora, ativo, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('agenda/form.html', evento=evento)
        evento.titulo, evento.descricao, evento.data = titulo, descricao, data_ev
        evento.hora, evento.ativo = hora, ativo
        db.session.commit()
        flash('Evento atualizado.', 'success')
        return redirect(url_for('agenda.index'))
    return render_template('agenda/form.html', evento=evento)


@bp.route('/<int:evento_id>/toggle', methods=['POST'])
def toggle(evento_id):
    rid = _rid()
    evento = Evento.query.filter_by(id=evento_id, restaurant_id=rid).first_or_404()
    evento.ativo = not evento.ativo
    db.session.commit()
    flash(('Evento publicado.' if evento.ativo else 'Evento ocultado.'), 'success')
    return redirect(url_for('agenda.index'))


@bp.route('/<int:evento_id>/excluir', methods=['POST'])
def excluir(evento_id):
    rid = _rid()
    evento = Evento.query.filter_by(id=evento_id, restaurant_id=rid).first_or_404()
    db.session.delete(evento)
    db.session.commit()
    flash('Evento excluído.', 'warning')
    return redirect(url_for('agenda.index'))
