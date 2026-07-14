from datetime import datetime, date

from flask import render_template, redirect, url_for, flash, request, abort

from app.extensions import db
from app.models.modelo_promocao import Promocao
from app.routes.promocoes import bp
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
    promocoes = Promocao.query.filter_by(restaurant_id=rid).order_by(Promocao.data_cadastro.desc()).all()
    return render_template('promocoes/index.html', promocoes=promocoes, hoje=date.today())


def _ler_form():
    titulo = (request.form.get('titulo') or '').strip()
    descricao = (request.form.get('descricao') or '').strip() or None
    validade_str = (request.form.get('validade') or '').strip()
    ativo = request.form.get('ativo') == 'on'

    erros = []
    if len(titulo) < 2:
        erros.append('Informe o título da promoção.')
    validade = None
    if validade_str:
        try:
            validade = datetime.strptime(validade_str, '%Y-%m-%d').date()
        except ValueError:
            erros.append('Data de validade inválida.')
    return titulo, descricao, validade, ativo, erros


@bp.route('/nova', methods=['GET', 'POST'])
def nova():
    rid = _rid()
    if request.method == 'POST':
        titulo, descricao, validade, ativo, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('promocoes/form.html', promo=None)
        db.session.add(Promocao(titulo=titulo, descricao=descricao, validade=validade,
                                ativo=ativo, restaurant_id=rid))
        db.session.commit()
        flash('Promoção criada.', 'success')
        return redirect(url_for('promocoes.index'))
    return render_template('promocoes/form.html', promo=None)


@bp.route('/<int:promo_id>/editar', methods=['GET', 'POST'])
def editar(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    if request.method == 'POST':
        titulo, descricao, validade, ativo, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('promocoes/form.html', promo=promo)
        promo.titulo, promo.descricao, promo.validade, promo.ativo = titulo, descricao, validade, ativo
        db.session.commit()
        flash('Promoção atualizada.', 'success')
        return redirect(url_for('promocoes.index'))
    return render_template('promocoes/form.html', promo=promo)


@bp.route('/<int:promo_id>/toggle', methods=['POST'])
def toggle(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    promo.ativo = not promo.ativo
    db.session.commit()
    flash(('Promoção publicada.' if promo.ativo else 'Promoção ocultada.'), 'success')
    return redirect(url_for('promocoes.index'))


@bp.route('/<int:promo_id>/excluir', methods=['POST'])
def excluir(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    db.session.delete(promo)
    db.session.commit()
    flash('Promoção excluída.', 'warning')
    return redirect(url_for('promocoes.index'))
