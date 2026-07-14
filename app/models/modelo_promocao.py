from app.extensions import db
from datetime import datetime, date


class Promocao(db.Model):
    """Promoção do bar. Gerenciada pelo lojista, exibida na landing enquanto
    estiver ativa e dentro da validade. Multi-tenant via restaurant_id."""
    __tablename__ = 'promocao'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, index=True)
    validade = db.Column(db.Date, nullable=True)   # nulo = sem prazo
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=True, index=True)

    @property
    def vigente(self):
        return self.ativo and (self.validade is None or self.validade >= date.today())

    def __repr__(self):
        return f'<Promocao {self.titulo}>'
