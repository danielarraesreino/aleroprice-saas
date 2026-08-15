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
