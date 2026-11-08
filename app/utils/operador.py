"""Quem opera a campanha e plataforma global (SuperAdmin Master).

O painel de campanha e o Modo Campo mexem em múltiplos tenants (prospecção de
novos bares, configuração de demonstrações e métricas globais).
Essa permissão é restrita a usuários com `tipo == 'superadmin'` (Master Admin),
garantindo que donos de bares comuns (`tipo == 'admin'`) fiquem 100% isolados
no seu próprio restaurante.
"""
from flask_login import current_user


def e_operador(usuario=None):
    """Retorna True apenas se o usuário for o Master Admin (SuperAdmin)."""
    usuario = current_user if usuario is None else usuario
    if not usuario or not getattr(usuario, 'is_authenticated', False):
        return False
    return getattr(usuario, 'tipo', None) == 'superadmin'


def operador_real():
    """O superadmin de verdade, mesmo de dentro do admin de um negócio.

    Quem abre o admin de um bar entra logado como o dono dele (`campo.abrir_admin`)
    e o vínculo com o operador fica em `session['operador_id']`. Para trocar de
    negócio sem voltar ao Campo, o guard precisa reconhecer esse operador:
    `e_operador()` sozinho olha só o usuário logado, que ali é o dono.
    """
    from flask import session
    if e_operador():
        return current_user
    operador_id = session.get('operador_id')
    if operador_id:
        from app.models.usuario import Usuario
        candidato = Usuario.query.get(operador_id)
        if candidato is not None and e_operador(candidato):
            return candidato
    return None
