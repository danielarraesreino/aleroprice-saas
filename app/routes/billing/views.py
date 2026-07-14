from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort, session
from flask_login import current_user, login_required
from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.routes.billing import bp
import stripe
import os

# Session id usado pelo fluxo mock (dev/demo, sem chave real do Stripe).
# É o único session_id que ativa o Pro sem consultar o Stripe — e só fora de produção.
MOCK_SESSION_ID = 'mock_checkout_session'


def _stripe_secret_key():
    return os.environ.get('STRIPE_SECRET_KEY', 'sk_test_PLACEHOLDER')


def _is_production():
    return current_app.config.get('CONFIG_NAME') == 'production'


def _mock_billing():
    """True quando o billing deve rodar simulado (sem falar com o Stripe).

    Só acontece com chave placeholder E fora de produção. Em produção, chave
    placeholder NÃO vira mock: o checkout falha alto. Antes, subir em produção
    sem STRIPE_SECRET_KEY dava plano Pro de graça pra qualquer um.
    """
    return 'test_PLACEHOLDER' in _stripe_secret_key() and not _is_production()


def _ativar_pro(restaurante):
    restaurante.subscription_tier = 'pro'
    restaurante.subscription_status = 'active'
    db.session.commit()
    current_app.logger.info(f'Plano Pro ativado para restaurante {restaurante.id}.')


def _sessao_confere(checkout_session, restaurante):
    """A sessão do Stripe está paga E pertence a este restaurante?

    O client_reference_id é gravado por nós no create_checkout_session. Sem essa
    checagem, um tenant poderia ativar o Pro reusando o session_id de outro.
    """
    pago = checkout_session.get('payment_status') == 'paid'
    dono = str(checkout_session.get('client_reference_id') or '') == str(restaurante.id)
    return pago and dono


@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Cria uma sessão de checkout no Stripe para o plano Pro"""
    restaurante = current_user.restaurante

    # Dev/demo sem chave do Stripe: simula o retorno do checkout.
    if _mock_billing():
        flash('Modo de Teste: Redirecionando para sucesso simulado...', 'info')
        return redirect(url_for('billing.success', session_id=MOCK_SESSION_ID))

    if 'test_PLACEHOLDER' in _stripe_secret_key():
        # Produção sem chave configurada: falhar é o comportamento correto.
        current_app.logger.error('STRIPE_SECRET_KEY não configurada em produção.')
        flash('Pagamento indisponível no momento. Fale conosco no WhatsApp.', 'danger')
        return redirect(url_for('dashboard.upgrade'))

    stripe.api_key = _stripe_secret_key()

    try:
        price_id = os.environ.get('STRIPE_PRICE_ID_PRO', 'price_fake_pro_monthly')

        # A/B Testing Logic
        if restaurante.pricing_strategy == 'volume_based':
            price_id = os.environ.get('STRIPE_PRICE_ID_VOLUME', 'price_fake_volume_test')

        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            client_reference_id=str(restaurante.id),
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.cancel', _external=True),
            metadata={
                'pricing_strategy': restaurante.pricing_strategy,
                'restaurant_id': restaurante.id
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        current_app.logger.exception('Falha ao criar checkout session.')
        flash(f"Erro ao iniciar pagamento: {str(e)}", 'danger')
        return redirect(url_for('dashboard.upgrade'))


@bp.route('/success')
@login_required
def success():
    """Retorno do checkout. Só ativa o Pro se o Stripe confirmar o pagamento.

    Não é mais otimista: antes, um GET nesta URL bastava pra virar Pro.
    """
    session_id = request.args.get('session_id')
    restaurante = current_user.restaurante

    if _mock_billing():
        if session_id != MOCK_SESSION_ID:
            flash('Sessão de pagamento inválida.', 'danger')
            return redirect(url_for('dashboard.upgrade'))
        _ativar_pro(restaurante)
        flash('Pagamento confirmado! Bem-vindo ao AleroPrice Pro 🚀', 'success')
        return redirect(url_for('dashboard.index'))

    if not session_id:
        flash('Não recebemos a confirmação do pagamento.', 'warning')
        return redirect(url_for('dashboard.upgrade'))

    stripe.api_key = _stripe_secret_key()

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        current_app.logger.exception(f'Falha ao recuperar checkout session {session_id}.')
        flash('Não foi possível confirmar o pagamento. Se o valor foi cobrado, fale conosco.', 'danger')
        return redirect(url_for('dashboard.upgrade'))

    if not _sessao_confere(checkout_session, restaurante):
        current_app.logger.warning(
            f'Tentativa de ativação com sessão não confirmada. '
            f'restaurante={restaurante.id} session={session_id}'
        )
        flash('Pagamento ainda não confirmado. Se você concluiu o pagamento, aguarde alguns instantes.', 'warning')
        return redirect(url_for('dashboard.upgrade'))

    _ativar_pro(restaurante)
    flash('Pagamento confirmado! Bem-vindo ao AleroPrice Pro 🚀', 'success')
    return redirect(url_for('dashboard.index'))


@bp.route('/cancel')
@login_required
def cancel():
    """Página de cancelamento/retorno do checkout"""
    flash('Pagamento cancelado. Se tiver dúvidas, fale conosco no WhatsApp.', 'warning')
    return redirect(url_for('dashboard.upgrade'))


@bp.route('/webhook', methods=['POST'])
def webhook():
    """Webhook do Stripe. Endpoint público (sem login) — a assinatura é a autenticação.

    Fonte de verdade da ativação: `checkout.session.completed`.
    """
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # Sem segredo configurado não há como distinguir o Stripe de um impostor.
    # Recusar é a única opção segura: antes, o modo mock aceitava qualquer POST.
    if not endpoint_secret:
        current_app.logger.error('Webhook recebido sem STRIPE_WEBHOOK_SECRET configurado.')
        return jsonify(error='webhook not configured'), 503

    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return jsonify(error='invalid payload'), 400
    except stripe.SignatureVerificationError:
        current_app.logger.warning('Webhook com assinatura inválida rejeitado.')
        return jsonify(error='invalid signature'), 400

    if event['type'] == 'checkout.session.completed':
        sessao = event['data']['object']
        restaurant_id = sessao.get('client_reference_id')
        restaurante = Restaurante.query.get(restaurant_id) if restaurant_id else None

        if restaurante is None:
            current_app.logger.error(
                f'checkout.session.completed sem restaurante válido (ref={restaurant_id}).'
            )
            return jsonify(success=True)  # 200: não pedir retry ao Stripe

        if sessao.get('payment_status') == 'paid':
            _ativar_pro(restaurante)

    return jsonify(success=True)
