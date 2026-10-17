"""E-mail transacional pelo Brevo (API v3, sem SDK).

Usado para o link de troca de senha. Precisa de `BREVO_API_KEY` no ambiente;
o remetente (`BREVO_REMETENTE`) tem que estar verificado na conta Brevo.
Sem chave, não envia e devolve False: quem chama decide o que dizer.
"""
import json
import os
import urllib.request

from flask import current_app

URL_BREVO = 'https://api.brevo.com/v3/smtp/email'


def enviar_email(para, assunto, html):
    chave = os.environ.get('BREVO_API_KEY')
    if not chave:
        current_app.logger.warning('BREVO_API_KEY ausente: e-mail não enviado.')
        return False
    corpo = {
        'sender': {
            'name': os.environ.get('BREVO_REMETENTE_NOME', 'Feira de Barão'),
            'email': os.environ.get('BREVO_REMETENTE', 'coletivoaruatemvoz@gmail.com'),
        },
        'to': [{'email': para}],
        'subject': assunto,
        'htmlContent': html,
    }
    req = urllib.request.Request(
        URL_BREVO, data=json.dumps(corpo).encode('utf-8'), method='POST',
        headers={'api-key': chave, 'Content-Type': 'application/json',
                 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as e:  # noqa: BLE001 — falha de envio não derruba a tela
        current_app.logger.error(f'Brevo falhou: {e}')
        return False
