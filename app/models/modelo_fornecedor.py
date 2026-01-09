from app.extensions import db
from sqlalchemy.sql import func

class Fornecedor(db.Model):
    """Modelo para representar fornecedores de produtos/insumos"""
    __tablename__ = 'fornecedor'
    
    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(14), nullable=False, index=True)
    razao_social = db.Column(db.String(100), nullable=False)
    nome_fantasia = db.Column(db.String(100))
    endereco = db.Column(db.String(200))
    cidade = db.Column(db.String(50))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(8))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    inscricao_estadual = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=func.now())
    data_atualizacao = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('cnpj', 'restaurant_id', name='uq_fornecedor_cnpj_restaurant'),
    )
    
    # Relações
    produtos = db.relationship('Produto', back_populates='fornecedor', lazy='dynamic')
    notas_fiscais = db.relationship('NFNota', back_populates='fornecedor', lazy='dynamic')
    
    def __repr__(self):
        return f'<Fornecedor {self.razao_social}>'
    
    @property
    def cnpj_formatado(self):
        """Retorna o CNPJ formatado xx.xxx.xxx/xxxx-xx"""
        if not self.cnpj or len(self.cnpj) != 14:
            return self.cnpj
        return f'{self.cnpj[:2]}.{self.cnpj[2:5]}.{self.cnpj[5:8]}/{self.cnpj[8:12]}-{self.cnpj[12:]}'
    
    def get_produtos_ativos(self):
        """Retorna os produtos ativos deste fornecedor"""
        return self.produtos.filter_by(ativo=True).all()
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'cnpj': self.cnpj,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'endereco': self.endereco,
            'cidade': self.cidade,
            'estado': self.estado,
            'cep': self.cep,
            'telefone': self.telefone,
            'email': self.email,
            'inscricao_estadual': self.inscricao_estadual,
            'ativo': self.ativo,
            'cnpj_formatado': self.cnpj_formatado
        }
    
    @classmethod
    def validar_cnpj(cls, cnpj):
        """Valida o formato do CNPJ"""
        if not cnpj or len(cnpj) != 14 or not cnpj.isdigit():
            return False
        return True
