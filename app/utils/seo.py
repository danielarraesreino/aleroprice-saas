"""Dados estruturados (JSON-LD) do site público — um lugar só, todo tenant.

Por que existe
--------------
Um bar não perde busca por ser feio: perde por não ser legível por máquina. Quem
lê o site hoje não é só o Google — é o AI Overview, o Perplexity e o ChatGPT, e
os três extraem *sinal estruturado*, não parágrafo bonito. Sem JSON-LD o bar
existe como imagem; com JSON-LD ele existe como fato: nome, endereço, telefone,
horário, nota, cardápio, agenda.

A referência de mercado que o dono do projeto admira (Café Container, Cambuí)
foi medida no navegador: zero JSON-LD, zero Open Graph, zero `<h1>`, sem meta
description. Bonito e ilegível. O plano é ganhar dessas casas por engenharia —
e isso só escala se o grafo for montado num lugar só, igual para os 76 bares que
já estão no banco e para todo bar que entrar depois.

A regra de ouro
---------------
**Campo ausente = chave ausente.** Nunca string vazia, nunca "None", nunca
placeholder, nunca default inventado. Um bar sem telefone não emite `telephone`;
um bar sem nota não emite `AggregateRating`. Marcar dado que não existe é pior
que não marcar nada: o Google trata schema mentiroso como spam estrutural, e uma
penalidade cai sobre o site do cliente, não sobre o nosso código.

Pelo mesmo motivo os itens de demonstração (`app/utils/vitrine.py` marca cada um
com `exemplo=True`) **nunca** entram no grafo: publicar show inventado como
`Event` seria mentir pro Google em nome do bar.

O que é montado
---------------
`Restaurant`/`BarOrPub` (NAP + horário + redes + mapa), `AggregateRating`,
`Menu`/`MenuItem`, `Review`, `Event`, `BreadcrumbList` e `WebSite`. O
`dateModified` sai de `SiteConfig.data_atualizacao` porque frescor é critério de
citação: página tocada nos últimos 30 dias é mais citada por IA generativa.

Validação: Google Rich Results Test + Schema.org Validator.
"""
import json
import re
import unicodedata
import urllib.parse
from datetime import date, datetime

# Única dependência interna deste módulo, e de propósito: preço aceito na tela
# e preço publicado no grafo têm que ser o mesmo julgamento. `formatacao_br` é
# folha (stdlib só), então o motor de SEO segue testável com dicts simples.
from app.utils.formatacao_br import ler_moeda

# Prefixo de assets do Flask (`static_url_path` padrão). Só é usado para
# absolutizar caminho relativo gravado no banco ("img/demo/x/capa.jpg"); URL
# absoluta e caminho que já começa com "/" passam intactos.
PREFIXO_STATIC = '/static/'

# Vibe -> tipo schema.org. Boteco e pub são bar antes de serem restaurante, e o
# `BarOrPub` é o que o Google usa pra montar o painel certo (horário de bar,
# não de almoço). O resto continua `Restaurant`.
TIPO_POR_VIBE = {
    'boteco': 'BarOrPub',
    'pub': 'BarOrPub',
    'hamburgueria': 'Restaurant',
    'praia': 'Restaurant',
}

# Vibe -> `servesCuisine`. Derivado da vibe (que o dono escolheu em /config-site),
# não adivinhado do nome. Vibe desconhecida não emite cozinha nenhuma.
COZINHA_POR_VIBE = {
    'boteco': 'Brasileira',
    'pub': 'Pub',
    'hamburgueria': 'Hambúrguer',
    'praia': 'Petiscos',
}

TAMANHO_META_MAX = 160   # onde o Google corta a descrição no resultado


# --------------------------------------------------------------- utilitários

def _limpo(valor):
    """Texto útil, ou None. É este filtro que faz valer a regra de ouro.

    Rejeita '', espaço em branco e a string 'None' — que aparece quando algum
    caminho fez `str(None)` antes de chegar aqui e é exatamente o lixo que não
    pode virar dado estruturado.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto == 'None':
        return None
    return texto


def _campo(obj, nome):
    """Lê `nome` de um objeto ORM ou de um dict, indiferentemente.

    Existe para o grafo aceitar tanto `Evento` (banco) quanto o dict que os
    testes montam, sem duplicar a montagem.
    """
    if isinstance(obj, dict):
        return obj.get(nome)
    return getattr(obj, nome, None)


def _sem_vazios(dados):
    """Remove recursivamente chave com valor vazio. Rede de segurança final."""
    if isinstance(dados, dict):
        limpo = {}
        for chave, valor in dados.items():
            valor = _sem_vazios(valor)
            if valor is None or valor == '' or valor == [] or valor == {}:
                continue
            limpo[chave] = valor
        return limpo
    if isinstance(dados, list):
        itens = [_sem_vazios(v) for v in dados]
        return [v for v in itens if v not in (None, '', [], {})]
    if isinstance(dados, str):
        return _limpo(dados)
    return dados


def _origem(url):
    """'https://bardavila.bar/bar/x' -> 'https://bardavila.bar'."""
    partes = urllib.parse.urlsplit(url or '')
    if not partes.scheme or not partes.netloc:
        return ''
    return f'{partes.scheme}://{partes.netloc}'


def _url_absoluta(caminho, origem):
    """Caminho de imagem do banco -> URL absoluta. Vazio devolve None."""
    caminho = _limpo(caminho)
    if not caminho:
        return None
    if caminho.startswith('http://') or caminho.startswith('https://'):
        return caminho
    if not caminho.startswith('/'):
        caminho = PREFIXO_STATIC + caminho
    return f'{origem}{caminho}' if origem else caminho


def _sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto)
                   if not unicodedata.combining(c))


def _iso(valor):
    """date/datetime -> ISO 8601. Qualquer outra coisa vira None (nunca chuta)."""
    if isinstance(valor, datetime):
        return valor.isoformat(timespec='seconds')
    if isinstance(valor, date):
        return valor.isoformat()
    return None


# ------------------------------------------------------------------- horário

_DIAS = {
    'seg': 'Mo', 'segunda': 'Mo', 'segundas': 'Mo',
    'ter': 'Tu', 'terca': 'Tu', 'tercas': 'Tu',
    'qua': 'We', 'quarta': 'We', 'quartas': 'We',
    'qui': 'Th', 'quinta': 'Th', 'quintas': 'Th',
    'sex': 'Fr', 'sexta': 'Fr', 'sextas': 'Fr',
    'sab': 'Sa', 'sabado': 'Sa', 'sabados': 'Sa',
    'dom': 'Su', 'domingo': 'Su', 'domingos': 'Su',
}
_TODOS_OS_DIAS = ('todos os dias', 'todo dia', 'diariamente', 'todos dias')

# "11h", "11h30", "11:30" — os três formatos que aparecem nos leads reais.
_HORA = re.compile(r'(\d{1,2})\s*(?:h|:)\s*(\d{2})?')
_INTERVALO_DE_DIAS = re.compile(r'^([a-z]+)(?:\s*-\s*|\s+a\s+|\s+ate\s+)([a-z]+)$')
_SEPARADOR_DE_BLOCO = re.compile(r'[·•;|\n]+')
_LIGACAO_DE_FAIXA = re.compile(r'\s+e\s+|,')


def _normalizar_horario(texto):
    """Tudo em minúscula, sem acento e com um traço só. 'Seg–Qui' -> 'seg-qui'."""
    texto = _sem_acento(str(texto)).lower()
    for travessao in ('–', '—', '‒', '−'):
        texto = texto.replace(travessao, '-')
    # \xa0 e o espaco 'duro' que vem colado quando o texto foi copiado do Google.
    return texto.replace('-feira', '').replace('\xa0', ' ')


def _hhmm(hora, minuto):
    hora, minuto = int(hora), int(minuto or 0)
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None
    return f'{hora:02d}:{minuto:02d}'


def _dias_schema(trecho):
    """'ter, qua e sex' -> 'Tu,We,Fr'. 'seg-qui' -> 'Mo-Th'. Falha -> None."""
    trecho = trecho.strip(' ,.-')
    # "Seg a sex das 11h às 15h" deixa um 'das'/'de' pendurado no fim, e
    # "Qua–Sex a partir das 18h" deixa a locução inteira. Os dias vêm antes;
    # o que sobra entre eles e a hora é ligação, não informação.
    trecho = re.sub(r'\s+a\s+partir\s+(d[aeo]s?\s*)?$', '', trecho)
    trecho = re.sub(r'\s+(das|de|dos|entre|a)$', '', trecho).strip(' ,.-')
    if not trecho:
        return None
    if any(marca in trecho for marca in _TODOS_OS_DIAS):
        return 'Mo-Su'

    partes = []
    for pedaco in re.split(r'\s+e\s+|,', trecho):
        pedaco = pedaco.strip()
        if not pedaco:
            continue
        # Dia sozinho ANTES do intervalo: sem isso "sabado" casaria como
        # "sab" + "a" + "do" e viraria um intervalo inexistente.
        if pedaco in _DIAS:
            partes.append(_DIAS[pedaco])
            continue
        faixa = _INTERVALO_DE_DIAS.match(pedaco)
        if faixa and faixa.group(1) in _DIAS and faixa.group(2) in _DIAS:
            partes.append(f'{_DIAS[faixa.group(1)]}-{_DIAS[faixa.group(2)]}')
            continue
        return None
    return ','.join(partes) or None


def _faixas_schema(trecho):
    """'11h30-14h e 18h-23h' -> ['11:30-14:00', '18:00-23:00']. Falha -> None.

    Faixa sem fim ("a partir das 18h") não vira nada: openingHours é um
    intervalo fechado, e inventar a hora de fechar é chutar o horário do bar.
    """
    faixas = []
    for pedaco in _LIGACAO_DE_FAIXA.split(trecho):
        horas = _HORA.findall(pedaco)
        if not horas:
            continue
        if len(horas) != 2:
            return None
        inicio = _hhmm(*horas[0])
        fim = _hhmm(*horas[1])
        if not inicio or not fim:
            return None
        faixas.append(f'{inicio}-{fim}')
    return faixas or None


_DIA_LONGO = {
    'Mo': 'Monday', 'Tu': 'Tuesday', 'We': 'Wednesday', 'Th': 'Thursday',
    'Fr': 'Friday', 'Sa': 'Saturday', 'Su': 'Sunday',
}
_ORDEM_DIAS = list(_DIA_LONGO)


def _expandir_dias(codigo):
    """'Th-Sa' -> ['Thursday','Friday','Saturday'] · 'We' -> ['Wednesday']."""
    nomes = []
    for parte in codigo.split(','):
        if '-' in parte:
            ini, fim = parte.split('-', 1)
            if ini not in _ORDEM_DIAS or fim not in _ORDEM_DIAS:
                return []
            i, f = _ORDEM_DIAS.index(ini), _ORDEM_DIAS.index(fim)
            faixa = (_ORDEM_DIAS[i:f + 1] if i <= f
                     else _ORDEM_DIAS[i:] + _ORDEM_DIAS[:f + 1])
            nomes += [_DIA_LONGO[d] for d in faixa]
        elif parte in _DIA_LONGO:
            nomes.append(_DIA_LONGO[parte])
        else:
            return []
    return nomes


def abertura_schema(texto):
    """Horário que só diz quando ABRE -> lista de OpeningHoursSpecification.

    Seis bares de Barão escrevem "Qua–Sex a partir das 18h": a hora de fechar
    simplesmente não é pública. `openingHours` (string) exige intervalo fechado,
    então esse texto virava silêncio — o bar ficava sem horário nenhum no
    Google, que é pior do que dizer só a abertura.

    `OpeningHoursSpecification` aceita `opens` sem `closes`, e é isso que se faz
    aqui: publica o que se sabe, cala o que não se sabe. Continua valendo a
    regra de não inventar — hora de fechamento nunca é estimada.

    Devolve [] quando o texto já tem intervalo completo (aí quem responde é
    `horario_schema`) ou quando não dá pra ler os dias com segurança.
    """
    texto = _limpo(texto)
    if not texto:
        return []

    especificacoes = []
    for bloco in _SEPARADOR_DE_BLOCO.split(_normalizar_horario(texto)):
        bloco = bloco.strip()
        if not bloco:
            continue
        primeira = _HORA.search(bloco)
        if not primeira:
            return []
        horas = _HORA.findall(bloco[primeira.start():])
        # dois horários = intervalo fechado: não é caso desta função
        if len(horas) != 1:
            return []
        abre = _hhmm(*horas[0])
        dias = _expandir_dias(_dias_schema(bloco[:primeira.start()]) or '')
        if not abre or not dias:
            return []
        especificacoes.append({
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': dias,
            'opens': abre,
        })
    return especificacoes


def horario_schema(texto):
    """Horário como o lead escreve -> `openingHours` do schema.org.

    "Seg–Qui 11h–00h · Sex–Sáb 11h–01h" vira
    ["Mo-Th 11:00-00:00", "Fr-Sa 11:00-01:00"].

    Tudo ou nada de propósito: se **qualquer** bloco do texto não converter com
    segurança, devolve lista vazia. Publicar metade do horário é pior que não
    publicar — o Google leria "fechado na quarta" para um bar que abre na
    quarta, e o cliente bate na porta trancada por causa do nosso parser.
    """
    texto = _limpo(texto)
    if not texto:
        return []

    resultado = []
    for bloco in _SEPARADOR_DE_BLOCO.split(_normalizar_horario(texto)):
        bloco = bloco.strip()
        if not bloco:
            continue
        primeira_hora = _HORA.search(bloco)
        if not primeira_hora:
            return []
        dias = _dias_schema(bloco[:primeira_hora.start()])
        faixas = _faixas_schema(bloco[primeira_hora.start():])
        if not dias or not faixas:
            return []
        resultado.extend(f'{dias} {faixa}' for faixa in faixas)

    # dict.fromkeys: remove repetição preservando a ordem em que o bar escreveu.
    return list(dict.fromkeys(resultado))


# ------------------------------------------------------------------ endereço

_UFS = {'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS',
        'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC',
        'SE', 'SP', 'TO'}
_CEP = re.compile(r'\b(\d{5})-?(\d{3})\b')
_UF_NO_FIM = re.compile(r'[-–—/(,]\s*([A-Za-z]{2})\s*\)?\s*$')


def endereco_schema(texto):
    """Endereço em uma linha -> `PostalAddress`. Sem texto, devolve None.

    "Av. Santa Isabel, 57 - Barão Geraldo, Campinas - SP, 13084-012" vira
    streetAddress/addressLocality/addressRegion/postalCode/addressCountry.

    O que não parsear com certeza vira **só** `streetAddress` com o texto
    inteiro. É o comportamento certo: endereço numa linha ainda é endereço
    válido pro Google, enquanto adivinhar a cidade a partir de um bairro
    ("Av. Prof. Atílio Martini, 940 — Barão Geraldo") plantaria NAP errado, que
    é justamente o que derruba ranking local.

    O bairro fica no `streetAddress` junto com a rua e o número: é a linha de
    entrega brasileira, e `addressLocality` no schema é o município.
    """
    texto = _limpo(texto)
    if not texto:
        return None

    inteiro = {'@type': 'PostalAddress', 'streetAddress': texto}

    resto = texto
    cep = None
    achou_cep = _CEP.search(resto)
    if achou_cep:
        cep = f'{achou_cep.group(1)}-{achou_cep.group(2)}'
        resto = (resto[:achou_cep.start()] + resto[achou_cep.end():])
    resto = resto.strip(' ,;-–—')

    achou_uf = _UF_NO_FIM.search(resto)
    if not achou_uf or achou_uf.group(1).upper() not in _UFS:
        return inteiro
    uf = achou_uf.group(1).upper()

    resto = resto[:achou_uf.start()].strip(' ,;-–—')
    if ',' not in resto:
        return inteiro

    logradouro, _, cidade = resto.rpartition(',')
    logradouro = logradouro.strip(' ,;-–—')
    cidade = cidade.strip(' ,;-–—')
    if not logradouro or not cidade:
        return inteiro

    endereco = {
        '@type': 'PostalAddress',
        'streetAddress': logradouro,
        'addressLocality': cidade,
        'addressRegion': uf,
        # País só sai quando a UF foi reconhecida — é dedução da UF brasileira,
        # não default carimbado em cima de endereço que não parseou.
        'addressCountry': 'BR',
    }
    if cep:
        endereco['postalCode'] = cep
    return endereco


# -------------------------------------------------------------------- rating

def _nota_decimal(valor):
    """'4,7' -> 4.7. Brasileiro escreve com vírgula; JSON-LD exige ponto."""
    texto = _limpo(valor)
    if texto is None:
        return None
    achou = re.search(r'(\d{1,2})(?:[.,](\d{1,2}))?', texto)
    if not achou:
        return None
    nota = float(f'{achou.group(1)}.{achou.group(2) or 0}')
    return nota if 0 < nota <= 5 else None


def _avaliacao_agregada(site):
    """`AggregateRating` — só quando a nota existe de verdade."""
    nota = _nota_decimal(site.get('nota_google'))
    if nota is None:
        return None
    agregado = {'@type': 'AggregateRating', 'ratingValue': nota, 'bestRating': 5}
    try:
        quantidade = int(site.get('qtd_avaliacoes') or 0)
    except (TypeError, ValueError):
        quantidade = 0
    if quantidade > 0:
        agregado['reviewCount'] = quantidade
    return agregado


# ----------------------------------------------------------- meta description

def meta_descricao(site, rest=None):
    """Descrição na faixa de 140–160 caracteres, só com dado real do bar.

    Ordem de importância: quem é (nome + descritor), como é (tagline), onde fica
    (cidade) e a prova social (nota). Vai empilhando enquanto couber em 160 —
    o ponto em que o Google corta. Bar com pouco cadastrado sai mais curto que
    140: o alvo é o teto, nunca encher linguiça pra bater um número.

    A nota fica por último de propósito. A estrela já aparece sozinha no
    resultado, vinda do `AggregateRating`; o que o Google não tem de outra fonte
    é o que a casa é e onde fica.

    Sem nada além do nome, devolve None e o template omite a tag: descrição
    genérica não é melhor que descrição nenhuma, e a alternativa (o Google
    montar o trecho sozinho a partir da página) costuma render mais.
    """
    site = site or {}
    nome = _limpo(site.get('nome')) or _limpo(_campo(rest, 'nome'))
    if not nome:
        return None

    descritor = _limpo(site.get('descritor'))
    tagline = _limpo(site.get('tagline'))
    cidade = _limpo(site.get('cidade_uf'))
    nota = _nota_decimal(site.get('nota_google'))

    abertura = f'{nome} — {descritor}.' if descritor else f'{nome}.'

    extras = []
    if tagline:
        extras.append(tagline if tagline.endswith(('.', '!', '?')) else f'{tagline}.')
    if cidade and cidade.lower() not in abertura.lower():
        extras.append(f'Em {cidade}.')
    if nota is not None:
        texto_nota = _limpo(site.get('nota_google'))
        try:
            quantidade = int(site.get('qtd_avaliacoes') or 0)
        except (TypeError, ValueError):
            quantidade = 0
        extras.append(f'Nota {texto_nota} no Google com {quantidade} avaliações.'
                      if quantidade > 0 else f'Nota {texto_nota} no Google.')

    texto = abertura
    usou_extra = False
    for parte in extras:
        if len(texto) + 1 + len(parte) > TAMANHO_META_MAX:
            continue
        texto = f'{texto} {parte}'
        usou_extra = True

    # Só o nome não descreve nada — nesse caso a tag não vale a linha de HTML.
    if not usou_extra and not descritor:
        return None
    return texto


# ----------------------------------------------------------------- o grafo

def _preco_schema(valor):
    """Preço do prato -> string com ponto decimal ('18.50'), ou None.

    Duas notações, uma verdade: o cliente lê `R$ 18,50` na tela e o Google lê
    `"price": "18.50"` no grafo. Schema.org exige ponto decimal e nada de
    símbolo de moeda dentro de `price` (a moeda vai em `priceCurrency`) —
    mandar "R$ 18,50" ali é preço inválido, que o Rich Results ignora ou
    reprova.

    Quem decide o que conta como preço é `ler_moeda`, o mesmo juiz dos dois
    formulários: vazio, zero, negativo e lixo não são preço. Assim o grafo não
    tem como anunciar `price: "0.00"` num prato sem preço — que seria a versão
    estruturada de mentir pro Google, exatamente o que a regra de ouro proíbe.
    """
    valor = ler_moeda(valor)
    return None if valor is None else f'{valor:.2f}'


def _pedacos_do_cardapio(dishes, origem, id_cardapio):
    itens = []
    for i, prato in enumerate(dishes or [], start=1):
        nome = _limpo(_campo(prato, 'nome'))
        if not nome:
            continue
        item = {'@type': 'MenuItem', '@id': f'{id_cardapio}-{i}', 'name': nome}
        descricao = _limpo(_campo(prato, 'descricao'))
        if descricao:
            item['description'] = descricao
        imagem = _url_absoluta(_campo(prato, 'img') or _campo(prato, 'imagem'), origem)
        if imagem:
            item['image'] = imagem
        # `offers` é o que faz o preço aparecer no resultado de busca. Só entra
        # quando existe preço — item sem preço sai sem a chave, não com Offer
        # vazio (que `_sem_vazios` limparia, mas que nem deve ser montado).
        preco = _preco_schema(_campo(prato, 'preco'))
        if preco:
            item['offers'] = {'@type': 'Offer', 'price': preco,
                              'priceCurrency': 'BRL'}
        itens.append(item)
    return itens


def menu_schema(nome, dishes, url_canonica, url_cardapio=None):
    """Nó `Menu` deste bar, ou None quando não há prato cadastrado.

    Um só cardápio, um só `@id` (`<canônica>#cardapio`) — o mesmo emitido pela
    landing e pela página `/bar/<slug>/cardapio`. Se cada página inventasse o
    próprio identificador, o mesmo cardápio viraria duas entidades no grafo.

    `url` é o que muda: a documentação do schema.org pede que `hasMenu` leve a
    um cardápio acessível em HTML, e a partir de agora existe um — a página do
    QR. Sem ela (bar sem slug), sobra a âncora da seção dentro da landing, que
    é o que sempre houve.
    """
    origem = _origem(url_canonica)
    id_cardapio = f'{url_canonica}#cardapio'
    itens = _pedacos_do_cardapio(dishes, origem, id_cardapio)
    if not itens:
        return None
    return {
        '@type': 'Menu',
        '@id': id_cardapio,
        'name': f'Cardápio — {nome}' if nome else 'Cardápio',
        'url': url_cardapio or id_cardapio,
        'inLanguage': 'pt-BR',
        'hasMenuItem': itens,
    }


def cardapio_estruturado(rest, site, dishes, url_canonica, url_cardapio=None):
    """Grafo da página de cardápio: o cardápio e o bar a que ele pertence.

    Deliberadamente menor que `dados_estruturados`. Esta página é o cardápio —
    repetir aqui endereço, horário e nota seria duplicar em duas URLs os fatos
    que a landing já afirma, com o risco de as duas divergirem no dia em que
    uma for editada. O `Restaurant` entra só como referência (`@id` + nome),
    para que o `Menu` tenha dono e o robô saiba de que casa é este cardápio.
    """
    site = dict(site or {})
    nome = _limpo(site.get('nome')) or _limpo(_campo(rest, 'nome'))
    cardapio = menu_schema(nome, dishes, url_canonica, url_cardapio)
    if cardapio is None:
        return None

    id_restaurante = f'{url_canonica}#restaurante'
    cardapio['isPartOf'] = {'@id': id_restaurante}
    casa = {
        '@type': TIPO_POR_VIBE.get(
            _limpo(site.get('vibe')) or _limpo(_campo(_campo(rest, 'site_config'), 'vibe')),
            'Restaurant'),
        '@id': id_restaurante,
        'name': nome,
        'url': url_canonica,
        'hasMenu': {'@id': cardapio['@id']},
    }
    return _sem_vazios({'@context': 'https://schema.org', '@graph': [casa, cardapio]})


def _pedacos_de_avaliacao(reviews, url_canonica, id_restaurante):
    nos = []
    for i, avaliacao in enumerate(reviews or [], start=1):
        autor = _limpo(_campo(avaliacao, 'autor'))
        texto = _limpo(_campo(avaliacao, 'texto'))
        if not autor or not texto:
            continue
        no = {
            '@type': 'Review',
            '@id': f'{url_canonica}#avaliacao-{i}',
            'author': {'@type': 'Person', 'name': autor},
            'reviewBody': texto,
            'itemReviewed': {'@id': id_restaurante},
        }
        try:
            estrelas = int(_campo(avaliacao, 'estrelas') or 0)
        except (TypeError, ValueError):
            estrelas = 0
        if 1 <= estrelas <= 5:
            no['reviewRating'] = {'@type': 'Rating', 'ratingValue': estrelas,
                                  'bestRating': 5}
        nos.append(no)
    return nos


def _pedacos_de_evento(eventos, url_canonica, id_restaurante):
    """Eventos reais do bar. Os de demonstração ficam de fora, sempre.

    `app/utils/vitrine.py` injeta agenda de exemplo na prévia comercial pra que
    o vendedor consiga mostrar o recurso. Na tela isso é honesto (cada item leva
    selo de exemplo e a página é declaradamente prévia); em JSON-LD não seria:
    o Google não lê selo, ele lê `Event`. Show inventado publicado como dado
    estruturado é mentira em nome do bar.
    """
    nos = []
    for i, evento in enumerate(eventos or [], start=1):
        if _campo(evento, 'exemplo'):
            continue
        titulo = _limpo(_campo(evento, 'titulo'))
        quando = _iso(_campo(evento, 'data'))
        if not titulo or not quando:
            continue
        hora = _limpo(_campo(evento, 'hora'))
        if hora and re.fullmatch(r'\d{2}:\d{2}', hora):
            quando = f'{quando}T{hora}:00'
        no = {
            '@type': 'Event',
            '@id': f'{url_canonica}#evento-{i}',
            'name': titulo,
            'startDate': quando,
            'eventStatus': 'https://schema.org/EventScheduled',
            'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
            'location': {'@id': id_restaurante},
            'organizer': {'@id': id_restaurante},
        }
        descricao = _limpo(_campo(evento, 'descricao'))
        if descricao:
            no['description'] = descricao
        nos.append(no)
    return nos


def _comodidades(servicos):
    """'Wi-Fi, estacionamento' -> amenityFeature. Sem campo, sem chave."""
    texto = _limpo(servicos)
    if not texto:
        return []
    nomes = [n.strip() for n in re.split(r'[,;·]', texto) if n.strip()]
    return [{'@type': 'LocationFeatureSpecification', 'name': n, 'value': True}
            for n in nomes]


def dados_estruturados(rest, site, dishes, reviews, eventos, url_canonica,
                       url_cardapio=None):
    """Grafo JSON-LD completo deste bar, pronto pra `json.dumps`.

    Recebe exatamente o que `_render_landing` já montou — nada é consultado no
    banco aqui, o que deixa a função testável com dicts simples e impede que o
    motor de SEO vaze query sem filtro de tenant.

    Toda chave é condicional: o bar que só tem nome sai com um grafo pequeno e
    verdadeiro, não com um grafo grande e falso.
    """
    site = dict(site or {})
    cfg = _campo(rest, 'site_config')
    origem = _origem(url_canonica)

    nome = _limpo(site.get('nome')) or _limpo(_campo(rest, 'nome'))
    vibe = _limpo(site.get('vibe')) or _limpo(_campo(cfg, 'vibe'))

    id_restaurante = f'{url_canonica}#restaurante'
    id_cardapio = f'{url_canonica}#cardapio'

    restaurante = {
        '@type': TIPO_POR_VIBE.get(vibe, 'Restaurant'),
        '@id': id_restaurante,
        'name': nome,
        'url': url_canonica,
    }

    descricao = _limpo(site.get('tagline')) or _limpo(site.get('descritor'))
    if descricao:
        restaurante['description'] = descricao

    # Imagem: capa do bar primeiro, depois as fotos do cardápio. Só as que
    # existem — a capa de outro bar seria pior que nenhuma foto.
    imagens = [_url_absoluta(site.get('hero_foto'), origem)]
    imagens += [_url_absoluta(_campo(d, 'img'), origem) for d in (dishes or [])]
    imagens = list(dict.fromkeys([i for i in imagens if i]))[:6]
    if imagens:
        restaurante['image'] = imagens

    telefone = _limpo(site.get('telefone_exibicao'))
    if not telefone:
        whatsapp = _limpo(site.get('whatsapp'))
        # whatsapp é gravado só em dígitos com DDI (5519999779942) — vira E.164.
        if whatsapp and whatsapp.isdigit():
            telefone = f'+{whatsapp}'
    if telefone:
        restaurante['telephone'] = telefone

    endereco = endereco_schema(site.get('endereco'))
    if endereco:
        restaurante['address'] = endereco

    cozinha = COZINHA_POR_VIBE.get(vibe)
    if cozinha:
        restaurante['servesCuisine'] = cozinha

    # Não existe campo de faixa de preço no CMS hoje, então na prática esta
    # chave não sai. Fica montada pra quando existir — o dia em que sair, sai
    # de dado do bar e não de estimativa nossa.
    faixa_preco = _limpo(site.get('faixa_preco'))
    if faixa_preco:
        restaurante['priceRange'] = faixa_preco

    # Intervalo fechado vira `openingHours`. Quando a casa só divulga a
    # abertura ("Qua–Sex a partir das 18h"), cai em
    # `openingHoursSpecification` com `opens` e sem `closes`: publica o que se
    # sabe em vez de deixar o bar sem horário nenhum no Google.
    horarios = horario_schema(site.get('horario'))
    if horarios:
        restaurante['openingHours'] = horarios
    else:
        aberturas = abertura_schema(site.get('horario'))
        if aberturas:
            restaurante['openingHoursSpecification'] = aberturas

    redes = [_limpo(site.get('instagram_url')), _limpo(site.get('facebook_url'))]
    redes = [r for r in redes if r]
    if redes:
        restaurante['sameAs'] = redes

    mapa = _limpo(site.get('maps_query'))
    if mapa:
        restaurante['hasMap'] = mapa if mapa.startswith(('http://', 'https://')) else (
            'https://www.google.com/maps/search/?api=1&query='
            + urllib.parse.quote(mapa)
        )

    comodidades = _comodidades(site.get('servicos'))
    if comodidades:
        restaurante['amenityFeature'] = comodidades

    agregado = _avaliacao_agregada(site)
    if agregado:
        restaurante['aggregateRating'] = agregado

    grafo = [restaurante]

    # Cardápio: `hasMenu` aponta pro nó do cardápio em vez de embutir o
    # cardápio inteiro dentro do Restaurant — é o que o Google pede pra render
    # o cardápio no resultado. O nó, por sua vez, leva o robô à página de
    # cardápio em HTML (`url_cardapio`), que é o que a documentação do
    # schema.org recomenda; sem ela, à âncora da seção, como sempre foi.
    cardapio = menu_schema(nome, dishes, url_canonica, url_cardapio)
    itens = cardapio['hasMenuItem'] if cardapio else []
    if cardapio:
        restaurante['hasMenu'] = {'@id': id_cardapio}
        grafo.append(cardapio)

    grafo.extend(_pedacos_de_avaliacao(reviews, url_canonica, id_restaurante))
    grafo.extend(_pedacos_de_evento(eventos, url_canonica, id_restaurante))

    trilha = [{'@type': 'ListItem', 'position': 1, 'name': nome or 'Início',
               'item': url_canonica}]
    if itens:
        trilha.append({'@type': 'ListItem', 'position': 2, 'name': 'Cardápio',
                       'item': id_cardapio})
    grafo.append({'@type': 'BreadcrumbList', '@id': f'{url_canonica}#trilha',
                  'itemListElement': trilha})

    site_web = {
        '@type': 'WebSite',
        '@id': f'{url_canonica}#site',
        'url': url_canonica,
        'inLanguage': 'pt-BR',
        'publisher': {'@id': id_restaurante},
    }
    if nome:
        site_web['name'] = nome

    # Frescor: o Perplexity cita mais página tocada nos últimos 30 dias, e
    # `data_atualizacao` é o único carimbo real que temos. Vai no WebSite
    # porque `dateModified` é propriedade de CreativeWork — pendurar em
    # Restaurant seria schema inválido.
    atualizado = _iso(site.get('data_atualizacao') or _campo(cfg, 'data_atualizacao'))
    if atualizado:
        site_web['dateModified'] = atualizado
    grafo.append(site_web)

    return _sem_vazios({'@context': 'https://schema.org', '@graph': grafo})


def serializar(dados):
    """JSON-LD como string pronta pro `<script type="application/ld+json">`.

    `ensure_ascii=False` porque acento em UTF-8 é menor e mais legível que
    escape. O `<` vira `\\u003c` porque o conteúdo é escrito pelo dono do bar:
    um "</script>" na tagline fecharia a tag e viraria XSS no site dele.
    """
    return (json.dumps(dados, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c')
            .replace('>', '\\u003e')
            .replace('&', '\\u0026'))
