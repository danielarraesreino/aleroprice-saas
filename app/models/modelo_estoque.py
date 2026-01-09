from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from datetime import datetime

class EstoqueMovimentacao(db.Model):
    """Modelo para representar movimentações de estoque (entradas e saídas)"""
    __tablename__ = 'estoque_movimentacao'
    
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada' ou 'saída'
    data_movimentacao = db.Column(db.DateTime, nullable=False, default=func.now())
    referencia = db.Column(db.String(100))  # Ex: "NF 1234", "Pedido 567", "Ajuste Manual"
    ref_id = db.Column(db.Integer)  # ID da entidade relacionada (NFItem, Pedido, etc)
    valor_unitario = db.Column(db.Numeric(10, 2))  # Valor unitário na movimentação
    observacao = db.Column(db.Text)
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    produto = db.relationship('Produto', back_populates='movimentacoes')
    
    # Restrições
    __table_args__ = (
        CheckConstraint("tipo in ('entrada', 'saída')", name='check_tipo_movimento'),
        CheckConstraint('quantidade > 0', name='check_quantidade_positiva'),
        CheckConstraint('valor_unitario IS NULL OR valor_unitario >= 0', name='check_valor_positivo'),
    )
    
    def __repr__(self):
        return f'<EstoqueMovimentacao {self.tipo} de {self.quantidade} {self.produto.unidade} de {self.produto.nome}>'
    
    @property
    def valor_total(self):
        """Calcula o valor total da movimentação"""
        if self.valor_unitario is not None:
            return float(self.valor_unitario) * float(self.quantidade)
        return None
    
    @classmethod
    def registrar_entrada(cls, produto_id, quantidade, referencia=None, ref_id=None, valor_unitario=None, observacao=None):
        """Método de classe para registrar uma entrada de estoque"""
        from app.models.modelo_produto import Produto
        
        produto = Produto.query.get(produto_id)
        if not produto:
             raise ValueError(f'Produto com ID {produto_id} não encontrado') # Deveria filtrar por tenant? O caller já filtra.
        
        movimento = cls(
            produto_id=produto_id,
            quantidade=quantidade,
            tipo='entrada',
            data_movimentacao=datetime.now(),
            referencia=referencia,
            ref_id=ref_id,
            valor_unitario=valor_unitario,
            observacao=observacao,
            restaurant_id=produto.restaurant_id # HERANÇA DE TENANT
        )
        
        # Atualiza o estoque atual do produto
        produto.estoque_atual += float(quantidade)
        if valor_unitario is not None:
            produto.preco_unitario = valor_unitario
        
        db.session.add(movimento)
        db.session.commit()
        return movimento
    
    @classmethod
    def registrar_saida(cls, produto_id, quantidade, referencia=None, ref_id=None, observacao=None):
        """Método de classe para registrar uma saída de estoque"""
        from app.models.modelo_produto import Produto
        
        produto = Produto.query.get(produto_id)
        if not produto:
            raise ValueError(f'Produto com ID {produto_id} não encontrado')
        
        if produto.estoque_atual < float(quantidade):
            raise ValueError(f'Estoque insuficiente para {produto.nome}. Atual: {produto.estoque_atual}, Solicitado: {quantidade}')
        
        movimento = cls(
            produto_id=produto_id,
            quantidade=quantidade,
            tipo='saída',
            data_movimentacao=datetime.now(),
            referencia=referencia,
            ref_id=ref_id,
            valor_unitario=produto.preco_unitario,  # Usa o preço atual do produto
            observacao=observacao,
            restaurant_id=produto.restaurant_id # HERANÇA DE TENANT
        )
        
        # Atualiza o estoque atual do produto
        produto.estoque_atual -= float(quantidade)
        
        db.session.add(movimento)
        db.session.commit()
        return movimento
    
    @classmethod
    def get_produtos_em_falta(cls):
        """Retorna os produtos que estão abaixo do estoque mínimo"""
        from app.models.modelo_produto import Produto
        return Produto.query.filter(Produto.estoque_atual < Produto.estoque_minimo).all()
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'produto_id': self.produto_id,
            'quantidade': self.quantidade,
            'tipo': self.tipo,
            'data_movimentacao': self.data_movimentacao.isoformat(),
            'referencia': self.referencia,
            'ref_id': self.ref_id,
            'valor_unitario': float(self.valor_unitario) if self.valor_unitario else None,
            'observacao': self.observacao,
            'valor_total': float(self.valor_total) if self.valor_total else None,
            'produto': self.produto.to_dict() if self.produto else None
        }
