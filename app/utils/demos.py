"""Prévias comerciais: transformar um lead num site publicado, e um site
publicado num cliente.

Como funciona
-------------
Cada lead é um arquivo `app/data/leads/<slug>.yml` versionado junto com as
fotos em `app/static/img/demo/<slug>/`. Os dois andam juntos por um motivo
prático: o filesystem da Vercel é read-only e não existe upload no CMS, então
imagem tem que estar no commit. Se a foto já é versionada, o dado também é.

O aplicador é **idempotente**: rodar duas vezes no mesmo lead atualiza em vez
de duplicar. Isso não é luxo — ele é chamado por HTTP (`/bootstrap-demo`), que
pode dar timeout no meio e ser reexecutado.

Ética da prévia
---------------
O site é montado a partir de dados públicos do bar, antes de qualquer contato.
Por isso toda demo nasce com `noindex` e banner dizendo que não é o site
oficial (ver `landing.html`). Não é opcional: sem isso a prévia compete no
Google com o negócio real de alguém que não pediu nada.
"""
import os
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, Review, TeamMember, GalleryItem
from app.utils.site_router import gerar_slug, slug_unico

DIR_LEADS = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'leads')

DIAS_VALIDADE_PADRAO = 30

# Só estas chaves são gravadas em SiteConfig. Whitelist em vez de setattr solto:
# um typo no .yml vira erro visível, não coluna fantasma.
# Derivada do próprio modelo pra não dessincronizar quando um campo novo entrar.
CAMPOS_SITE = {
    c.name for c in SiteConfig.__table__.columns
} - {'id', 'restaurant_id', 'data_atualizacao'}

# (chave no yml, model, campos aceitos por item)
LISTAS = (
    ('cardapio', DishCard, ('nome', 'descricao', 'imagem', 'tag', 'destaque')),
    ('avaliacoes', Review, ('autor', 'texto', 'estrelas')),
    ('equipe', TeamMember, ('nome', 'papel', 'emoji')),
    ('galeria', GalleryItem, ('imagem', 'legenda')),
)


class LeadInvalido(ValueError):
    pass


def carregar_lead(caminho):
    import yaml
    with open(caminho, encoding='utf-8') as f:
        dados = yaml.safe_load(f) or {}
    if not isinstance(dados, dict):
        raise LeadInvalido(f'{os.path.basename(caminho)}: raiz precisa ser um mapa')
    if not (dados.get('nome') or '').strip():
        raise LeadInvalido(f'{os.path.basename(caminho)}: falta `nome`')
    return dados


def listar_leads():
    if not os.path.isdir(DIR_LEADS):
        return []
    return sorted(
        os.path.join(DIR_LEADS, n) for n in os.listdir(DIR_LEADS)
        if n.endswith(('.yml', '.yaml'))
    )


def _slug_do_lead(dados, caminho):
    """Slug explícito no arquivo, senão o nome do arquivo, senão o nome do bar."""
    slug = (dados.get('slug') or '').strip().lower()
    if not slug:
        slug = os.path.splitext(os.path.basename(caminho))[0].lower()
    return slug or gerar_slug(dados['nome'])


def _expira_em(dados):
    bloco = dados.get('demo') or {}
    valor = bloco.get('expira_em')
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        return datetime.strptime(valor.strip(), '%Y-%m-%d').date()
    return date.today() + timedelta(days=DIAS_VALIDADE_PADRAO)


DIR_FOTOS = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         'static', 'img', 'demo')
EXTENSOES = ('.jpg', '.jpeg', '.png', '.webp')


def pasta_do_bar(slug):
    return os.path.join(DIR_FOTOS, slug)


def fotos_do_bar(slug):
    """Lê a pasta do bar e separa as fotos por função, pelo nome do arquivo.

    Convenção (documentada em app/static/img/demo/LEIA-ME.md):

        capa.jpg              foto do topo
        prato-<nome>.jpg      vira item do cardápio, com o nome tirado do arquivo
        equipe-<nome>.jpg     ignorada por ora (equipe é texto)
        qualquer-outra.jpg    entra na galeria

    Existe pra resolver o caso real de campo: o dono manda as fotos no
    WhatsApp, você joga na pasta e roda um comando — sem editar YAML na frente
    dele. O que o .yml declara explicitamente sempre vence o que a pasta traz.
    """
    pasta = pasta_do_bar(slug)
    if not os.path.isdir(pasta):
        return {'capa': None, 'pratos': [], 'galeria': []}

    capa, pratos, galeria = None, [], []
    for nome in sorted(os.listdir(pasta)):
        if not nome.lower().endswith(EXTENSOES):
            continue
        caminho = f'img/demo/{slug}/{nome}'
        base = os.path.splitext(nome)[0].lower()

        if base in ('capa', 'hero', '00-capa'):
            capa = caminho
        elif base.startswith('prato-'):
            # "prato-costela-na-brasa.jpg" -> "Costela na brasa"
            rotulo = base[len('prato-'):].replace('-', ' ').replace('_', ' ').strip()
            pratos.append({'nome': rotulo.capitalize() or 'Prato da casa',
                           'imagem': caminho})
        elif base.startswith('equipe-'):
            continue
        else:
            galeria.append({'imagem': caminho})

    # Sem capa explícita, a primeira da galeria assume o topo — melhor que
    # abrir o site sem imagem nenhuma.
    if capa is None and galeria:
        capa = galeria[0]['imagem']
    return {'capa': capa, 'pratos': pratos, 'galeria': galeria}


def _aplicar_listas(dados, rid, log):
    """Substitui o conteúdo das seções. Apagar e recriar (em vez de casar item
    a item) mantém o .yml como fonte única da verdade: o que sai do arquivo sai
    do site. Seguro porque demo não é editada pelo CMS."""
    for chave, Model, campos in LISTAS:
        itens = dados.get(chave) or []
        if not isinstance(itens, list):
            raise LeadInvalido(f'`{chave}` precisa ser uma lista')

        Model.query.filter_by(restaurant_id=rid).delete()
        for ordem, bruto in enumerate(itens):
            if chave == 'galeria' and isinstance(bruto, str):
                bruto = {'imagem': bruto}          # atalho: lista de caminhos
            if not isinstance(bruto, dict):
                raise LeadInvalido(f'`{chave}[{ordem}]` precisa ser um mapa')
            campos_item = {k: v for k, v in bruto.items() if k in campos}
            db.session.add(Model(restaurant_id=rid, ordem=ordem, ativo=True, **campos_item))
        if itens:
            log.append(f'  {chave}: {len(itens)}')


def aplicar_lead(caminho):
    """Cria ou atualiza a demo descrita no arquivo. Idempotente.

    Devolve (restaurante, log). Não commita — quem chama decide a transação.
    """
    dados = carregar_lead(caminho)
    slug = _slug_do_lead(dados, caminho)
    log = []

    rest = Restaurante.query.filter_by(slug=slug).first()
    if rest is None:
        rest = Restaurante(nome=dados['nome'], slug=slug_unico(dados['nome'], preferido=slug))
        db.session.add(rest)
        db.session.flush()
        log.append(f'criado tenant #{rest.id} /bar/{rest.slug}')
    else:
        log.append(f'atualizado tenant #{rest.id} /bar/{rest.slug}')
        if rest.tipo_conta not in (None, 'demo'):
            # Nunca sobrescrever um bar que já é cliente pagante.
            raise LeadInvalido(
                f'slug "{slug}" pertence a um cliente (tipo_conta={rest.tipo_conta}). '
                f'Recusando sobrescrever.')

    rest.nome = dados['nome']
    rest.tipo_conta = 'demo'
    # `ativo: false` no arquivo tira a prévia do ar e a mantém fora.
    #
    # Sem isso o aplicador reativava tudo a cada rodada, e casa que fechou (o
    # Google marca "permanentemente fechado") voltava a ter site publicado no
    # nome dela — além de reentrar no roteiro e custar um deslocamento à toa.
    # Apagar o lead não serve: a próxima varredura o recriaria.
    rest.ativo = dados.get('ativo', True) is not False
    rest.demo_expira_em = _expira_em(dados)
    rest.demo_fonte = (dados.get('demo') or {}).get('fonte')

    cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first()
    if cfg is None:
        cfg = SiteConfig(restaurant_id=rest.id)
        db.session.add(cfg)

    # Fotos que estiverem na pasta do bar entram sozinhas. O .yml continua
    # mandando: só preenchemos o que ele não declarou.
    fotos = fotos_do_bar(rest.slug)
    if fotos['capa'] or fotos['pratos'] or fotos['galeria']:
        log.append(f"  fotos da pasta: capa={'sim' if fotos['capa'] else 'não'}, "
                   f"pratos={len(fotos['pratos'])}, galeria={len(fotos['galeria'])}")

    site = dict(dados.get('site') or {})
    site.setdefault('nome', dados['nome'])
    if fotos['capa'] and not site.get('hero_foto'):
        site['hero_foto'] = fotos['capa']
    if fotos['pratos'] and not dados.get('cardapio'):
        dados['cardapio'] = fotos['pratos']
    if fotos['galeria'] and not dados.get('galeria'):
        dados['galeria'] = fotos['galeria']
    for chave in ('tema', 'cidade_uf'):          # aceitos no topo por conveniência
        if dados.get(chave) and not site.get(chave):
            site[chave] = dados[chave]

    desconhecidos = set(site) - CAMPOS_SITE
    if desconhecidos:
        raise LeadInvalido(f'campos desconhecidos em `site`: {sorted(desconhecidos)}')
    for chave, valor in site.items():
        setattr(cfg, chave, valor)

    db.session.flush()
    _aplicar_listas(dados, rest.id, log)
    return rest, log


def aplicar_todos(slug=None):
    """Aplica todos os leads (ou um só). Commita por lead: um arquivo com erro
    não derruba os que já passaram."""
    resultado = {'ok': [], 'erros': []}
    for caminho in listar_leads():
        nome_arq = os.path.basename(caminho)
        if slug and os.path.splitext(nome_arq)[0].lower() != slug.lower():
            continue
        try:
            rest, log = aplicar_lead(caminho)
            db.session.commit()
            resultado['ok'].append({'arquivo': nome_arq, 'slug': rest.slug, 'log': log})
        except Exception as e:
            db.session.rollback()
            resultado['erros'].append({'arquivo': nome_arq, 'erro': f'{type(e).__name__}: {e}'})
    return resultado


def converter_demo(rest, email, senha, nome_admin='Responsável', dias_trial=None):
    """Demo vira cliente. Adiciona o que faltava, não migra nada.

    Todo o conteúdo curado continua nas mesmas linhas, no mesmo restaurant_id —
    é justamente por isso que a demo não tem Usuario: converter é só criar o
    dono e desligar a marcação de prévia.
    """
    from app.models.usuario import Usuario
    from app.utils.planos import DIAS_DE_TRIAL

    dias_trial = DIAS_DE_TRIAL if dias_trial is None else dias_trial

    email = (email or '').strip().lower()
    if Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
        raise LeadInvalido(f'já existe conta com o e-mail {email}')

    rest.tipo_conta = 'cliente'
    rest.demo_expira_em = None
    rest.ativo = True
    # Quem carrega os 14 dias é `trial_termina_em`, não o tier.
    #
    # Isto era `subscription_tier = 'site'`, e o efeito não era o pretendido:
    # `plano_efetivo` lê `plano_ate is not None and hoje > plano_ate`, ou seja,
    # data nula significa "sem corte conhecido — vale o tier". A regra existe
    # pra proteger os tenants criados antes do campo `plano_ate`, mas toda
    # conversão nascia dentro dela: tier 'site' + data nula = plano Site
    # vitalício, de graça, e o trial de 14 dias nunca chegava a valer de nada.
    #
    # Com 'free' aqui, o acesso dos 14 dias vem de `plano_efetivo` devolvendo
    # 'trial' (que vale como pro). Passado o prazo sem pagamento, cai pra free —
    # site no ar, controle congelado, que é a degradação desenhada. Quem paga
    # sobe pra 'site'/'pro' com data por `planos.registrar_pagamento`.
    rest.subscription_tier = 'free'
    rest.trial_termina_em = date.today() + timedelta(days=dias_trial)

    admin = Usuario(nome=nome_admin, email=email, senha=senha,
                    tipo='admin', restaurant_id=rest.id)
    db.session.add(admin)
    return admin
