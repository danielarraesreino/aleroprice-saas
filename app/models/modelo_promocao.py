from app.extensions import db
from datetime import datetime, date


DIAS_SEMANA = [
    (0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'),
    (4, 'Sexta'), (5, 'Sábado'), (6, 'Domingo'),
]
DIAS_SEMANA_MAP = dict(DIAS_SEMANA)


class Promocao(db.Model):
    """Promoção do bar. Gerenciada pelo lojista no CMS, exibida na landing.

    Dois tipos, definidos por `dia_semana`:

    - Recorrente semanal (`dia_semana` preenchido): o "Lanche de Quarta". Fica
      no site toda semana anunciando o dia, e ganha destaque quando é hoje.
    - Pontual (`dia_semana` nulo): vale no intervalo [data_inicio, validade].

    A janela [data_inicio, validade] vale para os dois: dá pra agendar uma
    promoção pra começar mês que vem, ou encerrar a de quarta em dezembro.
    Cada ponta é opcional (nulo = sem limite daquele lado).
    """
    __tablename__ = 'promocao'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Janela de exibição. `validade` é o fim — nome mantido porque a coluna já
    # existe em produção.
    data_inicio = db.Column(db.Date, nullable=True)   # nulo = já vale
    validade = db.Column(db.Date, nullable=True)      # nulo = sem prazo

    # Recorrência semanal. Nulo = promoção pontual.
    dia_semana = db.Column(db.Integer, nullable=True)  # 0=Segunda ... 6=Domingo

    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=True, index=True)

    @property
    def vigente(self):
        """Deve aparecer no site hoje?

        A promoção recorrente de quarta aparece TODOS os dias — é anúncio: o
        cliente precisa saber na segunda que quarta tem lanche. O destaque de
        "é hoje" fica por conta de `acontece_hoje`.
        """
        if not self.ativo:
            return False
        hoje = date.today()
        if self.data_inicio and hoje < self.data_inicio:
            return False
        if self.validade and hoje > self.validade:
            return False
        return True

    @property
    def acontece_hoje(self):
        """Recorrente cujo dia é hoje — a landing dá destaque."""
        if self.dia_semana is None:
            return False
        return self.vigente and date.today().weekday() == self.dia_semana

    @property
    def rotulo(self):
        """Etiqueta pro site: 'TODA QUARTA' ou 'ATÉ 31/12'."""
        if self.dia_semana is not None:
            return f'TODA {DIAS_SEMANA_MAP[self.dia_semana].upper()}'
        if self.validade:
            return f'ATÉ {self.validade.strftime("%d/%m")}'
        return None

    @property
    def agendada(self):
        """Ainda não começou: o lojista vê no CMS, o cliente não vê no site."""
        return bool(self.data_inicio and date.today() < self.data_inicio)

    def __repr__(self):
        return f'<Promocao {self.titulo}>'
