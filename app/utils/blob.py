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

Redimensionamento: no navegador e de novo aqui
----------------------------------------------
Foto de celular tem 4MB; o `<canvas>` do formulário reduz pra ~200KB antes de
subir. É o que faz o upload terminar no 4G do bar. O limite daqui
(`TAMANHO_MAXIMO`) é rede de segurança pra POST que não passou pelo navegador.

Mesmo assim, o servidor regrava toda imagem com Pillow (`_otimizar`): nem todo
upload passa pelo canvas (Modo Campo antigo, API, navegador que falhou), foto
de celular chega deitada pelo EXIF, e PNG de foto pesa 5x o JPEG. Junto sai a
miniatura `<nome>-md.webp` (480 px), a mesma convenção de `feira._miniatura()`,
pra vitrine não baixar a foto grande num card de 200 px.
"""
import io
import json
import os
import secrets
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

LADO_MAXIMO = 1600
LADO_MINIATURA = 480
SUFIXO_MINIATURA = '-md.webp'

API = 'https://blob.vercel-storage.com'
VERSAO_API = '7'


class UploadInvalido(ValueError):
    """Culpa de quem enviou: extensão errada, arquivo vazio, grande demais."""


class UploadIndisponivel(RuntimeError):
    """Culpa da configuração: sem token e sem disco gravável."""


def _extensao(nome):
    ext = os.path.splitext(nome or '')[1].lower()
    if ext in ('.heic', '.heif'):
        raise UploadInvalido(
            'Manda a foto como JPG ou PNG. No iPhone, ajuste em Ajustes > Câmera > '
            'Formatos > Mais compatível.')
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


def _otimizar(dados, ext):
    """Abre de verdade (extensão não prova nada), endireita pelo EXIF, limita
    o lado maior e regrava. Devolve (bytes, extensão final, bytes da miniatura).

    PNG sem transparência é foto salva no formato errado: vira JPEG. PNG com
    transparência (logo) continua PNG, senão o fundo vira preto."""
    # Import aqui: o Pillow puxa o numpy, e o boot do site não pode carregá-lo
    # (tests/integration/test_sem_gestao.py). Só upload paga esse custo.
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(dados)) as teste:
            teste.verify()
        img = Image.open(io.BytesIO(dados))
        img.load()
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise UploadInvalido('o arquivo não parece uma imagem (JPG, PNG ou WEBP).')

    transparente = img.mode in ('RGBA', 'LA', 'P') and (
        img.mode != 'P' or 'transparency' in img.info)
    if transparente:
        img = img.convert('RGBA')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    saida = io.BytesIO()
    if ext == '.webp':
        img.save(saida, 'WEBP', quality=80, method=4)
    elif ext == '.png' and transparente:
        img.save(saida, 'PNG', optimize=True)
    else:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(saida, 'JPEG', quality=82, optimize=True, progressive=True)
        ext = '.jpeg' if ext == '.jpeg' else '.jpg'

    mini = img.copy()
    mini.thumbnail((LADO_MINIATURA, LADO_MINIATURA))
    saida_mini = io.BytesIO()
    mini.save(saida_mini, 'WEBP', quality=78, method=4)
    return saida.getvalue(), ext, saida_mini.getvalue()


def miniatura_de(nome):
    """`pasta/foto.jpg` -> `pasta/foto-md.webp`. Vale pra caminho e pra URL."""
    return os.path.splitext(nome)[0] + SUFIXO_MINIATURA


def token():
    return (os.environ.get('BLOB_READ_WRITE_TOKEN') or '').strip() or None


def _para_blob(dados, caminho, content_type):
    """PUT direto na API. O sufixo contra colisão (IMG_0001.jpg é o padrão de
    todo celular) já vem no `caminho`, posto por `enviar`: o sufixo aleatório
    do Blob seria diferente pra foto e miniatura, e a miniatura precisa de um
    endereço que dê pra deduzir da foto."""
    req = urllib.request.Request(
        f'{API}/{caminho}',
        data=dados,
        method='PUT',
        headers={
            'authorization': f'Bearer {token()}',
            'x-api-version': VERSAO_API,
            'x-content-type': content_type,
            'x-add-random-suffix': '0',
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


def _para_disco(dados, slug, nome_arquivo, mini=None):
    """Dev: grava na pasta que o aplicador de leads já lê."""
    from app.utils import demos

    pasta = demos.pasta_do_bar(slug)
    try:
        os.makedirs(pasta, exist_ok=True)
        base = secure_filename(os.path.basename(nome_arquivo)) or 'foto.jpg'
        with open(os.path.join(pasta, base), 'wb') as f:
            f.write(dados)
        if mini:
            with open(os.path.join(pasta, miniatura_de(base)), 'wb') as f:
                f.write(mini)
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

    dados, ext_final, mini = _otimizar(dados, ext)
    nome = os.path.splitext(arquivo.filename)[0] + ext_final

    if token():
        caminho = _caminho(slug, nome)
        raiz, _ = os.path.splitext(caminho)
        caminho = f'{raiz}.{secrets.token_hex(4)}{ext_final}'
        url = _para_blob(dados, caminho, TIPOS[ext_final])
        _para_blob(mini, miniatura_de(caminho), 'image/webp')
        return url
    return _para_disco(dados, slug, nome, mini)
