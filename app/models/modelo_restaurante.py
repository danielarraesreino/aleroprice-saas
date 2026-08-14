from app.extensions import db
from datetime import datetime

class Restaurante(db.Model):
    """Modelo para representar o Restaurante (Tenant)"""
    __tablename__ = 'restaurante'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14), unique=True, index=True)

    # --- Roteamento do site público -----------------------------------------
    # `slug`: endereço sempre disponível (/bar/<slug>). Serve de demo e de
    #         fallback quando o cliente não tem domínio próprio.
    # `dominio`: domínio do cliente (ex.: 'bardavila.bar'). Quando o Host da
    #         requisição bate aqui, servimos o site DESTE tenant. É assim que
    #         um só app atende N bares sem subdomínio nem wildcard.
    slug = db.Column(db.String(60), unique=True, index=True)
    dominio = db.Column(db.String(120), unique=True, index=True)

    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.now)

    # --- Prospecção ---------------------------------------------------------
    # 'demo' é uma prévia comercial: montada por nós a partir de dados públicos
    # do bar, antes de qualquer contato. Não tem dono, não tem login, não é
    # indexável e mostra banner dizendo que não é o site oficial. Vira
    # 'cliente' na conversão, sem recriar nada (ver utils/demos.py).
    tipo_conta = db.Column(db.String(20), default='cliente', index=True)
    demo_expira_em = db.Column(db.Date)
    demo_visitas = db.Column(db.Integer, default=0)
    demo_primeira_visita = db.Column(db.DateTime)
    demo_fonte = db.Column(db.String(80))   # de onde veio o lead

    # Billing / Subscription
    subscription_status = db.Column(db.String(50), default='free') # free, active, past_due, canceled
    subscription_tier = db.Column(db.String(50), default='free')   # free, site, pro
    # Datas que decidem o plano efetivo. Quem interpreta é utils/planos.py —
    # não compare estas datas espalhado pelo código.
    trial_termina_em = db.Column(db.Date)
    plano_ate = db.Column(db.Date)
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    
    # A/B Testing
    pricing_strategy = db.Column(db.String(50), default='standard') # 'standard' (97/mo) vs 'volume_based' (flex)
    
    # Relações
    usuarios = db.relationship('Usuario', back_populates='restaurante')

    # --- Prévias comerciais -------------------------------------------------
    @property
    def eh_demo(self):
        return self.tipo_conta == 'demo'

    @property
    def demo_expirada(self):
        """Prévia vencida. Não tira o site do ar — a landing troca o conteúdo
        por um convite pra reativar (o lead pode voltar meses depois)."""
        from datetime import date
        return bool(self.eh_demo and self.demo_expira_em and date.today() > self.demo_expira_em)

    @classmethod
    def clientes(cls):
        """Query só de contas reais. Use em qualquer contagem comercial —
        demo não é cliente e não pode entrar em métrica de negócio.

        NULL conta como cliente: a coluna nasceu por ALTER TABLE ADD COLUMN e
        os tenants que já existiam ficaram sem valor.
        """
        return cls.query.filter(
            db.or_(cls.tipo_conta.is_(None), cls.tipo_conta != 'demo')
        )

    def __repr__(self):
        return f'<Restaurante {self.nome}>'
