"""Número de WhatsApp no formato do wa.me: só dígitos, com 55.

O painel guardava o que o dono digitava, e "(19) 99235-9917" virava
`wa.me/(19)…`: o botão de encomenda e a mensagem da sacola morriam sem aviso.
"""
import re


def normalizar_whatsapp(valor):
    """Só dígitos com DDI 55, ou None quando não dá para confiar no número."""
    d = re.sub(r'\D', '', str(valor or ''))
    if d.startswith('55') and len(d) in (12, 13):
        return d
    if len(d) in (10, 11):
        return '55' + d
    return None
