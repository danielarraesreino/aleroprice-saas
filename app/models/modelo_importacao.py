"""
Modelo para histórico de importações de vendas
"""
from app.extensions import db
from sqlalchemy import func
from datetime import datetime
import json


class ImportacaoHistorico(db.Model):
    """Modelo para registrar histórico de importações"""
    __tablename__ = 'importacao_historico'
    
    id = db.Column(db.Integer, primary_key=True)
    data_importacao = db.Column(db.DateTime, default=func.now(), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_arquivo = db.Column(db.String(10))  # csv, xlsx, xls
    
    # Estatísticas da importação
    total_linhas = db.Column(db.Integer, default=0)
    total_agregados = db.Column(db.Integer, default=0)
    total_importados = db.Column(db.Integer, default=0)
    total_ignorados = db.Column(db.Integer, default=0)
    
    # Produtos não encontrados (JSON)
    produtos_nao_encontrados = db.Column(db.Text)  # JSON array
    
    # Mapeamentos manuais realizados (JSON)
    mapeamentos_manuais = db.Column(db.Text)  # JSON object
    
    # Status da importação
    status = db.Column(db.String(20), default='concluida')  # concluida, erro, cancelada
    mensagem_erro = db.Column(db.Text)
    
    # Tempo de processamento
    tempo_processamento = db.Column(db.Float)  # em segundos
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='importacoes')
    
    def __repr__(self):
        return f'<ImportacaoHistorico {self.nome_arquivo} - {self.data_importacao}>'
    
    def get_produtos_nao_encontrados(self):
        """Retorna lista de produtos não encontrados"""
        if self.produtos_nao_encontrados:
            return json.loads(self.produtos_nao_encontrados)
        return []
    
    def set_produtos_nao_encontrados(self, produtos):
        """Define lista de produtos não encontrados"""
        self.produtos_nao_encontrados = json.dumps(produtos)
    
    def get_mapeamentos_manuais(self):
        """Retorna dicionário de mapeamentos manuais"""
        if self.mapeamentos_manuais:
            return json.loads(self.mapeamentos_manuais)
        return {}
    
    def set_mapeamentos_manuais(self, mapeamentos):
        """Define dicionário de mapeamentos manuais"""
        self.mapeamentos_manuais = json.dumps(mapeamentos)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'data_importacao': self.data_importacao.isoformat(),
            'nome_arquivo': self.nome_arquivo,
            'tipo_arquivo': self.tipo_arquivo,
            'total_linhas': self.total_linhas,
            'total_agregados': self.total_agregados,
            'total_importados': self.total_importados,
            'total_ignorados': self.total_ignorados,
            'produtos_nao_encontrados': self.get_produtos_nao_encontrados(),
            'mapeamentos_manuais': self.get_mapeamentos_manuais(),
            'status': self.status,
            'mensagem_erro': self.mensagem_erro,
            'tempo_processamento': self.tempo_processamento,
            'usuario': self.usuario.nome if self.usuario else None
        }


class MapeamentoProduto(db.Model):
    """Modelo para armazenar mapeamentos manuais de produtos"""
    __tablename__ = 'mapeamento_produto'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_original = db.Column(db.String(255), nullable=False, index=True)
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'), nullable=False)
    
    # Metadados
    data_criacao = db.Column(db.DateTime, default=func.now())
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    vezes_usado = db.Column(db.Integer, default=0)
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relacionamentos
    prato = db.relationship('Prato', backref='mapeamentos')
    criado_por = db.relationship('Usuario', backref='mapeamentos_criados')
    
    def __repr__(self):
        return f'<MapeamentoProduto "{self.nome_original}" → {self.prato.nome if self.prato else "N/A"}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome_original': self.nome_original,
            'prato_id': self.prato_id,
            'prato_nome': self.prato.nome if self.prato else None,
            'vezes_usado': self.vezes_usado,
            'data_criacao': self.data_criacao.isoformat()
        }
