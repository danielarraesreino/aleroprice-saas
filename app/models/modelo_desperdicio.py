from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from datetime import datetime, date
from decimal import Decimal

class CategoriaDesperdicio(db.Model):
    """Modelo para categorias de desperdício (ex: sobras, estragado, preparo, etc)"""
    __tablename__ = 'categoria_desperdicio'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    cor = db.Column(db.String(7))  # Para uso em gráficos (ex: #FF0000)
    ativo = db.Column(db.Boolean, default=True)
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    registros = db.relationship('RegistroDesperdicio', back_populates='categoria')
    metas = db.relationship('MetaDesperdicio', back_populates='categoria')
    
    def __repr__(self):
        return f'<CategoriaDesperdicio {self.nome}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'cor': self.cor,
            'ativo': self.ativo
        }

class RegistroDesperdicio(db.Model):
    """Modelo para registrar instancias de desperdício"""
    __tablename__ = 'registro_desperdicio'
    
    id = db.Column(db.Integer, primary_key=True)
    data_registro = db.Column(db.DateTime, default=func.now(), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria_desperdicio.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'))
    quantidade = db.Column(db.Float, nullable=False)  # Quantidade desperdiçada
    unidade = db.Column(db.String(10), nullable=False)  # kg, g, l, ml, un, etc
    valor_estimado = db.Column(db.Numeric(10, 2))  # Valor monetario estimado da perda
    motivo = db.Column(db.String(100))  # Motivo do desperdício
    responsavel = db.Column(db.String(100))  # Pessoa que registrou
    local = db.Column(db.String(100))  # Local onde ocorreu (cozinha, salão, estoque, etc)
    descricao = db.Column(db.Text)  # Detalhes adicionais
    acoes_corretivas = db.Column(db.Text)  # Ações tomadas para evitar recorrência
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Restrições
    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_positiva'),
        CheckConstraint('produto_id IS NOT NULL OR prato_id IS NOT NULL', 
                       name='check_produto_ou_prato'),  # Pelo menos um deve ser especificado
    )
    
    # Relações
    categoria = db.relationship('CategoriaDesperdicio', back_populates='registros')
    produto = db.relationship('Produto', back_populates='registros_desperdicio')
    prato = db.relationship('Prato', back_populates='registros_desperdicio')
    
    def __repr__(self):
        item = self.produto.nome if self.produto else self.prato.nome if self.prato else "N/A"
        return f'<RegistroDesperdicio {self.quantidade} {self.unidade} de {item}>'
    
    @property
    def item_nome(self):
        """Retorna o nome do item desperdiçado (produto ou prato)"""
        if self.produto:
            return self.produto.nome
        elif self.prato:
            return self.prato.nome
        return "Não especificado"
    
    @property
    def tipo_item(self):
        """Retorna o tipo do item desperdiçado (produto ou prato)"""
        if self.produto:
            return "Produto/Insumo"
        elif self.prato:
            return "Prato"
        return "Não especificado"
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'data_registro': self.data_registro.isoformat(),
            'categoria_id': self.categoria_id,
            'produto_id': self.produto_id,
            'prato_id': self.prato_id,
            'quantidade': self.quantidade,
            'unidade': self.unidade,
            'valor_estimado': float(self.valor_estimado) if self.valor_estimado else None,
            'motivo': self.motivo,
            'responsavel': self.responsavel,
            'local': self.local,
            'descricao': self.descricao,
            'acoes_corretivas': self.acoes_corretivas,
            'item_nome': self.item_nome,
            'tipo_item': self.tipo_item
        }

class MetaDesperdicio(db.Model):
    """Modelo para gerenciar metas de redução de desperdício"""
    __tablename__ = 'meta_desperdicio'
    
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False, default=date.today)
    data_fim = db.Column(db.Date, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria_desperdicio.id'))
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'))
    valor_inicial = db.Column(db.Float, nullable=False)  # Valor base de desperdício
    valor_meta = db.Column(db.Float, nullable=False)  # Valor absoluto da meta
    meta_reducao_percentual = db.Column(db.Float, nullable=False)  # % de redução desejada
    ativo = db.Column(db.Boolean, default=True)
    acoes_propostas = db.Column(db.Text)  # Ações a serem implementadas
    responsavel = db.Column(db.String(100))  # Pessoa responsavel pela meta
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    categoria = db.relationship('CategoriaDesperdicio', back_populates='metas')
    produto = db.relationship('Produto', back_populates='metas_desperdicio')
    prato = db.relationship('Prato', back_populates='metas_desperdicio', foreign_keys=[prato_id])
    
    def __repr__(self):
        return f'<MetaDesperdicio {self.descricao}>'
    
    @property
    def valor_atual(self):
        """Calcula o valor atual de desperdício"""
        from sqlalchemy import func
        
        query = db.session.query(func.sum(RegistroDesperdicio.quantidade))
        query = query.filter(RegistroDesperdicio.data_registro >= self.data_inicio)
        
        if date.today() < self.data_fim:
            end_date = date.today()
        else:
            end_date = self.data_fim
            
        query = query.filter(RegistroDesperdicio.data_registro <= end_date)
        
        if self.categoria_id:
            query = query.filter(RegistroDesperdicio.categoria_id == self.categoria_id)
        if self.produto_id:
            query = query.filter(RegistroDesperdicio.produto_id == self.produto_id)
        
        return query.scalar() or 0
    
    @property
    def status(self):
        """Retorna o status da meta (Em Andamento, Concluída, Atrasada)"""
        if not self.ativo:
            return "Cancelada"
            
        if date.today() > self.data_fim:
            if self.valor_atual <= self.valor_meta:
                return "Concluída"
            return "Atrasada"
            
        return "Em Andamento"
    
    @property
    def progresso(self):
        """Calcula o progresso atual em relação à meta"""
        if self.valor_inicial == 0:
            return 0
            
        reducao_absoluta = self.valor_inicial - self.valor_atual
        reducao_percentual = (reducao_absoluta / self.valor_inicial) * 100
        
        if self.meta_reducao_percentual == 0:
            return 100 if reducao_percentual >= 0 else 0
            
        progresso = (reducao_percentual / self.meta_reducao_percentual) * 100
        return min(max(progresso, 0), 100)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'descricao': self.descricao,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat(),
            'categoria_id': self.categoria_id,
            'produto_id': self.produto_id,
            'prato_id': self.prato_id,
            'valor_inicial': self.valor_inicial,
            'valor_meta': self.valor_meta,
            'meta_reducao_percentual': self.meta_reducao_percentual,
            'ativo': self.ativo,
            'acoes_propostas': self.acoes_propostas,
            'responsavel': self.responsavel,
            'valor_atual': self.valor_atual,
            'status': self.status,
            'progresso': self.progresso
        }
