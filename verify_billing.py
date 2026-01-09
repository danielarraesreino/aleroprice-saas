
import unittest
from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
import io

class TestBilling(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        # Reset tenant to free
        rest = Restaurante.query.get(1)
        if rest:
            rest.subscription_tier = 'free'
            rest.subscription_status = 'free'
            db.session.commit()
        self.ctx.pop()

    def test_pro_content_block(self):
        # 1. Ensure Tenant is FREE
        rest = Restaurante.query.get(1)
        rest.subscription_tier = 'free'
        db.session.commit()
        
        # 2. Login
        self.client.post('/auth/login', data={'email': 'admin@teste.com', 'senha': 'password123'}, follow_redirects=True)
        
        # 3. Try to access Protected Route (BCG Matrix API)
        response = self.client.get('/api/bcg-matrix', follow_redirects=True)
        response_text = response.data.decode('utf-8')
        
        # Expect redirect to upgrade or flash message
        if "/dashboard/upgrade" in response.request.url or "upgrade.html" in response_text or "Upgrade para Pro" in response_text:
            print("✅ PASSED: Free user blocked from Pro route.")
        else:
            print(f"❌ FAILED: Free user accessed Pro route! URL: {response.request.url}")

    def test_checkout_flow(self):
        # 1. Login
        self.client.post('/auth/login', data={'email': 'admin@teste.com', 'senha': 'password123'}, follow_redirects=True)
        
        # 2. Create Checkout Session (Mocked)
        response = self.client.post('/billing/create-checkout-session', follow_redirects=True)
        response_text = response.data.decode('utf-8')
        
        # Expect success page (Mock mode)
        if "Pagamento confirmado" in response_text:
             print("✅ PASSED: Checkout flow (Mock) completed.")
             
             # Verify DB updated
             rest = Restaurante.query.get(1)
             if rest.subscription_tier == 'pro':
                 print("✅ PASSED: DB updated to PRO.")
             else:
                 print(f"❌ FAILED: DB not updated. Tier: {rest.subscription_tier}")
        else:
             print("❌ FAILED: Checkout flow did not reach success page.")

if __name__ == "__main__":
    unittest.main()
