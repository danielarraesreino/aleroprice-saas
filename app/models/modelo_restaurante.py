from app.extensions import db
from datetime import datetime

class Restaurante(db.Model):
    """Modelo para representar o Restaurante (Tenant)"""
    __tablename__ = 'restaurante'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, index=True)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    # Billing / Subscription
    subscription_status = db.Column(db.String(50), default='free') # free, active, past_due, canceled
    subscription_tier = db.Column(db.String(50), default='free')   # free, pro
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    
    # Relações
    usuarios = db.relationship('Usuario', back_populates='restaurante')
    
    def __repr__(self):
        return f'<Restaurante {self.nome}>'
