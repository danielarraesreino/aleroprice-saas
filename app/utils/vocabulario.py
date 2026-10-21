"""Vocabulário por tipo de negócio: o mesmo app fala "cardápio" com o bar e
"produtos" com o artesão.

Só rótulos e o `@type` do schema.org. Estrutura de dados e layout não passam
por aqui. Tipo desconhecido ou NULL (linha antiga) cai em 'bar', então nada do
que já está no ar muda.
"""

TIPO_PADRAO = 'bar'
TIPOS = ('bar', 'artesao')

VOCABULARIO = {
    'bar': {
        'barraca': 'Barraca',
        'cardapio': 'Cardápio',
        'cardapio_completo': 'Ver cardápio completo',
        'item': 'Prato',
        'itens': 'Pratos',
    },
    'artesao': {
        'barraca': 'Ateliê',
        'cardapio': 'Produtos',
        'cardapio_completo': 'Ver todos os produtos',
        'item': 'Peça',
        'itens': 'Peças',
    },
}

# `CraftsStore` não existe no schema.org; `Store` é o tipo válido mais próximo.
SCHEMA_ARTESAO = 'Store'


def tipo_do(rest):
    tipo = getattr(rest, 'tipo_negocio', None)
    return tipo if tipo in TIPOS else TIPO_PADRAO


def rotulo(rest_ou_tipo, chave):
    """Rótulo de `chave` para o negócio (objeto com tipo_negocio ou o próprio tipo)."""
    tipo = rest_ou_tipo if isinstance(rest_ou_tipo, str) else tipo_do(rest_ou_tipo)
    tabela = VOCABULARIO.get(tipo, VOCABULARIO[TIPO_PADRAO])
    return tabela.get(chave) or VOCABULARIO[TIPO_PADRAO][chave]


def tipo_schema(tipo_negocio, padrao):
    """`@type` do grafo JSON-LD. Bar devolve `padrao` (o que a vibe já decidia)."""
    return SCHEMA_ARTESAO if tipo_negocio == 'artesao' else padrao
