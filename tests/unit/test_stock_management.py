"""
Unit tests for stock deduction and management logic
Tests stock movements, deductions from sales, and inventory tracking
"""
import pytest
from datetime import datetime
from app.models.modelo_produto import Produto
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_estoque import EstoqueMovimentacao


class TestStockManagement:
    
    def test_stock_entry_movement(self, session, restaurant, fornecedor):
        """Test creating a stock entry movement"""
        # Create product
        produto = Produto(
            nome="Arroz",
            unidade="kg",
            preco_unitario=5.00,
            estoque_atual=0.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        initial_stock = produto.estoque_atual
        
        # Create entry movement using class method
        movimentacao = EstoqueMovimentacao.registrar_entrada(
            produto_id=produto.id,
            quantidade=50.0,
            referencia="Compra",
            observacao="Compra de fornecedor"
        )
        
        # Refresh to get updated values
        session.refresh(produto)
        
        # Verify
        assert produto.estoque_atual == initial_stock + 50.0
        assert movimentacao.tipo == "entrada"
        assert movimentacao.quantidade == 50.0
    
    def test_stock_exit_movement(self, session, restaurant, fornecedor):
        """Test creating a stock exit movement"""
        # Create product with stock
        produto = Produto(
            nome="Feijão",
            unidade="kg",
            preco_unitario=8.00,
            estoque_atual=100.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        initial_stock = produto.estoque_atual
        
        # Create exit movement using class method
        movimentacao = EstoqueMovimentacao.registrar_saida(
            produto_id=produto.id,
            quantidade=20.0,
            referencia="Venda",
            observacao="Venda de prato"
        )
        
        # Refresh to get updated values
        session.refresh(produto)
        
        # Verify
        assert produto.estoque_atual == initial_stock - 20.0
        assert movimentacao.tipo == "saída"
    
    def test_insufficient_stock_error(self, session, restaurant, fornecedor):
        """Test error when trying to deduct more stock than available"""
        # Create product with limited stock
        produto = Produto(
            nome="Óleo",
            unidade="l",
            preco_unitario=10.00,
            estoque_atual=5.0,  # Only 5 liters available
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        # Try to deduct more than available using class method
        with pytest.raises(ValueError, match="Estoque insuficiente"):
            EstoqueMovimentacao.registrar_saida(
                produto_id=produto.id,
                quantidade=10.0
            )
    
    def test_stock_deduction_from_recipe(self, session, restaurant, fornecedor):
        """Test stock deduction based on recipe when dish is sold"""
        # Create ingredients
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
            estoque_atual=80.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add_all([arroz, feijao])
        
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
        
        # Create recipe
        insumos = [
            PratoInsumo(prato_id=prato.id, produto_id=arroz.id, quantidade=0.2),  # 200g rice
            PratoInsumo(prato_id=prato.id, produto_id=feijao.id, quantidade=0.15),  # 150g beans
        ]
        session.add_all(insumos)
        session.commit()
        
        # Record initial stocks
        initial_arroz = arroz.estoque_atual
        initial_feijao = feijao.estoque_atual
        
        # Simulate selling 10 dishes
        quantidade_vendida = 10
        
        # Deduct stock for each ingredient using class method
        for insumo in prato.insumos:
            quantidade_usar = insumo.quantidade * quantidade_vendida
            EstoqueMovimentacao.registrar_saida(
                produto_id=insumo.produto_id,
                quantidade=quantidade_usar,
                referencia=f"Venda de {prato.nome}",
                observacao=f"Venda de {quantidade_vendida} porções"
            )
        
        # Refresh to get updated values
        session.refresh(arroz)
        session.refresh(feijao)
        
        # Verify stock deductions
        assert arroz.estoque_atual == pytest.approx(initial_arroz - (0.2 * 10), rel=0.01)  # 98.0
        assert feijao.estoque_atual == pytest.approx(initial_feijao - (0.15 * 10), rel=0.01)  # 78.5
    
    def test_stock_alert_low_stock(self, session, restaurant, fornecedor):
        """Test low stock alert when stock falls below minimum"""
        # Create product with minimum stock level
        produto = Produto(
            nome="Sal",
            unidade="kg",
            preco_unitario=2.00,
            estoque_atual=15.0,
            estoque_minimo=10.0,  # Alert when below 10kg
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        # Stock is above minimum
        assert not produto.esta_em_falta()
        
        # Deduct stock below minimum
        EstoqueMovimentacao.registrar_saida(
            produto_id=produto.id,
            quantidade=8.0
        )
        
        # Refresh to get updated values
        session.refresh(produto)
        
        # Stock should now be below minimum (7.0 < 10.0)
        assert produto.esta_em_falta()
        assert produto.estoque_atual == 7.0
    
    def test_stock_value_calculation(self, session, restaurant, fornecedor):
        """Test calculation of total stock value"""
        # Create product
        produto = Produto(
            nome="Carne",
            unidade="kg",
            preco_unitario=25.00,
            estoque_atual=40.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        # Calculate stock value
        valor_estoque = produto.calcular_valor_em_estoque()
        
        # Expected: 40kg * R$25/kg = R$1000
        assert valor_estoque == pytest.approx(1000.00, rel=0.01)
    
    def test_multiple_movements_tracking(self, session, restaurant, fornecedor):
        """Test tracking multiple stock movements for a product"""
        # Create product
        produto = Produto(
            nome="Tomate",
            unidade="kg",
            preco_unitario=4.00,
            estoque_atual=0.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        # Create multiple movements
        EstoqueMovimentacao.registrar_entrada(produto.id, 50.0, observacao="Compra inicial")
        EstoqueMovimentacao.registrar_saida(produto.id, 10.0, observacao="Venda")
        EstoqueMovimentacao.registrar_entrada(produto.id, 30.0, observacao="Reposição")
        EstoqueMovimentacao.registrar_saida(produto.id, 15.0, observacao="Venda")
        
        # Refresh to get updated values
        session.refresh(produto)
        
        # Expected final stock: 0 + 50 - 10 + 30 - 15 = 55
        assert produto.estoque_atual == 55.0
        
        # Verify all movements were recorded
        all_movements = session.query(EstoqueMovimentacao).filter_by(
            produto_id=produto.id
        ).all()
        assert len(all_movements) == 4
    
    def test_movement_value_tracking(self, session, restaurant, fornecedor):
        """Test that movement values are tracked correctly"""
        # Create product
        produto = Produto(
            nome="Açúcar",
            unidade="kg",
            preco_unitario=3.00,
            estoque_atual=0.0,
            fornecedor_id=fornecedor.id,
            restaurant_id=restaurant.id
        )
        session.add(produto)
        session.commit()
        
        # Register entry with specific unit value
        movimentacao = EstoqueMovimentacao.registrar_entrada(
            produto_id=produto.id,
            quantidade=20.0,
            valor_unitario=3.50,
            observacao="Compra com preço especial"
        )
        
        # Verify movement value
        assert movimentacao.valor_unitario == 3.50
        assert movimentacao.valor_total == pytest.approx(70.00, rel=0.01)  # 20 * 3.50
        
        # Verify product price was updated
        session.refresh(produto)
        assert produto.preco_unitario == 3.50
