"""
Unit tests for profit calculation logic in the dashboard
Tests various scenarios including constant costs, mid-month price changes, and edge cases
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_produto import Produto
from app.models.modelo_previsao import HistoricoVendas


class TestProfitCalculations:
    
    def test_profit_with_constant_costs(self, session, restaurant, fornecedor):
        """Test profit calculation when ingredient costs don't change"""
        # Create product
        produto = Produto(
            nome="Arroz",
            unidade="kg",
            preco_unitario=5.50,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        
        # Create dish
        prato = Prato(
            nome="Arroz com Feijão",
            categoria="Pratos Principais",
            rendimento=1,
            unidade_rendimento="kg",
            porcoes_rendimento=1,
            preco_venda=15.00,
            restaurant_id=restaurant.id
        )
        session.add(prato)
        session.commit()
        
        # Create recipe (1kg rice per dish)
        insumo = PratoInsumo(
            prato_id=prato.id,
            produto_id=produto.id,
            quantidade=1.0
        )
        session.add(insumo)
        session.commit()
        
        # Create sales
        venda = HistoricoVendas(
            prato_id=prato.id,
            data=datetime.now().date(),
            quantidade=10,
            valor_total=150.00,  # 10 * R$15
            restaurant_id=restaurant.id
        )
        session.add(venda)
        session.commit()
        
        # Calculate expected values
        # Revenue: 10 dishes * R$15 = R$150
        # Cost: 10 dishes * 1kg * R$5.50 = R$55
        # Profit: R$150 - R$55 = R$95
        # Margin: (R$95 / R$150) * 100 = 63.33%
        
        # Verify dish cost calculation
        assert prato.custo_direto_total == pytest.approx(5.50, rel=0.01)
        assert prato.custo_direto_por_porcao == pytest.approx(5.50, rel=0.01)
    
    def test_profit_with_mid_month_cost_change(self, session, restaurant, fornecedor):
        """Test profit calculation when ingredient cost changes mid-period"""
        # Create product with initial price
        produto = Produto(
            nome="Carne",
            unidade="kg",
            preco_unitario=20.00,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        
        # Create dish
        prato = Prato(
            nome="Bife",
            categoria="Pratos Principais",
            rendimento=1,
            unidade_rendimento="kg",
            porcoes_rendimento=1,
            preco_venda=40.00,
            restaurant_id=restaurant.id
        )
        session.add(prato)
        session.commit()
        
        # Create recipe
        insumo = PratoInsumo(
            prato_id=prato.id,
            produto_id=produto.id,
            quantidade=0.3  # 300g per dish
        )
        session.add(insumo)
        session.commit()
        
        # Create sales before price change
        venda1 = HistoricoVendas(
            prato_id=prato.id,
            data=datetime.now().date() - timedelta(days=15),
            quantidade=10,
            valor_total=400.00,
            restaurant_id=restaurant.id
        )
        session.add(venda1)
        session.commit()
        
        # Update product price (simulate price increase)
        produto.ultimo_custo_anterior = produto.preco_unitario
        produto.preco_unitario = 25.00  # +25% increase
        produto.variacao_preco_pct = 25.0
        produto.data_alerta_inflacao = datetime.now()
        session.commit()
        
        # Create sales after price change
        venda2 = HistoricoVendas(
            prato_id=prato.id,
            data=datetime.now().date(),
            quantidade=10,
            valor_total=400.00,
            restaurant_id=restaurant.id
        )
        session.add(venda2)
        session.commit()
        
        # Verify price change tracking
        assert produto.variacao_preco_pct == 25.0
        assert produto.ultimo_custo_anterior == 20.00
        assert produto.preco_unitario == 25.00
    
    def test_profit_with_multiple_ingredients(self, session, restaurant, fornecedor):
        """Test profit calculation for dish with multiple ingredients"""
        # Create multiple products
        arroz = Produto(
            nome="Arroz",
            unidade="kg",
            preco_unitario=5.00,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        feijao = Produto(
            nome="Feijão",
            unidade="kg",
            preco_unitario=8.00,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        oleo = Produto(
            nome="Óleo",
            unidade="l",
            preco_unitario=10.00,
            estoque_atual=50.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add_all([arroz, feijao, oleo])
        
        # Create dish
        prato = Prato(
            nome="Arroz com Feijão",
            categoria="Pratos Principais",
            rendimento=1,
            unidade_rendimento="kg",
            porcoes_rendimento=1,
            preco_venda=20.00,
            restaurant_id=restaurant.id
        )
        session.add(prato)
        session.commit()
        
        # Create recipe with multiple ingredients
        insumos = [
            PratoInsumo(prato_id=prato.id, produto_id=arroz.id, quantidade=0.2),  # 200g rice = R$1.00
            PratoInsumo(prato_id=prato.id, produto_id=feijao.id, quantidade=0.15),  # 150g beans = R$1.20
            PratoInsumo(prato_id=prato.id, produto_id=oleo.id, quantidade=0.02),  # 20ml oil = R$0.20
        ]
        session.add_all(insumos)
        session.commit()
        
        # Expected total cost: R$1.00 + R$1.20 + R$0.20 = R$2.40
        assert prato.custo_direto_total == pytest.approx(2.40, rel=0.01)
        assert prato.custo_direto_por_porcao == pytest.approx(2.40, rel=0.01)
    
    def test_profit_with_zero_price_ingredient(self, session, restaurant, fornecedor):
        """Test handling of ingredients with no price set"""
        # Create product with zero price
        produto = Produto(
            nome="Ingrediente Novo",
            unidade="kg",
            preco_unitario=0.00,  # No price set yet
            estoque_atual=10.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        
        # Create dish
        prato = Prato(
            nome="Prato Teste",
            categoria="Testes",
            rendimento=1,
            unidade_rendimento="kg",
            porcoes_rendimento=1,
            preco_venda=15.00,
            restaurant_id=restaurant.id
        )
        session.add(prato)
        session.commit()
        
        # Create recipe
        insumo = PratoInsumo(
            prato_id=prato.id,
            produto_id=produto.id,
            quantidade=1.0
        )
        session.add(insumo)
        session.commit()
        
        # Cost should be zero
        assert prato.custo_direto_total == 0.00
    
    def test_margin_calculation(self, session, restaurant, fornecedor):
        """Test profit margin calculation"""
        # Create product
        produto = Produto(
            nome="Ingrediente",
            unidade="kg",
            preco_unitario=10.00,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        
        # Create dish with 50% margin
        prato = Prato(
            nome="Prato 50% Margem",
            categoria="Testes",
            rendimento=1,
            unidade_rendimento="kg",
            porcoes_rendimento=1,
            preco_venda=20.00,  # Cost R$10, Price R$20 = 50% margin
            restaurant_id=restaurant.id
        )
        session.add(prato)
        session.commit()
        
        # Create recipe
        insumo = PratoInsumo(
            prato_id=prato.id,
            produto_id=produto.id,
            quantidade=1.0  # R$10 cost
        )
        session.add(insumo)
        session.commit()
        
        # Calculate margin: ((20 - 10) / 20) * 100 = 50%
        custo = float(prato.custo_direto_por_porcao)
        preco = float(prato.preco_venda)
        margem = ((preco - custo) / preco) * 100 if preco > 0 else 0
        
        assert margem == pytest.approx(50.0, rel=0.01)
