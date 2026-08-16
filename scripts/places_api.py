"""Cliente mínimo da Places API (New), do Google.

Por que REST na mão e não o cliente oficial
-------------------------------------------
`googlemaps/google-maps-services-python` só implementa a API **legada**
(`/maps/api/place/...`); a New (`places.googleapis.com/v1`, com FieldMask) tem
issue aberta pedindo suporte e não chegou. Como a New é REST simples, sai mais
barato falar com ela por `urllib` — mesma escolha do `app/utils/blob.py`, e o
projeto continua sem dependência nova.

Por que a API oficial e não um scraper
--------------------------------------
A coleta anterior lia o painel do Google renderizado e já leu "4,6 1.951
avaliações" como nota **1,9** — um separador de milhar quase publicou nota
errada no site de um bar. Aqui o dado vem tipado, e a foto vem com licença de
uso e atribuição, sem ninguém logado em conta nenhuma.

Custo (faixa gratuita mensal por SKU, ago/2026)
-----------------------------------------------
    Essentials              10.000   fotos, endereço, coordenadas
    Enterprise               1.000   nota, nº de avaliações, horário, site, telefone
    Enterprise + Atmosphere  1.000   avaliações escritas, resumo editorial

Uma chamada de detalhes é cobrada pelo campo mais caro que ela pede — pedir
`reviews` cobra a chamada inteira como Enterprise+Atmosphere. Com 76 bares, o
levantamento completo usa ~7% da faixa mais restrita, e dá pra repetir toda
semana sem entrar em cobrança.

Chave
-----
    export GOOGLE_MAPS_API_KEY='...'

Console → APIs e Serviços → Credenciais → Criar credencial → Chave de API, com
a "Places API (New)" ativada. Restrinja por API; não precisa de OAuth nem de
conta logada em lugar nenhum.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://places.googleapis.com/v1'

# O que pedimos de cada bar. Ordem importa pra leitura, não pra API.
#
# `id` e `photos` são Essentials; `rating`, `userRatingCount`, `priceLevel`,
# `regularOpeningHours`, `websiteUri` e `nationalPhoneNumber` são Enterprise;
# `reviews` e `editorialSummary` são Enterprise+Atmosphere. Pedimos tudo de uma
# vez porque a resposta inteira é o levantamento — dividir em duas chamadas pra
# economizar tier custaria duas chamadas.
CAMPOS = (
    'id',
    'displayName',
    'formattedAddress',
    'location',
    'nationalPhoneNumber',
    'websiteUri',
    'rating',
    'userRatingCount',
    'priceLevel',
    'regularOpeningHours',
    'businessStatus',
    'primaryTypeDisplayName',
    'editorialSummary',
    'reviews',
    'photos',
)


class SemChave(Exception):
    """Falta configurar GOOGLE_MAPS_API_KEY. Erro de setup, não de dado."""


class ErroDaAPI(Exception):
    """A API respondeu erro. Mensagem original preservada — chute aqui vira
    dado errado no site de um bar."""


def _chave():
    chave = (os.environ.get('GOOGLE_MAPS_API_KEY') or '').strip()
    if not chave:
        raise SemChave(
            'defina GOOGLE_MAPS_API_KEY antes de rodar '
            '(Google Cloud Console → Credenciais → Chave de API, '
            'com a Places API (New) ativada)')
    return chave


def _pedir(url, corpo=None, mascara=None, tentativas=3):
    """Uma requisição, com repetição só no que adianta repetir.

    429 (cota por minuto) e 5xx passam; 400 e 403 não — chave errada ou campo
    inválido não melhora tentando de novo, e insistir queima cota.
    """
    cabecalhos = {'X-Goog-Api-Key': _chave(), 'Content-Type': 'application/json'}
    if mascara:
        cabecalhos['X-Goog-FieldMask'] = mascara

    dados = json.dumps(corpo).encode('utf-8') if corpo is not None else None
    espera = 1.0
    for tentativa in range(tentativas):
        req = urllib.request.Request(url, data=dados, headers=cabecalhos,
                                     method='POST' if dados else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode('utf-8', 'ignore')[:400]
            if e.code in (429, 500, 502, 503) and tentativa < tentativas - 1:
                time.sleep(espera)
                espera *= 2
                continue
            raise ErroDaAPI(f'HTTP {e.code}: {detalhe}') from e
        except urllib.error.URLError as e:
            if tentativa < tentativas - 1:
                time.sleep(espera)
                espera *= 2
                continue
            raise ErroDaAPI(f'rede: {e.reason}') from e


def procurar(nome, contexto='Barão Geraldo, Campinas, SP'):
    """Acha o lugar por nome. Devolve o dicionário do primeiro, ou None.

    O contexto vai na consulta e não como filtro geográfico de propósito: bar de
    bairro costuma ter homônimo em outra cidade, e "Bar do Zé Barão Geraldo
    Campinas" desempata melhor do que um raio em volta de uma coordenada que a
    gente ainda não tem.

    Só o primeiro resultado interessa: a lista de leads já foi conferida a pé, e
    escolher entre candidatos sem alguém olhando é como se grava o bar errado no
    lugar do certo.
    """
    corpo = {'textQuery': f'{nome} {contexto}'.strip(), 'languageCode': 'pt-BR',
             'maxResultCount': 1}
    mascara = ','.join(f'places.{c}' for c in CAMPOS)
    resposta = _pedir(f'{BASE}/places:searchText', corpo=corpo, mascara=mascara)
    lugares = resposta.get('places') or []
    return lugares[0] if lugares else None


def detalhes(place_id):
    """Ficha completa de um lugar já identificado."""
    mascara = ','.join(CAMPOS)
    return _pedir(f'{BASE}/places/{place_id}', mascara=mascara)


def baixar_foto(nome_da_foto, largura=1600, timeout=30):
    """Bytes da foto, pelo endpoint oficial.

    `nome_da_foto` é o campo `name` de um item de `photos`
    (`places/XXX/photos/YYY`). O endpoint responde 302 pro CDN; o urllib segue
    sozinho.

    Quem publica a foto precisa exibir a atribuição que veio junto
    (`authorAttributions`) — é condição de uso, e é por isso que
    `levantar_bares.py` grava `creditos.json` ao lado das imagens.
    """
    url = (f'{BASE}/{nome_da_foto}/media'
           f'?maxWidthPx={largura}&key={urllib.parse.quote(_chave())}')
    req = urllib.request.Request(url, headers={'User-Agent': 'AleroPrice/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
