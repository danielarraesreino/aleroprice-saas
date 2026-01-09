import requests
from app import create_app, db
from app.models.usuario import Usuario
from app.models.modelo_restaurante import Restaurante

def verify_plg():
    """Verify Product-Led Growth Features"""
    
    # 1. Setup Data (Ensure New User)
    app_ctx = create_app('development').app_context()
    app_ctx.push()
    
    email_new = "novo_plg@teste.com"
    pwd = "password123"
    
    # Clean previous user
    existing_user = Usuario.query.filter_by(email=email_new).first()
    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()

    # Clean previous restaurant or reuse
    existing_rest = Restaurante.query.filter_by(cnpj="11111111111111").first()
    if existing_rest:
        rest = existing_rest
        print(f"Reuse existing restaurant: {rest.nome}")
    else:
        # Create User/Tenant
        rest = Restaurante(nome="Restaurante PLG", cnpj="11111111111111")
        db.session.add(rest)
        db.session.commit()
    
    user = Usuario(nome="Novo PLG", email=email_new, senha=pwd, restaurant_id=rest.id)
    db.session.add(user)
    db.session.commit()
    
    print(f"User created: {email_new}")
    
    # 2. Verify ROI Calculator (Public)
    print("\n--- Testing ROI Calculator (Public) ---")
    session = requests.Session()
    roi_url = "http://localhost:5000/calculadora-roi"
    
    try:
        resp = session.get(roi_url)
        if resp.status_code == 200 and "Calculadora de Desperdício" in resp.text:
            print("✅ ROI Calculator Route: ACCESSIBLE (200 OK)")
        else:
            print(f"❌ ROI Calculator Route: FAILED ({resp.status_code})")
        
        # Test Calculation
        resp_post = session.post(roi_url, data={'faturamento_estimado': '50000'})
        if "R$ 5.000,00" in resp_post.text:
             print("✅ ROI Calculation: ACCURATE (10% of 50000 is 5000)")
        else:
             print("❌ ROI Calculation: FAILED")
             
    except Exception as e:
        print(f"❌ ROI Request Error: {e}")

    # 3. Verify Onboarding (Gamified)
    print("\n--- Testing Gamified Onboarding (Empty State) ---")
    login_url = "http://localhost:5000/auth/login"
    session.post(login_url, data={'email': email_new, 'senha': pwd})
    
    resp_dash = session.get("http://localhost:5000/index")
    
    # Check for specific Gamification elements
    checks = [
        ("Bem-vindo ao AleroPrice! 🚀", "Welcome Header"),
        ("progress-bar bg-success", "Progress Bar"),
        ("Importe uma nota para descobrir imediatamente", "ROI Copy"),
        ("Lucro Real", "Locked Step") 
    ]
    
    all_pass = True
    for text, label in checks:
        if text in resp_dash.text:
            print(f"✅ {label}: FOUND")
        else:
            print(f"❌ {label}: NOT FOUND")
            all_pass = False
            
    if all_pass:
        print("🎉 GAMIFIED ONBOARDING VERIFIED!")
    else:
        print("⚠️ SOME ELEMENTS MISSING.")

if __name__ == "__main__":
    verify_plg()
