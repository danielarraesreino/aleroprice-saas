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

## Stack

- Flask 2.3 (app factory em `app/__init__.py:create_app`), Flask-SQLAlchemy 3.1, Flask-Migrate/Alembic, Flask-Login
- Postgres em produção (`DATABASE_URL`), SQLite em dev (`instance/alerodb.sqlite`)
- pandas/numpy (dashboard, previsão, importação de vendas), `thefuzz` (match de nome de prato), `xmltodict` + `pydantic` (parser NF-e), `openpyxl` (xlsx)
- Stripe (billing), Sentry (opcional, ativa só se `SENTRY_DSN` existir)
- Deploy: Render/qualquer container (`Procfile`, `render.yaml`) — Vercel existe (`api/index.py`, `vercel.json`) mas é o caminho ruim pra essa stack (FS read-only, pandas pesado)

## Mapa do código

| Caminho | Papel |
|---|---|
| `app/__init__.py` | app factory, registro de blueprints, **guard global de login** |
| `app/config.py` | `DevelopmentConfig` / `TestingConfig` / `ProductionConfig` |
| `app/extensions.py` | `db`, `migrate`, `login_manager` |
| `app/cli.py` | `flask create-tenant` — único jeito oficial de provisionar tenant via CLI |
| `app/models/` | 20+ modelos, um arquivo por domínio (`modelo_*.py`) |
| `app/routes/<dominio>/views.py` | um blueprint por domínio |
| `app/utils/` | cálculos, parser NF-e, importação de vendas, filtros BR, tenant |
| `app/templates/` | Jinja2; `site/` = site público, resto = sistema interno |
| `app/scripts/`, `scripts/` | seeds e populadores de demo |
| `migrations/versions/` | 7 migrations Alembic |
| `tests/` | `unit/`, `integration/`, `e2e/` (Playwright) + `conftest.py` |

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

**4. Formatação é brasileira.** Use os filtros Jinja registrados em
`app/utils/template_filters.py` (`moeda_br`, `peso_br`, `percentual_br`,
`data_br`, `numero_br`), não formate à mão no template.

**5. Endpoints destrutivos são gated.** `/debug-db`, `/seed-vegan` e `/reset-db`
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

# testes
pytest tests/unit tests/integration      # rápido
pytest tests/e2e                         # Playwright, precisa do app no ar
```

## Armadilhas conhecidas (dívida real, não teoria)

- `run.py` roda `db.create_all()` **no import**, e as migrations Alembic ficam comentadas nesse caminho. Schema em produção pode divergir do histórico de migrations.
- `billing/success` marca `subscription_tier='pro'` **sem verificar a sessão no Stripe** (otimista). O webhook (`billing.webhook`) não faz a ativação — o handler de `checkout.session.completed` é um `pass`.
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
