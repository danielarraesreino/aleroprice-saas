from app.extensions import db
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
from datetime import datetime

class CustoIndireto(db.Model):
    """Modelo para representar custos indiretos (fixos) para rateio"""
    __tablename__ = 'custo_indireto'
    
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_referencia = db.Column(db.Date, nullable=False)  # Mês/ano de referência
    tipo = db.Column(db.String(50))  # Ex: aluguel, energia, salários, etc.
    recorrente = db.Column(db.Boolean, default=False)  # Se é um custo recorrente
    observacao = db.Column(db.Text)
    data_cadastro = db.Column(db.DateTime, default=func.now())
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Restrições
    __table_args__ = (
        CheckConstraint('valor >= 0', name='check_valor_positivo'),
    )
    
    def __repr__(self):
        return f'<CustoIndireto {self.descricao}: R${self.valor:.2f}>'
    
    @classmethod
    def get_total_por_periodo(cls, data_inicio, data_fim, restaurant_id):
        """Retorna o total de custos indiretos em um período para um tenant"""
        if not restaurant_id:
            return 0
            
        query = cls.query.filter(
            cls.data_referencia >= data_inicio,
            cls.data_referencia <= data_fim,
            cls.restaurant_id == restaurant_id
        )
        # Soma todos os valores
        return sum(float(custo.valor) for custo in query.all())
    
    @classmethod
    def calcular_rateio_por_prato(cls, mes_referencia, total_producao, restaurant_id):
        """Calcula o valor de rateio por prato para um determinado mês
        
        Args:
            mes_referencia: Data de referência (primeiro dia do mês)
            total_producao: Total de pratos produzidos no período
            restaurant_id: ID do restaurante
            
        Returns:
            float: Valor de rateio por prato
        """
        if not restaurant_id:
            return 0

        # Calcula o primeiro e último dia do mês
        from calendar import monthrange
        ultimo_dia = monthrange(mes_referencia.year, mes_referencia.month)[1]
        data_inicio = datetime(mes_referencia.year, mes_referencia.month, 1).date()
        data_fim = datetime(mes_referencia.year, mes_referencia.month, ultimo_dia).date()
        
        # Obtém o total de custos no mês para o tenant
        total_custos = cls.get_total_por_periodo(data_inicio, data_fim, restaurant_id)
        
        # Evita divisão por zero
        if total_producao <= 0:
            return 0
            
        # Calcula valor de rateio por prato
        return total_custos / total_producao
    
    @classmethod
    def atualizar_rateio_pratos(cls, mes_referencia, total_producao, restaurant_id):
        """Atualiza o custo indireto rateado para todos os pratos de um tenant
        
        Args:
            mes_referencia: Data de referência (primeiro dia do mês)
            total_producao: Total de pratos produzidos no período
            restaurant_id: ID do restaurante
        """
        if not restaurant_id:
            return 0, 0

        from app.models.modelo_prato import Prato
        
        # Calcula o valor de rateio por prato
        valor_rateio = cls.calcular_rateio_por_prato(mes_referencia, total_producao, restaurant_id)
        
        # Atualiza o custo indireto em todos os pratos ativos DO TENANT
        pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).all()
        for prato in pratos:
            prato.custo_indireto = valor_rateio
            # Atualiza o preço sugerido
            prato.atualizar_preco_sugerido()
        
        db.session.commit()
        return len(pratos), valor_rateio
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'descricao': self.descricao,
            'valor': float(self.valor),
            'data_referencia': self.data_referencia.isoformat(),
            'tipo': self.tipo,
            'recorrente': self.recorrente,
            'observacao': self.observacao,
            'data_cadastro': self.data_cadastro.isoformat()
        }
