"""Upload de imagem: o dono do bar entrega a foto e ela entra no site na hora.

Por que existe
--------------
Até aqui, foto só entrava por commit — `app/static/img/demo/<slug>/` versionada,
porque o filesystem da Vercel é read-only. Isso funciona pra montar prévia em
casa e é inútil na frente do dono do bar, que é onde a venda acontece.

Onde a imagem fica
------------------
**Vercel Blob**, via API REST direta. Sem SDK: a chamada é um PUT com um header
de token, e trazer `boto3` ou `cloudinary` significaria conta nova e dependência
nova pro mesmo resultado. O bucket já vem junto do deploy que já existe.

Em dev, sem `BLOB_READ_WRITE_TOKEN`, grava em `app/static/img/demo/<slug>/` —
a mesma pasta que `demos.fotos_do_bar()` lê. Assim o fluxo de campo é testável
no notebook antes de ir pro bar.

Redimensionamento é no navegador
--------------------------------
Foto de celular tem 4MB; o `<canvas>` do formulário reduz pra ~200KB antes de
subir. É o que faz o upload terminar no 4G do bar, e é o que dispensa Pillow no
runtime. O limite daqui (`TAMANHO_MAXIMO`) é rede de segurança pra POST que não
passou pelo navegador.
"""
import json
import os
import urllib.error
import urllib.request

from werkzeug.utils import secure_filename

# Mesmo conjunto que demos.EXTENSOES: o que a pasta do bar aceita, o upload
# aceita. Duas listas divergentes viram bug silencioso de "subiu mas não aparece".
EXTENSOES = ('.jpg', '.jpeg', '.png', '.webp')

TIPOS = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}

TAMANHO_MAXIMO = 8 * 1024 * 1024

API = 'https://blob.vercel-storage.com'
VERSAO_API = '7'


class UploadInvalido(ValueError):
    """Culpa de quem enviou: extensão errada, arquivo vazio, grande demais."""


class UploadIndisponivel(RuntimeError):
    """Culpa da configuração: sem token e sem disco gravável."""


def _extensao(nome):
    ext = os.path.splitext(nome or '')[1].lower()
    if ext not in EXTENSOES:
        raise UploadInvalido(
            f'formato não aceito: "{ext or nome}". Use JPG, PNG ou WEBP.')
    return ext


def _caminho(slug, nome_arquivo):
    """Nome final, previsível e sem colisão entre bares."""
    base = secure_filename(os.path.basename(nome_arquivo or 'foto'))
    if not base:
        base = 'foto' + _extensao(nome_arquivo)
    return f'{slug}/{base}'


def token():
    return (os.environ.get('BLOB_READ_WRITE_TOKEN') or '').strip() or None


def _para_blob(dados, caminho, content_type):
    """PUT direto na API. `x-add-random-suffix` evita que duas fotos com o
    mesmo nome (IMG_0001.jpg é o padrão de todo celular) se sobrescrevam."""
    req = urllib.request.Request(
        f'{API}/{caminho}',
        data=dados,
        method='PUT',
        headers={
            'authorization': f'Bearer {token()}',
            'x-api-version': VERSAO_API,
            'x-content-type': content_type,
            'x-add-random-suffix': '1',
            'content-type': content_type,
            'content-length': str(len(dados)),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            corpo = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode('utf-8', 'replace')[:200]
        raise UploadIndisponivel(f'Vercel Blob respondeu {e.code}: {detalhe}')
    except urllib.error.URLError as e:
        raise UploadIndisponivel(f'não consegui falar com o Vercel Blob: {e.reason}')

    url = corpo.get('url')
    if not url:
        raise UploadIndisponivel(f'resposta do Blob sem url: {corpo}')
    return url


def _para_disco(dados, slug, nome_arquivo):
    """Dev: grava na pasta que o aplicador de leads já lê."""
    from app.utils import demos

    pasta = demos.pasta_do_bar(slug)
    try:
        os.makedirs(pasta, exist_ok=True)
        base = secure_filename(os.path.basename(nome_arquivo)) or 'foto.jpg'
        with open(os.path.join(pasta, base), 'wb') as f:
            f.write(dados)
    except OSError as e:
        raise UploadIndisponivel(
            'sem BLOB_READ_WRITE_TOKEN e o disco não aceita escrita '
            f'({e}). Configure o token para subir foto em produção.')
    return f'img/demo/{slug}/{base}'


def enviar(arquivo, slug):
    """Recebe um FileStorage do form e devolve o endereço a gravar no banco.

    Devolve URL absoluta (Blob) ou caminho relativo a `static/` (disco) — as
    duas formas que `publico.views._img()` já sabe resolver, então nada muda
    no render.
    """
    if arquivo is None or not getattr(arquivo, 'filename', ''):
        raise UploadInvalido('nenhum arquivo enviado')

    ext = _extensao(arquivo.filename)
    dados = arquivo.read()
    if not dados:
        raise UploadInvalido('arquivo vazio')
    if len(dados) > TAMANHO_MAXIMO:
        mb = len(dados) / 1024 / 1024
        raise UploadInvalido(
            f'imagem de {mb:.1f}MB — o limite é {TAMANHO_MAXIMO // 1024 // 1024}MB.')

    if token():
        return _para_blob(dados, _caminho(slug, arquivo.filename), TIPOS[ext])
    return _para_disco(dados, slug, arquivo.filename)
