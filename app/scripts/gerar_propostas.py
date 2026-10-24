"""PDFs de proposta e do vendedor, gerados das próprias páginas do site.

Uso:  venv/bin/python -m app.scripts.gerar_propostas [--saida ~/Documentos/FEIRADEBARAO/propostas]
Renderiza /site-para-bar-em-campinas, /expor e /vendedor com o Chrome do sistema (A4, CSS de impressão).
Os valores vêm de `planos`, a mesma fonte do site: PDF e página nunca divergem.
"""
import argparse
import os
import sys
import tempfile
import threading

CHROME = '/usr/bin/google-chrome'
PAGINAS = (
    ('/site-para-bar-em-campinas', 'proposta-bar.pdf'),
    ('/expor', 'proposta-expositor.pdf'),
    ('/vendedor', 'vendedor-e-comissao.pdf'),
)
# O site esconde blocos até o scroll (reveal) e anima o hero; no PDF tudo precisa estar visível.
MOSTRAR_TUDO = '[data-reveal],[data-hero]{opacity:1!important;transform:none!important}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', default=os.path.expanduser('~/Documentos/FEIRADEBARAO/propostas'))
    args = ap.parse_args()
    if 'PROPOSTAS_DB' not in os.environ:
        # mesmo cuidado do capturar_modelos: nunca tocar o banco de desenvolvimento.
        os.environ['PROPOSTAS_DB'] = '1'
        os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mkdtemp()}/propostas.sqlite'
        os.execv(sys.executable, [sys.executable, '-m', 'app.scripts.gerar_propostas', *sys.argv[1:]])

    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    from app import create_app, db

    app = create_app('development')
    with app.app_context():
        db.create_all()
    srv = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    os.makedirs(args.saida, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=CHROME)
        for rota, arquivo in PAGINAS:
            pg = nav.new_page(viewport={'width': 1000, 'height': 1200})
            pg.goto(f'http://127.0.0.1:{srv.server_port}{rota}', wait_until='networkidle')
            pg.add_style_tag(content=MOSTRAR_TUDO)
            pg.emulate_media(media='print')
            destino = os.path.join(args.saida, arquivo)
            pg.pdf(path=destino, format='A4', print_background=True, prefer_css_page_size=True)
            pg.close()
            print('ok', destino)
        nav.close()
    srv.shutdown()


if __name__ == '__main__':
    main()
