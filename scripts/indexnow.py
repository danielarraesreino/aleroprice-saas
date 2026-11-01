"""Avisa o IndexNow (Bing, Yandex, Seznam, Naver, Yep) de todas as URLs do sitemap.

Uso, depois de um deploy:
    venv/bin/python scripts/indexnow.py                       # feiradebarao.com.br
    venv/bin/python scripts/indexnow.py https://bardavila.bar

O buscador confere a chave em https://<host>/<chave>.txt (rota indexnow_chave).
Resposta 200/202 = recebido; o rastreamento acontece depois, no tempo do buscador.
"""
import json
import os
import re
import sys
import urllib.request
from urllib.parse import urlparse

CHAVE = os.environ.get('INDEXNOW_KEY', '6639fef929c816ee0aa2818c182b954f')


def main(base='https://feiradebarao.com.br'):
    xml = urllib.request.urlopen(f'{base}/sitemap.xml', timeout=30).read().decode()
    urls = re.findall(r'<loc>([^<]+)</loc>', xml)
    host = urlparse(base).netloc
    # Só URLs do próprio host: o IndexNow recusa o lote inteiro se vier outro domínio.
    urls = [u for u in urls if urlparse(u).netloc == host]
    corpo = json.dumps({'host': host, 'key': CHAVE, 'keyLocation': f'https://{host}/{CHAVE}.txt',
                        'urlList': urls}).encode()
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=corpo, method='POST',
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f'{len(urls)} URLs enviadas: HTTP {r.status}')
    except urllib.error.HTTPError as e:
        print(f'{len(urls)} URLs recusadas: HTTP {e.code} {e.read().decode()[:200]}')
        sys.exit(1)


if __name__ == '__main__':
    main(*sys.argv[1:])
