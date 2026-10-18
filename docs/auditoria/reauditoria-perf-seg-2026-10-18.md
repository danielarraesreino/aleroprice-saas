# Reauditoria de desempenho, segurança e operação — 18/10/2026

Depois das correções publicadas em 18/10 (`10d9f34`, `eb6410c`; o deploy `8db8f7a`, só de
documentação, entrou durante a medição). Somente leitura: sem banco, sem login, sem
formulário, sem deploy. Método: `curl -w` (2 chamadas seguidas), navegador embutido em 375×812
(`performance.getEntriesByType`, LCP e CLS por `PerformanceObserver`), leitura do código e
Vercel (`get_runtime_errors`, `get_runtime_logs`, `list_deployments`). Critério de segurança:
só achados com ≥80% de confiança e cenário concreto.

| | Antes (17/10) | Agora | Por quê |
|---|---|---|---|
| **Desempenho** | 7 | **8,5** | Tudo o que o visitante abre sai da borda (HIT, TTFB ~0,11 s); Bar da Vila caiu de 1.361 KB para 557 KB; estáticos não passam mais pela função |
| **Segurança** | 5 | **7** | S3–S7 corrigidos no código; sobra um desvio no filtro do open redirect e duas pendências do dono que não consegui confirmar (S1 e S2) |
| **Operação** | 6 | **7** | Nenhum erro de runtime registrado (antes: 11 grupos de 500 do Neon); ainda falta medir o que importa (Analytics só no login/painel) e barrar varreduras |

## Medições (mobile 375, produção)

| Página | TTFB curl (1ª / 2ª) | Cache borda | HTML | Total / req | LCP (elemento) | CLS |
|---|---|---|---|---|---|---|
| feiradebarao.com.br/ | 122 / 103 ms | HIT / HIT | 24 KB | 146 KB / 24 (antes 465 KB) | 592 ms (texto `.gravata-lead`) | 0 |
| bardavila.bar/ | 110 / 123 ms | HIT / HIT (antes MISS) | 21 KB | **557 KB / 11** (antes 1.361 KB) | 224 ms (texto `span.b`) | 0 |
| /bar/bar-do-guiu | 119 / 114 ms | HIT / HIT (antes MISS) | 24 KB | 76 KB / 4 | 400 ms (texto) | 0 |
| bardavila.bar/bar/bar-da-vila/cardapio | 197 / 204 ms | **MISS / MISS** | 3 KB | 101 KB / 5 (antes 326 KB) | 272 ms (texto) | 0 |
| /auth/login | 175 / 153 ms | MISS (correto: tem sessão) | 1,5 KB | 79 KB / 8 | 260 ms | 0 |

- `/static/*` vem da borda **sem passar pela função**: `foto-3-400.webp` MISS 235 ms → HIT 82 ms,
  sem `Server-Timing` e sem linha no log da função; `Cache-Control: public, max-age=86400,
  s-maxage=604800` (rotas `/static/img/*` e `/static/*.ext` do `vercel.json`).
- Todas as métricas estão bem dentro do "bom" (LCP < 2,5 s, CLS < 0,1, TTFB < 0,8 s). Pela regra
  da skill web-perf, o que sobra é ganho de bytes, não de Core Web Vitals.

## O que melhorou (verificado)

- **Cache de borda nos bares** (`publico/views.py:189-196`): HTML sem token de sessão, `Vary:
  Cookie` removido; o CSRF vem de `/novidades/token` (`no-store`). Conferido: nenhum
  `csrf_token` no HTML em cache.
- **Imagens WebP 400/800 com `srcset`** nos cards e na galeria do Bar da Vila e no cardápio.
- **Leaflet com `defer`** e CSS não bloqueante na vitrine; DataTables/animate.css saíram do login.
- **Código-fonte fora do ar:** `/run.py`, `/requirements.txt`, `/app/config.py`, `/app/__init__.py`,
  `/api/index.py`, `/vercel.json`, `/CLAUDE.md` e `/.env` → **404**.
- **Cabeçalhos** nos dois domínios: `nosniff`, `Referrer-Policy`, `X-Frame-Options: SAMEORIGIN`,
  `Permissions-Policy`, HSTS de 2 anos. Cookie `session` com `Secure; HttpOnly; SameSite=Lax`.
- **S3 (open redirect)** fechado para `//evil` e `/\evil` (teste local abaixo). **S4** `ProxyFix(x_for=1)`
  quando `VERCEL` (`app/__init__.py:33-35`); **S5** login limitado por IP (20/15 min) e por e-mail
  (8/15 min); `is_active` respeitado no login e na sessão aberta; **S6** concierge com limite e
  `texto[:300]`; **S7** `X-Seed-Token` por header e `/bootstrap-demo` → 404 (SEED_TOKEN fora).
- `X-Forwarded-Host` forjado é ignorado: a Vercel reescreve (testado com query única, a vitrine
  continuou a da Feira). Links de Instagram/Facebook só com `https://`.
- **O1/O2:** handler de `OperationalError` descarta o pool e repete o GET uma vez (`_r=1`);
  `get_runtime_errors` (7 dias) → **nenhum erro**. `import os` corrigido em `configsite/views.py`.

## Achados restantes

### Segurança

**R1 · MÉDIO — O filtro do `next` no login ainda deixa passar `/<TAB>/dominio`** · Esforço **P**
- Evidência: teste local (`create_app('testing_site')`, test client, usuário fictício em SQLite).
  `POST /auth/login?next=%2F%09%2Fevil.example` → `302`, header bruto `Location: '/\t/evil.example'`.
  O parser de URL do navegador (WHATWG) apaga TAB e quebra de linha antes de resolver, então
  o destino vira `//evil.example`, outro domínio. `next=%2F%0A...` derruba a view em 500
  (`ValueError: Header values must not contain newline characters`).
- Cenário: o mesmo do S3: link `feiradebarao.com.br/auth/login?next=/%09/golpe.com/login`. O dono
  do bar digita a senha certa e cai numa cópia que diz "senha incorreta" e captura a senha.
- Correção (`auth/views.py:52-58`): recusar qualquer caractere < 0x20 e validar com
  `urlsplit(next)`: exigir `scheme == ''`, `netloc == ''` e o começo em `/`, sem `//` nem `\`.
  Somar um teste com `\t`, `\n` e `%09`.

**Pendências do dono, não verificáveis sem o banco/painel** (seguem da auditoria anterior):
S1, desativar `ze@bardoze.com` e `demo@alero.com.br` (a senha vazou no histórico público), e
S2, revogar a chave NVIDIA do commit `d61d507`. O código novo não grava mais senha fixa
(`run.py:486`, `secrets.token_urlsafe`), mas a senha antiga continua válida até alguém trocá-la.

Endurecimento (não é vulnerabilidade comprovada, **P** cada):
- Falta `Content-Security-Policy` (pelo menos `frame-ancestors 'self'; base-uri 'self'; object-src 'none'`).
- O `run.py:246` ainda aceita `?token=` como alternativa ao header. Hoje está inerte (SEED_TOKEN
  fora), mas o token iria para o log se voltasse a ser usado.
- O limite de tentativas vive na memória de cada instância e zera no cold start e com mais de
  5.000 chaves (`tenant.py:30`). Para o login do superadmin, somar uma regra no Vercel Firewall
  (`POST /auth/login`) e, depois, 2FA.

### Desempenho

**P1 · MÉDIO — O cardápio do QR da mesa não sai da borda** · Esforço **P**
- Evidência: `bardavila.bar/bar/bar-da-vila/cardapio` → `cache-control: public, max-age=0,
  must-revalidate`, `vary: Cookie`, `x-vercel-cache: MISS` nas 2 chamadas, TTFB ~200 ms. Com a
  função quente está bom, mas o primeiro cliente depois de um tempo parado paga cold start
  (~0,9–1,0 s no `BOOT_TIMING`) mais o Neon acordando, sentado na mesa e no 4G.
- Correção: aplicar em `cardapio()` (`publico/views.py:678`) a mesma regra de `_render_landing`:
  sem cookie de sessão e sem args, `Cache-Control: public, s-maxage=300,
  stale-while-revalidate=86400` e `session.accessed = False`.

**P2 · BAIXO — A capa do Bar da Vila ainda é o JPEG de 251 KB, com preload de prioridade alta** · **P**
- Evidência: `<link rel="preload" as="image" fetchpriority="high" href="/static/img/bar/foto-18.jpg">`
  e `.hero-bg` com `background-image` do mesmo JPEG (`site/landing.html:679`). Já existe
  `foto-18-800.webp`. O LCP é texto (224 ms), então o ganho fica em ~180 KB no 4G e numa banda
  que hoje disputa com as fontes, sem efeito no LCP.
- Correção: `image-set()` com o WebP 800 (ou trocar `hero_foto` para o `.webp`) e o preload com
  `imagesrcset`.

**P3 · BAIXO — Fontes e bibliotecas por página** · **P**
- Bar da Vila: 4 famílias (Monoton, Anton, Fraunces, Bebas Neue), ~143 KB de woff2. Vitrine:
  Font Awesome 6.4 inteiro (18 KB CSS + fontes) para poucos ícones. Login: Bootstrap + FA 6.0 +
  jQuery síncronos (79 KB) numa tela com 2 campos. Nada disso afeta o LCP medido; vale fazer
  quando mexer nesses templates.

### Operação

**O1 · MÉDIO — O Speed Insights e o Web Analytics só medem o login e o painel** · Esforço **P**
- Evidência: os scripts `/_vercel/speed-insights` e `/_vercel/insights` estão só em
  `app/templates/base.html:191-192`. As páginas públicas (vitrine, bardavila.bar, prévias e
  cardápio) têm **0** referências. Os dados de visitante real (Core Web Vitals, origem) não
  existem justamente onde está o público.
- Correção: incluir os dois `<script defer>` em `produto/landing.html`, `site/landing.html`,
  `site/cardapio.html` e nos modelos de prévia.

**O2 · BAIXO — `/favicon.ico` acorda a função em toda visita e responde 404** · **P**
- Evidência: o log tem `GET /favicon.ico ... 404` depois de cada página nos dois domínios
  (04:35:22, 04:36:02, 04:36:26, 04:38:11). A rota estática só cobre `/static/*`.
- Correção: em `vercel.json`, `{"src": "/favicon.ico", "dest": "/app/static/favicon.ico"}` com o
  mesmo `Cache-Control`, antes do rewrite final.

**O3 · BAIXO — Varreduras ainda executam Python** · **P**
- `/wp-admin/install.php`, `/x.php` e `/.env` chegam à função (no log). Uma regra no Firewall
  (negar `*.php`, `/wp-*`, `/.env`) ou uma rota 404 no `vercel.json` corta essas invocações.
  Não consultei a configuração do Firewall (a API exige `configVersion`).

**O4 · BAIXO — Pendências de configuração**
- `www.bardavila.bar` responde **200** (conteúdo duplicado); `www.feiradebarao.com.br` já faz 308.
- Os logs de 1 h continuam, e não deu para confirmar o `SENTRY_DSN` (sem leitura das envs).
- O log de acesso sempre mostra `127.0.0.1`, porque é o socket do servidor interno da Vercel e
  não o `remote_addr` depois do `ProxyFix`. O IP real está correto **pelo código**, mas não dá
  para vê-lo no log. Sugestão: logar `request.remote_addr` nas linhas de 429 para confirmar.

## Ordem sugerida
1. R1 (filtro do `next`) e P1 (cache do cardápio): os dois são P, de uma linha cada mais o teste.
2. O1 (Analytics nas páginas públicas) e O2 (favicon).
3. Pendências do dono: S1/S2, `www.bardavila.bar` → 308, Sentry, regra de Firewall.
4. P2/P3 e CSP quando mexer nos templates.
