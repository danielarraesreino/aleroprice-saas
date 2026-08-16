"""Escreve o prompt de imagem de cada bar, a partir do que o bar é.

O erro que este script existe pra evitar
----------------------------------------
Prompt genérico ("bar brasileiro à noite") devolve foto de banco de imagens, e
o dono não se reconhece — que é exatamente a coisa que a campanha inteira tenta
resolver. Aqui o prompt sai do YAML do lead: `descritor`, `subline`, `vibe` e
`tema` são o que aquele bar diz ser.

    Toca do Tatu   "Espetaria de esquina com cachaças artesanais"
                   -> espetos na brasa, prateleira de garrafas de cachaça
    Ponto 1        "O bar mais antigo de Barão", "BLUES · DESDE 1978"
                   -> parede de discos, luz baixa, madeira envelhecida
    Bronco Burger  "Hamburgueria artesanal", "CHIMI"
                   -> chapa quente, smash, molho chimichurri

Dois bares com a mesma `vibe` mas `subline` diferente saem diferentes. É o que
faz a prévia parecer o lugar.

O DNA visual
------------
Todas as imagens do MESMO bar levam o mesmo bloco de abertura, para parecerem a
mesma noite, do mesmo fotógrafo. Sem isso, capa e prato parecem de dois
restaurantes — e some a única coisa que dá unidade a uma página com 3 fotos.

Como usar
---------
    python3 scripts/prompts_de_imagem.py --sem-capa      # quem precisa
    python3 scripts/prompts_de_imagem.py --slug tabuas
    python3 scripts/prompts_de_imagem.py --top 5

Escreve em `scripts/saida/prompts/<slug>.md`. Não toca em mais nada.
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ranquear_leads import DIR_LEADS, carregar  # noqa: E402

DIR_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'saida', 'prompts')

# Luz e textura por tema. O tema já foi escolhido para o bar e pinta o site —
# a foto tem que combinar com a paleta, senão o hero briga com o próprio CSS.
LUZ = {
    'boteco-ambar': ('luz âmbar quente de lâmpadas incandescentes, madeira '
                     'escura envernizada pelo uso, azulejo branco antigo com '
                     'rejunte escurecido'),
    # O neon é ACENTO, não a luz principal.
    #
    # A primeira versão pedia "neon magenta e ciano refletindo em superfícies
    # escuras, preto fosco, contraste alto" — e o modelo entregou uma caverna
    # magenta onde não dava pra ver o bar. Bar real com identidade neon tem luz
    # quente de trabalho no balcão e neon nas bordas; dizer isso explicitamente
    # é o que separa "hamburgueria à noite" de "porão roxo".
    'neon-noite':   ('luz quente de trabalho iluminando o balcão e as mesas, '
                     'com letreiros de neon magenta e ciano ao fundo apenas '
                     'como acento colorido nas bordas do quadro; ambiente '
                     'legível e bem exposto, nunca escuro demais'),
    'pub-escuro':   ('luz baixa de lâmpadas de filamento, verde-garrafa, couro '
                     'gasto, latão opaco e madeira maciça escura'),
    'praia-claro':  ('luz natural de fim de tarde, turquesa e areia, madeira '
                     'clara, fibra natural, ambiente arejado e aberto'),
}

# O que a câmera procura, por tipo de casa.
CENA = {
    'boteco':       'mesas de madeira na calçada, balcão com torneira de chope',
    'pub':          'balcão comprido com torneiras alinhadas, banquetas altas',
    'hamburgueria': 'chapa quente atrás do balcão, banquetas altas, cozinha à vista',
    'praia':        'mesas ao ar livre sob cobertura de palha, pé-direito aberto',
}

# Palavra no descritor/subline -> o que a imagem precisa mostrar. É o que
# diferencia dois botecos que só se distinguem pelo que servem.
PISTAS = (
    ('espeto',      'espetos de carne assando na brasa, espetinhos em pé numa grelha'),
    ('espetinho',   'espetos de carne assando na brasa, espetinhos em pé numa grelha'),
    ('cachaça',     'prateleira com garrafas de cachaça artesanal de alambique'),
    ('chopp',       'torneira de chope tirando um copo com colarinho denso'),
    ('chope',       'torneira de chope tirando um copo com colarinho denso'),
    ('cerveja',     'copos de cerveja gelada suando sobre a mesa'),
    ('artesanal',   'torneiras de cerveja artesanal com plaquinhas de estilo'),
    ('blues',       'parede com discos de vinil e um palco pequeno ao fundo'),
    ('música ao vivo', 'palco baixo com instrumentos, luz quente sobre o palco'),
    ('sertanejo',   'palco simples com viola caipira e caixas de som'),
    ('vivo',        'palco pequeno com instrumentos e luz dirigida'),
    ('burger',      'hambúrguer artesanal na chapa, queijo derretendo'),
    ('hamburgueria', 'hambúrguer artesanal na chapa, queijo derretendo'),
    ('chimi',       'potinho de molho chimichurri verde ao lado do prato'),
    ('petisco',     'porções de petisco para dividir espalhadas na mesa'),
    ('almoço',      'prato feito servido no balcão, comida caseira no vapor'),
    ('pf',          'prato feito servido no balcão, comida caseira no vapor'),
    ('vinho',       'taças de vinho e garrafas em prateleira de madeira'),
    ('pizza',       'forno a lenha aceso ao fundo com a boca iluminada'),
    ('calçada',     'mesas na calçada ocupadas, movimento de rua ao fundo'),
    ('antig',       'móveis gastos pelo tempo, fotografias antigas na parede'),
    ('1978',        'móveis gastos pelo tempo, fotografias antigas na parede'),
)

FIM = ('Sem qualquer texto, letreiro legível, cardápio escrito, logotipo, marca '
       'ou watermark. Nenhum rosto identificável — pessoas apenas em silhueta '
       'ou desfocadas.')


def pistas_do_bar(site):
    """O que este bar tem que a foto precisa mostrar."""
    texto = ' '.join(str(site.get(c) or '') for c in
                     ('descritor', 'subline', 'tagline', 'kicker')).lower()
    achadas, vistas = [], set()
    for chave, instrucao in PISTAS:
        if chave in texto and instrucao not in vistas:
            achadas.append(instrucao)
            vistas.add(instrucao)
    return achadas[:3]   # três já bastam; mais que isso o modelo se perde


def dna(nome, site, tema, vibe):
    luz = LUZ.get(tema, LUZ['boteco-ambar'])
    cena = CENA.get(vibe, CENA['boteco'])
    linhas = [
        f'Fotografia documental de um bar de bairro em Barão Geraldo, Campinas, '
        f'Brasil, à noite. {cena.capitalize()}.',
        f'Ambiente: {luz}.',
    ]
    pistas = pistas_do_bar(site)
    if pistas:
        linhas.append('A casa é conhecida por: ' + '; '.join(pistas) + '.')
    linhas.append(
        'Estética de filme 35mm: grão sutil, cores quentes e saturação natural, '
        'pretos profundos e não lavados. Realista e vivido, nada de estúdio nem '
        'de publicidade.')
    return ' '.join(linhas)


def prompts_do_bar(lead):
    """Capa (16:10) e dois enquadramentos de apoio (4:3)."""
    site = lead.get('site') or {}
    nome = lead.get('nome') or '?'
    base = dna(nome, site, lead.get('tema'), site.get('vibe'))

    itens = [i.get('nome') for i in (lead.get('cardapio') or []) if i.get('nome')]

    saida = [(
        'capa.jpg', '16:10',
        f'{base} Plano aberto da fachada aberta vista da calçada, mesas '
        f'ocupadas, luz derramando para fora, o interior iluminado ao fundo. '
        f'Profundidade de campo rasa, câmera na altura dos olhos de quem está '
        f'em pé, horizonte reto. Deixe o centro do quadro respirável — o nome '
        f'do bar entra por cima na página. {FIM}')]

    saida.append((
        'ambiente-balcao.jpg', '4:3',
        f'{base} O balcão visto de lado, em close, com o atendente servindo — '
        f'mão presente, rosto fora do quadro. Prateleiras desfocadas ao fundo. '
        f'{FIM}'))

    if itens:
        primeiro = itens[0]
        saida.append((
            f'prato-{_slugify(primeiro)}.jpg', '4:3',
            f'{base} Close de "{primeiro}", visto de cima em ângulo de 45 graus, '
            f'ocupando dois terços do quadro, sobre a mesa de madeira. Luz vindo '
            f'da esquerda. Comida de bar de bairro: porção farta e desarrumada, '
            f'louça com marcas de uso, não gastronomia. {FIM}'))
    else:
        saida.append((
            'ambiente-mesa.jpg', '4:3',
            f'{base} Vista de cima de uma mesa no meio da noite: porções pela '
            f'metade, copos suados, guardanapos amassados, mãos alcançando a '
            f'comida. Bagunça honesta de mesa boa. {FIM}'))
    return saida


def _slugify(texto):
    import re
    import unicodedata
    t = unicodedata.normalize('NFD', texto.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:40]


def escrever(slug, lead):
    site = lead.get('site') or {}
    linhas = [
        f'# {lead.get("nome") or slug} — imagens',
        '',
        f'Pasta de destino: `app/static/img/demo/{slug}/`',
        f'Identidade do lead: {site.get("descritor") or "—"}'
        + (f' · {site.get("subline")}' if site.get('subline') else ''),
        '',
        'Um prompt por imagem, já com o contexto do bar embutido. Gere na ordem: '
        'a capa é a que mais pesa.',
        '',
    ]
    for arquivo, proporcao, prompt in prompts_do_bar(lead):
        linhas += [f'## `{arquivo}` · {proporcao}', '', '> ' + prompt, '']
    linhas += [
        '---',
        '',
        'Depois de salvar as imagens na pasta acima:',
        '',
        '```bash',
        f'python3 scripts/aplicar_imagens.py {slug}',
        '```',
        '',
        'Ele redimensiona, otimiza e liga a capa ao `hero_foto` do lead.',
    ]
    os.makedirs(DIR_SAIDA, exist_ok=True)
    caminho = os.path.join(DIR_SAIDA, f'{slug}.md')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas) + '\n')
    return caminho


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--slug', help='um bar específico')
    p.add_argument('--sem-capa', action='store_true', help='só quem não tem capa')
    p.add_argument('--top', type=int, metavar='N')
    p.add_argument('--barao', action='store_true', default=True)
    a = p.parse_args()

    if a.slug:
        alvos = [a.slug]
    else:
        linhas = carregar(apenas_barao=a.barao)
        if a.sem_capa:
            linhas = [l for l in linhas if not l['tem_capa']]
        if a.top:
            linhas = linhas[:a.top]
        alvos = [l['slug'] for l in linhas]

    for slug in alvos:
        caminho = os.path.join(DIR_LEADS, f'{slug}.yml')
        if not os.path.isfile(caminho):
            print(f'  {slug}: sem arquivo de lead')
            continue
        lead = yaml.safe_load(open(caminho, encoding='utf-8')) or {}
        destino = escrever(slug, lead)
        pistas = pistas_do_bar(lead.get('site') or {})
        print(f'  {slug:24} {len(prompts_do_bar(lead))} prompts · '
              f'{len(pistas)} pista(s) do bar')
    print(f'\nEscrito em {DIR_SAIDA}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
