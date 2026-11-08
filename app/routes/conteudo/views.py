from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user

from app.extensions import db
from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem, ProdutoSite
from app.routes.conteudo import bp
from app.utils.tenant import get_current_restaurant_id
from app.utils import blob, categorias
from app.utils.decorators import plano_minimo
from app.utils.formatacao_br import ler_moeda
from app.utils.planos import limite
from app.utils.vocabulario import tipo_do

# Motor genérico: cada tipo mapeia um model + a definição dos campos do formulário.
# campo = (nome, rótulo, tipo_widget, obrigatório)
#
# Widgets: 'text', 'textarea', 'check', 'number', 'preco', 'foto' e 'categoria'. O 'preco' existe
# separado do 'number' porque `number` grava int e dinheiro tem centavo — e
# porque o campo aceita o que o dono escreve ("R$ 18,50"), não um formato só.
# O 'foto' é upload de arquivo (mesmo `blob.enviar` da capa do site), com o
# endereço em texto como alternativa — e o que já está gravado continua valendo.
# O 'categoria' é texto com sugestão (`app/utils/categorias.py`): o expositor
# escreve o que quiser, mas vê a lista da Feira e as seções que já tem.
TIPOS = {
    'cardapio': {
        'model': DishCard, 'label': 'Cardápio', 'singular': 'prato', 'resumo': 'nome',
        'campos': [
            ('nome', 'Nome do prato', 'text', True),
            ('descricao', 'Descrição', 'textarea', False),
            # Não obrigatório: prato sob consulta existe, e forçar um número
            # faria o dono digitar 0 — que vira "R$ 0,00" na cara do cliente.
            ('preco', 'Preço (ex: 18,50 — deixe vazio para não mostrar)', 'preco', False),
            ('imagem', 'Foto do prato', 'foto', False),
            ('tag', 'Selo (ex: ★ O MAIS PEDIDO)', 'text', False),
            ('destaque', 'Destacar com borda', 'check', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
    'produtos': {
        'model': ProdutoSite, 'label': 'Produtos', 'singular': 'produto', 'resumo': 'nome',
        'campos': [
            ('nome', 'Nome do produto', 'text', True),
            ('descricao', 'Descrição', 'textarea', False),
            ('categoria', 'Categoria (comece a digitar: Geleias, Cerâmica, Crochê…)', 'categoria', False),
            ('preco', 'Preço (ex: 18,50 — deixe vazio para não mostrar)', 'preco', False),
            ('sob_encomenda', 'Sob encomenda', 'check', False),
            ('prazo_dias', 'Prazo de produção em dias úteis (deixe vazio se não souber)', 'number', False),
            ('imagem', 'Foto do produto', 'foto', False),
            ('destaque', 'Destacar na vitrine', 'check', False),
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
            ('imagem', 'Foto', 'foto', True),
            ('legenda', 'Legenda', 'text', False),
            ('ordem', 'Ordem', 'number', False),
        ],
    },
}


# Aba que só existe para um tipo de negócio: bar edita "cardapio", artesão
# edita "produtos". As demais (avaliações, equipe, galeria) servem aos dois.
SO_PARA = {'cardapio': 'bar', 'produtos': 'artesao'}


def _tipo(tipo):
    if tipo not in TIPOS:
        abort(404)
    return TIPOS[tipo]


def _tipos_do_negocio():
    """TIPOS que o negócio logado enxerga (esconde a aba do outro tipo)."""
    negocio = tipo_do(getattr(current_user, 'restaurante', None))
    return {k: v for k, v in TIPOS.items() if SO_PARA.get(k, negocio) == negocio}


# Número que vazio vira None (o rótulo diz "deixe vazio"), não 0.
SEM_PADRAO_NUMERICO = {'prazo_dias'}


def _form(tipo, t, item, sugestoes, valores=None):
    """Renderiza o formulário; `valores` (request.form) vence o item gravado,
    pra erro não apagar o que a pessoa acabou de digitar."""
    return render_template('conteudo/form.html', tipo=tipo, t=t, item=item,
                           tipos=_tipos_do_negocio(), sugestoes=sugestoes, valores=valores)


def _rid():
    rid = get_current_restaurant_id()
    if not rid:
        abort(403)
    return rid


@bp.route('/')
def home():
    return redirect(url_for('conteudo.index', tipo=next(iter(_tipos_do_negocio()))))


@bp.route('/<tipo>')
def index(tipo):
    t = _tipo(tipo)
    rid = get_current_restaurant_id()
    if not rid:
        flash('Não encontramos o seu negócio. Entre de novo.', 'danger')
        return redirect(url_for('auth.login'))
    Model = t['model']
    itens = Model.query.filter_by(restaurant_id=rid).order_by(Model.ordem, Model.id).all()
    return render_template('conteudo/index.html', tipo=tipo, t=t, tipos=_tipos_do_negocio(), itens=itens)


@bp.route('/<tipo>/novo', methods=['GET', 'POST'])
@bp.route('/<tipo>/<int:item_id>/editar', methods=['GET', 'POST'])
@plano_minimo('site')
def salvar(tipo, item_id=None):
    t = _tipo(tipo)
    rid = _rid()
    Model = t['model']
    item = Model.query.filter_by(id=item_id, restaurant_id=rid).first_or_404() if item_id else None
    sugestoes = []
    if any(w == 'categoria' for _, _, w, _ in t['campos']):
        # Só as do próprio expositor: categoria de outro tenant não vaza aqui.
        proprias = [c for (c,) in db.session.query(Model.categoria).filter(
            Model.restaurant_id == rid, Model.categoria.isnot(None)).distinct()]
        sugestoes = categorias.opcoes(sorted(proprias))

    if request.method == 'POST':
        # A foto sobe antes de qualquer gravação: arquivo recusado não pode
        # deixar produto criado pela metade.
        enviadas = {}
        for campo, label, widget, obrig in t['campos']:
            arquivo = request.files.get(f'{campo}_arquivo') if widget == 'foto' else None
            if arquivo is None or not arquivo.filename:
                continue
            try:
                enviadas[campo] = blob.enviar(arquivo, current_user.restaurante.slug or f's{rid}')
            except (blob.UploadInvalido, blob.UploadIndisponivel) as e:
                flash(f'A foto não subiu: {e}', 'danger')
                return _form(tipo, t, item, sugestoes, request.form), 400

        # Obrigatório faltando: avisa antes de tocar no item, e devolve o que
        # a pessoa digitou (o formulário não pode voltar vazio).
        for campo, label, widget, obrig in t['campos']:
            if not obrig or widget in ('check', 'preco', 'categoria', 'number'):
                continue
            if widget == 'foto' and enviadas.get(campo):
                continue
            if not (request.form.get(campo) or '').strip():
                flash(f'{label} é obrigatório.', 'danger')
                return _form(tipo, t, item, sugestoes, request.form), 400

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
            elif widget == 'preco':
                # `ler_moeda` devolve None pra vazio, zero e lixo — e None é
                # exatamente "não mostrar preço". Campo apagado limpa o preço;
                # campo preenchido que não foi lido avisa e mantém o anterior.
                bruto = (request.form.get(campo) or '').strip()
                valor = ler_moeda(bruto)
                if bruto and valor is None:
                    flash(f'Não entendi o preço "{bruto}"; mantive o anterior. '
                          f'Escreva só números, como 18,50.', 'warning')
                else:
                    setattr(item, campo, valor)
            elif widget == 'categoria':
                setattr(item, campo, categorias.canonizar(request.form.get(campo), sugestoes))
            elif widget == 'foto':
                # Sem arquivo novo, vale o endereço do campo de texto (que já
                # vem preenchido com o atual); apagá-lo tira a foto.
                v = enviadas.get(campo) or (request.form.get(campo) or '').strip()
                setattr(item, campo, v or None)
            elif widget == 'number':
                raw = (request.form.get(campo) or '').strip()
                val = int(raw) if raw.lstrip('-').isdigit() else None
                if val is None and campo not in SEM_PADRAO_NUMERICO:
                    val = 5 if campo == 'estrelas' else 0
                if campo == 'estrelas':
                    val = max(1, min(5, val))
                setattr(item, campo, val)
            else:
                v = (request.form.get(campo) or '').strip()
                setattr(item, campo, v or None)
        db.session.commit()
        flash('Salvo.', 'success')
        return redirect(url_for('conteudo.index', tipo=tipo))

    return _form(tipo, t, item, sugestoes)


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


@bp.post('/gerar-descricao-ia')
@plano_minimo('site')
def gerar_descricao_ia():
    """Gera descrição gastronômica com IA para o formulário de pratos."""
    from flask import jsonify
    from app.utils.ai_copy import gerar_descricao_prato

    dados = request.get_json(silent=True) or request.form
    nome = (dados.get('nome') or '').strip()
    vibe = (dados.get('vibe') or 'boteco').strip()
    detalhes = (dados.get('detalhes') or '').strip()

    if not nome:
        return jsonify({'ok': False, 'erro': 'Nome do prato é obrigatório.'}), 400

    descricao = gerar_descricao_prato(nome, vibe=vibe, detalhes=detalhes)
    return jsonify({'ok': True, 'descricao': descricao})

