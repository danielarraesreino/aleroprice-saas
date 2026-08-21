from flask import render_template, redirect, url_for, flash, request, jsonify

from app.extensions import db
from app.models.modelo_siteconfig import SiteConfig
from app.routes.configsite import bp
from app.routes.publico.views import SITE_DEFAULTS
from app.utils.tenant import get_current_restaurant_id
from app.utils import blob
from app.utils.decorators import plano_minimo
from app.utils.temas import opcoes_de_tema, tema_valido
from app.utils.copy_site import opcoes_de_vibe, vibe_valida
from app.utils.modelos import (
    MODELO_PADRAO, modelo_valido, opcoes_de_modelo,
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
        if modelo and modelo_valido(modelo):
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
                           modelos=opcoes_de_modelo(),
                           modelo_atual=(cfg.modelo if cfg and modelo_valido(cfg.modelo)
                                         else MODELO_PADRAO),
                           modo_atual=(cfg.tema_modo if cfg and cfg.tema_modo
                                       in ('auto', 'claro', 'escuro') else 'auto'),
                           slug=(rest.slug if rest else None))


@bp.post('/testar-callmebot')
@plano_minimo('site')
def testar_callmebot():
    """Envia uma mensagem de teste para o WhatsApp do bar via CallMeBot."""
    import urllib.parse
    import urllib.request
    
    rid = get_current_restaurant_id()
    if not rid:
        return jsonify({'ok': False, 'erro': 'Sessão sem restaurante'}), 400

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    
    # Pode receber do form do teste ou do SiteConfig salvo
    phone = (request.form.get('callmebot_phone') or request.json.get('callmebot_phone') if request.is_json else None)
    apikey = (request.form.get('callmebot_apikey') or request.json.get('callmebot_apikey') if request.is_json else None)
    
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
