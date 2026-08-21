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
