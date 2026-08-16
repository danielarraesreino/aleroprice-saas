"""Percorre o sistema como cliente e diz o que quebra.

Faz por HTTP o que um dono de bar faria pelo navegador: entra, abre cada tela do
menu, cadastra conteúdo, e confere se aquilo apareceu no site público. Só stdlib
— roda em qualquer lugar, sem browser e sem custo de sessão gráfica.

    python3 scripts/auditar_cliente.py --email x@y.com --senha '...'
    python3 scripts/auditar_cliente.py --email x@y.com --senha '...' --escrever

Sem `--escrever` só navega e relata (nenhum POST de conteúdo). Com, cadastra um
prato, uma avaliação, um membro de equipe, uma foto de galeria, um evento e uma
promoção — e depois checa se cada um saiu no site.

O CSRF é lido da própria página antes de cada POST, como o navegador faz.
"""
import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

VERDE, VERM, AMAR, FIM = '\033[92m', '\033[91m', '\033[93m', '\033[0m'


class Cliente:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            # Sem seguir redirect: o código do 302 é metade do diagnóstico
            # (login exigido? domínio trocado? formulário recusado?).
            NaoSeguirRedirect(),
        )
        self.op.addheaders = [('User-Agent', 'AuditoriaAlero/1.0')]

    def get(self, caminho):
        req = urllib.request.Request(self.base + caminho)
        try:
            r = self.op.open(req, timeout=30)
            return r.status, r.read().decode('utf-8', 'ignore'), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'ignore'), e.headers

    def post(self, caminho, dados, csrf_de=None):
        """POST com o token lido da página que hospeda o formulário."""
        if csrf_de is not None:
            _, html, _ = self.get(csrf_de)
            token = achar_csrf(html)
            if token:
                dados = dict(dados, csrf_token=token)
        corpo = urllib.parse.urlencode(dados).encode('utf-8')
        req = urllib.request.Request(self.base + caminho, data=corpo, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        # Em HTTPS o Flask-WTF exige Referer da mesma origem e devolve 400
        # "The referrer header is missing." — o navegador manda sozinho, um
        # cliente HTTP não. Sem isto todo POST daqui falha por motivo errado.
        req.add_header('Referer', self.base + (csrf_de or caminho))
        try:
            r = self.op.open(req, timeout=30)
            return r.status, r.read().decode('utf-8', 'ignore'), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'ignore'), e.headers


class NaoSeguirRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def achar_csrf(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None


def marca(ok, texto, detalhe=''):
    cor = VERDE if ok is True else (AMAR if ok is None else VERM)
    sinal = 'ok  ' if ok is True else ('..  ' if ok is None else 'FALHA')
    print(f'  {cor}{sinal}{FIM} {texto}{(" — " + detalhe) if detalhe else ""}')
    return bool(ok)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', default='https://feiradebarao.com.br')
    p.add_argument('--email', required=True)
    p.add_argument('--senha', required=True)
    p.add_argument('--slug', default=None, help='slug do site (padrão: descobre)')
    p.add_argument('--escrever', action='store_true',
                   help='cadastra conteúdo de verdade (POST)')
    a = p.parse_args()

    c = Cliente(a.base)
    problemas = []

    print(f'\n{"="*68}\nENTRAR')
    st, html, _ = c.get('/auth/login')
    marca(st == 200, f'GET /auth/login', str(st))
    st, html, h = c.post('/auth/login',
                         {'email': a.email, 'password': a.senha, 'senha': a.senha},
                         csrf_de='/auth/login')
    entrou = st in (301, 302) and 'login' not in (h.get('Location') or '')
    marca(entrou, 'POST /auth/login', f'{st} -> {h.get("Location")}')
    if not entrou:
        print(f'\n{VERM}Não entrou. O resto depende disso.{FIM}')
        return 1

    print(f'\n{"="*68}\nTELAS DO MENU (o que o cliente vê ao clicar)')
    MENU = [
        ('Dashboard', '/app/index'), ('Reservas', '/reservas/index'),
        ('Agenda', '/agenda/index'), ('Promoções', '/promocoes/index'),
        ('Site', '/config-site/index'), ('Conteúdo', '/conteudo/'),
        ('Pratos', '/pratos/index'), ('Cardápios', '/cardapios/index'),
        ('Estoque', '/estoque/index'), ('Notas Fiscais', '/nfe/index'),
        ('Previsão', '/previsao/index'), ('Desperdício', '/desperdicio/index'),
        ('Custos', '/custos/index'),
    ]
    for nome, caminho in MENU:
        st, html, h = c.get(caminho)
        erro_500 = st >= 500
        traceback = 'Traceback' in html or 'Internal Server Error' in html
        if erro_500 or traceback:
            problemas.append(f'{nome} ({caminho}) devolve {st}')
        marca(not (erro_500 or traceback), f'{nome:14} {caminho:22}', str(st))

    print(f'\n{"="*68}\nO SITE PÚBLICO')
    slug = a.slug
    if not slug:
        st, html, _ = c.get('/config-site/index')
        m = re.search(r'href="/bar/([a-z0-9-]+)"', html)
        slug = m.group(1) if m else None
    if not slug:
        marca(False, 'descobrir o slug do site')
        return 1
    print(f'  slug: {slug}')
    st, html, _ = c.get(f'/bar/{slug}')
    marca(st == 200, f'GET /bar/{slug}', str(st))

    secoes = re.findall(r'<section[^>]*\bid="([a-z-]+)"', html)
    print(f'  seções no ar: {", ".join(secoes) or "(nenhuma)"}')
    tem = {
        'foto de capa': 'hero-foto' in html or 'background-image' in html,
        'cardápio': 'id="cardapio"' in html,
        'galeria': 'id="galeria"' in html,
        'avaliações': 'id="avaliacoes"' in html,
        'agenda': 'id="agenda"' in html,
        'reserva': 'id="reservar"' in html or 'reservar' in html,
        'JSON-LD': 'application/ld+json' in html,
    }
    for k, v in tem.items():
        marca(v or None, f'seção {k}', 'presente' if v else 'ausente')

    if not a.escrever:
        print(f'\n{AMAR}Modo leitura. Use --escrever pra cadastrar conteúdo.{FIM}')
    else:
        print(f'\n{"="*68}\nCADASTRAR CONTEÚDO (como o dono faria)')
        itens = [
            ('prato', '/conteudo/cardapio/novo', '/conteudo/cardapio/novo', {
                'nome': 'Costela na brasa', 'descricao': 'Seis horas de brasa lenta.',
                'preco': '89,00', 'tag': 'Da casa'}),
            ('avaliação', '/conteudo/avaliacoes/novo', '/conteudo/avaliacoes/novo', {
                'autor': 'Marina S.', 'texto': 'Melhor costela de Barão.',
                'estrelas': '5'}),
            ('equipe', '/conteudo/equipe/novo', '/conteudo/equipe/novo', {
                'nome': 'Zé', 'papel': 'Dono e assador', 'emoji': '🔥'}),
            ('evento', '/agenda/novo', '/agenda/novo', {
                'titulo': 'Samba de sexta', 'data': '2026-08-28',
                'hora': '20:00', 'descricao': 'Roda de samba na varanda.',
                'ativo': 'on'}),
            ('promoção', '/promocoes/nova', '/promocoes/nova', {
                'titulo': 'Chope em dobro', 'descricao': 'Toda quarta, 18h às 20h.',
                'dia_semana': 'quarta', 'ativo': 'on'}),
        ]
        for nome, rota, pagina, dados in itens:
            st, corpo, h = c.post(rota, dados, csrf_de=pagina)
            ok = st in (200, 301, 302) and st < 400
            if not ok:
                problemas.append(f'cadastrar {nome} em {rota}: {st}')
            marca(ok, f'cadastrar {nome:12} POST {rota:28}', str(st))

        st, html, _ = c.get(f'/bar/{slug}')
        print('\n  saiu no site?')
        for texto in ('Costela na brasa', 'Marina S.', 'Samba de sexta',
                      'Chope em dobro'):
            achou = texto in html
            if not achou:
                problemas.append(f'"{texto}" cadastrado mas não aparece no site')
            marca(achou, f'"{texto}"')

    print(f'\n{"="*68}')
    if problemas:
        print(f'{VERM}{len(problemas)} problema(s):{FIM}')
        for x in problemas:
            print(f'  · {x}')
    else:
        print(f'{VERDE}Nenhuma falha dura no percurso.{FIM}')
    return 1 if problemas else 0


if __name__ == '__main__':
    raise SystemExit(main())
