"""Presets de tema do site público.

Cada bar escolhe um preset em /config-site. Não é CSS livre: são paletas
fechadas, para que o dono do bar não consiga deixar o próprio site feio (e
transformar isso em chamado de suporte).

O template `site/landing.html` já define a paleta 'boteco-ambar' no seu :root
(dark) e em :root[data-theme="light"]. Os presets aqui SOBRESCREVEM essas
variáveis. Consequência importante: o tema default não injeta nada, então o
site do Bar da Vila continua idêntico ao que está no ar hoje.

Para adicionar um bar novo com cara própria, adicione um preset aqui — não
mexa no template.
"""

TEMA_PADRAO = 'boteco-ambar'

# Variáveis que cada preset pode definir. Qualquer uma omitida cai no valor do
# :root do template.
_VARS = ('--ink', '--ink-2', '--wood', '--cream', '--cream-dim',
         '--amber', '--ember', '--gold', '--neon', '--green')

TEMAS = {
    'boteco-ambar': {
        'label': 'Boteco Âmbar',
        'descricao': 'Madeira, brasa e âmbar. O padrão — cara de buteco de família.',
        'amostra': ('#100a06', '#ffb43d', '#ff6a2b'),
        # Vazio de propósito: é o que já está no :root do template.
        'dark': {},
        'light': {},
    },

    'neon-noite': {
        'label': 'Neon Noite',
        'descricao': 'Preto, magenta e ciano. Hamburgueria, rock, balada.',
        'amostra': ('#0b0710', '#ff2e88', '#25e0e0'),
        'dark': {
            '--ink': '#0b0710',
            '--ink-2': '#150d1e',
            '--wood': '#241535',
            '--cream': '#f2e9ff',
            '--cream-dim': '#a99bc4',
            '--amber': '#ff2e88',
            '--ember': '#25e0e0',
            '--gold': '#c86bff',
            '--neon': '#ff2e88',
            '--green': '#25e0e0',
        },
        'light': {
            '--ink': '#f6f1ff',
            '--ink-2': '#ebe2f7',
            '--wood': '#ded1f0',
            '--cream': '#1b1026',
            '--cream-dim': '#5c4a75',
            '--amber': '#c4176a',
            '--ember': '#0f8f8f',
            '--gold': '#7d2fb5',
            '--neon': '#c4176a',
            '--green': '#0f8f8f',
        },
    },

    'pub-escuro': {
        'label': 'Pub Escuro',
        'descricao': 'Verde garrafa, couro e latão. Pub inglês, cerveja artesanal.',
        'amostra': ('#0c1210', '#c9a227', '#8f2f2f'),
        'dark': {
            '--ink': '#0c1210',
            '--ink-2': '#131c18',
            '--wood': '#1d2b23',
            '--cream': '#eee6d2',
            '--cream-dim': '#a99f88',
            '--amber': '#c9a227',
            '--ember': '#8f2f2f',
            '--gold': '#b08d3a',
            '--neon': '#d8b44a',
            '--green': '#5f8c5a',
        },
        'light': {
            '--ink': '#f0ede2',
            '--ink-2': '#e5e0d0',
            '--wood': '#d5cdb8',
            '--cream': '#16211c',
            '--cream-dim': '#4e5a50',
            '--amber': '#8a6d12',
            '--ember': '#7a2626',
            '--gold': '#7d6321',
            '--neon': '#6d5510',
            '--green': '#3f6a3a',
        },
    },

    'praia-claro': {
        'label': 'Praia Claro',
        'descricao': 'Turquesa, areia e coral. Quiosque, petisco de praia, verão.',
        'amostra': ('#062a2e', '#00d1c1', '#ff7a59'),
        'dark': {
            '--ink': '#062a2e',
            '--ink-2': '#0a3a3f',
            '--wood': '#0f4c52',
            '--cream': '#f3efe2',
            '--cream-dim': '#a9c4c2',
            '--amber': '#00d1c1',
            '--ember': '#ff7a59',
            '--gold': '#f2c14e',
            '--neon': '#3ee8d6',
            '--green': '#5fbf8f',
        },
        'light': {
            '--ink': '#f7f3e8',
            '--ink-2': '#eae5d6',
            '--wood': '#d9e3df',
            '--cream': '#093036',
            '--cream-dim': '#4a6b6b',
            '--amber': '#00857a',
            '--ember': '#d9502f',
            '--gold': '#b8862a',
            '--neon': '#00756c',
            '--green': '#3f8a63',
        },
    },
}


def tema_valido(nome):
    return nome in TEMAS


def css_do_tema(nome):
    """Devolve o CSS que sobrescreve a paleta, ou '' para o tema padrão.

    String vazia é o caminho feliz do Bar da Vila: nada é injetado e o site
    fica byte a byte igual ao atual.
    """
    tema = TEMAS.get(nome or TEMA_PADRAO)
    if not tema:
        return ''

    def bloco(seletor, mapa):
        if not mapa:
            return ''
        linhas = ''.join(f'{k}:{v};' for k, v in mapa.items() if k in _VARS)
        return f'{seletor}{{{linhas}}}' if linhas else ''

    return bloco(':root', tema['dark']) + bloco(':root[data-theme="light"]', tema['light'])


def opcoes_de_tema():
    """Lista pro seletor do /config-site."""
    return [
        {'valor': chave, 'label': t['label'], 'descricao': t['descricao'], 'amostra': t['amostra']}
        for chave, t in TEMAS.items()
    ]
