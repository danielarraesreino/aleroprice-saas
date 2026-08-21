from app.extensions import db
from datetime import datetime


class SiteConfig(db.Model):
    """Configuração de identidade/contato do site público, por restaurante (tenant).

    Um registro por restaurante. Campos nulos caem no fallback do Bar da Vila
    na view — então o site atual não muda até alguém editar. É a base pra
    revender a landing pra outros bares sem mexer no código.
    """
    __tablename__ = 'site_config'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, unique=True, index=True)

    # Identidade
    nome = db.Column(db.String(80))              # marca exibida (nav/footer)
    hero_linha1 = db.Column(db.String(40))       # neon linha 1 (ex.: "Bar da")
    hero_linha2 = db.Column(db.String(40))       # neon linha 2 (ex.: "Vila")
    kicker = db.Column(db.String(120))           # "VILA LEMOS · CAMPINAS–SP · DESDE SEMPRE"
    tagline = db.Column(db.String(300))
    subline = db.Column(db.String(200))
    selo_estrelas = db.Column(db.String(120))    # "4,9 no Google · 39 avaliações"
    # Caminho em static ("img/bar/foto-18.jpg") ou URL absoluta. 300 porque URL
    # de Vercel Blob passa fácil de 120 — mesmo tamanho de DishCard.imagem.
    hero_foto = db.Column(db.String(300))

    # Contato
    whatsapp = db.Column(db.String(20))          # só dígitos c/ DDI, ex.: 5519999779942
    telefone_exibicao = db.Column(db.String(30))
    endereco = db.Column(db.String(200))
    cidade_uf = db.Column(db.String(80))
    horario = db.Column(db.String(120))
    maps_query = db.Column(db.String(200))

    # Subtítulo da marca: vai no <title> e no card de compartilhamento.
    # Ex.: "Hamburgueria artesanal em Vinhedo". Nulo cai em cidade_uf.
    descritor = db.Column(db.String(80))

    # Redes
    instagram_url = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))

    # Aparência: nome de um preset em app/utils/temas.py (não é CSS livre —
    # cliente escolhe entre paletas fechadas para não conseguir feiar o site).
    tema = db.Column(db.String(30), default='boteco-ambar')

    # Tom do texto: preset em app/utils/copy_site.py. Define títulos de seção,
    # faixa rolante e mensagem do WhatsApp. Um campo em vez de vinte.
    vibe = db.Column(db.String(30), default='boteco')

    # Layout do site: nome de um modelo em app/utils/modelos.py. Não é cor nem
    # texto (isso é `tema`/`vibe`) — é a ESTRUTURA da página: quais seções
    # existem, em que ordem e com que cara. 'classico' é a landing atual, então
    # todo mundo que já está no ar continua igual.
    modelo = db.Column(db.String(30), default='classico')

    # Claro ou escuro: 'auto' segue o aparelho de quem visita (comportamento
    # histórico), 'claro'/'escuro' fixam. Existe porque a casa tem uma escolha
    # — e porque o vendedor precisa mostrar as duas na hora.
    tema_modo = db.Column(db.String(10), default='auto')

    # O bar escolhe exibir no rodapé que apoia o Caminhos Campinas, projeto de
    # dados abertos e formação com a população em situação de rua.
    #
    # Opt-in, e desligado por padrão, por dois motivos. O primeiro é do dono: o
    # rodapé do site é dele, e causa é escolha, não brinde que vem embutido no
    # plano. O segundo é da causa: selo que aparece sem ninguém pedir vira
    # decoração, e decoração não sustenta projeto nenhum.
    apoia_caminhos = db.Column(db.Boolean, default=False)

    # Prova social. Vazios = o bloco de nota some (melhor do que exibir a nota
    # de outro bar, que era o que acontecia com o 4,9/39 fixo no template).
    nota_google = db.Column(db.String(10))
    qtd_avaliacoes = db.Column(db.Integer)
    # Notificações WhatsApp via CallMeBot (grátis)
    callmebot_phone = db.Column(db.String(20))
    callmebot_apikey = db.Column(db.String(50))

    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    restaurante = db.relationship('Restaurante', backref=db.backref('site_config', uselist=False))
