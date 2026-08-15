from app.extensions import db
from datetime import datetime


class DishCard(db.Model):
    """Prato em destaque no cardápio da landing (conteúdo de marketing, por tenant)."""
    __tablename__ = 'site_dish'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(300))        # caminho em static (ex: img/bar/foto-5.jpg) ou URL
    tag = db.Column(db.String(40))            # selo, ex: "★ O MAIS PEDIDO"
    destaque = db.Column(db.Boolean, default=False)   # borda/realce
    ordem = db.Column(db.Integer, default=0, index=True)
    ativo = db.Column(db.Boolean, default=True, index=True)


class Review(db.Model):
    """Avaliação exibida na landing, por tenant."""
    __tablename__ = 'site_review'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, index=True)
    autor = db.Column(db.String(120), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    estrelas = db.Column(db.Integer, default=5)
    ordem = db.Column(db.Integer, default=0, index=True)
    ativo = db.Column(db.Boolean, default=True, index=True)


class TeamMember(db.Model):
    """Membro da equipe/família na seção história, por tenant."""
    __tablename__ = 'site_team'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, index=True)
    nome = db.Column(db.String(80), nullable=False)
    papel = db.Column(db.String(160))
    emoji = db.Column(db.String(8), default='💛')
    ordem = db.Column(db.Integer, default=0, index=True)
    ativo = db.Column(db.Boolean, default=True, index=True)


class GalleryItem(db.Model):
    """Foto da galeria, por tenant."""
    __tablename__ = 'site_gallery'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False, index=True)
    imagem = db.Column(db.String(300), nullable=False)   # caminho em static ou URL
    legenda = db.Column(db.String(160))
    ordem = db.Column(db.Integer, default=0, index=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
