"""Funil da campanha de prospecção, num lugar só.

Sem isto não dá pra responder a única pergunta que importa depois de mandar 60
links: **quantos abriram?** O projeto não tem analytics, e reserva sozinha não
serve de métrica porque falta o denominador.

Painel interno: fica atrás do login e só o dono do produto usa. Não é feature
de cliente — por isso não entra em nenhum plano.
"""
from flask import render_template, abort

from app.extensions import db
from app.models.modelo_reserva import Reserva
from app.models.modelo_restaurante import Restaurante
from app.routes.campanha import bp
from app.utils.operador import e_operador as _e_operador
from app.utils.planos import plano_efetivo


@bp.route('/')
@bp.route('/index')
def index():
    if not _e_operador():
        abort(404)   # 404 e não 403: painel interno não se anuncia

    tenants = Restaurante.query.order_by(Restaurante.id.desc()).all()

    reservas_por_tenant = dict(
        db.session.query(Reserva.restaurant_id, db.func.count(Reserva.id))
        .group_by(Reserva.restaurant_id).all()
    )

    linhas = []
    for t in tenants:
        linhas.append({
            'id': t.id,
            'nome': t.nome,
            'slug': t.slug,
            'tipo': t.tipo_conta or 'cliente',
            'plano': plano_efetivo(t),
            'fonte': t.demo_fonte,
            'visitas': t.demo_visitas or 0,
            'aberta_em': t.demo_primeira_visita,
            'expira': t.demo_expira_em,
            'reservas': reservas_por_tenant.get(t.id, 0),
        })

    demos = [l for l in linhas if l['tipo'] == 'demo']
    funil = {
        'demos': len(demos),
        'abertas': sum(1 for l in demos if l['visitas'] > 0),
        'com_reserva': sum(1 for l in demos if l['reservas'] > 0),
        'clientes': sum(1 for l in linhas if l['tipo'] != 'demo'),
        'pagantes': sum(1 for l in linhas if l['plano'] in ('site', 'pro')),
    }
    return render_template('campanha/index.html', linhas=linhas, funil=funil)
