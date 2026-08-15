"""Modo Campo: montar e vender o site dentro do bar, pelo celular.

O painel normal tem 14 itens de menu e foi desenhado pra notebook. Usar aquilo
em pé, na frente do dono, com ele olhando, perde a venda. Aqui é uma tela só,
na ordem em que a conversa acontece:

    foto da capa -> nome e zap -> cara do site -> pratos -> QR -> fechar

Nada aqui é feature de cliente. É ferramenta de venda do operador da campanha,
por isso o guard é `e_operador()` e não plano — e responde 404, não 403, porque
painel interno não se anuncia.
"""
import os
import secrets

from flask import (
    abort, flash, jsonify, redirect, render_template, request, url_for, Response,
)

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, GalleryItem
from app.routes.campo import bp
from app.utils import blob, demos, dominios
from app.utils.copy_site import opcoes_de_vibe, vibe_valida
from app.utils.demos import LeadInvalido, converter_demo
from app.utils.modelos import (
    MODELO_PADRAO, MODELOS, modelo_valido, opcoes_de_modelo,
)
from app.utils.operador import e_operador
from app.utils.planos import DIAS_DE_TRIAL, precos
from app.utils.temas import opcoes_de_tema, tema_valido

# Campos que o Modo Campo edita. Curto de propósito: o resto continua no
# /config-site, que é onde se mexe sentado.
BASICOS = ('nome', 'whatsapp', 'descritor', 'endereco')


def _bar(slug):
    if not e_operador():
        abort(404)
    rest = Restaurante.query.filter_by(slug=slug).first()
    if rest is None:
        abort(404)
    return rest


def _config(rest):
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first()
    if cfg is None:
        cfg = SiteConfig(restaurant_id=rest.id, nome=rest.nome)
        db.session.add(cfg)
        db.session.commit()
    return cfg


@bp.route('/')
def index():
    """Home de quem está em campo: achar o bar em dois toques.

    É para cá que o operador cai ao entrar (ver `auth._destino_depois_do_login`),
    porque a pergunta dele ao abrir o celular no bar é sempre a mesma: qual bar
    é este e o que já está pronto nele. Bar com foto aparece marcado, e os que
    ainda não têm sobem para o topo — é o trabalho que falta.
    """
    if not e_operador():
        abort(404)

    bares = Restaurante.query.order_by(Restaurante.nome).all()
    configs = {c.restaurant_id: c for c in SiteConfig.query.all()}

    linhas = []
    for b in bares:
        if not b.slug:
            continue
        cfg = configs.get(b.id)
        linhas.append({
            'slug': b.slug,
            'nome': b.nome,
            'tipo': b.tipo_conta or 'cliente',
            'tem_foto': bool(cfg and cfg.hero_foto),
            'nota': cfg.nota_google if cfg else None,
            # Pronto para mostrar = tem foto e tem nota. É o que faz a prévia
            # parecer o bar dele em vez de um modelo com o nome trocado.
            'pronto': bool(cfg and cfg.hero_foto and cfg.nota_google),
        })

    resumo = {
        'total': len(linhas),
        'prontos': sum(1 for l in linhas if l['pronto']),
        'clientes': sum(1 for l in linhas if l['tipo'] != 'demo'),
    }
    return render_template('campo/lista.html', linhas=linhas, resumo=resumo)


@bp.route('/<slug>')
def editar(slug):
    rest = _bar(slug)
    cfg = _config(rest)
    pratos = (DishCard.query.filter_by(restaurant_id=rest.id)
              .order_by(DishCard.ordem).all())
    galeria = (GalleryItem.query.filter_by(restaurant_id=rest.id)
               .order_by(GalleryItem.ordem).all())
    return render_template(
        'campo/editar.html', rest=rest, cfg=cfg, pratos=pratos, galeria=galeria,
        temas=opcoes_de_tema(), vibes=opcoes_de_vibe(),
        # Sugestão pronta: em campo ninguém inventa senha boa de cabeça.
        senha_sugerida=secrets.token_urlsafe(9),
    )


@bp.post('/<slug>/basico')
def basico(slug):
    rest = _bar(slug)
    cfg = _config(rest)
    for campo in BASICOS:
        if campo in request.form:
            setattr(cfg, campo, (request.form.get(campo) or '').strip() or None)
    if cfg.nome:
        rest.nome = cfg.nome
    db.session.commit()
    flash('Salvo.', 'success')
    return redirect(url_for('campo.editar', slug=slug))


@bp.post('/<slug>/estilo')
def estilo(slug):
    rest = _bar(slug)
    cfg = _config(rest)
    tema = request.form.get('tema')
    vibe = request.form.get('vibe')
    if tema and tema_valido(tema):
        cfg.tema = tema
    if vibe and vibe_valida(vibe):
        cfg.vibe = vibe
    db.session.commit()
    return redirect(url_for('campo.editar', slug=slug))


@bp.route('/<slug>/visual', methods=('GET', 'POST'))
def visual(slug):
    """Trocar o esqueleto do site na frente do dono, vendo mudar.

    Tema e vibe cabem em radio button porque a diferença é uma cor e uma
    palavra. Modelo não: é a página inteira mudando de ordem. Descrever isso
    ("hero grande, cardápio depois") não vende — mostrar vende. Por isso a tela
    é uma moldura de celular com a prévia dentro, e tocar num cartão só troca o
    `src` do iframe: o site salvo continua o que era enquanto os dois olham as
    opções.

    O POST é o único momento em que grava. Modelo desconhecido não escreve nada
    — mesma regra fechada de `estilo()`: preset conhecido ou nada.
    """
    rest = _bar(slug)
    cfg = _config(rest)

    if request.method == 'POST':
        escolhido = (request.form.get('modelo') or '').strip()
        if not modelo_valido(escolhido):
            flash('Esse modelo eu não conheço — não mudei nada.', 'danger')
            return redirect(url_for('campo.visual', slug=slug))
        cfg.modelo = escolhido
        # Claro/escuro vem junto: quem escolheu o layout olhando no claro quer
        # salvar o claro, não voltar pro automático.
        modo = (request.form.get('modo') or '').strip()
        if modo in ('auto', 'claro', 'escuro'):
            cfg.tema_modo = modo
        db.session.commit()
        flash(f'Pronto: o site do {cfg.nome or rest.nome} agora é o '
              f'{MODELOS[escolhido]["label"]}.', 'success')
        return redirect(url_for('campo.visual', slug=slug))

    return render_template(
        'campo/visual.html', rest=rest, cfg=cfg,
        modelos=opcoes_de_modelo(),
        # O que está salvo hoje — é o cartão que abre marcado e o que leva o
        # selo "no ar". Valor órfão (modelo removido) cai no clássico, que é o
        # que o visitante do site está vendo de fato.
        modelo_atual=(cfg.modelo if modelo_valido(cfg.modelo) else MODELO_PADRAO),
        modo_atual=(cfg.tema_modo if cfg.tema_modo in ('auto', 'claro', 'escuro')
                    else 'auto'),
        url_previa=url_for('public.landing_slug', slug=rest.slug, _external=True),
    )


@bp.post('/<slug>/foto')
def foto(slug):
    """Recebe uma imagem já reduzida pelo navegador e a coloca no site.

    Responde JSON porque o formulário sobe por fetch: recarregar a página
    inteira depois de cada foto, no 4G do bar, é lento demais pra fazer na
    frente de alguém.
    """
    rest = _bar(slug)
    cfg = _config(rest)
    alvo = request.form.get('alvo', 'capa')

    try:
        url = blob.enviar(request.files.get('imagem'), rest.slug)
    except blob.UploadInvalido as e:
        return jsonify({'erro': str(e)}), 400
    except blob.UploadIndisponivel as e:
        return jsonify({'erro': str(e)}), 503

    if alvo == 'capa':
        cfg.hero_foto = url
    elif alvo == 'prato':
        nome = (request.form.get('nome') or '').strip() or 'Prato da casa'
        ordem = db.session.query(db.func.count(DishCard.id)).filter_by(
            restaurant_id=rest.id).scalar() or 0
        db.session.add(DishCard(restaurant_id=rest.id, nome=nome, imagem=url,
                                ordem=ordem, ativo=True))
    else:
        ordem = db.session.query(db.func.count(GalleryItem.id)).filter_by(
            restaurant_id=rest.id).scalar() or 0
        db.session.add(GalleryItem(restaurant_id=rest.id, imagem=url,
                                   ordem=ordem, ativo=True))
    db.session.commit()
    return jsonify({'ok': True, 'url': url, 'alvo': alvo})


@bp.post('/<slug>/remover/<tipo>/<int:item_id>')
def remover(slug, tipo, item_id):
    rest = _bar(slug)
    Model = {'prato': DishCard, 'galeria': GalleryItem}.get(tipo)
    if Model is None:
        abort(404)
    # filtro por restaurant_id junto: id sozinho apagaria item de outro bar
    item = Model.query.filter_by(id=item_id, restaurant_id=rest.id).first()
    if item is not None:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('campo.editar', slug=slug))


@bp.post('/<slug>/converter')
def converter(slug):
    """O momento da venda: a prévia vira conta do dono, ali na mesa."""
    rest = _bar(slug)
    email = (request.form.get('email') or '').strip()
    senha = (request.form.get('senha') or '').strip()

    if '@' not in email or len(senha) < 6:
        flash('Preciso de um e-mail válido e senha de 6+ caracteres.', 'danger')
        return redirect(url_for('campo.editar', slug=slug))

    try:
        converter_demo(rest, email, senha,
                       nome_admin=(request.form.get('responsavel') or '').strip()
                       or 'Responsável')
        db.session.commit()
    except LeadInvalido as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('campo.editar', slug=slug))

    flash(f'Pronto. Conta de {rest.nome} criada: {email} / {senha} — '
          f'anote antes de sair desta tela.', 'success')
    return redirect(url_for('campo.editar', slug=slug))


def _dados_da_proposta(rest, cfg):
    """Compõe os dados do local: o que o painel já tem vence; o que falta vem
    do YAML do lead. A proposta nunca abre com campo em branco se a informação
    existe em algum dos dois lugares."""
    lead, lead_site = {}, {}
    caminho = os.path.join(demos.DIR_LEADS, f'{rest.slug}.yml')
    if os.path.isfile(caminho):
        try:
            lead = demos.carregar_lead(caminho)
        except LeadInvalido:
            lead = {}
        lead_site = lead.get('site') or {}

    def compor(campo):
        return getattr(cfg, campo, None) or lead_site.get(campo) or None

    return {
        'nome': cfg.nome or rest.nome or lead.get('nome'),
        'descritor': compor('descritor'),
        'endereco': compor('endereco'),
        'cidade_uf': compor('cidade_uf'),
        'horario': compor('horario'),
        'instagram': compor('instagram_url'),
        'whatsapp': compor('whatsapp'),
        'nota_google': compor('nota_google'),
        'qtd_avaliacoes': compor('qtd_avaliacoes'),
        'maps_query': compor('maps_query'),
    }


@bp.route('/<slug>/proposta')
def proposta(slug):
    """Proposta pronta, composta com os dados do local: o vendedor abre, mostra
    e manda no WhatsApp do dono — pronto pra o cara assumir o site."""
    rest = _bar(slug)
    cfg = _config(rest)
    dados = _dados_da_proposta(rest, cfg)

    # Consulta na hora, mas curta: a proposta carrega com o dono do bar olhando.
    # RDAP fora do ar não pode derrubar a página — sem resposta, o bloco vira
    # "conferimos na hora", nunca "está livre".
    try:
        consulta = dominios.consultar(dados['nome'], cidade=dados.get('cidade_uf'), limite=2)
    except Exception:
        consulta = []

    return render_template(
        'campo/proposta.html', rest=rest, cfg=cfg, dados=dados,
        precos=precos(),
        dominios_consulta=consulta,
        dominio_livre=dominios.primeiro_livre(consulta),
        taxa_setup=dominios.taxa_de_instalacao(),
        url_previa=url_for('public.landing_slug', slug=rest.slug, _external=True),
        e_demo=(rest.tipo_conta or 'cliente') == 'demo',
        expira_em=rest.demo_expira_em,
        dias_validade=demos.DIAS_VALIDADE_PADRAO,
        dias_trial=DIAS_DE_TRIAL,
    )


@bp.route('/<slug>/dominio')
def dominio(slug):
    """Consulta de domínio sob demanda, pra usar na mesa.

    JSON porque o card do Modo Campo consulta por fetch: o vendedor aperta,
    espera 2s e lê o resultado sem sair da tela que está mostrando ao dono.
    """
    rest = _bar(slug)
    cfg = _config(rest)
    nome = cfg.nome or rest.nome
    try:
        consulta = dominios.consultar(nome, cidade=cfg.cidade_uf)
    except Exception:
        return jsonify({'erro': 'não consegui consultar agora'}), 503
    return jsonify({'consulta': consulta, 'livre': dominios.primeiro_livre(consulta)})


@bp.route('/<slug>/qr.svg')
def qr(slug):
    """QR do site pro dono apontar o celular dele e ver na hora.

    Ver o próprio bar aparecer na tela do próprio telefone é o que fecha a
    conversa — mais do que qualquer explicação de recurso.
    """
    import segno

    rest = _bar(slug)
    destino = url_for('public.landing_slug', slug=rest.slug, _external=True)
    svg = segno.make(destino, error='m').svg_inline(scale=6, border=2)
    return Response(svg, mimetype='image/svg+xml')
