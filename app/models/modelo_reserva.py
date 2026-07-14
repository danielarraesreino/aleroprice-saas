from app.extensions import db
from datetime import datetime


class Reserva(db.Model):
    """Reserva de mesa feita pelo site público do restaurante.

    Origem tipicamente 'site' (formulário da landing). O lojista visualiza,
    confirma ou cancela pelo painel. Multi-tenant via restaurant_id — nulo é
    tolerado para não perder reservas caso o tenant ainda não esteja resolvido.
    """
    __tablename__ = 'reserva'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(30), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    hora = db.Column(db.String(5), nullable=False)          # "HH:MM"
    num_pessoas = db.Column(db.Integer, nullable=False, default=2)
    observacao = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='pendente', index=True)  # pendente, confirmada, cancelada
    origem = db.Column(db.String(20), default='site')
    data_cadastro = db.Column(db.DateTime, default=datetime.now, index=True)

    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=True, index=True)

    STATUS_VALIDOS = ('pendente', 'confirmada', 'cancelada')
    STATUS_BADGE = {'pendente': 'warning', 'confirmada': 'success', 'cancelada': 'secondary'}
    STATUS_LABEL = {'pendente': 'Pendente', 'confirmada': 'Confirmada', 'cancelada': 'Cancelada'}

    @property
    def badge(self):
        return self.STATUS_BADGE.get(self.status, 'light')

    @property
    def status_label(self):
        return self.STATUS_LABEL.get(self.status, self.status)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'telefone': self.telefone,
            'data': self.data.isoformat() if self.data else None,
            'hora': self.hora,
            'num_pessoas': self.num_pessoas,
            'observacao': self.observacao,
            'status': self.status,
            'origem': self.origem,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
        }

    def __repr__(self):
        return f'<Reserva {self.nome} {self.data} {self.hora} [{self.status}]>'
