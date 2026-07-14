import os
import urllib.parse
import urllib.request
from datetime import datetime, date

from flask import Blueprint, render_template, request, jsonify, current_app

from app.extensions import db
from app.models.modelo_reserva import Reserva
from app.models.modelo_restaurante import Restaurante

from . import bp

# WhatsApp do bar (Gustavo) — recebe o alerta de nova reserva.
BAR_WHATSAPP = '5519999779942'


def _alerta_whatsapp(texto):
    """Dispara alerta no WhatsApp do bar via CallMeBot (grátis).

    Só age se CALLMEBOT_APIKEY estiver configurado (env). Falha é silenciosa:
    nunca quebra a reserva — o botão wa.me segue como fallback pro cliente.
    """
    apikey = os.environ.get('CALLMEBOT_APIKEY')
    if not apikey:
        return
    phone = os.environ.get('CALLMEBOT_PHONE', BAR_WHATSAPP)
    params = urllib.parse.urlencode({'phone': phone, 'text': texto, 'apikey': apikey})
    url = 'https://api.callmebot.com/whatsapp.php?' + params
    try:
        urllib.request.urlopen(url, timeout=6)
        current_app.logger.info('CallMeBot: alerta de reserva enviado.')
    except Exception as e:  # noqa: BLE001 — alerta é best-effort
        current_app.logger.warning(f'CallMeBot falhou: {e}')


def _render_landing(rest):
    """Renderiza a landing pra um restaurante (tenant) qualquer."""
    from app.models.modelo_evento import Evento
    from app.models.modelo_promocao import Promocao

    hoje = date.today()
    rid = rest.id if rest else None

    eventos_q = Evento.query.filter(Evento.ativo.is_(True), Evento.data >= hoje)
    promos_q = Promocao.query.filter(Promocao.ativo.is_(True))
    if rid is not None:
        eventos_q = eventos_q.filter(Evento.restaurant_id == rid)
        promos_q = promos_q.filter(Promocao.restaurant_id == rid)

    eventos = eventos_q.order_by(Evento.data.asc()).limit(6).all()
    promocoes = [p for p in promos_q.order_by(Promocao.data_cadastro.desc()).all() if p.vigente][:4]

    return render_template('site/landing.html', eventos=eventos, promocoes=promocoes,
                           site=montar_site(rest), **montar_conteudo(rest))


@bp.route('/')
def landing():
    """Landing pública do tenant principal (primeiro restaurante)."""
    rest = Restaurante.query.order_by(Restaurante.id).first()
    return _render_landing(rest)


@bp.route('/s/<int:rid>')
def landing_tenant(rid):
    """Landing pública de um tenant específico (preview por id, até ter subdomínio)."""
    rest = Restaurante.query.get_or_404(rid)
    return _render_landing(rest)


@bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Self-serve: cria o restaurante (tenant) + admin e já loga. Sem CLI."""
    from flask_login import login_user, current_user
    from app.models.usuario import Usuario
    from app.models.modelo_siteconfig import SiteConfig

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    dados = {'nome_bar': '', 'nome': '', 'email': ''}
    if request.method == 'POST':
        nome_bar = (request.form.get('nome_bar') or '').strip()
        nome = (request.form.get('nome') or '').strip() or 'Responsável'
        email = (request.form.get('email') or '').strip().lower()
        senha = request.form.get('senha') or ''
        dados = {'nome_bar': nome_bar, 'nome': nome, 'email': email}

        erros = []
        if len(nome_bar) < 2:
            erros.append('Informe o nome do bar/restaurante.')
        if '@' not in email or '.' not in email:
            erros.append('E-mail inválido.')
        if len(senha) < 6:
            erros.append('A senha precisa de ao menos 6 caracteres.')
        if email and Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
            erros.append('Já existe uma conta com esse e-mail. Faça login.')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('site/cadastro.html', **dados)

        rest = Restaurante(nome=nome_bar)
        db.session.add(rest)
        db.session.commit()
        db.session.add(SiteConfig(restaurant_id=rest.id, nome=nome_bar))
        admin = Usuario(nome=nome, email=email, senha=senha, tipo='admin', restaurant_id=rest.id)
        db.session.add(admin)
        db.session.commit()

        login_user(admin)
        current_app.logger.info(f"Context: SIGNUP | {nome_bar} | {email} | rid={rest.id}")
        flash('Conta criada! Personalize em Site e Conteúdo, depois veja seu site.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('site/cadastro.html', **dados)


# Identidade/contato padrão (Bar da Vila) — fallback quando o tenant não configurou.
SITE_DEFAULTS = {
    'nome': 'Bar da Vila',
    'hero_linha1': 'Bar da',
    'hero_linha2': 'Vila',
    'kicker': 'VILA LEMOS · CAMPINAS–SP · DESDE SEMPRE',
    'tagline': 'Buteco de família de verdade — comida de vó, cerveja gelada e samba pra ninguém botar defeito.',
    'subline': 'COSTELINHA · CROQUETE DA BRUNA · SAMBA AO VIVO',
    'selo_estrelas': '4,9 no Google · 39 avaliações',
    'hero_foto': 'img/bar/foto-18.jpg',
    'whatsapp': '5519999779942',
    'telefone_exibicao': '(19) 99977-9942',
    'endereco': 'R. Madalena Barbosa Ferreira, 178 — Vila Lemos, Campinas–SP · 13100-486',
    'cidade_uf': 'Vila Lemos, Campinas–SP',
    'horario': 'Aberto até as 21:00 · Quarta é o dia de pico',
    'maps_query': 'Bar+da+Vila+R.+Madalena+Barbosa+Ferreira+178+Vila+Lemos+Campinas',
    'instagram_url': 'https://www.instagram.com/barda_vila178/',
    'facebook_url': 'https://www.facebook.com/p/Bar-da-VILA-61561126014944/',
}


def montar_site(rest):
    """Dict de identidade/contato do site: valor do SiteConfig do tenant ou o padrão."""
    from app.models.modelo_siteconfig import SiteConfig
    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first() if rest else None
    site = {}
    for chave, padrao in SITE_DEFAULTS.items():
        valor = getattr(cfg, chave, None) if cfg else None
        site[chave] = valor if (valor is not None and str(valor).strip() != '') else padrao
    return site


# --- Conteúdo padrão (Bar da Vila) pras seções de lista, usado como fallback ---
DISH_DEFAULTS = [
    {'nome': 'Croquete da Bruna', 'descricao': 'Crocante por fora, macio por dentro, bem temperado — com aquela pimenta saborosa da casa. O xodó do bar.', 'imagem': 'img/bar/foto-5.jpg', 'tag': '★ O MAIS PEDIDO', 'destaque': True},
    {'nome': 'Costelinha', 'descricao': 'Costelinha com farofa e ora-pro-nóbis refogadinha. Prato que faz gente voltar sempre.', 'imagem': 'img/bar/foto-3.jpg', 'tag': None, 'destaque': False},
    {'nome': 'Porções pra dividir', 'descricao': 'Frango a passarinho, batata na hora e cerveja estupidamente gelada. O combo do fim de tarde.', 'imagem': 'img/bar/foto-20.jpg', 'tag': None, 'destaque': False},
    {'nome': 'Prato do dia', 'descricao': 'Comida caseira no capricho — arroz, feijão, o acompanhamento e aquele tempero de vó.', 'imagem': 'img/bar/foto-17.jpg', 'tag': None, 'destaque': False},
]
REVIEW_DEFAULTS = [
    {'autor': 'Gerzio Vieira Junior', 'texto': 'Buteco de família, extremamente acolhedor. A costelinha com farofa e ora-pro-nóbis estava maravilhosa.', 'estrelas': 5},
    {'autor': 'Rony Nunes', 'texto': 'Autêntico bar raiz. Bruna e Gustavo são excelentes anfitriões. Comida de buteco típica de vó.', 'estrelas': 5},
    {'autor': 'Aline Fernandes', 'texto': 'Croquete delicioso, crocante e bem temperado, pimenta muito saborosa! A carbonara é maravilhosa.', 'estrelas': 5},
    {'autor': 'Antonio Ribeiro', 'texto': 'O grupo de samba que se apresenta torna o ambiente muito agradável. Cerveja, boa música e amigos.', 'estrelas': 5},
    {'autor': 'Jairo Castro', 'texto': 'A melhor comida de boteco de Campinas e Região.', 'estrelas': 5},
    {'autor': 'Tia Andreia', 'texto': 'Lugar familiar, comida e música boa. A Bruna é uma cozinheira de mão cheia, família abençoada!', 'estrelas': 5},
]
TEAM_DEFAULTS = [
    {'nome': 'Bruna', 'papel': 'Cozinheira e anfitriã · o tempero de vó', 'emoji': '👩‍🍳'},
    {'nome': 'Gustavo', 'papel': 'Anfitrião · o samba e a resenha', 'emoji': '🍺'},
]
GALLERY_DEFAULTS = [{'imagem': 'img/bar/foto-%d.jpg' % n, 'legenda': None}
                    for n in [18, 3, 5, 7, 12, 20, 6, 8, 17, 14, 1, 4, 9, 16, 19]]


def _img(path):
    from flask import url_for
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return url_for('static', filename=path)


def montar_conteudo(rest):
    """Listas das seções (cardápio, avaliações, equipe, galeria): do tenant ou padrão."""
    from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem
    rid = rest.id if rest else None

    def rows(model):
        if not rid:
            return []
        return model.query.filter_by(restaurant_id=rid, ativo=True).order_by(model.ordem, model.id).all()

    dcards = rows(DishCard)
    dishes = ([{'nome': d.nome, 'descricao': d.descricao, 'img': _img(d.imagem), 'tag': d.tag, 'destaque': d.destaque} for d in dcards]
              if dcards else [{**d, 'img': _img(d['imagem'])} for d in DISH_DEFAULTS])

    rrows = rows(Review)
    reviews = ([{'autor': r.autor, 'texto': r.texto, 'estrelas': r.estrelas} for r in rrows]
               if rrows else REVIEW_DEFAULTS)

    trows = rows(TeamMember)
    team = ([{'nome': t.nome, 'papel': t.papel, 'emoji': t.emoji} for t in trows]
            if trows else TEAM_DEFAULTS)

    grows = rows(GalleryItem)
    gallery = ([{'img': _img(g.imagem), 'legenda': g.legenda} for g in grows]
               if grows else [{'img': _img(g['imagem']), 'legenda': None} for g in GALLERY_DEFAULTS])

    return {'dishes': dishes, 'reviews': reviews, 'team': team, 'gallery': gallery}


@bp.route('/reservar', methods=['POST'])
def reservar():
    """Recebe uma reserva de mesa do formulário público da landing.

    Sem login (endpoint public.*). Grava no banco; o lojista vê/confirma no
    painel /reservas. Resolve o tenant pelo primeiro restaurante cadastrado
    (deploy single-tenant do Bar da Vila).
    """
    dados = request.form if request.form else (request.get_json(silent=True) or {})

    nome = (dados.get('nome') or '').strip()
    telefone = (dados.get('telefone') or '').strip()
    data_str = (dados.get('data') or '').strip()
    hora = (dados.get('hora') or '').strip()
    pessoas_str = str(dados.get('num_pessoas') or '').strip()
    observacao = (dados.get('observacao') or '').strip() or None

    erros = []
    if len(nome) < 2:
        erros.append('Informe seu nome.')
    if len(telefone) < 8:
        erros.append('Informe um telefone/WhatsApp válido.')

    data_reserva = None
    try:
        data_reserva = datetime.strptime(data_str, '%Y-%m-%d').date()
        if data_reserva < date.today():
            erros.append('A data da reserva não pode ser no passado.')
    except ValueError:
        erros.append('Escolha uma data válida.')

    try:
        datetime.strptime(hora, '%H:%M')
    except ValueError:
        erros.append('Escolha um horário válido.')

    num_pessoas = None
    try:
        num_pessoas = int(pessoas_str)
        if num_pessoas < 1 or num_pessoas > 50:
            raise ValueError
    except ValueError:
        erros.append('Número de pessoas inválido.')

    if erros:
        return jsonify({'ok': False, 'erros': erros}), 400

    restaurante = Restaurante.query.order_by(Restaurante.id).first()

    reserva = Reserva(
        nome=nome,
        telefone=telefone,
        data=data_reserva,
        hora=hora,
        num_pessoas=num_pessoas,
        observacao=observacao,
        status='pendente',
        origem='site',
        restaurant_id=restaurante.id if restaurante else None,
    )
    db.session.add(reserva)
    db.session.commit()

    current_app.logger.info(
        f"Context: RESERVA_SITE | {nome} | {telefone} | {data_reserva} {hora} | {num_pessoas}p"
    )

    # Alerta pro WhatsApp do bar: link pré-preenchido com os dados da reserva.
    linhas = [
        '🍺 *Nova reserva pelo site do Bar da Vila!*',
        '',
        f'👤 {nome}',
        f'📞 {telefone}',
        f'📅 {data_reserva.strftime("%d/%m/%Y")} às {hora}',
        f'👥 {num_pessoas} pessoa(s)',
    ]
    if observacao:
        linhas.append(f'📝 {observacao}')
    texto = '\n'.join(linhas)
    wa_url = 'https://wa.me/' + BAR_WHATSAPP + '?text=' + urllib.parse.quote(texto)

    # Alerta automático pro WhatsApp do bar (grátis, via CallMeBot). Best-effort.
    _alerta_whatsapp(texto)

    return jsonify({
        'ok': True,
        'mensagem': f'Reserva recebida, {nome.split()[0]}! Toque abaixo pra avisar o bar no WhatsApp. 🍺',
        'wa_url': wa_url,
    })


@bp.route('/calculadora-roi', methods=['GET', 'POST'])
def calculadora_roi():
    """Calculadora de ROI pública (Lead Magnet)"""
    resultado = None
    faturamento = None
    
    if request.method == 'POST':
        try:
            faturamento_str = request.form.get('faturamento_estimado', '0')
            # Limpar formatação de moeda se houver (R$, pontos, virgulas)
            faturamento_str = faturamento_str.replace('R$', '').replace('.', '').replace(',', '.')
            faturamento = float(faturamento_str)
            
            # Retention / Lead Capture
            email = request.form.get('email')
            if email:
                # Log for backend processing (Concierge / Marketing)
                # In production, this goes to Vercel Logs -> Datadog/Splunk or manually extracted
                from flask import current_app
                current_app.logger.info(f"Context: LEAD_CALCULADORA_ROI | Email: {email} | Faturamento: {faturamento}")
            
            # Estimativa de desperdício (10% - Dado de mercado Abrasel)
            desperdicio = faturamento * 0.10
            
            resultado = {
                'faturamento': faturamento,
                'desperdicio': desperdicio,
                'mensagem': f"Você pode estar perdendo R$ {desperdicio:,.2f} por mês em desperdício invisível."
            }
        except ValueError:
            resultado = {'erro': 'Por favor, insira um valor válido.'}
            
    return render_template('public/roi.html', resultado=resultado, faturamento=faturamento)
