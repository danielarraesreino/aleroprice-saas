from flask_login import current_user

def get_current_restaurant_id():
    """Retorna o ID do restaurante do usuário atual.
    Se o usuário não estiver logado ou não tiver restaurante, retorna None.
    """
    if current_user.is_authenticated and hasattr(current_user, 'restaurant_id'):
        return current_user.restaurant_id
    return None
