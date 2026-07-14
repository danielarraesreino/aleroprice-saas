from flask import render_template, redirect, url_for, flash, request

from app.extensions import db
from app.models.modelo_siteconfig import SiteConfig
from app.routes.configsite import bp
from app.routes.publico.views import SITE_DEFAULTS
from app.utils.tenant import get_current_restaurant_id

CAMPOS = list(SITE_DEFAULTS.keys())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    rid = get_current_restaurant_id()
    if not rid:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()

    if request.method == 'POST':
        if not cfg:
            cfg = SiteConfig(restaurant_id=rid)
            db.session.add(cfg)
        for campo in CAMPOS:
            valor = (request.form.get(campo) or '').strip()
            setattr(cfg, campo, valor or None)
        db.session.commit()
        flash('Site atualizado. Recarregue a página pública pra ver.', 'success')
        return redirect(url_for('configsite.index'))

    return render_template('configsite/index.html', cfg=cfg, defaults=SITE_DEFAULTS)
