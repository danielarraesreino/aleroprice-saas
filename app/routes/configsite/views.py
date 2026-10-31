from flask import render_template, redirect, url_for, flash, request, jsonify

from app.extensions import db
from app.models.modelo_siteconfig import SiteConfig
from app.routes.configsite import bp
from app.routes.publico.views import SITE_DEFAULTS
from app.utils.feira import hoje_br
from app.utils.tenant import get_current_restaurant_id
from app.utils import blob
from app.utils.decorators import plano_minimo
from app.utils.temas import opcoes_de_tema, tema_valido
from app.utils.copy_site import opcoes_de_vibe, vibe_valida
from app.utils.modelos import (
    MODELO_PADRAO, modelo_valido, opcoes_de_modelo, catalogo_de_modelos,
)

CAMPOS = list(SITE_DEFAULTS.keys())


@bp.post('/foto')
@plano_minimo('site')
def foto():
    """O dono troca a própria foto de capa.

    Existia só no Modo Campo (`campo.foto`), que é ferramenta do operador e
    responde 404 pro cliente. No painel, o campo de capa era um texto pedindo
    "caminho em static, ex: img/bar/foto-18.jpg" — ou seja, o dono do bar não
    tinha como pôr foto nenhuma no site que ele paga. Quem podia era só quem
    vendeu.

    Mesma mecânica do Modo Campo: a imagem chega já reduzida pelo navegador
    (foto de celular tem ~4MB e o 4G não sobe isso enquanto alguém espera), sobe
    pro Vercel Blob e a resposta é JSON — recarregar a página inteira depois de
    cada foto é lento e faz perder o resto do formulário preenchido.
    """
    rid = get_current_restaurant_id()
    if not rid:
        return jsonify({'erro': 'sessão sem restaurante'}), 400

    from app.models.modelo_restaurante import Restaurante
    rest = Restaurante.query.get(rid)
    if rest is None:
        return jsonify({'erro': 'restaurante não encontrado'}), 404

    try:
        url = blob.enviar(request.files.get('imagem'), rest.slug or f's{rid}')
    except blob.UploadInvalido as e:
        return jsonify({'erro': str(e)}), 400
    except blob.UploadIndisponivel as e:
        return jsonify({'erro': str(e)}), 503

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    if cfg is None:
        cfg = SiteConfig(restaurant_id=rid, nome=rest.nome)
        db.session.add(cfg)
    cfg.hero_foto = url
    db.session.commit()
    return jsonify({'ok': True, 'url': url})


@bp.post('/na-feira')
@plano_minimo('site')
def na_feira():
    """O expositor avisa "estou na feira hoje". Vale só no dia (data, não flag)."""
    from app.utils.feira import alternar_na_feira

    rid = get_current_restaurant_id()
    if not rid:
        return redirect(url_for('auth.login'))
    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    if cfg is None:
        cfg = SiteConfig(restaurant_id=rid)
        db.session.add(cfg)
    ligado = alternar_na_feira(cfg)
    db.session.commit()
    flash('Pronto: seu site aparece como "na feira hoje".' if ligado
          else 'Tirei o "na feira hoje" do seu site.', 'success')
    return redirect(url_for('configsite.index'))


@bp.route('/encomendas', methods=['GET', 'POST'])
@plano_minimo('site')
def encomendas():
    """Encomenda com retirada na feira: o cliente escolhe o sábado ou domingo
    na sacola do site e o pedido chega no WhatsApp já com a data."""
    from app.utils.feira import proximas_retiradas

    rid = get_current_restaurant_id()
    if not rid:
        return redirect(url_for('auth.login'))
    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    if request.method == 'POST':
        if cfg is None:
            cfg = SiteConfig(restaurant_id=rid)
            db.session.add(cfg)
        cfg.retirada_na_feira = request.form.get('retirada_na_feira') == '1'
        try:
            cfg.retirada_antecedencia = min(max(int(request.form.get('retirada_antecedencia', 2)), 0), 30)
        except ValueError:
            cfg.retirada_antecedencia = 2
        db.session.commit()
        flash('Encomendas com retirada na feira ligadas.' if cfg.retirada_na_feira
              else 'Retirada na feira desligada: a sacola volta a só mandar a lista.', 'success')
        return redirect(url_for('configsite.encomendas'))
    ligado = bool(cfg and cfg.retirada_na_feira)
    antecedencia = cfg.retirada_antecedencia if cfg and cfg.retirada_antecedencia is not None else 2
    return render_template('configsite/encomendas.html', ligado=ligado, antecedencia=antecedencia,
                           datas=proximas_retiradas(hoje_br(), antecedencia))


@bp.route('/catalogo')
@plano_minimo('site')
def catalogo():
    """Os mesmos produtos do site no WhatsApp Business e no Instagram, pelo
    feed da Meta. Mostra o endereço do feed, o que entra e o que falta."""
    from app.models.modelo_restaurante import Restaurante
    from app.utils import catalogo as feed
    from app.utils.site_router import dominio_do_produto

    rid = get_current_restaurant_id()
    if not rid:
        return redirect(url_for('auth.login'))
    rest = Restaurante.query.get_or_404(rid)
    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    linhas, fora = feed.itens(rest, cfg.nome if cfg and cfg.nome else None)
    url_feed = (f'https://{dominio_do_produto()}'
                + url_for('public.catalogo_meta', slug=rest.slug)) if rest.slug else ''
    return render_template('configsite/catalogo.html', linhas=linhas, fora=fora, url_feed=url_feed)


@bp.route('/numeros')
@plano_minimo('site')
def numeros():
    """"Seus números": o que o site fez pelo cliente. É a prova que segura a
    renovação; sem ela, o plano parece custo."""
    from app.models.modelo_reserva import Reserva
    from app.models.modelo_restaurante import Restaurante
    from app.utils import metricas
    from app.utils.site_router import url_canonica

    rid = get_current_restaurant_id()
    if not rid:
        return redirect(url_for('auth.login'))
    rest = Restaurante.query.get_or_404(rid)
    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    hoje = hoje_br()
    serie = metricas.por_dia(rid, 30, hoje)
    mes_ini = hoje.replace(day=1)
    ant_ini, ant_fim = metricas.mes_anterior(hoje)

    def reservas(inicio, fim):
        return (Reserva.query.filter(Reserva.restaurant_id == rid, Reserva.status != 'cancelada',
                                     Reserva.data >= inicio, Reserva.data <= fim).count())

    return render_template(
        'configsite/numeros.html',
        tipos=metricas.TIPOS,
        este_mes=metricas.totais(rid, mes_ini, hoje),
        mes_passado=metricas.totais(rid, ant_ini, ant_fim),
        nome_mes=metricas.MESES[hoje.month - 1],
        nome_mes_passado=metricas.MESES[ant_ini.month - 1],
        reservas_mes=reservas(mes_ini, hoje),
        reservas_passado=reservas(ant_ini, ant_fim),
        avaliacoes=(cfg.cliques_avaliacao or 0) if cfg else 0,
        serie=serie,
        pico=max([d['visita'] for _, d in serie] + [1]),
        link=url_canonica(rest) if rest.slug else '',
    )


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@plano_minimo('site')
def index():
    rid = get_current_restaurant_id()
    if not rid:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()

    if request.method == 'POST':
        if not cfg:
            cfg = SiteConfig(restaurant_id=rid)
            db.session.add(cfg)
        for campo in CAMPOS:
            # Só grava o que o formulário mandou. Sem esta guarda, todo campo
            # de CAMPOS sem <input> correspondente era apagado no primeiro save
            # — e o formulário vive crescendo/agrupando.
            if campo not in request.form:
                continue
            valor = (request.form.get(campo) or '').strip()
            setattr(cfg, campo, valor or None)

        # Tema é <select> de preset, não texto livre: validar evita gravar
        # nome inválido e servir CSS vazio sem o dono entender por quê.
        tema = (request.form.get('tema') or '').strip()
        if tema and tema_valido(tema):
            cfg.tema = tema
        vibe = (request.form.get('vibe') or '').strip()
        if vibe and vibe_valida(vibe):
            cfg.vibe = vibe

        # Modelo é a decisão maior que existe aqui — troca o esqueleto da
        # página, não a paleta. Faltava no painel: o dono só via as 4 cores e
        # ficava no `classico` pra sempre, sem saber que existiam outros cinco.
        # Trocar o layout do próprio site é escolha dele, não do vendedor.
        modelo = (request.form.get('modelo') or '').strip()
        from app.models.modelo_restaurante import Restaurante as _R
        catalogo, _, _ = catalogo_de_modelos(getattr(_R.query.get(rid), 'tipo_negocio', None))
        if modelo and modelo in catalogo:
            cfg.modelo = modelo
        modo = (request.form.get('tema_modo') or '').strip()
        if modo in ('auto', 'claro', 'escuro'):
            cfg.tema_modo = modo

        # Checkbox não enviado = desmarcado. Por isso lê presença na chave, e
        # não `CAMPOS` — que ignora campo ausente pra não apagar texto que o
        # formulário não trouxe. Aqui ausência é justamente a resposta "não".
        cfg.apoia_caminhos = bool(request.form.get('apoia_caminhos'))

        db.session.commit()
        flash('Site atualizado. Recarregue a página pública pra ver.', 'success')
        return redirect(url_for('configsite.index'))

    from app.models.modelo_restaurante import Restaurante
    rest = Restaurante.query.get(rid)
    return render_template('configsite/index.html', cfg=cfg, defaults=SITE_DEFAULTS,
                           temas=opcoes_de_tema(), vibes=opcoes_de_vibe(),
                           modelos=catalogo_de_modelos(getattr(rest, 'tipo_negocio', None))[2],
                           modelo_atual=(cfg.modelo if cfg and cfg.modelo in
                                         catalogo_de_modelos(getattr(rest, 'tipo_negocio', None))[0]
                                         else catalogo_de_modelos(getattr(rest, 'tipo_negocio', None))[1]),
                           modo_atual=(cfg.tema_modo if cfg and cfg.tema_modo
                                       in ('auto', 'claro', 'escuro') else 'auto'),
                           slug=(rest.slug if rest else None),
                           na_feira_hoje=bool(cfg and cfg.na_feira_em == hoje_br()),
                           eh_artesao=(getattr(rest, 'tipo_negocio', None) == 'artesao'))


@bp.post('/testar-callmebot')
@plano_minimo('site')
def testar_callmebot():
    """Envia uma mensagem de teste para o WhatsApp do bar via CallMeBot."""
    import os
    import urllib.parse
    import urllib.request
    
    rid = get_current_restaurant_id()
    if not rid:
        return jsonify({'ok': False, 'erro': 'Sessão sem restaurante'}), 400

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    
    # Pode receber do form do teste ou do SiteConfig salvo
    corpo = request.get_json(silent=True) or {}
    phone = request.form.get('callmebot_phone') or corpo.get('callmebot_phone')
    apikey = request.form.get('callmebot_apikey') or corpo.get('callmebot_apikey')
    
    if not phone and cfg:
        phone = cfg.callmebot_phone or cfg.whatsapp
    if not apikey and cfg:
        apikey = cfg.callmebot_apikey or os.environ.get('CALLMEBOT_APIKEY')

    if not phone or not apikey:
        return jsonify({'ok': False, 'erro': 'Preencha o número do WhatsApp e a API Key do CallMeBot antes de testar.'}), 400

    # Limpa caracteres não numéricos do telefone
    phone_clean = ''.join(c for c in str(phone) if c.isdigit())
    apikey_clean = str(apikey).strip()

    texto = "🔔 *AleroPrice*: Teste de notificação CallMeBot recebido com sucesso no seu WhatsApp! As novas reservas do seu site tocarão aqui instantaneamente. 🍻"
    params = urllib.parse.urlencode({'phone': phone_clean, 'text': texto, 'apikey': apikey_clean})
    url = 'https://api.callmebot.com/whatsapp.php?' + params

    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            if '200' in str(resp.status) or 'Message queued' in body or 'OK' in body:
                return jsonify({'ok': True, 'mensagem': 'Alerta de teste enviado! Verifique seu WhatsApp.'})
            return jsonify({'ok': True, 'mensagem': f'Chamada realizada: {body[:100]}'})
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'Falha ao conectar com CallMeBot: {str(e)}'}), 500
