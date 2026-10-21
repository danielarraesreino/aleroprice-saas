"""Modelos (layouts) do site público.

Mesma ideia do `temas.py` e do `copy_site.py`, um nível acima: `tema` é a cor,
`vibe` é o texto, e **modelo é o esqueleto** — quais seções a página tem, em
que ordem e com que cara. Uma espetaria e uma cervejaria artesanal não vendem
com a mesma página, por mais que você troque a paleta.

É um dicionário fechado de propósito: o vendedor escolhe entre 6 opções que a
gente sabe que funcionam, não desenha uma página nova por cliente.

`classico` é a landing que já está no ar (`site/landing.html`), intocada — quem
não escolher nada continua exatamente como está. Os outros apontam para
`site/modelos/<nome>.html`.

Fluxo de venda: o vendedor abre o site do bar com `?modelo=craft` na URL e
mostra a opção na hora, sem gravar nada. O dono escolhe, aí sim salva no
SiteConfig.
"""

MODELO_PADRAO = 'classico'

MODELOS = {
    'classico': {
        'label': 'Clássico',
        'descricao': 'Hero grande, cardápio, história, avaliações, agenda e reserva. '
                     'A página completa, na ordem que já vende hoje.',
        'para': 'Pro bar que faz um pouco de tudo e não quer errar.',
        'arquivo': 'site/landing.html',
    },

    'craft': {
        'label': 'Craft',
        'descricao': 'Chopes e rótulos em destaque logo no topo, com espaço pra '
                     'descrever cada torneira e o que combina com o quê.',
        'para': 'Pra cervejaria artesanal, taproom e bar de chope.',
        'arquivo': 'site/modelos/craft.html',
    },

    'tradicional': {
        'label': 'Tradicional',
        'descricao': 'A história da casa vem primeiro: fundação, família, fotos '
                     'antigas e os pratos que não saem do cardápio desde sempre.',
        'para': 'Pra casa antiga, com história e freguês de anos.',
        'arquivo': 'site/modelos/tradicional.html',
    },

    'autoral': {
        'label': 'Autoral',
        'descricao': 'Foto grande de prato mandando na página, cardápio em '
                     'destaque e a assinatura de quem cozinha.',
        'para': 'Pra cozinha autoral, bistrô e chef que assina o prato.',
        'arquivo': 'site/modelos/autoral.html',
    },

    'noturno': {
        'label': 'Noturno',
        'descricao': 'Agenda de shows no topo, clima de noite, e reserva de mesa '
                     'sempre à mão pra quem chega pelo evento.',
        'para': 'Pra casa de música ao vivo, com agenda toda semana.',
        'arquivo': 'site/modelos/noturno.html',
    },

    'brasa': {
        'label': 'Brasa',
        'descricao': 'Porções e cortes na frente, com preço e tamanho claros — a '
                     'página inteira gira em torno do que sai da grelha.',
        'para': 'Pra espetaria, churrascaria e casa de porção.',
        'arquivo': 'site/modelos/brasa.html',
    },
}


def modelo_valido(nome):
    return nome in MODELOS


def arquivo_do_modelo(nome):
    """Template a renderizar. Nome desconhecido cai no padrão, em silêncio.

    Fallback silencioso é de propósito: um modelo removido (ou um `?modelo=`
    digitado errado) não pode tirar o site do bar do ar — ele volta pro
    clássico, que sempre existe.
    """
    modelo = MODELOS.get(nome or MODELO_PADRAO) or MODELOS[MODELO_PADRAO]
    return modelo['arquivo']


def opcoes_de_modelo():
    """Lista pro seletor: o vendedor lê o `para` e sabe qual mostrar."""
    return [
        {'valor': chave, 'label': m['label'], 'descricao': m['descricao'], 'para': m['para']}
        for chave, m in MODELOS.items()
    ]


# --------------------------------------------------------------------------
# Modelos do hotsite de ARTESÃO (tipo_negocio='artesao')
#
# Mesma ideia dos modelos de bar: o esqueleto muda (hero, jeito de mostrar o
# que vende, tipo, paleta), não só a cor. Ficam fora de `MODELOS` de propósito:
# bar e artesão têm catálogos separados, e um `?modelo=` de um não vale no outro.
# Todos estendem `site/modelos/artesao/_base.html` (menu, encomenda, contato).
# --------------------------------------------------------------------------

MODELO_ARTESAO_PADRAO = 'vitrine'

MODELOS_ARTESAO = {
    'vitrine': {
        'label': 'Vitrine',
        'descricao': 'Foto do produto inteira, rótulo preto por cima e vitrine por categoria. '
                     'Funciona melhor quando há boas fotos.',
        'para': 'Pra charcutaria, conservas e quem tem foto forte de produto.',
        'arquivo': 'site/modelos/artesao/vitrine.html',
    },
    'atelie': {
        'label': 'Ateliê',
        'descricao': 'Nome gigante, bloco de cor com o que a pessoa faz e catálogo em '
                     'lista editorial. Não depende de foto para ficar bonito.',
        'para': 'Pra peças feitas à mão: crochê, cerâmica, madeira, joia, costura, mosaico.',
        'arquivo': 'site/modelos/artesao/atelie.html',
    },
    'cozinha': {
        'label': 'Cozinha',
        'descricao': 'Campo de cor cheio, horário em destaque e cardápio da barraca em '
                     'linhas grandes, com botão de pedir em cada prato.',
        'para': 'Pra comida na feira: pão, pizza, empada, risoto, biscoito, vegano.',
        'arquivo': 'site/modelos/artesao/cozinha.html',
    },
    'jardim': {
        'label': 'Jardim',
        'descricao': 'Verdes e cantos macios, com o que a pessoa cultiva ou monta em '
                     'etiquetas, e um catálogo leve.',
        'para': 'Pra plantas, terrários, kokedamas e quem trabalha com natureza.',
        'arquivo': 'site/modelos/artesao/jardim.html',
    },
    'ritual': {
        'label': 'Ritual',
        'descricao': 'Noite e dourado, título centralizado e serviços em lista, com '
                     'chamada para agendar ou conversar.',
        'para': 'Pra incenso, cristais, tarô, terapias e mandalas.',
        'arquivo': 'site/modelos/artesao/ritual.html',
    },
}

# Palavras da categoria -> modelo. A primeira que casar vale; sem casar, ateliê
# (a maioria da feira é peça feita à mão).
_CATEGORIA_PARA_MODELO = (
    ('vitrine', ('charcut', 'defumad', 'conserva', 'embutid')),
    ('cozinha', ('comida', 'empada', 'risot', 'pizza', 'pao', 'padaria', 'biscoito', 'cookie',
                 'culinaria', 'vegan', 'lanche', 'doce', 'bolo', 'quiche')),
    ('jardim', ('planta', 'terrario', 'kokedama', 'jardim', 'horta', 'suculenta')),
    ('ritual', ('incenso', 'esoter', 'taro', 'cristal', 'terapia', 'reiki', 'astrolog')),
)


def modelo_artesao_valido(nome):
    return nome in MODELOS_ARTESAO


def arquivo_do_modelo_artesao(nome):
    """Template do modelo; nome desconhecido cai na vitrine, em silêncio."""
    return (MODELOS_ARTESAO.get(nome) or MODELOS_ARTESAO[MODELO_ARTESAO_PADRAO])['arquivo']


def modelo_para_categoria(categoria):
    """Sugere o modelo pela categoria que o expositor declarou ('Pão artesanal' -> cozinha)."""
    import unicodedata
    base = unicodedata.normalize('NFKD', categoria or '')
    texto = ''.join(c for c in base if not unicodedata.combining(c)).casefold()
    for modelo, palavras in _CATEGORIA_PARA_MODELO:
        if any(p in texto for p in palavras):
            return modelo
    return 'atelie'


def opcoes_de_modelo_artesao():
    return [{'valor': k, 'label': m['label'], 'descricao': m['descricao'], 'para': m['para']}
            for k, m in MODELOS_ARTESAO.items()]


def catalogo_de_modelos(tipo):
    """(dicionário de modelos, modelo padrão, opções p/ seletor) do tipo de negócio."""
    if tipo == 'artesao':
        return MODELOS_ARTESAO, MODELO_ARTESAO_PADRAO, opcoes_de_modelo_artesao()
    return MODELOS, MODELO_PADRAO, opcoes_de_modelo()
