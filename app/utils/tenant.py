import time
from collections import defaultdict, deque

from flask_login import current_user

# Rate limit simples, em memória. Não é Redis de propósito: em serverless cada
# instância tem o seu contador, o que é suficiente para conter script bobo
# batendo em /reservar e /cadastro. Abuso distribuído de verdade é problema da
# borda (Vercel WAF), não da aplicação.
_ACESSOS = defaultdict(deque)


def limite_excedido(chave, maximo=10, janela_segundos=300):
    """True quando `chave` estourou `maximo` tentativas na janela.

    Inerte sob TESTING: o contador é global do processo e vazaria de um teste
    para o outro, fazendo suíte passar ou falhar conforme a ordem.
    """
    from flask import current_app
    if current_app and current_app.config.get('TESTING'):
        return False

    agora = time.monotonic()
    marcas = _ACESSOS[chave]
    while marcas and agora - marcas[0] > janela_segundos:
        marcas.popleft()
    if len(marcas) >= maximo:
        return True
    marcas.append(agora)
    if len(_ACESSOS) > 5000:          # teto de memória do processo
        _ACESSOS.clear()
    return False

def get_current_restaurant_id():
    """Retorna o ID do restaurante do usuário atual.
    Se o usuário não estiver logado ou não tiver restaurante, retorna None.
    """
    if current_user.is_authenticated and hasattr(current_user, 'restaurant_id'):
        return current_user.restaurant_id
    return None
