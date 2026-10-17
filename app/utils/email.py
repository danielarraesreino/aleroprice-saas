"""Brevo pela API v3, sem SDK: e-mail transacional e contatos (leads).

`enviar_email` manda o link de troca de senha; `salvar_contato` põe um lead
numa lista. Precisa de `BREVO_API_KEY` no ambiente; o remetente
(`BREVO_REMETENTE`) tem que estar verificado na conta Brevo. Sem chave, nada
sai e as funções devolvem False: quem chama decide o que dizer.
"""
import json
import os
import urllib.error
import urllib.request

from flask import current_app

URL_BREVO = 'https://api.brevo.com/v3/smtp/email'
URL_CONTATOS = 'https://api.brevo.com/v3/contacts'


def _post(url, corpo, chave):
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode('utf-8'), method='POST',
        headers={'api-key': chave, 'Content-Type': 'application/json',
                 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        # O corpo diz o motivo (ex.: atributo inexistente, template inválido).
        current_app.logger.error(f'Brevo falhou: {e} {e.read()[:300]!r}')
        return False
    except Exception as e:  # noqa: BLE001 — falha do Brevo não derruba a tela
        current_app.logger.error(f'Brevo falhou: {e}')
        return False


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
    return _post(URL_BREVO, corpo, chave)


def salvar_contato(email, atributos, lista_env, dupla_confirmacao=False,
                   redirecionar=None):
    """Põe `email` na lista cujo id está na env `lista_env`.

    Com `dupla_confirmacao`, o Brevo manda o e-mail "confirme sua inscrição"
    (template da env `BREVO_TEMPLATE_DOI`) e só põe na lista quem clicar: é a
    prova de consentimento que a LGPD pede para quem não é cliente. Sem o
    template configurado, cai no cadastro direto — o consentimento marcado no
    formulário fica registrado nos atributos.
    """
    chave = os.environ.get('BREVO_API_KEY')
    lista = os.environ.get(lista_env, '')
    if not chave or not lista.isdigit():
        current_app.logger.warning(f'Brevo sem chave ou {lista_env}: contato não salvo.')
        return False
    template = os.environ.get('BREVO_TEMPLATE_DOI', '')
    if dupla_confirmacao and template.isdigit() and redirecionar:
        if _post(f'{URL_CONTATOS}/doubleOptinConfirmation', {
            'email': email, 'attributes': atributos,
            'includeListIds': [int(lista)], 'templateId': int(template),
            'redirectionUrl': redirecionar,
        }, chave):
            return True
        # Dupla confirmação recusada (template mal configurado, p.ex.): o lead
        # não se perde — entra direto, com o consentimento do formulário.
    return _post(URL_CONTATOS, {
        'email': email, 'attributes': atributos,
        'listIds': [int(lista)], 'updateEnabled': True,
    }, chave)
