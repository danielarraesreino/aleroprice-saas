from app.extensions import db
from datetime import datetime


class Evento(db.Model):
    """Evento da agenda do bar (samba, show, roda etc). Gerenciado pelo lojista,
    exibido na landing pública. Multi-tenant via restaurant_id."""
    __tablename__ = 'evento'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    data = db.Column(db.Date, nullable=False, index=True)
    hora = db.Column(db.String(5))                 # "HH:MM" (opcional)
    ativo = db.Column(db.Boolean, default=True, index=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=True, index=True)

    def __repr__(self):
        return f'<Evento {self.titulo} {self.data}>'
