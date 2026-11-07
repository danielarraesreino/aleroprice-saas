"""Logo do expositor: só vale se der para abrir.

O campo era texto livre e o Viaverde ficou com a palavra "logo" gravada: o site
montou `/static/logo`, que dá 404, e o topo mostrou imagem quebrada em vez do
monograma. Aqui o valor é conferido na hora de montar o site, para nenhum
modelo desenhar uma imagem que não existe (regra R4 do design-feira).
"""
import os

from flask import current_app


def logo_utilizavel(valor):
    """O próprio valor se abrir (URL absoluta ou arquivo em static/); senão None."""
    v = (valor or '').strip()
    if not v:
        return None
    if v.startswith(('http://', 'https://')):
        return v
    base = os.path.realpath(current_app.static_folder)
    alvo = os.path.realpath(os.path.join(base, v.lstrip('/')))
    if alvo.startswith(base + os.sep) and os.path.isfile(alvo):
        return v
    return None
