from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import db
from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem
from app.routes.conteudo import bp
from app.utils.tenant import get_current_restaurant_id
from app.utils.decorators import plano_minimo
from app.utils.planos import limite

# Motor genérico: cada tipo mapeia um model + a definição dos campos do formulário.
# campo = (nome, rótulo, tipo_widget, obrigatório)
TIPOS = {
    'cardapio': {
        'model': DishCard, 'label': 'Cardápio', 'singular': 'prato', 'resumo': 'nome',
        'campos': [
            ('nome', 'Nome do prato', 'text', True),
            ('descricao', 'Descrição', 'textarea', False),
            ('imagem', 'Imagem (caminho em static, ex: img/bar/foto-5.jpg, ou URL)', 'text', False),
            ('tag', 'Selo (ex: ★ O MAIS PEDIDO)', 'text', False),
            ('destaque', 'Destacar com borda', 'check', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
    'avaliacoes': {
        'model': Review, 'label': 'Avaliações', 'singular': 'avaliação', 'resumo': 'autor',
        'campos': [
            ('autor', 'Autor', 'text', True),
            ('texto', 'Texto da avaliação', 'textarea', True),
            ('estrelas', 'Estrelas (1 a 5)', 'number', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
    'equipe': {
        'model': TeamMember, 'label': 'Equipe', 'singular': 'pessoa', 'resumo': 'nome',
        'campos': [
            ('nome', 'Nome', 'text', True),
            ('papel', 'Papel (ex: Cozinheira e anfitriã)', 'text', False),
            ('emoji', 'Emoji (ex: 👩‍🍳)', 'text', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
    'galeria': {
        'model': GalleryItem, 'label': 'Galeria', 'singular': 'foto', 'resumo': 'imagem',
        'campos': [
            ('imagem', 'Imagem (caminho em static ou URL)', 'text', True),
            ('legenda', 'Legenda', 'text', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
}


def _tipo(tipo):
    if tipo not in TIPOS:
        abort(404)
    return TIPOS[tipo]


def _rid():
    rid = get_current_restaurant_id()
    if not rid:
        abort(403)
    return rid


@bp.route('/')
def home():
    return redirect(url_for('conteudo.index', tipo='cardapio'))


@bp.route('/<tipo>')
def index(tipo):
    t = _tipo(tipo)
    rid = get_current_restaurant_id()
    if not rid:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))
    Model = t['model']
    itens = Model.query.filter_by(restaurant_id=rid).order_by(Model.ordem, Model.id).all()
    return render_template('conteudo/index.html', tipo=tipo, t=t, tipos=TIPOS, itens=itens)


@bp.route('/<tipo>/novo', methods=['GET', 'POST'])
@bp.route('/<tipo>/<int:item_id>/editar', methods=['GET', 'POST'])
@plano_minimo('site')
def salvar(tipo, item_id=None):
    t = _tipo(tipo)
    rid = _rid()
    Model = t['model']
    item = Model.query.filter_by(id=item_id, restaurant_id=rid).first_or_404() if item_id else None

    if request.method == 'POST':
        novo = item is None
        if novo:
            # Limite por plano, checado uma vez só: o motor é genérico, então
            # este `if` cobre cardápio, avaliações, equipe e galeria juntos.
            teto = limite(current_user.restaurante, tipo)
            if teto is not None and Model.query.filter_by(restaurant_id=rid).count() >= teto:
                flash(f'Seu plano permite até {teto} itens em {t["label"]}. '
                      f'Faça upgrade para adicionar mais.', 'warning')
                return redirect(url_for('conteudo.index', tipo=tipo))
            item = Model(restaurant_id=rid, ativo=True)
            db.session.add(item)
        for campo, label, widget, obrig in t['campos']:
            if widget == 'check':
                setattr(item, campo, request.form.get(campo) == 'on')
            elif widget == 'number':
                raw = (request.form.get(campo) or '').strip()
                val = int(raw) if raw.lstrip('-').isdigit() else None
                if val is None:
                    val = 5 if campo == 'estrelas' else 0
                if campo == 'estrelas':
                    val = max(1, min(5, val))
                setattr(item, campo, val)
            else:
                v = (request.form.get(campo) or '').strip()
                if obrig and not v:
                    flash(f'{label} é obrigatório.', 'danger')
                    return render_template('conteudo/form.html', tipo=tipo, t=t, item=item, tipos=TIPOS)
                setattr(item, campo, v or None)
        db.session.commit()
        flash('Salvo.', 'success')
        return redirect(url_for('conteudo.index', tipo=tipo))

    return render_template('conteudo/form.html', tipo=tipo, t=t, item=item, tipos=TIPOS)


@bp.route('/<tipo>/<int:item_id>/toggle', methods=['POST'])
@plano_minimo('site')
def toggle(tipo, item_id):
    t = _tipo(tipo)
    rid = _rid()
    item = t['model'].query.filter_by(id=item_id, restaurant_id=rid).first_or_404()
    item.ativo = not item.ativo
    db.session.commit()
    return redirect(url_for('conteudo.index', tipo=tipo))


@bp.route('/<tipo>/<int:item_id>/excluir', methods=['POST'])
@plano_minimo('site')
def excluir(tipo, item_id):
    t = _tipo(tipo)
    rid = _rid()
    item = t['model'].query.filter_by(id=item_id, restaurant_id=rid).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Excluído.', 'warning')
    return redirect(url_for('conteudo.index', tipo=tipo))
