"""
Script para criar pratos de teste para validar importação de vendas
"""
from app import create_app, db
from app.models.modelo_prato import Prato
from app.models.modelo_restaurante import Restaurante

def criar_pratos_teste():
    app = create_app()
    with app.app_context():
        # Buscar primeiro restaurante
        restaurante = Restaurante.query.first()
        if not restaurante:
            print("❌ Nenhum restaurante encontrado. Execute seed_demo_full.py primeiro.")
            return
        
        print(f"✅ Usando restaurante: {restaurante.nome} (ID: {restaurante.id})")
        
        # Verificar se pratos já existem
        pratos_existentes = Prato.query.filter(
            Prato.nome.in_(['Pastel de Carne', 'Pastel de Queijo', 'Coxinha']),
            Prato.restaurant_id == restaurante.id
        ).all()
        
        if pratos_existentes:
            print(f"⚠️  {len(pratos_existentes)} pratos já existem:")
            for p in pratos_existentes:
                print(f"   - {p.nome} (ID: {p.id})")
            return
        
        # Criar pratos de teste
        pratos_teste = [
            {
                'nome': 'Pastel de Carne',
                'descricao': 'Pastel tradicional recheado com carne moída temperada',
                'categoria': 'Salgados',
                'rendimento': 10.0,
                'unidade_rendimento': 'un',
                'porcoes_rendimento': 10,
                'tempo_preparo': 20,
                'preco_venda': 5.00,
                'margem': 60.0,
                'custo_indireto': 0.50,
                'restaurant_id': restaurante.id
            },
            {
                'nome': 'Pastel de Queijo',
                'descricao': 'Pastel recheado com queijo mussarela',
                'categoria': 'Salgados',
                'rendimento': 10.0,
                'unidade_rendimento': 'un',
                'porcoes_rendimento': 10,
                'tempo_preparo': 20,
                'preco_venda': 6.00,
                'margem': 65.0,
                'custo_indireto': 0.50,
                'restaurant_id': restaurante.id
            },
            {
                'nome': 'Coxinha',
                'descricao': 'Coxinha de frango com catupiry',
                'categoria': 'Salgados',
                'rendimento': 15.0,
                'unidade_rendimento': 'un',
                'porcoes_rendimento': 15,
                'tempo_preparo': 30,
                'preco_venda': 4.50,
                'margem': 55.0,
                'custo_indireto': 0.40,
                'restaurant_id': restaurante.id
            }
        ]
        
        pratos_criados = []
        for dados in pratos_teste:
            prato = Prato(**dados)
            db.session.add(prato)
            pratos_criados.append(prato)
        
        db.session.commit()
        
        print(f"\n✅ {len(pratos_criados)} pratos criados com sucesso:")
        for p in pratos_criados:
            print(f"   - {p.nome} (ID: {p.id}) - R$ {p.preco_venda}")
        
        print("\n🎯 Agora você pode testar a importação com vendas_teste.csv!")

if __name__ == '__main__':
    criar_pratos_teste()
