from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    """Modelo de usuário do sistema"""
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='usuario')  # admin, gerente, usuario
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False) # Enforce tenant
    restaurante = db.relationship('Restaurante', back_populates='usuarios')
    
    def __init__(self, **kwargs):
        super(Usuario, self).__init__(**kwargs)
        # Se uma senha foi fornecida, gera o hash
        if 'senha' in kwargs:
            self.set_senha(kwargs['senha'])
    
    def set_senha(self, senha):
        """Gera um hash da senha fornecida"""
        self.senha = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        """Verifica se a senha fornecida está correta"""
        return check_password_hash(self.senha, senha)
    
    def is_admin(self):
        """Verifica se o usuário é um administrador do seu tenant"""
        return self.tipo in ('admin', 'superadmin')
    
    def is_superadmin(self):
        """Verifica se o usuário é o Master Admin da plataforma global"""
        return self.tipo == 'superadmin'
    
    def to_dict(self):
        """Retorna um dicionário com os dados do usuário (sem a senha)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,
            'ativo': self.ativo,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }
    
    def __repr__(self):
        return f'<Usuario {self.email}>'
