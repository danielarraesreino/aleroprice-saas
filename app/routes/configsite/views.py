from flask import render_template, redirect, url_for, flash, request

from app.extensions import db
from app.models.modelo_siteconfig import SiteConfig
from app.routes.configsite import bp
from app.routes.publico.views import SITE_DEFAULTS
from app.utils.tenant import get_current_restaurant_id
from app.utils.decorators import plano_minimo
from app.utils.temas import opcoes_de_tema, tema_valido
from app.utils.copy_site import opcoes_de_vibe, vibe_valida

CAMPOS = list(SITE_DEFAULTS.keys())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@plano_minimo('site')
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
            # Só grava o que o formulário mandou. Sem esta guarda, todo campo
            # de CAMPOS sem <input> correspondente era apagado no primeiro save
            # — e o formulário vive crescendo/agrupando.
            if campo not in request.form:
                continue
            valor = (request.form.get(campo) or '').strip()
            setattr(cfg, campo, valor or None)

        # Tema é <select> de preset, não texto livre: validar evita gravar
        # nome inválido e servir CSS vazio sem o dono entender por quê.
        tema = (request.form.get('tema') or '').strip()
        if tema and tema_valido(tema):
            cfg.tema = tema
        vibe = (request.form.get('vibe') or '').strip()
        if vibe and vibe_valida(vibe):
            cfg.vibe = vibe

        db.session.commit()
        flash('Site atualizado. Recarregue a página pública pra ver.', 'success')
        return redirect(url_for('configsite.index'))

    from app.models.modelo_restaurante import Restaurante
    rest = Restaurante.query.get(rid)
    return render_template('configsite/index.html', cfg=cfg, defaults=SITE_DEFAULTS,
                           temas=opcoes_de_tema(), vibes=opcoes_de_vibe(),
                           slug=(rest.slug if rest else None))
