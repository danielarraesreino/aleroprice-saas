from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def pro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
             return redirect(url_for('auth.login'))
             
        restaurante = current_user.restaurante
        # Logic: If it's not active or not Pro, redirect
        # We can implement a trial period logic later here too.
        if restaurante.subscription_tier != 'pro':
            flash('Esta funcionalidade é exclusiva do plano Pro. Faça o upgrade para desbloquear!', 'warning')
            return redirect(url_for('dashboard.upgrade'))
            
        return f(*args, **kwargs)
    return decorated_function
