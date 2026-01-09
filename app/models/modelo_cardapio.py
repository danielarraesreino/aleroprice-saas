from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from datetime import datetime, date

class Cardapio(db.Model):
    """Modelo para representar um cardápio"""
    __tablename__ = 'cardapio'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    data_inicio = db.Column(db.Date, nullable=False, default=date.today)
    data_fim = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(50))  # Ex: diário, semanal, sazonal, eventos
    temporada = db.Column(db.String(50))  # Ex: verão, inverno, natal, ano novo
    data_criacao = db.Column(db.DateTime, default=func.now())
    data_atualizacao = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relações
    secoes = db.relationship('CardapioSecao', back_populates='cardapio', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Cardapio {self.nome}>'
    
    @property
    def total_pratos(self):
        """Retorna o total de pratos deste cardápio"""
        total = 0
        for secao in self.secoes:
            total += len(secao.itens)
        return total
    
    @property
    def ticket_medio_estimado(self):
        """Calcula o ticket médio estimado do cardápio"""
        if self.total_pratos == 0:
            return 0
        
        soma_precos = 0
        total_itens = 0
        
        for secao in self.secoes:
            for item in secao.itens:
                if item.preco_venda:
                    soma_precos += float(item.preco_venda)
                    total_itens += 1
        
        if total_itens == 0:
            return 0
            
        return soma_precos / total_itens
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativo': self.ativo,
            'tipo': self.tipo,
            'temporada': self.temporada,
            'data_criacao': self.data_criacao.isoformat(),
            'data_atualizacao': self.data_atualizacao.isoformat(),
            'total_pratos': self.total_pratos,
            'ticket_medio_estimado': float(self.ticket_medio_estimado),
            'secoes': [secao.to_dict() for secao in self.secoes]
        }

class CardapioSecao(db.Model):
    """Modelo para representar uma seção do cardápio (ex: entradas, pratos principais)"""
    __tablename__ = 'cardapio_secao'
    
    id = db.Column(db.Integer, primary_key=True)
    cardapio_id = db.Column(db.Integer, db.ForeignKey('cardapio.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, default=1)  # Ordem de exibição da seção
    
    # Relações
    cardapio = db.relationship('Cardapio', back_populates='secoes')
    itens = db.relationship('CardapioItem', back_populates='secao', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CardapioSecao {self.nome} do {self.cardapio.nome if self.cardapio else "cardápio não definido"}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'cardapio_id': self.cardapio_id,
            'nome': self.nome,
            'descricao': self.descricao,
            'ordem': self.ordem,
            'itens': [item.to_dict() for item in self.itens]
        }

class CardapioItem(db.Model):
    """Modelo para representar um item do cardápio (prato incluído no cardápio)"""
    __tablename__ = 'cardapio_item'
    
    id = db.Column(db.Integer, primary_key=True)
    secao_id = db.Column(db.Integer, db.ForeignKey('cardapio_secao.id'), nullable=False)
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'), nullable=False)
    ordem = db.Column(db.Integer, default=1)  # Ordem de exibição do item na seção
    preco_venda = db.Column(db.Numeric(10, 2))  # Preço específico para este cardápio (opcional)
    destaque = db.Column(db.Boolean, default=False)  # Se é um prato em destaque
    disponivel = db.Column(db.Boolean, default=True)  # Se está disponível no cardápio atualmente
    observacao = db.Column(db.Text)  # Observações específicas para este cardápio
    
    # Relações
    secao = db.relationship('CardapioSecao', back_populates='itens')
    prato = db.relationship('Prato')
    
    __table_args__ = (
        # Garantir que o mesmo prato não apareça duas vezes na mesma seção
        db.UniqueConstraint('secao_id', 'prato_id', name='uq_secao_prato'),
    )
    
    def __repr__(self):
        return f'<CardapioItem {self.prato.nome if self.prato else "não definido"} em {self.secao.nome if self.secao else "seção não definida"}>'
    
    @property
    def get_preco_venda(self):
        """Retorna o preço de venda para este item no cardápio"""
        # Se tiver preço específico para o cardápio, usa este
        if self.preco_venda is not None:
            return self.preco_venda
        # Senão, usa o preço padrão do prato
        return self.prato.preco_venda if self.prato else None
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'secao_id': self.secao_id,
            'prato_id': self.prato_id,
            'ordem': self.ordem,
            'preco_venda': float(self.preco_venda) if self.preco_venda else None,
            'destaque': self.destaque,
            'disponivel': self.disponivel,
            'observacao': self.observacao,
            'preco_venda_atual': float(self.get_preco_venda) if self.get_preco_venda else None,
            'prato': self.prato.to_dict() if self.prato else None
        }
