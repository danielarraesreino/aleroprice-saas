"""Capturas de todos os modelos de site: modelo x modo x largura x com/sem foto.

Uso:  venv/bin/python -m app.scripts.capturar_modelos [--saida /tmp/capturas] [--so artesao|bar]
Sobe o app com um SQLite temporário, semeia um bar e o piloto de artesão e fotografa com o Chrome do
sistema. É o passo 4 do checklist da skill design-feira; abra as imagens ao lado do bardavila.bar.
"""
import argparse
import os
import sys
import tempfile
import threading

LARGURAS = ((320, 700), (390, 844), (768, 1024), (1440, 900))
CHROME = '/usr/bin/google-chrome'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', default='/tmp/capturas-modelos')
    ap.add_argument('--so', choices=('bar', 'artesao'))
    args = ap.parse_args()
    if 'CAPTURA_DB' not in os.environ:
        # `python -m app.scripts...` importa `app` (e lê DATABASE_URL) antes de main(): sem este
        # re-exec o script escreveria no banco de desenvolvimento em vez do SQLite temporário.
        os.environ['CAPTURA_DB'] = '1'
        os.environ['DATABASE_URL'] = f'sqlite:///{tempfile.mkdtemp()}/captura.sqlite'
        os.execv(sys.executable, [sys.executable, '-m', 'app.scripts.capturar_modelos', *sys.argv[1:]])

    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    from app import create_app, db
    from app.models.modelo_restaurante import Restaurante
    from app.models.modelo_siteconfig import SiteConfig
    from app.models.modelo_sitecontent import ProdutoSite
    from app.scripts.seed_berga import SLUG, semear
    from app.utils.modelos import MODELOS, MODELOS_ARTESAO

    app = create_app('development')
    with app.app_context():
        db.create_all()
        bar = Restaurante(nome='Bar de Captura', cnpj='55555555000155', slug='bar-captura',
                          subscription_tier='site')
        db.session.add(bar)
        db.session.commit()
        db.session.add(SiteConfig(restaurant_id=bar.id, nome='Bar de Captura', modelo='classico'))
        rest, _ = semear(no_ar=True)
        rest.tipo_conta = 'demo'
        db.session.commit()
        rid = rest.id

    srv = make_server('127.0.0.1', 0, app, threaded=True)
    porta = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    alvos = []
    if args.so != 'artesao':
        alvos += [('bar-captura', m, 'com-foto') for m in MODELOS]
    if args.so != 'bar':
        for m in MODELOS_ARTESAO:
            alvos += [(SLUG, m, 'com-foto'), (SLUG, m, 'sem-foto')]

    os.makedirs(args.saida, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=CHROME)
        for slug, modelo, foto in alvos:
            if slug == SLUG:
                with app.app_context():
                    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
                    com = foto == 'com-foto'
                    if com:
                        semear(no_ar=True)   # restitui as imagens do piloto
                    else:
                        cfg.hero_foto = cfg.logo = None
                        ProdutoSite.query.filter_by(restaurant_id=rid).update({'imagem': None})
                        db.session.commit()
            for modo in ('light', 'dark'):
                for w, h in LARGURAS:
                    pg = nav.new_page(viewport={'width': w, 'height': h}, color_scheme=modo)
                    pg.goto(f'http://127.0.0.1:{porta}/bar/{slug}?modelo={modelo}', wait_until='networkidle')
                    pg.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,60))}window.scrollTo(0,0)}")
                    pg.wait_for_timeout(900)
                    base = f'{args.saida}/{modelo}-{foto}-{modo}-{w}'
                    # full_page reabre os reveals e sai em branco; no celular (390) fotografa 3 telas rolando de verdade
                    for i, y in enumerate((0, h, 2 * h) if w == 390 else (0,)):
                        pg.evaluate(f'window.scrollTo(0,{y})')
                        pg.wait_for_timeout(700)
                        pg.screenshot(path=f'{base}-{i + 1}.png')
                    pg.close()
            print('ok', modelo, foto)
        nav.close()
    srv.shutdown()
    print('capturas em', args.saida)


if __name__ == '__main__':
    main()
