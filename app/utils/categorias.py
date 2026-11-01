"""Categorias de produto da Feira: o que o expositor vende, em dois níveis.

De onde veio a lista
--------------------
Do levantamento de nov/2026 (`FEIRADEBARAO/levantamento-2026-11/categorias.md`):
194 perfis cruzados entre o @feiradebarao, o site de 2022 e as listas da
organização. Cada subcategoria aqui tem pelo menos um expositor de verdade
vendendo aquilo — não é catálogo inventado.

O texto continua sendo do expositor
-----------------------------------
`ProdutoSite.categoria` agrupa as seções do hotsite: quem escreve "Geleias" e
"Conservas" quer duas seções, não uma "Geleias, molhos e conservas". Por isso
nada aqui regrava o que ele escreveu. O cadastro só sugere (`opcoes`) e unifica
a grafia (`canonizar`); a subcategoria é deduzida na leitura
(`subcategoria_de`), para o SEO e para a página da Feira. Sem coluna nova.
"""
import unicodedata

# (slug, nome, ((sub_slug, sub_nome, palavras), ...))
# Palavras são começo de palavra, sem acento ('doce' casa 'doces');
# terminada em '$', só a palavra inteira ('mel$' não casa 'melancia').
TAXONOMIA = (
    ('comida-artesanal', 'Comida artesanal', (
        ('doces-e-confeitaria', 'Doces e confeitaria',
         ('doce', 'bolo', 'biscoito', 'cookie', 'confeit', 'brigadeiro', 'strudel',
          'chocolate', 'brownie', 'bombo', 'trufa')),
        ('salgados-e-lanches', 'Salgados e lanches',
         ('salgad', 'lanche', 'empad', 'quiche', 'esfiha', 'coxinha', 'pastel', 'batata')),
        ('refeicoes', 'Refeições e comida de rua',
         ('refeic', 'risot', 'pizza', 'feijao', 'tropeiro', 'mexican', 'marmita',
          'culinaria', 'comida')),
        ('comida-vegana', 'Comida vegana', ('vegan', 'vegetarian')),
        ('paes-e-fermentados', 'Pães e fermentados',
         ('pao', 'paes', 'padaria', 'fermenta', 'kombucha')),
        ('charcutaria-e-queijos', 'Charcutaria e queijos',
         ('charcut', 'embutido', 'defumad', 'salame', 'linguica', 'queijo')),
        ('geleias-molhos-e-conservas', 'Geleias, molhos e conservas',
         ('geleia', 'molho', 'conserva', 'compota', 'pimenta', 'tempero', 'antepasto', 'pesto')),
        ('cafes-mel-e-emporio', 'Cafés, mel e empório',
         ('cafe', 'mel$', 'emporio', 'granola', 'cha$', 'chas$')),
        ('frutas-e-hortalicas', 'Frutas e hortaliças',
         ('fruta', 'hortali', 'verdura', 'legume', 'organico')),
        ('bebidas-artesanais', 'Bebidas artesanais',
         ('bebida', 'chopp', 'chope', 'cerveja', 'vinho', 'licor', 'cachaca')),
    )),
    ('artesanato', 'Artesanato', (
        ('costura-criativa', 'Costura criativa e patchwork',
         ('costura', 'patchwork', 'enxoval', 'laco', 'gravata', 'bordado', 'tecido')),
        ('bonecos-e-brinquedos', 'Bonecos e brinquedos',
         ('boneca', 'boneco', 'brinquedo', 'feltro', 'biscuit', 'pelucia')),
        ('bolsas-e-acessorios', 'Bolsas, mochilas e acessórios',
         ('bolsa', 'mochila', 'pochete', 'necessaire', 'carteira', 'acessorio')),
        ('macrame', 'Macramê', ('macrame',)),
        ('cartonagem-e-papel', 'Cartonagem e papel',
         ('cartonagem', 'papel', 'caderno', 'agenda', 'encaderna')),
        ('saboaria-e-cosmeticos', 'Saboaria e cosméticos naturais',
         ('sabonete', 'saboaria', 'sabao', 'cosmetic', 'hidratante')),
        ('madeira', 'Madeira',
         ('madeira', 'tornearia', 'marcenaria', 'laser', 'mdf', 'bambu', 'luminaria', 'movel', 'moveis')),
        ('croche-trico-e-amigurumi', 'Crochê, tricô e amigurumi',
         ('croche', 'trico', 'amigurumi', 'la$')),
        ('velas-aromas-e-incensos', 'Velas, aromas e incensos',
         ('vela', 'aroma', 'incenso', 'difusor', 'esoter')),
        ('ceramica', 'Cerâmica', ('ceramica', 'porcelana', 'argila')),
        ('mosaico-e-vidro', 'Mosaico e vidro', ('mosaico', 'vidro', 'vitral')),
        ('tecelagem-e-tapetes', 'Tecelagem e tapetes', ('tecelagem', 'tear$', 'tapete', 'trama')),
        ('pintura-decorativa', 'Peças pintadas', ('caneca', 'azulejo', 'pintad')),
        ('moda-autoral', 'Moda autoral e consciente',
         ('moda', 'roupa', 'camiseta', 'camisa', 'vestido')),
        ('reciclagem-e-customizacao', 'Reciclagem e customização',
         ('reciclag', 'customiz', 'upcycl', 'reaproveit', 'chapeu')),
        ('cestaria', 'Cestaria e palha', ('cesto', 'cestaria', 'palha', 'vime')),
    )),
    ('joias', 'Joias e bijuterias', (
        ('bijuteria-autoral', 'Bijuteria autoral',
         ('bijuteria', 'bijoux', 'brinco', 'colar', 'pulseira', 'micanga', 'polymer', 'anel', 'aneis')),
        ('prata-e-pedras', 'Prata e pedras naturais', ('prata', 'pedra', 'cristal', 'joia')),
        ('materiais-mistos', 'Madeira, resina e vidro', ('resina',)),
        ('metal-e-arame', 'Metal e arame', ('arame', 'metal')),
        ('semijoias', 'Semijoias', ('semijoia', 'folheado')),
    )),
    ('plantas', 'Plantas', (
        ('terrarios-e-kokedamas', 'Terrários e kokedamas', ('terrario', 'kokedama')),
        ('suculentas-e-cactos', 'Suculentas e cactos', ('suculenta', 'cacto')),
        ('mudas-e-hortas', 'Mudas, hortas e compostagem', ('muda', 'horta', 'compost', 'semente')),
        ('plantas-ornamentais', 'Orquídeas, bonsais e ornamentais',
         ('orquidea', 'bonsai', 'planta', 'flor')),
    )),
    ('arte', 'Arte', (
        ('pintura', 'Pintura e mandalas', ('pintura', 'quadro', 'tela', 'mandala', 'aquarela')),
        ('arte-textil', 'Arte têxtil', ('seda', 'tingimento', 'textil')),
        ('ilustracao', 'Ilustração', ('ilustra', 'desenho', 'poster', 'gravura')),
        ('escultura', 'Escultura', ('escultura',)),
    )),
)


def _norm(texto):
    sem_acento = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in sem_acento.lower()).split())


def _casa(palavra, chave):
    return palavra == chave[:-1] if chave.endswith('$') else palavra.startswith(chave)


SUBCATEGORIAS = [(cat, sub, nome) for cat, _, subs in TAXONOMIA for sub, nome, _ in subs]
_POR_NOME = {_norm(nome): (cat, sub, nome) for cat, sub, nome in SUBCATEGORIAS}
_CHAVES = [(chave, (cat, sub, nome))
           for cat, _, subs in TAXONOMIA for sub, nome, chaves in subs for chave in chaves]


def subcategoria_de(texto):
    """(categoria, subcategoria, nome) do que o expositor escreveu, ou None.

    A palavra que vem primeiro decide: em português o núcleo abre a frase,
    então "Brincos de madeira" é bijuteria, e "Madeira para brincos", não."""
    n = _norm(texto)
    if not n:
        return None
    if n in _POR_NOME:
        return _POR_NOME[n]
    for palavra in n.split():
        for chave, alvo in _CHAVES:
            if _casa(palavra, chave):
                return alvo
    return None


def opcoes(proprias=()):
    """Sugestões do campo: primeiro as categorias que o expositor já usa (as
    seções do site dele), depois a taxonomia. Sem repetir grafia."""
    vistas, saida = set(), []
    for nome in list(proprias) + [nome for _, _, nome in SUBCATEGORIAS]:
        chave = _norm(nome)
        if chave and chave not in vistas:
            vistas.add(chave)
            saida.append(nome.strip())
    return saida


def canonizar(texto, conhecidas=()):
    """Mesma categoria, mesma grafia: "geleias " vira "Geleias" se já existe
    "Geleias". Texto novo passa como veio (só sem espaço sobrando)."""
    limpo = ' '.join((texto or '').split())
    if not limpo:
        return None
    alvo = _norm(limpo)
    for nome in conhecidas:
        if _norm(nome) == alvo:
            return nome.strip()
    return limpo
