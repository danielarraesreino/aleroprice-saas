from app.extensions import db


class MetricaDiaria(db.Model):
    """Quanto o site de um cliente trabalhou num dia: visitas e cliques.

    Sem isto o cliente não vê resultado e cancela no primeiro mês fraco. Um
    contador por (cliente, dia, tipo) em vez de uma linha por evento: o banco
    não cresce com o tráfego e o relatório do mês é uma soma.
    Tipos em `app.utils.metricas.TIPOS`.
    """
    __tablename__ = 'site_metrica'
    __table_args__ = (db.UniqueConstraint('restaurant_id', 'dia', 'tipo', name='uq_site_metrica'),)

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, index=True)
    dia = db.Column(db.Date, nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Integer, nullable=False, default=0)
