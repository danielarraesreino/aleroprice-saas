"""Grava no lead o que o painel do Google mostra sobre o bar.

Como se usa
-----------
A leitura do painel é manual (navegador aberto na busca do bar, JS lendo o DOM);
este script é a outra metade: recebe o JSON dessa leitura e o transforma em
arquivo de lead + fotos na pasta do bar.

    python3 scripts/coletar_google.py <slug> '<json>'

O JSON aceita: nota, avaliacoes, telefone, endereco, fotos (lista de URLs).
Campo ausente não é gravado — o lead nunca perde dado que já tinha.

Por que fica versionado
-----------------------
Estava em /tmp e sumiu quando a sessão caiu, no meio da coleta dos 24 bares de
Barão. A parte chata não é escrever de novo: é lembrar as regras (qual foto vira
capa, o que fazer com endereço sujo, como o Google marca foto de prato).
"""
import json
import os
import re
import struct
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120'}
LADO_MINIMO = 700          # abaixo disso é ícone de interface, não foto do bar
IDEAL = 16 / 10            # o hero é uma faixa larga


def dimensoes(dados):
    i = 2
    while i < len(dados) - 9:
        if dados[i] != 0xFF:
            i += 1
            continue
        if dados[i + 1] in (0xC0, 0xC1, 0xC2):
            altura, largura = struct.unpack('>HH', dados[i + 5:i + 9])
            return largura, altura
        i += 2 + struct.unpack('>H', dados[i + 2:i + 4])[0]
    return 0, 0


def limpar_endereco(texto):
    """O painel emenda a descrição do lugar no endereço. Corta no CEP."""
    if not texto:
        return None
    achou = re.search(r'^(.*?\d{5}-?\d{3})', texto)
    if achou:
        return achou.group(1).strip()
    achou = re.search(r'^(.*?-\s*[A-Z]{2})\b', texto)
    return achou.group(1).strip() if achou else texto.split('.')[0].strip()[:190]


def baixar(slug, urls):
    """URLs com /food/ são foto de prato no Google e viram cardápio; o resto,
    ambiente. A capa é a mais próxima de paisagem — foto retrato vira faixa
    cortada no pescoço das pessoas."""
    pasta = os.path.join(REPO, 'app/static/img/demo', slug)
    os.makedirs(pasta, exist_ok=True)

    ambiente, comida = [], []
    for url in urls:
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=30) as resp:
                dados = resp.read()
        except Exception:
            continue
        if dados[:3] != b'\xff\xd8\xff':
            continue
        largura, altura = dimensoes(dados)
        if max(largura, altura) < LADO_MINIMO:
            continue
        ('/food/' in url and comida or ambiente).append((dados, largura, altura))

    salvos = []
    for n, (dados, largura, altura) in enumerate(comida[:4]):
        nome = f'prato-da-casa-{n + 1}.jpg'
        open(os.path.join(pasta, nome), 'wb').write(dados)
        salvos.append(f'{nome} {largura}x{altura}')

    ambiente.sort(key=lambda f: abs(f[1] / max(f[2], 1) - IDEAL) - min(f[1], 2500) / 20000)
    for n, (dados, largura, altura) in enumerate(ambiente[:8]):
        nome = 'capa.jpg' if n == 0 else f'ambiente-{n}.jpg'
        open(os.path.join(pasta, nome), 'wb').write(dados)
        salvos.append(f'{nome} {largura}x{altura}')
    return salvos


def gravar_lead(slug, dados):
    caminho = os.path.join(REPO, 'app/data/leads', f'{slug}.yml')
    if not os.path.isfile(caminho):
        return 'lead inexistente'

    texto = open(caminho, encoding='utf-8').read()
    gravados = []
    campos = (
        ('nota_google', dados.get('nota')),
        ('qtd_avaliacoes', dados.get('avaliacoes')),
        ('endereco', limpar_endereco(dados.get('endereco'))),
        ('telefone_exibicao', dados.get('telefone')),
    )
    for chave, valor in campos:
        if not valor:
            continue
        if chave == 'qtd_avaliacoes':
            linha = f'  {chave}: {str(valor).replace(".", "")}'
        else:
            linha = f'  {chave}: "{valor}"'
        if re.search(rf'^\s+{chave}:', texto, re.M):
            texto = re.sub(rf'^\s+{chave}:.*$', linha, texto, count=1, flags=re.M)
        else:
            texto = re.sub(r'^(site:\n)', rf'\1{linha}\n', texto, count=1, flags=re.M)
        gravados.append(chave)

    open(caminho, 'w', encoding='utf-8').write(texto)
    return ', '.join(gravados) or 'nada'


if __name__ == '__main__':
    slug = sys.argv[1]
    dados = json.loads(sys.argv[2])
    fotos = baixar(slug, dados.get('fotos') or [])
    campos = gravar_lead(slug, dados)
    print(f'{slug}: {len(fotos)} fotos [{campos}]')
    for f in fotos:
        print('   ', f)
