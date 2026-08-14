from datetime import datetime, date

from flask import render_template, redirect, url_for, flash, request, abort

from app.extensions import db
from app.models.modelo_promocao import Promocao, DIAS_SEMANA, DIAS_SEMANA_MAP
from app.routes.promocoes import bp
from app.utils.tenant import get_current_restaurant_id
from app.utils.decorators import plano_minimo


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


def _data(valor, rotulo, erros):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        erros.append(f'{rotulo} inválida.')
        return None


def _ler_form():
    titulo = (request.form.get('titulo') or '').strip()
    descricao = (request.form.get('descricao') or '').strip() or None
    ativo = request.form.get('ativo') == 'on'

    erros = []
    if len(titulo) < 2:
        erros.append('Informe o título da promoção.')

    data_inicio = _data((request.form.get('data_inicio') or '').strip(), 'Data de início', erros)
    validade = _data((request.form.get('validade') or '').strip(), 'Data de término', erros)

    if data_inicio and validade and data_inicio > validade:
        erros.append('A data de início não pode ser depois do término.')

    # '' = promoção pontual (sem recorrência)
    dia_str = (request.form.get('dia_semana') or '').strip()
    dia_semana = None
    if dia_str:
        try:
            dia_semana = int(dia_str)
            if dia_semana not in DIAS_SEMANA_MAP:
                raise ValueError
        except ValueError:
            erros.append('Dia da semana inválido.')

    return {
        'titulo': titulo, 'descricao': descricao, 'ativo': ativo,
        'data_inicio': data_inicio, 'validade': validade, 'dia_semana': dia_semana,
    }, erros


@bp.route('/nova', methods=['GET', 'POST'])
@plano_minimo('site')
def nova():
    rid = _rid()
    if request.method == 'POST':
        dados, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('promocoes/form.html', promo=None, dias=DIAS_SEMANA)
        db.session.add(Promocao(restaurant_id=rid, **dados))
        db.session.commit()
        flash('Promoção criada.', 'success')
        return redirect(url_for('promocoes.index'))
    return render_template('promocoes/form.html', promo=None, dias=DIAS_SEMANA)


@bp.route('/<int:promo_id>/editar', methods=['GET', 'POST'])
@plano_minimo('site')
def editar(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    if request.method == 'POST':
        dados, erros = _ler_form()
        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('promocoes/form.html', promo=promo, dias=DIAS_SEMANA)
        for campo, valor in dados.items():
            setattr(promo, campo, valor)
        db.session.commit()
        flash('Promoção atualizada.', 'success')
        return redirect(url_for('promocoes.index'))
    return render_template('promocoes/form.html', promo=promo, dias=DIAS_SEMANA)


@bp.route('/<int:promo_id>/toggle', methods=['POST'])
@plano_minimo('site')
def toggle(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    promo.ativo = not promo.ativo
    db.session.commit()
    flash(('Promoção publicada.' if promo.ativo else 'Promoção ocultada.'), 'success')
    return redirect(url_for('promocoes.index'))


@bp.route('/<int:promo_id>/excluir', methods=['POST'])
@plano_minimo('site')
def excluir(promo_id):
    rid = _rid()
    promo = Promocao.query.filter_by(id=promo_id, restaurant_id=rid).first_or_404()
    db.session.delete(promo)
    db.session.commit()
    flash('Promoção excluída.', 'warning')
    return redirect(url_for('promocoes.index'))
