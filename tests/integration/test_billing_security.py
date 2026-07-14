"""Testes de segurança do billing.

Cobrem a falha que existia: `GET /billing/success` ativava o plano Pro sem
consultar o Stripe — qualquer usuário logado virava Pro só de acessar a URL.

Convenção destes testes: a chave 'sk_test_PLACEHOLDER' liga o modo mock (dev).
Para exercitar o caminho real do Stripe, trocamos a env por uma chave que não
contém 'test_PLACEHOLDER' e mockamos as chamadas à API.
"""
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
import stripe

CHAVE_STRIPE_REAL = 'sk_test_umachavequalquer'
WEBHOOK_SECRET = 'whsec_segredo_de_teste'


@pytest.fixture
def stripe_real(monkeypatch):
    """Desliga o modo mock: o billing passa a falar com o 'Stripe'."""
    monkeypatch.setenv('STRIPE_SECRET_KEY', CHAVE_STRIPE_REAL)
    return CHAVE_STRIPE_REAL


def _sessao_stripe(restaurant_id, payment_status='paid'):
    return {
        'id': 'cs_test_123',
        'payment_status': payment_status,
        'client_reference_id': str(restaurant_id),
    }


def _assinar(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Gera um header Stripe-Signature válido (mesmo esquema do Stripe)."""
    timestamp = int(time.time())
    assinado = f'{timestamp}.{payload.decode()}'.encode()
    v1 = hmac.new(secret.encode(), assinado, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={v1}'


# ---------------------------------------------------------------------------
# /billing/success
# ---------------------------------------------------------------------------

def test_success_sem_session_id_nao_ativa_pro(auth_client, restaurant, stripe_real):
    """A falha original: GET /billing/success cru dava Pro de graça."""
    assert restaurant.subscription_tier == 'free'

    resp = auth_client.get('/billing/success', follow_redirects=False)

    assert resp.status_code == 302
    assert restaurant.subscription_tier == 'free'
    assert restaurant.subscription_status == 'free'


def test_success_com_sessao_nao_paga_nao_ativa_pro(auth_client, restaurant, stripe_real):
    sessao = _sessao_stripe(restaurant.id, payment_status='unpaid')

    with patch.object(stripe.checkout.Session, 'retrieve', return_value=sessao):
        resp = auth_client.get('/billing/success?session_id=cs_test_123')

    assert resp.status_code in (200, 302)
    assert restaurant.subscription_tier == 'free'


def test_success_com_sessao_de_outro_tenant_nao_ativa_pro(auth_client, restaurant, stripe_real):
    """Sessão paga, mas pertencente a OUTRO restaurante: não pode ativar."""
    sessao = _sessao_stripe(restaurant_id=restaurant.id + 999, payment_status='paid')

    with patch.object(stripe.checkout.Session, 'retrieve', return_value=sessao):
        auth_client.get('/billing/success?session_id=cs_test_123')

    assert restaurant.subscription_tier == 'free'


def test_success_com_sessao_paga_ativa_pro(auth_client, restaurant, stripe_real):
    sessao = _sessao_stripe(restaurant.id, payment_status='paid')

    with patch.object(stripe.checkout.Session, 'retrieve', return_value=sessao):
        auth_client.get('/billing/success?session_id=cs_test_123')

    assert restaurant.subscription_tier == 'pro'
    assert restaurant.subscription_status == 'active'


def test_success_quando_stripe_falha_nao_ativa_pro(auth_client, restaurant, stripe_real):
    with patch.object(stripe.checkout.Session, 'retrieve', side_effect=Exception('boom')):
        auth_client.get('/billing/success?session_id=cs_test_123')

    assert restaurant.subscription_tier == 'free'


# ---------------------------------------------------------------------------
# /billing/webhook
# ---------------------------------------------------------------------------

def test_webhook_sem_segredo_configurado_recusa(client, monkeypatch):
    monkeypatch.delenv('STRIPE_WEBHOOK_SECRET', raising=False)

    resp = client.post('/billing/webhook', data=b'{}')

    assert resp.status_code == 503


def test_webhook_com_assinatura_invalida_recusa(client, restaurant, monkeypatch):
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', WEBHOOK_SECRET)
    payload = json.dumps({'type': 'checkout.session.completed'}).encode()

    resp = client.post(
        '/billing/webhook',
        data=payload,
        headers={'Stripe-Signature': 't=1,v1=assinatura_falsa'},
    )

    assert resp.status_code == 400
    assert restaurant.subscription_tier == 'free'


def test_webhook_sem_header_de_assinatura_recusa(client, restaurant, monkeypatch):
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', WEBHOOK_SECRET)

    resp = client.post('/billing/webhook', data=b'{}')

    assert resp.status_code == 400
    assert restaurant.subscription_tier == 'free'


def test_webhook_valido_ativa_pro(client, restaurant, monkeypatch):
    """Assinatura HMAC real — exercita stripe.Webhook.construct_event de verdade."""
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', WEBHOOK_SECRET)
    evento = {
        'type': 'checkout.session.completed',
        'data': {'object': _sessao_stripe(restaurant.id, payment_status='paid')},
    }
    payload = json.dumps(evento).encode()

    resp = client.post(
        '/billing/webhook',
        data=payload,
        headers={'Stripe-Signature': _assinar(payload)},
    )

    assert resp.status_code == 200
    assert restaurant.subscription_tier == 'pro'
    assert restaurant.subscription_status == 'active'


def test_webhook_valido_mas_nao_pago_nao_ativa(client, restaurant, monkeypatch):
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', WEBHOOK_SECRET)
    evento = {
        'type': 'checkout.session.completed',
        'data': {'object': _sessao_stripe(restaurant.id, payment_status='unpaid')},
    }
    payload = json.dumps(evento).encode()

    resp = client.post(
        '/billing/webhook',
        data=payload,
        headers={'Stripe-Signature': _assinar(payload)},
    )

    assert resp.status_code == 200
    assert restaurant.subscription_tier == 'free'


# ---------------------------------------------------------------------------
# Modo mock
# ---------------------------------------------------------------------------

def test_mock_desligado_em_producao(app, monkeypatch):
    """Produção + chave placeholder NÃO pode virar modo mock (= Pro de graça)."""
    from app.routes.billing.views import _mock_billing

    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_PLACEHOLDER')

    with app.test_request_context():
        monkeypatch.setitem(app.config, 'CONFIG_NAME', 'production')
        assert _mock_billing() is False

        monkeypatch.setitem(app.config, 'CONFIG_NAME', 'development')
        assert _mock_billing() is True
