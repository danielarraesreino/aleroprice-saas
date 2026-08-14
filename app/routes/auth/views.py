from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.usuario import Usuario

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
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
        login_user(usuario, remember=bool(request.form.get('lembrar')))
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        return redirect(next_page)
        
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
