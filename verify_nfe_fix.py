import requests
from app import create_app, db
from app.models.usuario import Usuario
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_restaurante import Restaurante

def verify_fix():
    app_ctx = create_app('development').app_context()
    app_ctx.push()

    # 1. Ensure Tenant 1 has the supplier
    cnpj_problem = "07374789000190"
    
    # Check/Create for tenant 1
    f1 = Fornecedor.query.filter_by(cnpj=cnpj_problem, restaurant_id=1).first()
    if not f1:
        print("Creating collision supplier for Tenant 1...")
        f1 = Fornecedor(
            cnpj=cnpj_problem, 
            razao_social="Fornecedor Colisao Ltda", 
            restaurant_id=1 
        )
        db.session.add(f1)
        db.session.commit()
    else:
        print("Supplier already exists for Tenant 1 (Good condition for test).")
        
    # 2. Try to Import for Tenant 3 (User novo_plg)
    # Verify Tenant 3 exists
    u3 = Usuario.query.filter_by(email="novo_plg@teste.com").first()
    if not u3:
        print("User novo_plg not found. Run verify_features_plg.py first?")
        return

    # Check if Tenant 3 already has it (should not, or allow duplicates now)
    f3 = Fornecedor.query.filter_by(cnpj=cnpj_problem, restaurant_id=3).first()
    if f3:
        print("Tenant 3 already has this supplier. Deleting to re-test insert...")
        db.session.delete(f3)
        db.session.commit()
    
    # 3. Import via Python function (to avoid mocking XML file upload via request complex setup)
    # We can just check if we can Insert a Fornecedor manually for tenant 3.
    # The error was SQL IntegrityError.
    
    print("Attempting to insert SAME CNPJ for Tenant 3...")
    try:
        f_new = Fornecedor(
            cnpj=cnpj_problem,
            razao_social="Fornecedor Teste Fix",
            restaurant_id=3
        )
        db.session.add(f_new)
        db.session.commit()
        print(f"✅ SUCCESS: Created Fornecedor {f_new.id} for Tenant 3 with CNPJ {cnpj_problem}")
        print("IntegrityError Global Constraint is GONE!")
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    verify_fix()
