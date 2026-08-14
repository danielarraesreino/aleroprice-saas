"""Upload de imagem.

Dois requisitos não-óbvios:

1. **Falhar alto quando não dá pra subir.** Foto que "some" na frente do dono do
   bar é pior que erro na tela — o vendedor acha que salvou e segue a conversa.
2. **Não aceitar qualquer arquivo.** O endereço devolvido vai direto pra um
   `<img src>` no site público.
"""
import io

import pytest
from werkzeug.datastructures import FileStorage

from app.utils import blob


def arquivo(nome='foto.jpg', conteudo=b'\xff\xd8\xff\xe0conteudo-de-imagem'):
    return FileStorage(stream=io.BytesIO(conteudo), filename=nome)


@pytest.fixture(autouse=True)
def sem_token(monkeypatch):
    """Padrão dos testes: sem token, então grava em disco."""
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    from app.utils import demos
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path))
    return tmp_path


def test_grava_em_disco_e_devolve_caminho_que_o_site_resolve(pasta):
    caminho = blob.enviar(arquivo('IMG_0042.jpg'), 'boteco-do-teste')

    # É exatamente a forma que publico.views._img() manda pro url_for('static')
    assert caminho == 'img/demo/boteco-do-teste/IMG_0042.jpg'
    assert (pasta / 'boteco-do-teste' / 'IMG_0042.jpg').exists()


def test_cai_na_mesma_pasta_que_o_aplicador_de_leads_le(pasta):
    """Foto subida em campo tem que ser vista por `demos.fotos_do_bar`."""
    from app.utils import demos

    blob.enviar(arquivo('capa.jpg'), 'bar-x')
    assert demos.fotos_do_bar('bar-x')['capa'] == 'img/demo/bar-x/capa.jpg'


@pytest.mark.parametrize('nome', ['planilha.xlsx', 'script.js', 'nota.pdf', 'semextensao'])
def test_recusa_arquivo_que_nao_e_imagem(pasta, nome):
    with pytest.raises(blob.UploadInvalido):
        blob.enviar(arquivo(nome), 'bar-x')


def test_recusa_arquivo_vazio(pasta):
    with pytest.raises(blob.UploadInvalido):
        blob.enviar(arquivo('foto.jpg', b''), 'bar-x')


def test_recusa_arquivo_gigante(pasta):
    """O canvas do formulário reduz antes de subir; quem chega grande aqui não
    passou por ele."""
    grande = arquivo('foto.jpg', b'x' * (blob.TAMANHO_MAXIMO + 1))
    with pytest.raises(blob.UploadInvalido, match='limite'):
        blob.enviar(grande, 'bar-x')


def test_recusa_quando_nao_veio_arquivo(pasta):
    with pytest.raises(blob.UploadInvalido):
        blob.enviar(None, 'bar-x')


def test_nome_de_arquivo_nao_escapa_da_pasta_do_bar(pasta):
    """`secure_filename` + basename: nome hostil não escreve fora do lugar."""
    caminho = blob.enviar(arquivo('../../../etc/senha.jpg'), 'bar-x')

    assert caminho.startswith('img/demo/bar-x/')
    assert '..' not in caminho
    assert (pasta / 'bar-x').exists()


def test_disco_read_only_falha_alto(monkeypatch, pasta):
    """Produção sem token: não pode engolir em silêncio."""
    def recusa(*a, **kw):
        raise OSError('Read-only file system')
    monkeypatch.setattr(blob.os, 'makedirs', recusa)

    with pytest.raises(blob.UploadIndisponivel, match='BLOB_READ_WRITE_TOKEN'):
        blob.enviar(arquivo(), 'bar-x')


def test_com_token_vai_pro_blob_e_devolve_a_url(monkeypatch):
    chamada = {}

    class Resposta:
        def read(self):
            return b'{"url": "https://abc.public.blob.vercel-storage.com/bar-x/foto-9z.jpg"}'
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def falso_urlopen(req, timeout=None):
        chamada['url'] = req.full_url
        chamada['metodo'] = req.get_method()
        chamada['headers'] = {k.lower(): v for k, v in req.headers.items()}
        chamada['corpo'] = req.data
        return Resposta()

    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN', 'vercel_blob_rw_TOKEN')
    monkeypatch.setattr(blob.urllib.request, 'urlopen', falso_urlopen)

    url = blob.enviar(arquivo('foto.jpg', b'bytes-da-imagem'), 'bar-x')

    assert url == 'https://abc.public.blob.vercel-storage.com/bar-x/foto-9z.jpg'
    assert chamada['url'] == 'https://blob.vercel-storage.com/bar-x/foto.jpg'
    assert chamada['metodo'] == 'PUT'
    assert chamada['headers']['authorization'] == 'Bearer vercel_blob_rw_TOKEN'
    assert chamada['headers']['x-api-version'] == blob.VERSAO_API
    assert chamada['headers']['x-content-type'] == 'image/jpeg'
    # sem sufixo aleatório, IMG_0001.jpg de dois bares se sobrescreveria
    assert chamada['headers']['x-add-random-suffix'] == '1'
    assert chamada['corpo'] == b'bytes-da-imagem'


def test_erro_do_blob_vira_mensagem_e_nao_url_quebrada(monkeypatch):
    import urllib.error

    def explode(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 403, 'Forbidden', {},
                                     io.BytesIO(b'token invalido'))

    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN', 'token-errado')
    monkeypatch.setattr(blob.urllib.request, 'urlopen', explode)

    with pytest.raises(blob.UploadIndisponivel, match='403'):
        blob.enviar(arquivo(), 'bar-x')
