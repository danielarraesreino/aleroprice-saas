"""
Script de Seeding Completo - Demo Bistrô
Gera 6 meses de dados históricos realistas para demonstração do sistema.
"""
from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
from app.models.modelo_fornecedor import Fornecedor
from app.models.modelo_produto import Produto
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_nfe import NFNota, NFItem
from app.models.modelo_estoque import EstoqueMovimentacao
from app.models.modelo_custo import CustoIndireto
from datetime import datetime, timedelta
import random

app = create_app('default')

# Dados base
FORNECEDORES = [
    "Atacadão Alimentos", "Distribuidora de Bebidas Premium", "Hortifruti São João",
    "Açougue Central", "Padaria Artesanal", "Laticínios do Campo",
    "Distribuidora de Temperos", "Mercado Gourmet", "Fornecedor de Descartáveis",
    "Distribuidora de Limpeza"
]

PRODUTOS = [
    {"nome": "Arroz Tipo 1 (5kg)", "unidade": "kg", "preco_base": 18.50, "categoria": "Grãos"},
    {"nome": "Feijão Preto (1kg)", "unidade": "kg", "preco_base": 7.80, "categoria": "Grãos"},
    {"nome": "Filé Mignon (kg)", "unidade": "kg", "preco_base": 65.00, "categoria": "Carnes", "inflacao": 0.15},
    {"nome": "Frango Inteiro (kg)", "unidade": "kg", "preco_base": 12.90, "categoria": "Carnes"},
    {"nome": "Óleo de Soja (900ml)", "unidade": "un", "preco_base": 8.50, "categoria": "Óleos", "inflacao": 0.18},
    {"nome": "Tomate (kg)", "unidade": "kg", "preco_base": 5.20, "categoria": "Hortifruti"},
    {"nome": "Alface Americana", "unidade": "un", "preco_base": 3.50, "categoria": "Hortifruti"},
    {"nome": "Queijo Mussarela (kg)", "unidade": "kg", "preco_base": 38.00, "categoria": "Laticínios", "inflacao": 0.12},
    {"nome": "Cerveja Lata 350ml", "unidade": "un", "preco_base": 3.20, "categoria": "Bebidas"},
    {"nome": "Refrigerante 2L", "unidade": "un", "preco_base": 6.50, "categoria": "Bebidas"},
    {"nome": "Farinha de Trigo (1kg)", "unidade": "kg", "preco_base": 4.80, "categoria": "Grãos"},
    {"nome": "Açúcar Refinado (1kg)", "unidade": "kg", "preco_base": 3.90, "categoria": "Grãos"},
    {"nome": "Sal Refinado (1kg)", "unidade": "kg", "preco_base": 1.50, "categoria": "Temperos"},
    {"nome": "Alho (kg)", "unidade": "kg", "preco_base": 22.00, "categoria": "Temperos"},
    {"nome": "Cebola (kg)", "unidade": "kg", "preco_base": 4.50, "categoria": "Hortifruti"},
    {"nome": "Batata (kg)", "unidade": "kg", "preco_base": 5.80, "categoria": "Hortifruti"},
    {"nome": "Macarrão Espaguete (500g)", "unidade": "un", "preco_base": 5.20, "categoria": "Massas"},
    {"nome": "Molho de Tomate (340g)", "unidade": "un", "preco_base": 3.80, "categoria": "Molhos"},
    {"nome": "Azeite Extra Virgem (500ml)", "unidade": "un", "preco_base": 28.00, "categoria": "Óleos"},
    {"nome": "Suco de Laranja Natural (1L)", "unidade": "un", "preco_base": 12.00, "categoria": "Bebidas"}
]

PRATOS = [
    {"nome": "Parmegiana de Frango", "preco_venda": 42.00, "categoria": "Principais", "popularidade": 0.15},
    {"nome": "Feijoada Completa", "preco_venda": 38.00, "categoria": "Principais", "popularidade": 0.12},
    {"nome": "Filé com Fritas", "preco_venda": 55.00, "categoria": "Principais", "popularidade": 0.10},
    {"nome": "Salada Caesar", "preco_venda": 28.00, "categoria": "Entradas", "popularidade": 0.08},
    {"nome": "Suco Natural", "preco_venda": 12.00, "categoria": "Bebidas", "popularidade": 0.20},
    {"nome": "Arroz com Feijão", "preco_venda": 18.00, "categoria": "Acompanhamentos", "popularidade": 0.25},
    {"nome": "Macarrão ao Molho", "preco_venda": 32.00, "categoria": "Principais", "popularidade": 0.14},
    {"nome": "Frango Grelhado", "preco_venda": 35.00, "categoria": "Principais", "popularidade": 0.11},
    {"nome": "Batata Frita", "preco_venda": 15.00, "categoria": "Acompanhamentos", "popularidade": 0.18},
    {"nome": "Refrigerante", "preco_venda": 8.00, "categoria": "Bebidas", "popularidade": 0.22}
]

def limpar_dados_demo(restaurante_id):
    """Remove dados anteriores do restaurante demo"""
    from app.models.modelo_previsao import HistoricoVendas
    
    print("🗑️  Limpando dados anteriores...")
    
    # Ordem de deleção respeitando foreign keys
    HistoricoVendas.query.filter_by(restaurant_id=restaurante_id).delete()
    EstoqueMovimentacao.query.filter_by(restaurant_id=restaurante_id).delete()
    CustoIndireto.query.filter_by(restaurant_id=restaurante_id).delete()
    NFItem.query.filter(NFItem.nf_nota_id.in_(
        db.session.query(NFNota.id).filter_by(restaurant_id=restaurante_id)
    )).delete(synchronize_session=False)
    NFNota.query.filter_by(restaurant_id=restaurante_id).delete()
    PratoInsumo.query.filter(PratoInsumo.prato_id.in_(
        db.session.query(Prato.id).filter_by(restaurant_id=restaurante_id)
    )).delete(synchronize_session=False)
    Prato.query.filter_by(restaurant_id=restaurante_id).delete()
    Produto.query.filter_by(restaurant_id=restaurante_id).delete()
    Fornecedor.query.filter_by(restaurant_id=restaurante_id).delete()
    
    db.session.commit()
    print("✅ Dados limpos!")

def criar_base_estatica(restaurante):
    """Cria fornecedores, produtos e pratos"""
    print("📦 Criando catálogo base...")
    
    # Fornecedores
    fornecedores_obj = []
    for nome in FORNECEDORES:
        f = Fornecedor(
            razao_social=nome,
            nome_fantasia=nome,
            cnpj=f"{random.randint(10000000, 99999999):08d}000100",
            telefone=f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            email=f"{nome.lower().replace(' ', '')}@email.com",
            restaurant_id=restaurante.id
        )
        fornecedores_obj.append(f)
        db.session.add(f)
    
    db.session.commit()
    
    # Produtos
    produtos_obj = {}
    for p in PRODUTOS:
        fornecedor = random.choice(fornecedores_obj)
        prod = Produto(
            nome=p["nome"],
            unidade=p["unidade"],
            preco_unitario=p["preco_base"],
            estoque_atual=random.randint(50, 200),
            estoque_minimo=20,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurante.id
        )
        produtos_obj[p["nome"]] = {"obj": prod, "preco_base": p["preco_base"], "inflacao": p.get("inflacao", 0)}
        db.session.add(prod)
    
    db.session.commit()
    
    # Pratos e Fichas Técnicas
    pratos_obj = []
    for prato_data in PRATOS:
        prato = Prato(
            nome=prato_data["nome"],
            descricao=f"Delicioso {prato_data['nome']}",
            preco_venda=prato_data["preco_venda"],
            categoria=prato_data["categoria"],
            rendimento=1.0,  # 1 kg/L de rendimento
            unidade_rendimento="kg",
            porcoes_rendimento=4,  # 4 porções por receita
            restaurant_id=restaurante.id
        )
        db.session.add(prato)
        db.session.flush()
        
        # Adicionar insumos aleatórios
        num_insumos = random.randint(2, 4)
        produtos_sample = random.sample(list(produtos_obj.values()), num_insumos)
        
        for prod_data in produtos_sample:
            quantidade = round(random.uniform(0.1, 0.5), 2)
            insumo = PratoInsumo(
                prato_id=prato.id,
                produto_id=prod_data["obj"].id,
                quantidade=quantidade
            )
            db.session.add(insumo)
        
        pratos_obj.append({"obj": prato, "popularidade": prato_data["popularidade"]})
    
    db.session.commit()
    print(f"✅ Criados {len(fornecedores_obj)} fornecedores, {len(produtos_obj)} produtos, {len(pratos_obj)} pratos")
    
    return fornecedores_obj, produtos_obj, pratos_obj

def simular_historico(restaurante, fornecedores, produtos, pratos, dias=180):
    """Simula 6 meses de operação"""
    print(f"📅 Simulando {dias} dias de operação...")
    
    data_inicial = datetime.now() - timedelta(days=dias)
    
    for dia in range(dias):
        data_atual = data_inicial + timedelta(days=dia)
        progresso_inflacao = dia / dias  # 0 a 1
        
        # Ciclo de Compras (a cada 3-5 dias)
        if dia % random.randint(3, 5) == 0:
            fornecedor = random.choice(fornecedores)
            
            # Criar NFE
            numero_nf = f"{random.randint(100000, 999999)}"
            serie_nf = f"{random.randint(1, 9)}"
            chave_acesso = f"{random.randint(10000000000000000000, 99999999999999999999):044d}"
            
            nf = NFNota(
                chave_acesso=chave_acesso,
                numero=numero_nf,
                serie=serie_nf,
                data_emissao=data_atual,
                fornecedor_id=fornecedor.id,
                valor_total=0,
                valor_produtos=0,
                restaurant_id=restaurante.id
            )
            db.session.add(nf)
            db.session.flush()
            
            valor_total_nf = 0
            produtos_comprados = random.sample(list(produtos.values()), random.randint(3, 8))
            
            for prod_data in produtos_comprados:
                produto = prod_data["obj"]
                quantidade = random.randint(10, 50)
                
                # Aplicar inflação progressiva
                preco_com_inflacao = prod_data["preco_base"] * (1 + prod_data["inflacao"] * progresso_inflacao)
                preco_unitario = round(preco_com_inflacao, 2)
                
                # Criar item da NF
                item = NFItem(
                    nf_nota_id=nf.id,
                    produto_id=produto.id,
                    num_item=len(produtos_comprados),
                    quantidade=quantidade,
                    valor_unitario=preco_unitario,
                    valor_total=quantidade * preco_unitario,
                    unidade_medida=produto.unidade
                )
                db.session.add(item)
                valor_total_nf += item.valor_total
                
                # Atualizar preço do produto (para ativar alerta de inflação)
                produto.preco_unitario = preco_unitario
                produto.estoque_atual += quantidade
                
                # Movimentação de estoque
                mov = EstoqueMovimentacao(
                    produto_id=produto.id,
                    tipo='entrada',
                    quantidade=quantidade,
                    data_movimentacao=data_atual,
                    observacao=f"Compra NF {nf.numero}",
                    valor_unitario=preco_unitario,
                    restaurant_id=restaurante.id
                )
                db.session.add(mov)
            
            nf.valor_total = valor_total_nf
            nf.valor_produtos = valor_total_nf
        
        # Simular consumo de estoque (saídas aleatórias)
        if dia % 2 == 0:  # A cada 2 dias
            produtos_consumo = random.sample(list(produtos.values()), random.randint(2, 5))
            
            for prod_data in produtos_consumo:
                produto = prod_data["obj"]
                if produto.estoque_atual > 5:
                    qtd_consumo = round(random.uniform(1, 5), 2)
                    produto.estoque_atual = max(0, produto.estoque_atual - qtd_consumo)
                    
                    mov = EstoqueMovimentacao(
                        produto_id=produto.id,
                        tipo='saída',
                        quantidade=qtd_consumo,
                        data_movimentacao=data_atual,
                        observacao="Consumo operacional",
                        valor_unitario=produto.preco_unitario,
                        restaurant_id=restaurante.id
                    )
                    db.session.add(mov)
        
        # Custos Fixos (mensais - dia 1)
        if data_atual.day == 1:
            custos_fixos = [
                {"tipo": "Aluguel", "descricao": "Aluguel do imóvel", "valor": 5000.00},
                {"tipo": "Energia", "descricao": "Energia Elétrica", "valor": random.uniform(800, 1200)},
                {"tipo": "Água", "descricao": "Água e Esgoto", "valor": random.uniform(300, 500)},
                {"tipo": "Folha", "descricao": "Folha de Pagamento", "valor": 12000.00},
                {"tipo": "Telecom", "descricao": "Internet/Telefone", "valor": 250.00}
            ]
            
            for custo in custos_fixos:
                c = CustoIndireto(
                    tipo=custo["tipo"],
                    descricao=custo["descricao"],
                    valor=custo["valor"],
                    data_referencia=data_atual.date(),
                    restaurant_id=restaurante.id
                )
                db.session.add(c)
        
        # Commit a cada 10 dias
        if dia % 10 == 0:
            db.session.commit()
            print(f"  ✓ Dia {dia}/{dias} processado")
    
    db.session.commit()
    print("✅ Histórico simulado!")

def simular_vendas(restaurante, pratos, dias=180):
    """Simula vendas realistas ao longo do período"""
    from app.models.modelo_previsao import HistoricoVendas
    
    print(f"💰 Simulando vendas para {dias} dias...")
    
    data_inicial = datetime.now() - timedelta(days=dias)
    total_vendas = 0
    
    # Padrões de vendas por período do dia
    periodos = {
        'almoço': {'inicio': 11, 'fim': 15, 'peso': 0.45},  # 45% das vendas
        'jantar': {'inicio': 18, 'fim': 22, 'peso': 0.40},  # 40% das vendas
        'outros': {'peso': 0.15}  # 15% das vendas (café, lanche)
    }
    
    for dia in range(dias):
        data_atual = data_inicial + timedelta(days=dia)
        dia_semana = data_atual.weekday()  # 0=Segunda, 6=Domingo
        
        # Fator de sazonalidade por dia da semana
        # Finais de semana têm mais movimento
        if dia_semana >= 5:  # Sábado ou Domingo
            fator_dia = random.uniform(1.3, 1.6)
        elif dia_semana == 4:  # Sexta
            fator_dia = random.uniform(1.1, 1.3)
        else:  # Segunda a Quinta
            fator_dia = random.uniform(0.8, 1.0)
        
        # Volume base de vendas por dia (entre 30 e 60 vendas)
        vendas_dia = int(random.uniform(30, 60) * fator_dia)
        
        for _ in range(vendas_dia):
            # Escolher prato baseado na popularidade
            prato_escolhido = random.choices(
                pratos,
                weights=[p['popularidade'] for p in pratos],
                k=1
            )[0]
            
            prato_obj = prato_escolhido['obj']
            
            # Determinar período do dia
            if random.random() < 0.85:  # 85% das vendas em almoço/jantar
                if random.random() < 0.53:  # 53% no almoço
                    periodo = 'almoço'
                else:
                    periodo = 'jantar'
            else:
                periodo = 'outros'
            
            # Quantidade (normalmente 1, às vezes 2-3 para grupos)
            quantidade = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1], k=1)[0]
            
            # Preço com pequena variação (promoções, descontos)
            preco_base = float(prato_obj.preco_venda)
            variacao = random.uniform(0.95, 1.0)  # Até 5% de desconto
            valor_unitario = round(preco_base * variacao, 2)
            
            # Criar venda
            venda = HistoricoVendas(
                data=data_atual.date(),
                prato_id=prato_obj.id,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=quantidade * valor_unitario,
                periodo_dia=periodo,
                dia_semana=dia_semana,
                semana_mes=(data_atual.day - 1) // 7 + 1,
                mes=data_atual.month,
                restaurant_id=restaurante.id
            )
            db.session.add(venda)
            total_vendas += 1
        
        # Commit a cada 10 dias
        if dia % 10 == 0:
            db.session.commit()
            print(f"  ✓ Dia {dia}/{dias} - {total_vendas} vendas criadas")
    
    db.session.commit()
    print(f"✅ {total_vendas} vendas simuladas!")

def main():
    with app.app_context():
        print("🚀 Iniciando Seeding do Demo Bistrô...\n")
        
        # 1. Criar/Buscar Restaurante
        restaurante = Restaurante.query.filter_by(nome="Demo Bistrô").first()
        if not restaurante:
            restaurante = Restaurante(
                nome="Demo Bistrô",
                cnpj="12345678000190",
                endereco="Rua Demo, 123 - São Paulo/SP",
                telefone="(11) 98765-4321",
                subscription_status="active",
                subscription_tier="pro",
                pricing_strategy="standard"
            )
            db.session.add(restaurante)
            db.session.commit()
            print(f"✅ Restaurante criado: {restaurante.nome}")
        else:
            print(f"ℹ️  Restaurante encontrado: {restaurante.nome}")
        
        # 2. Criar/Buscar Usuário
        usuario = Usuario.query.filter_by(email="demo@aleroprice.com").first()
        if not usuario:
            usuario = Usuario(
                nome="Admin Demo",
                email="demo@aleroprice.com",
                tipo="admin",
                restaurant_id=restaurante.id
            )
            usuario.set_senha("demo")
            db.session.add(usuario)
            db.session.commit()
            print(f"✅ Usuário criado: {usuario.email}")
        else:
            print(f"ℹ️  Usuário encontrado: {usuario.email}")
        
        # 3. Limpar dados anteriores
        limpar_dados_demo(restaurante.id)
        
        # 4. Criar catálogo base
        fornecedores, produtos, pratos = criar_base_estatica(restaurante)
        
        # 5. Simular 6 meses de compras e custos
        simular_historico(restaurante, fornecedores, produtos, pratos, dias=180)
        
        # 6. Simular vendas
        simular_vendas(restaurante, pratos, dias=180)
        
        print("\n" + "="*60)
        print("🎉 SEEDING COMPLETO!")
        print("="*60)
        print(f"\n📧 Login: demo@aleroprice.com")
        print(f"🔑 Senha: demo")
        print(f"\n🌐 Acesse: http://127.0.0.1:5000/auth/login\n")

if __name__ == '__main__':
    main()
