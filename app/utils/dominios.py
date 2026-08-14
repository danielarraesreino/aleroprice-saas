"""Domínio próprio: consultar disponibilidade pelo nome do bar.

Por que existe
--------------
Argumento de venda que se prova na hora. "Olha, `tabuascervejaria.com.br` está
livre agora" abre conversa muito melhor que "posso fazer seu site". E domínio
próprio é o gancho natural do plano Site — o bar sai de `/bar/<slug>` para um
endereço que é dele.

Como consulta
-------------
**RDAP do registro.br**, público e sem chave: `GET rdap.registro.br/domain/x.com.br`
responde **200 se registrado** e **404 se livre**. Cobre `.com.br` e `.net.br`.

Só estes dois TLDs entram aqui de propósito. TLDs de nicho (`.bar`, `.rest`,
`.pub`) seriam ótimos para o segmento — `bardavila.bar` é o exemplo vivo — mas
o resolver genérico `rdap.org` respondeu redirect para tudo e falhou no `.bar`
no teste de 14/08/2026. Prometer "livre" sem conseguir verificar é pior que não
oferecer: o vendedor repete na mesa e descobre errado na hora de registrar.

A compra continua manual (o operador registra e conecta). Aqui é só a consulta.
"""
import json
import os
import urllib.error
import urllib.request

from app.utils.site_router import gerar_slug

RDAP_BR = 'https://rdap.registro.br/domain'
TIMEOUT = 6

# Ordem de preferência: o primeiro que estiver livre é o que se oferece.
SUFIXOS = ('.com.br', '.net.br')

# Domínio que não cabe num cartão nem se fala no telefone não vale oferecer.
LIMITE_ROTULO = 24


def _rotulo(texto):
    """Nome do bar -> rótulo de domínio: sem acento, sem hífen, sem 'bar' solto.

    `gerar_slug` já tira acento e normaliza; aqui só se colapsa o hífen, porque
    domínio de bar quase nunca é vendido com hífen ("bardoze.com.br", não
    "bar-do-ze.com.br").

    Nome vazio devolve vazio: `gerar_slug` cai no fallback `'bar'`, que serve
    como slug de tenant e não serve aqui — ofereceria "bar.com.br" para um bar
    sem nome cadastrado.
    """
    if not (texto or '').strip():
        return ''
    return gerar_slug(texto).replace('-', '')[:63]


def candidatos(nome, cidade=None):
    """Domínios a testar, do mais desejável ao alternativo.

    O nome curto vem primeiro porque é o que o dono quer dizer no rádio. As
    variações com cidade existem para quando o nome sozinho já foi levado —
    caso comum em nome genérico ("Botequim", "Eskina").
    """
    base = _rotulo(nome)
    if not base:
        return []

    nomes = [base]
    if cidade:
        # `cidade_uf` chega como "Barão Geraldo, Campinas–SP": só o primeiro
        # termo entra. O campo inteiro geraria
        # "cervejariatabuasbaraogeraldocampinassp.com.br", que ninguém registra.
        curto = _rotulo(cidade.replace('–', ',').replace('-', ',').split(',')[0])
        if curto and curto not in base and len(base) + len(curto) <= LIMITE_ROTULO:
            nomes.append(f'{base}{curto}')
    if not base.startswith('bar'):
        nomes.append(f'bar{base}')

    saida = []
    for n in nomes:
        for sufixo in SUFIXOS:
            dominio = f'{n}{sufixo}'
            if dominio not in saida:
                saida.append(dominio)
    return saida


def disponivel(dominio):
    """`True` livre · `False` registrado · `None` não deu para consultar.

    `None` é resposta legítima e precisa aparecer na tela como "conferir na
    hora" — nunca virar "livre" por otimismo. Dizer que está livre e o vendedor
    descobrir o contrário na frente do dono queima a proposta inteira.
    """
    if not dominio:
        return None
    try:
        req = urllib.request.Request(
            f'{RDAP_BR}/{dominio}',
            headers={'Accept': 'application/rdap+json'},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status != 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True          # não existe no registro = livre
        if e.code == 429:
            return None          # rate limit: não é resposta sobre o domínio
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def consultar(nome, cidade=None, limite=4):
    """Lista pronta para a tela: [{'dominio', 'livre'}], na ordem de preferência.

    `limite` existe porque isto roda no meio do carregamento da proposta: cada
    consulta é uma ida à rede, e a proposta não pode demorar com o dono do bar
    olhando.
    """
    return [
        {'dominio': d, 'livre': disponivel(d)}
        for d in candidatos(nome, cidade)[:limite]
    ]


def primeiro_livre(consulta):
    """O domínio que vale citar na proposta, ou None se nenhum se confirmou."""
    for item in consulta:
        if item['livre'] is True:
            return item['dominio']
    return None


def taxa_de_instalacao():
    """Cobrança única de registrar o domínio e publicar o site.

    Sem a env a linha some da proposta — dá para testar o discurso antes de
    fixar preço, do mesmo jeito que `planos.precos()` faz com a mensalidade.
    """
    valor = (os.environ.get('FEIRA_TAXA_SETUP') or '').strip()
    return valor or None
