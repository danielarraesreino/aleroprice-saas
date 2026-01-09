from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from datetime import datetime

class NFNota(db.Model):
    """Modelo para representar as Notas Fiscais Eletrônicas"""
    __tablename__ = 'nf_nota'
    
    id = db.Column(db.Integer, primary_key=True)
    chave_acesso = db.Column(db.String(44), unique=True, nullable=False, index=True)
    numero = db.Column(db.String(10), nullable=False)
    serie = db.Column(db.String(3), nullable=False)
    data_emissao = db.Column(db.DateTime, nullable=False)
    data_importacao = db.Column(db.DateTime, default=func.now())
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    valor_produtos = db.Column(db.Numeric(10, 2), nullable=False)
    valor_frete = db.Column(db.Numeric(10, 2), default=0)
    valor_seguro = db.Column(db.Numeric(10, 2), default=0)
    valor_desconto = db.Column(db.Numeric(10, 2), default=0)
    valor_impostos = db.Column(db.Numeric(10, 2), default=0)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    xml_data = db.Column(db.Text)  # Armazena o XML original para referência
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    fornecedor = db.relationship('Fornecedor', back_populates='notas_fiscais')
    itens = db.relationship('NFItem', back_populates='nota', cascade='all, delete-orphan')
    
    # Restrições
    __table_args__ = (
        CheckConstraint('valor_total >= 0', name='check_valor_total_positivo'),
        CheckConstraint('valor_produtos >= 0', name='check_valor_produtos_positivo'),
        CheckConstraint('valor_frete >= 0', name='check_valor_frete_positivo'),
        CheckConstraint('valor_seguro >= 0', name='check_valor_seguro_positivo'),
        CheckConstraint('valor_desconto >= 0', name='check_valor_desconto_positivo'),
        CheckConstraint('valor_impostos >= 0', name='check_valor_impostos_positivo'),
    )
    
    def __repr__(self):
        return f'<NFNota {self.numero}/{self.serie} - {self.fornecedor.razao_social if self.fornecedor else "N/A"}>'
    
    def get_data_formatada(self):
        """Retorna a data de emissão formatada"""
        return self.data_emissao.strftime('%d/%m/%Y')
    
    @property
    def valor_liquido(self):
        """Calcula o valor líquido (total - descontos)"""
        return float(self.valor_total) - float(self.valor_desconto)
    
    def atualizar_estoque(self):
        """Atualiza o estoque com base nos itens da nota fiscal"""
        from app.models.modelo_estoque import EstoqueMovimentacao
        from app.utils.calculos import calcular_preco_medio_ponderado
        
        for item in self.itens:
            # Calcular novo preço médio ponderado
            novo_preco = calcular_preco_medio_ponderado(
                estoque_atual=float(item.produto.estoque_atual),
                preco_atual=float(item.produto.preco_unitario or 0),
                quantidade_nova=float(item.quantidade),
                preco_novo=float(item.valor_unitario)
            )
            
            # Atualiza o preço unitário do produto
            item.produto.preco_unitario = novo_preco
            
            # Cria um movimento de estoque para cada item
            movimento = EstoqueMovimentacao(
                produto_id=item.produto_id,
                quantidade=item.quantidade,
                tipo='entrada',
                data_movimentacao=datetime.now(),
                referencia=f'NF {self.numero}/{self.serie}',
                ref_id=item.id,
                valor_unitario=item.valor_unitario,
                restaurant_id=self.restaurant_id
            )
            db.session.add(movimento)
            
            # Atualiza o estoque atual
            item.produto.estoque_atual += float(item.quantidade)
            
        db.session.commit()


class NFItem(db.Model):
    """Modelo para representar os itens de uma Nota Fiscal"""
    __tablename__ = 'nf_item'
    
    id = db.Column(db.Integer, primary_key=True)
    nf_nota_id = db.Column(db.Integer, db.ForeignKey('nf_nota.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    num_item = db.Column(db.Integer, nullable=False)  # Número do item na NF
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Numeric(10, 4), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    unidade_medida = db.Column(db.String(5), nullable=False)  # Unidade na NF
    cfop = db.Column(db.String(4))  # Código Fiscal de Operações e Prestações
    ncm = db.Column(db.String(8))  # Nomenclatura Comum do Mercosul
    percentual_icms = db.Column(db.Numeric(5, 2), default=0)
    valor_icms = db.Column(db.Numeric(10, 2), default=0)
    percentual_ipi = db.Column(db.Numeric(5, 2), default=0)
    valor_ipi = db.Column(db.Numeric(10, 2), default=0)
    
    # Relações
    nota = db.relationship('NFNota', back_populates='itens')
    produto = db.relationship('Produto', back_populates='itens_nf')
    
    # Restrições
    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_positiva'),
        CheckConstraint('valor_unitario >= 0', name='check_valor_unitario_positivo'),
        CheckConstraint('valor_total >= 0', name='check_valor_total_item_positivo'),
    )
    
    def __repr__(self):
        return f'<NFItem {self.num_item} - {self.produto.nome if self.produto else "N/A"}>'
    
    @property
    def valor_com_impostos(self):
        """Calcula o valor com impostos incluídos"""
        valor_base = float(self.valor_total)
        valor_impostos = float(self.valor_icms) + float(self.valor_ipi)
        return valor_base + valor_impostos
