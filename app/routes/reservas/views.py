from datetime import date

from flask import render_template, redirect, url_for, flash, request, abort

from app.extensions import db
from app.models.modelo_reserva import Reserva
from app.routes.reservas import bp
from app.utils.tenant import get_current_restaurant_id
from app.utils.decorators import plano_minimo


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
@plano_minimo('site')
def confirmar(reserva_id):
    r = _mudar_status(reserva_id, 'confirmada')
    flash(f'Reserva de {r.nome} confirmada.', 'success')
    return redirect(request.referrer or url_for('reservas.index'))


@bp.route('/<int:reserva_id>/cancelar', methods=['POST'])
@plano_minimo('site')
def cancelar(reserva_id):
    r = _mudar_status(reserva_id, 'cancelada')
    flash(f'Reserva de {r.nome} cancelada.', 'warning')
    return redirect(request.referrer or url_for('reservas.index'))


def _whatsapp_do_cliente(telefone):
    """Telefone como o cliente digitou → número do wa.me (com 55 se faltar)."""
    digitos = ''.join(c for c in (telefone or '') if c.isdigit())
    if len(digitos) in (10, 11):
        digitos = '55' + digitos
    return digitos if len(digitos) >= 12 else ''


@bp.route('/avaliacoes', methods=['GET', 'POST'])
def avaliacoes():
    """Pedir avaliação no Google: link curto, QR e a mensagem pronta para cada
    reserva dos últimos dias.

    A mesma mensagem vai para todo cliente, sem filtrar quem gostou: pedir só
    aos satisfeitos é "review gating", proibido pelo Google — custa as
    avaliações e pode derrubar o perfil do bar. Quem envia é o dono, pelo
    WhatsApp dele: grátis e sem risco de bloqueio de número.
    """
    import urllib.parse
    from datetime import timedelta

    import segno

    from app.models.modelo_restaurante import Restaurante
    from app.models.modelo_siteconfig import SiteConfig

    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))
    rest = Restaurante.query.get_or_404(restaurant_id)
    cfg = SiteConfig.query.filter_by(restaurant_id=restaurant_id).first()

    if request.method == 'POST':
        place_id = (request.form.get('google_place_id') or '').strip()
        # place_id do Google: letras, números, _ e -. Recusa o resto em vez de
        # gravar uma URL colada por engano.
        if place_id and not all(c.isalnum() or c in '_-' for c in place_id):
            flash('Esse não parece um ID de lugar do Google (ex.: ChIJ...).', 'danger')
            return redirect(url_for('reservas.avaliacoes'))
        if cfg is None:
            cfg = SiteConfig(restaurant_id=restaurant_id, nome=rest.nome)
            db.session.add(cfg)
        cfg.google_place_id = place_id[:120] or None
        db.session.commit()
        flash('ID do Google salvo.', 'success')
        return redirect(url_for('reservas.avaliacoes'))

    link = qr_svg = None
    if cfg and cfg.google_place_id and rest.slug:
        link = url_for('public.avaliar', slug=rest.slug, _external=True)
        qr_svg = segno.make(link, error='m').svg_inline(scale=6, border=2)

    hoje = date.today()
    recentes = (Reserva.query
                .filter(Reserva.restaurant_id == restaurant_id,
                        Reserva.status != 'cancelada',
                        Reserva.data >= hoje - timedelta(days=3),
                        Reserva.data <= hoje)
                .order_by(Reserva.data.desc(), Reserva.hora.desc()).all())
    nome_bar = (cfg.nome if cfg and cfg.nome else rest.nome)
    pedidos = []
    for r in recentes:
        numero = _whatsapp_do_cliente(r.telefone)
        texto = (f'Oi, {r.nome.split()[0]}! Obrigado por ter vindo ao {nome_bar}. '
                 f'Se puder, conta como foi no Google — leva um minutinho e ajuda '
                 f'muito a gente: {link}') if link else ''
        pedidos.append({
            'reserva': r,
            'wa': (f'https://wa.me/{numero}?text={urllib.parse.quote(texto)}'
                   if numero and texto else ''),
        })

    return render_template('reservas/avaliacoes.html', cfg=cfg, link=link,
                           qr_svg=qr_svg, pedidos=pedidos, nome_bar=nome_bar)
