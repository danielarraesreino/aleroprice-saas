from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from decimal import Decimal
from datetime import datetime

class Prato(db.Model):
    """Modelo para representar pratos/receitas do cardápio"""
    __tablename__ = 'pratos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(50))  # Ex: Entrada, Prato Principal, Sobremesa
    rendimento = db.Column(db.Float, nullable=False)  # Quantidade total produzida
    unidade_rendimento = db.Column(db.String(20), nullable=False)  # kg, g, l, ml
    porcoes_rendimento = db.Column(db.Integer, nullable=False)  # Número de porções no rendimento total
    tempo_preparo = db.Column(db.Integer)  # em minutos
    preco_venda = db.Column(db.Numeric(10, 2))
    margem = db.Column(db.Numeric(5, 2), default=30.0)  # Margem de lucro em porcentagem
    custo_indireto = db.Column(db.Numeric(10, 2), default=0)  # Custo indireto por porção
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    insumos = db.relationship('PratoInsumo', back_populates='prato', cascade='all, delete-orphan')
    registros_desperdicio = db.relationship('RegistroDesperdicio', back_populates='prato')
    metas_desperdicio = db.relationship('MetaDesperdicio', back_populates='prato', foreign_keys='MetaDesperdicio.prato_id')
    
    # Restrições
    __table_args__ = (
        CheckConstraint('rendimento > 0', name='check_rendimento_positivo'),
        CheckConstraint('margem >= 0', name='check_margem_positiva'),
        CheckConstraint('preco_venda >= 0', name='check_preco_venda_positivo'),
    )
    
    def __repr__(self):
        return f'<Prato {self.nome}>'
    
    @property
    def custo_direto_total(self):
        """Custo total dos insumos para o rendimento completo"""
        return sum(insumo.custo_total for insumo in self.insumos)
    
    @property
    def custo_direto_por_porcao(self):
        """Custo direto por porção"""
        if self.porcoes_rendimento > 0:
            return self.custo_direto_total / self.porcoes_rendimento
        return 0
    
    @property
    def custo_total_por_porcao(self):
        """Custo total por porção (direto + indireto)"""
        return self.custo_direto_por_porcao + float(self.custo_indireto)
    
    def calcular_preco_sugerido(self):
        """Calcula o preço sugerido com base nos custos e margem"""
        custo_total = self.custo_total_por_porcao
        if custo_total > 0:
            return custo_total * (1 + float(self.margem) / 100)
        return 0
    
    def atualizar_preco_sugerido(self):
        """Atualiza o preço de venda com base no preço sugerido"""
        self.preco_venda = self.calcular_preco_sugerido()
        return self.preco_venda
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'rendimento': self.rendimento,
            'unidade_rendimento': self.unidade_rendimento,
            'porcoes_rendimento': self.porcoes_rendimento,
            'tempo_preparo': self.tempo_preparo,
            'preco_venda': float(self.preco_venda) if self.preco_venda else None,
            'margem': float(self.margem),
            'custo_direto_total': self.custo_direto_total,
            'custo_direto_por_porcao': self.custo_direto_por_porcao,
            'custo_indireto': float(self.custo_indireto),
            'custo_total_por_porcao': self.custo_total_por_porcao,
            'preco_sugerido': self.calcular_preco_sugerido(),
            'insumos': [insumo.to_dict() for insumo in self.insumos]
        }

class PratoInsumo(db.Model):
    """Modelo para associação entre Prato e Produto (insumos da receita)"""
    __tablename__ = 'prato_insumo'
    
    id = db.Column(db.Integer, primary_key=True)
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id', ondelete='CASCADE'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id', ondelete='CASCADE'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)  # Quantidade do insumo para o prato completo
    ordem = db.Column(db.Integer, default=1)  # Ordem do insumo na receita
    obrigatorio = db.Column(db.Boolean, default=True)  # Se é opcional ou não
    observacao = db.Column(db.Text)  # Observações sobre o uso do insumo
    
    # Relações
    prato = db.relationship('Prato', back_populates='insumos')
    produto = db.relationship('Produto', back_populates='prato_insumos')
    
    # Restrições
    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_positiva'),
    )
    
    def __repr__(self):
        return f'<PratoInsumo {self.produto.nome if self.produto else "N/A"} para {self.prato.nome if self.prato else "N/A"}>'
    
    @property
    def custo_unitario(self):
        """Retorna o custo unitário do insumo"""
        if self.produto:
            return float(self.produto.preco_unitario)
        return 0
    
    @property
    def custo_total(self):
        """Calcula o custo total do insumo para o prato"""
        return float(self.custo_unitario) * float(self.quantidade)
    
    @property
    def custo_por_porcao(self):
        """Calcula o custo do insumo por porção do prato"""
        if self.prato and self.prato.porcoes_rendimento > 0:
            return self.custo_total / self.prato.porcoes_rendimento
        return 0
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'prato_id': self.prato_id,
            'produto_id': self.produto_id,
            'quantidade': self.quantidade,
            'ordem': self.ordem,
            'obrigatorio': self.obrigatorio,
            'observacao': self.observacao,
            'custo_unitario': float(self.custo_unitario),
            'custo_total': float(self.custo_total),
            'custo_por_porcao': float(self.custo_por_porcao),
            'produto': self.produto.to_dict() if self.produto else None
        }
