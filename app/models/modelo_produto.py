from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from decimal import Decimal

class Produto(db.Model):
    """Modelo para representar produtos/insumos do estoque"""
    __tablename__ = 'produto'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True)  # Código interno ou EAN/GTIN
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    unidade = db.Column(db.String(5), nullable=False)  # kg, g, l, ml, un
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    estoque_minimo = db.Column(db.Float, default=0)
    estoque_atual = db.Column(db.Float, default=0)  # Atualizado via movimentações
    data_cadastro = db.Column(db.DateTime, default=func.now())
    data_atualizacao = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    ativo = db.Column(db.Boolean, default=True)
    categoria = db.Column(db.String(50))
    marca = db.Column(db.String(50))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'))
    
    # Validação de Preço / Inflação (Intelligence)
    ultimo_custo_anterior = db.Column(db.Numeric(10, 2)) # Preço antes da última atualização
    variacao_preco_pct = db.Column(db.Float) # % de variação no último update
    data_alerta_inflacao = db.Column(db.DateTime) # Data do último alerta significativo
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    fornecedor = db.relationship('Fornecedor', back_populates='produtos')
    movimentacoes = db.relationship('EstoqueMovimentacao', back_populates='produto', lazy='dynamic')
    itens_nf = db.relationship('NFItem', back_populates='produto', lazy='dynamic')
    prato_insumos = db.relationship('PratoInsumo', back_populates='produto', lazy='dynamic')
    registros_desperdicio = db.relationship('RegistroDesperdicio', back_populates='produto', lazy='dynamic')
    metas_desperdicio = db.relationship('MetaDesperdicio', back_populates='produto', foreign_keys='MetaDesperdicio.produto_id')
    
    # Restrições
    __table_args__ = (
        CheckConstraint('estoque_atual >= 0', name='check_estoque_positivo'),
        CheckConstraint('estoque_minimo >= 0', name='check_estoque_minimo_positivo'),
        CheckConstraint('preco_unitario >= 0', name='check_preco_positivo'),
    )
    
    def __repr__(self):
        return f'<Produto {self.nome} ({self.unidade})>'
    
    def calcular_valor_em_estoque(self):
        """Calcula o valor monetário total do estoque deste produto"""
        return float(self.preco_unitario) * self.estoque_atual
    
    def esta_em_falta(self):
        """Verifica se o produto está com estoque abaixo do mínimo"""
        return self.estoque_atual < self.estoque_minimo
    
    def atualizar_estoque(self, quantidade, tipo):
        """Atualiza o estoque com base na quantidade e tipo (entrada/saída)"""
        if tipo.lower() == 'entrada':
            self.estoque_atual += float(quantidade)
        elif tipo.lower() == 'saída':
            if self.estoque_atual < float(quantidade):
                raise ValueError(f'Estoque insuficiente para {self.nome}')
            self.estoque_atual -= float(quantidade)
        
        return self.estoque_atual
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nome': self.nome,
            'descricao': self.descricao,
            'unidade': self.unidade,
            'preco_unitario': float(self.preco_unitario),
            'estoque_minimo': self.estoque_minimo,
            'estoque_atual': self.estoque_atual,
            'categoria': self.categoria,
            'marca': self.marca,
            'fornecedor_id': self.fornecedor_id,
            'ativo': self.ativo
        }
