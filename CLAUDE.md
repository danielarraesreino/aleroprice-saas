# AleroPrice SaaS — guia do repositório

Documento escrito a partir da leitura do código (não dos .md legados, que estão
desatualizados). Fonte da verdade: `app/`, `run.py`, `migrations/`.

## O que é

SaaS multi-tenant de **gestão de custos e precificação para restaurantes**, em
Flask + SQLAlchemy, servido em HTML renderizado no servidor (Jinja2). Cada
restaurante é um tenant (`Restaurante`); o app cobre a cadeia completa:

```
NF-e (XML) → Produto/Estoque → Prato (ficha técnica) → Cardápio → Venda → Dashboard/Previsão
```

Em cima disso existe uma segunda camada, mais recente: um **site público por
tenant** (landing, reservas, eventos, promoções, cardápio digital), usada hoje
pelo piloto "Bar da Vila".

Monetização: plano `free` vs `pro` via Stripe, com A/B de estratégia de preço
(`standard` vs `volume_based`).

**Em produção hoje (out/2026) o produto é só o site + o admin do site.** A
gestão de custos (estoque, NF-e, pratos, cardápios, custos, previsão,
desperdício, agentes) está **desligada**: `GESTAO_ATIVA` (env, padrão `0`) não
registra esses blueprints, `pode('gestao')` devolve False e `/app` vira a home
"Seu site" (só `dashboard.index` e `dashboard.upgrade` respondem). Motivo e
lista do que está quebrado: [`docs/AVALIACAO_GESTAO_2026-10.md`](docs/AVALIACAO_GESTAO_2026-10.md).
Religar = `GESTAO_ATIVA=1` + instalar `requirements-gestao.txt`.

Os domínios `feiradebarao.com.br` e `bardavila.bar` ficam no projeto Vercel
**`aleroprice-bardavila`** (não no `aleroprice-saas`); os dois fazem deploy do
mesmo repo a cada push.

A função roda em **`gru1` (São Paulo)** por `regions` no `vercel.json`, colada no
banco Neon (`alerosaas`, sa-east-1). Em `iad1` (padrão) cada ida ao banco custava
~180 ms e a página de barraca levava ~2 s; em `gru1`, ~50 ms. Não mude a região
sem mudar o banco junto. `Server-Timing: app;dur=…` e o log `DB_CONNECT` (em
`run.py`) servem para conferir.

## Stack

- Flask 2.3 (app factory em `app/__init__.py:create_app`), Flask-SQLAlchemy 3.1, Flask-Migrate/Alembic, Flask-Login
- Postgres em produção (`DATABASE_URL`), SQLite em dev (`instance/alerodb.sqlite`)
- Só na gestão (`requirements-gestao.txt`): pandas/numpy (previsão, importação, exports), `thefuzz` (match de nome de prato), `xmltodict` + `pydantic` (parser NF-e), `openpyxl` (xlsx). `requirements.txt` é o do site, enxuto para caber na Vercel
- Stripe (billing), Sentry (opcional, ativa só se `SENTRY_DSN` existir)
- Deploy: Render/qualquer container (`Procfile`, `render.yaml`) — Vercel existe (`api/index.py`, `vercel.json`) mas é o caminho ruim pra essa stack (FS read-only, pandas pesado)

## Mapa do código

| Caminho | Papel |
|---|---|
| `app/__init__.py` | app factory, registro de blueprints, **guard global de login** |
| `app/config.py` | `DevelopmentConfig` / `TestingConfig` / `ProductionConfig` |
| `app/extensions.py` | `db`, `migrate`, `login_manager`, `csrf` |
| `app/cli.py` | `flask create-tenant` — único jeito oficial de provisionar tenant via CLI |
| `app/models/` | 20+ modelos, um arquivo por domínio (`modelo_*.py`) |
| `app/routes/<dominio>/views.py` | um blueprint por domínio |
| `app/utils/` | cálculos, parser NF-e, importação de vendas, filtros BR, tenant |
| `app/templates/` | Jinja2; `site/` = site público, resto = sistema interno |
| `app/scripts/`, `scripts/` | seeds e populadores de demo |
| `migrations/versions/` | 17 migrations Alembic |
| `tests/` | `unit/`, `integration/`, `e2e/` (Playwright) + `conftest.py` |

## Design: obrigatório (não pule)

Quem altera a aparência de qualquer site (você, outra IA, um dev) segue isto. O mecanismo está em
`.claude/settings.json` (hook que lembra ao editar) e `tests/integration/test_contrato_design.py` (gate).

- Editar `app/templates/site/**` (modelos de bar e de expositor): invocar a skill **`design-feira`** antes
  de abrir o arquivo; ler o modelo de bar-fonte (`.claude/skills/design-feira/references/receitas.md`).
- Editar `app/templates/produto/**` ou `app/static/css/feira*.css` (portal): `impeccable` + `frontend-design`.
- Precedência: palavra do dono > bardavila.bar (`site/landing.html`) > `docs/DESIGN.md` > `design-feira` > skills genéricas.
- Hotsite que parece menos trabalhado que os modelos de bar **não está pronto**, mesmo com teste verde.
- Entrega = capturas (320/390/768/1440, claro/escuro, com e sem foto) + suíte verde + OK do dono. Sem deploy sem OK.
- Imagem só com origem registrada (`creditos.json` ou `AUTORIZADO.txt`); nada de foto ampliada de miniatura.
- Vocabulário: expositor (quem vende na Feira), barraca (ponto físico), bar (casa de bebida). Feira = Praça do Coco.
- Mapa completo das skills e do acionamento: `~/Documentos/FEIRADEBARAO/documentacao/09_SKILLS_MAPA_E_ACIONAMENTO.md`.

## Regras que valem pra qualquer alteração

**1. Multi-tenancy é manual e obrigatório.** Não existe filtro automático de
tenant. Toda query em modelo com `restaurant_id` precisa filtrar
explicitamente:

```python
from app.utils.tenant import get_current_restaurant_id
restaurant_id = get_current_restaurant_id()
Produto.query.filter_by(restaurant_id=restaurant_id)
```

Esquecer o filtro = vazamento de dados entre restaurantes. Toda tabela de
negócio tem `restaurant_id` FK pra `restaurante.id` (migration
`7fc1334eef20_enforce_non_nullable_restaurant_id`).

**2. Login é enforçado globalmente, não por rota.** `app/__init__.py` tem um
`@app.before_request` que exige `current_user.is_authenticated` em tudo, exceto:
`static`, `auth.login`, `auth.logout`, `billing.webhook` e qualquer endpoint do
blueprint `public.*` (landing, cadastro, reservas, calculadora de ROI). Rota
nova nasce protegida por padrão — se precisar ser pública, tem que entrar nessa
allowlist conscientemente.

**3. Gating de plano é `@pro_required`** (`app/utils/decorators.py`): checa
`restaurante.subscription_tier != 'pro'` e redireciona pra `dashboard.upgrade`.
Hoje só os relatórios avançados do dashboard usam.

**4. Todo POST precisa de token de CSRF.** `CSRFProtect` está ligado em
`create_app`. Formulário novo nasce com

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

e POST por `fetch` manda o token no corpo (`FormData(form)` já leva o input
hidden) ou no header `X-CSRFToken`. Duas exceções, marcadas com `@csrf.exempt`
onde a rota vive: `billing.webhook` (o Stripe autentica por assinatura HMAC) e
`bootstrap_demo` em `run.py` (curl de manutenção, gated por `SEED_TOKEN`).
`tests/integration/test_csrf.py` varre `app/templates/` e falha se algum
`<form method="post">` ficar sem token.

**5. Formatação é brasileira.** Use os filtros Jinja registrados em
`app/utils/template_filters.py` (`moeda_br`, `peso_br`, `percentual_br`,
`data_br`, `numero_br`), não formate à mão no template.

**6. Endpoints destrutivos são gated.** `/debug-db`, `/seed-vegan` e `/reset-db`
(faz `db.drop_all()`) só existem quando `ENABLE_ADMIN_ENDPOINTS=1` **e** o
config não é `production` (`run.py`). Não afrouxe isso.

## Comandos

```bash
# dev
python run.py                      # sobe em :5000, roda alembic upgrade antes

# tenant novo (não há signup admin via CLI; há /cadastro self-serve no site)
flask create-tenant --restaurante "Bar da Vila" --email dono@x.com --nome "Gustavo"

# migrations
flask db migrate -m "descricao" && flask db upgrade

# testes (requirements-dev.txt já inclui o da gestão; a config `testing` liga
# a gestão, `testing_site` é o produto como roda em produção)
pytest tests/unit tests/integration      # rápido
pytest tests/e2e                         # Playwright, precisa do app no ar
```

## Armadilhas conhecidas (dívida real, não teoria)

- `run.py` alinha o schema (`db.create_all()` + colunas novas) **no import só fora de produção**. Em produção isso custava ~7s de cada cold start e saiu do boot: depois de deploy com model/coluna nova, rode `/bootstrap-demo?token=…&action=schema` (precisa `SEED_TOKEN` setada no `aleroprice-bardavila`) ou suba com `SCHEMA_NO_BOOT=1`. Migrations Alembic seguem fora desse caminho, então o schema de produção pode divergir do histórico.
- A home do produto (`public.landing` no domínio do produto, visitante sem sessão) sai com `s-maxage=300, stale-while-revalidate` e é servida pela borda da Vercel: mudanças na vitrine (ex.: barraca desligada) podem levar alguns minutos para aparecer.
- Billing: `billing/success` confere a sessão no Stripe (e o `client_reference_id` do tenant) antes de marcar `pro`; o webhook valida a assinatura e trata `checkout.session.completed`, `subscription.*` e `invoice.*` (`app/routes/billing/views.py`). A cobrança de expositor hoje é manual (`registrar_pagamento`).
- Com `STRIPE_SECRET_KEY` contendo `test_PLACEHOLDER`, o checkout e o webhook entram em modo mock: o checkout vira sucesso simulado direto.
- `Config.SECRET_KEY` tem fallback hardcoded (`'uma-chave-secreta-dificil-de-adivinhar'`); só `ProductionConfig` exige env.
- `Prato.nome` e `Produto.codigo` são `unique=True` **globais**, não por tenant — dois restaurantes não podem ter pratos de mesmo nome.
- `ProductionConfig` sem `DATABASE_URL` cai em SQLite in-memory (boot silencioso, dados somem).
- Vários templates têm par `X.html` / `X_fixed.html` (ex.: `desperdicio/relatorios*`); confira qual a view usa antes de editar.

## Docs detalhadas

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) — camadas, fluxos, request lifecycle
- [`docs/MODELO_DOMINIO.md`](docs/MODELO_DOMINIO.md) — todas as tabelas e relações
- [`docs/ROTAS.md`](docs/ROTAS.md) — inventário de blueprints e endpoints
- [`docs/OPERACOES.md`](docs/OPERACOES.md) — env vars, deploy, billing, runbook
- [`docs/RUFLO.md`](docs/RUFLO.md) — guia de swarm/agentes gerado pelo `ruflo init`

Os `.md` na raiz (`README.md`, `PROJECT_SUMMARY.md`, `GUIA_USUARIO.md`,
`CONTEXTO_NOTEBOOKLM_V2.md`, etc.) são anteriores ao multi-tenant e ao site
público. Trate como histórico, não como referência.
