from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.usuario import Usuario

bp = Blueprint('auth', __name__)


def _destino_depois_do_login():
    """Para onde cada perfil vai ao entrar.

    Quem opera a campanha entra pelo celular, em pé dentro de um bar, e precisa
    do Modo Campo. Mandá-lo para o painel de lucratividade — 14 itens de menu,
    desenhado para notebook — custa toques que não existem naquele momento.

    Dono de bar continua indo para o dashboard: é o painel dele.
    """
    from app.utils.operador import e_operador

    if e_operador():
        return url_for('campo.index')
    return url_for('dashboard.index')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_destino_depois_do_login())

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.verificar_senha(senha):
            flash('Email ou senha inválidos', 'danger')
            return redirect(url_for('auth.login'))

        # `lembrar` vem marcado por padrão no form. Sem cookie persistente o
        # login morre quando o navegador do celular descarta a aba — o que
        # acontece toda vez que se abre a câmera no meio de uma visita.
        session.pop('operador_id', None)     # login novo não herda "abrir admin"
        login_user(usuario, remember=bool(request.form.get('lembrar')))
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = _destino_depois_do_login()
        return redirect(next_page)

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    # Sair de dentro do admin de um bar (campo.abrir_admin) encerra também o
    # vínculo com o operador: senão o próximo login neste navegador herdaria
    # o botão "voltar ao meu admin".
    session.pop('operador_id', None)
    logout_user()
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------ troca de senha
#
# O link leva um token assinado com a SECRET_KEY que carrega o id do usuário e
# um pedaço do hash da senha atual: vale 30 minutos e morre sozinho assim que a
# senha muda (uso único sem tabela nova).

_SAL_SENHA = 'redefinir-senha'
_VALIDADE_LINK = 30 * 60
_MENSAGEM_ENVIO = ('Se esse e-mail tiver conta, mandamos um link para criar uma '
                   'senha nova. Ele vale por 30 minutos — confira também o spam.')


def _assinador():
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SAL_SENHA)


def _usuario_do_token(token):
    from itsdangerous import BadSignature, SignatureExpired
    try:
        dados = _assinador().loads(token, max_age=_VALIDADE_LINK)
    except (BadSignature, SignatureExpired):
        return None
    usuario = Usuario.query.get(dados.get('id') or 0)
    if usuario is None or usuario.senha[-16:] != dados.get('h'):
        return None                     # senha já trocada: link usado
    return usuario


@bp.route('/esqueci', methods=['GET', 'POST'])
def esqueci():
    from app.utils.email import enviar_email
    from app.utils.tenant import limite_excedido

    if request.method == 'POST':
        if limite_excedido(f'esqueci:{request.remote_addr}', maximo=5, janela_segundos=900):
            flash('Muitas tentativas. Aguarde alguns minutos.', 'warning')
            return redirect(url_for('auth.esqueci'))
        email = (request.form.get('email') or '').strip().lower()
        usuario = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()
        # Mesma resposta exista ou não a conta: a tela não revela quem é cliente.
        if usuario is not None and usuario.ativo is not False:
            token = _assinador().dumps({'id': usuario.id, 'h': usuario.senha[-16:]})
            link = url_for('auth.redefinir', token=token, _external=True)
            enviar_email(usuario.email, 'Crie uma senha nova',
                         f'<p>Oi, {usuario.nome}.</p>'
                         f'<p>Para criar uma senha nova, abra este link (vale por 30 minutos):</p>'
                         f'<p><a href="{link}">{link}</a></p>'
                         '<p>Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma.</p>')
        flash(_MENSAGEM_ENVIO, 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/esqueci.html')


@bp.route('/redefinir/<token>', methods=['GET', 'POST'])
def redefinir(token):
    usuario = _usuario_do_token(token)
    if usuario is None:
        flash('Esse link expirou ou já foi usado. Peça outro.', 'warning')
        return redirect(url_for('auth.esqueci'))
    if request.method == 'POST':
        senha = request.form.get('senha') or ''
        if len(senha) < 8:
            flash('A senha precisa ter pelo menos 8 caracteres.', 'danger')
            return render_template('auth/redefinir.html', token=token)
        usuario.set_senha(senha)
        db.session.commit()
        flash('Senha trocada. Entre com a senha nova.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/redefinir.html', token=token)
