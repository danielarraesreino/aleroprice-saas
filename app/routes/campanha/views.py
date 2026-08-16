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

# `demo_fonte` dos bares de demonstração (ver `app/data/leads/vitrine-*.yml`).
# Um valor só, num lugar só: a view e o template precisam concordar sobre o que
# é material de venda e o que é lead de verdade.
FONTE_VITRINE = 'vitrine-da-campanha'


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

    # Bar-vitrine é material de demonstração, não prospecção. Se entrar na
    # conta, "abertas pelo dono" passa a incluir as vezes que o VENDEDOR abriu a
    # vitrine pra mostrar o modelo — e a única métrica do funil vira ficção.
    reais = [l for l in linhas if l['fonte'] != FONTE_VITRINE]
    demos = [l for l in reais if l['tipo'] == 'demo']
    funil = {
        'demos': len(demos),
        'abertas': sum(1 for l in demos if l['visitas'] > 0),
        'com_reserva': sum(1 for l in demos if l['reservas'] > 0),
        'clientes': sum(1 for l in reais if l['tipo'] != 'demo'),
        'pagantes': sum(1 for l in reais if l['plano'] in ('site', 'pro')),
    }
    return render_template('campanha/index.html', linhas=linhas, funil=funil,
                           fonte_vitrine=FONTE_VITRINE)


# Cada modelo tem um bar-vitrine com o conteúdo que ELE foi feito pra destacar.
# Sem isso a demonstração não funciona: os leads de campo têm cardápio vazio, e
# com a página vazia os seis modelos renderizam a mesma coisa (ver os arquivos
# `app/data/leads/vitrine-*.yml`).
VITRINE = (
    ('classico', 'bar-do-ze', 'Bar do Zé',
     'Um pouco de tudo, na ordem que já vende hoje.',
     'Boteco que faz de tudo e não quer errar.'),
    ('craft', 'vitrine-tap-cinco', 'Tap Cinco',
     'Torneiras no topo, com estilo, IBU e teor de cada uma.',
     'Cervejaria artesanal, taproom, bar de chope.'),
    ('tradicional', 'vitrine-armazem-1948', 'Armazém 1948',
     'A história primeiro: cada prato marcado pelo ano em que entrou.',
     'Casa antiga, com história e freguês de anos.'),
    ('autoral', 'vitrine-fogo-e-sal', 'Fogo & Sal',
     'Menu curto, técnica e produtor na descrição de cada prato.',
     'Cozinha autoral, bistrô, chef que assina.'),
    ('noturno', 'vitrine-sala-vermelha', 'Sala Vermelha',
     'Agenda no topo, balcão e petisco de mão.',
     'Casa de música ao vivo, com agenda toda semana.'),
    ('brasa', 'vitrine-brasa-velha', 'Brasa Velha',
     'Porção com peso e quantas pessoas serve, preço em tudo.',
     'Espetaria, churrascaria, casa de porção.'),
)


@bp.route('/modelos')
def modelos():
    """As seis caras do site, prontas pra mostrar na mesa.

    O vendedor precisa responder "como fica o meu?" em dois toques, sem abrir o
    bar de outro cliente e sem mexer no site de ninguém. Aqui cada modelo tem um
    bar de demonstração próprio, e o link já vai com `?modelo=` — a prévia é só
    daquela resposta, nada é gravado.
    """
    if not _e_operador():
        abort(404)

    # Só entra o que existe de fato no banco: bar-vitrine que ainda não foi
    # aplicado viraria cartão com link quebrado na frente do dono do bar.
    existentes = {
        r.slug: r for r in Restaurante.query.filter(
            Restaurante.slug.in_([v[1] for v in VITRINE])).all()
    }

    cartoes = [
        {'modelo': modelo, 'slug': slug, 'bar': bar, 'destaque': destaque,
         'para': para, 'pronto': slug in existentes}
        for modelo, slug, bar, destaque, para in VITRINE
    ]
    return render_template('campanha/modelos.html', cartoes=cartoes,
                           faltando=[c for c in cartoes if not c['pronto']])
