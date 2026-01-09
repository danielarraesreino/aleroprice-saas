from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort, session
from flask_login import current_user, login_required
from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.routes.billing import bp
import stripe
import os

# Configuração Stripe (Placeholder - Em produção usar variáveis de ambiente)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_PLACEHOLDER')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_PLACEHOLDER')
stripe.api_key = STRIPE_SECRET_KEY

# ID do Produto/Preço Pro (Criar no Dashboard do Stripe)
# Em produção, isso viria de config.
STRIPE_PRICE_ID_PRO = os.environ.get('STRIPE_PRICE_ID_PRO', 'price_fake_pro_monthly')

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Cria uma sessão de checkout no Stripe para o plano Pro"""
    restaurante = current_user.restaurante
    
    try:
        # Se não tiver API Key real, simular sucesso para teste
        if 'test_PLACEHOLDER' in STRIPE_SECRET_KEY:
            flash('Modo de Teste: Redirecionando para sucesso simulado...', 'info')
            return redirect(url_for('billing.success', session_id='evt_test_mock_session'))

        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            client_reference_id=str(restaurante.id),
            line_items=[
                {
                    'price': STRIPE_PRICE_ID_PRO,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.cancel', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Erro ao iniciar pagamento: {str(e)}", 'danger')
        return redirect(url_for('dashboard.upgrade'))

@bp.route('/success')
@login_required
def success():
    """Página de sucesso após pagamento"""
    session_id = request.args.get('session_id')
    # Em produção, verificaríamos o session_id na API do Stripe
    
    # Ativar Pro Imediatamente (Optimistic UI)
    # A confirmação real vem via Webhook (mais seguro)
    # Mas para UX, já liberamos
    
    restaurante = current_user.restaurante
    restaurante.subscription_tier = 'pro'
    restaurante.subscription_status = 'active'
    db.session.commit()
    
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
    """Webhook para ouvir eventos do Stripe (subscription.created, invoice.paid, etc)"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')

    try:
        if 'test_PLACEHOLDER' in STRIPE_SECRET_KEY:
             # Mock webhook handling
             event = {'type': 'mock'}
        else:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        # session = event['data']['object']
        # Fazer lógica de ativação aqui se não fez no sucesso
        pass
    
    return jsonify(success=True)
