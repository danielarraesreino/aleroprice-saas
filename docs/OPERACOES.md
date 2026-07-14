# Operações — env, deploy, billing, runbook

## Variáveis de ambiente

Fonte: `.env.example`, `app/config.py`, `run.py`, `app/routes/billing/views.py`,
`app/routes/publico/views.py`.

| Var | Obrigatória | Efeito |
|---|---|---|
| `SECRET_KEY` | sim em prod | Assina sessão. Fora de `production` tem fallback hardcoded — não confie nele |
| `DATABASE_URL` | sim em prod | Postgres. `postgres://` é convertido pra `postgresql://`. **Se faltar em `production`, cai em SQLite in-memory e os dados somem no restart** |
| `JWT_SECRET_KEY` | não | Cai no `SECRET_KEY` |
| `APP_ENV` | recomendado | `production` \| `development` \| `testing`. Tem prioridade sobre a detecção de plataforma |
| `STRIPE_SECRET_KEY` | pro billing | Se contiver `test_PLACEHOLDER`, checkout e webhook viram **mock** (sucesso simulado) |
| `STRIPE_PUBLISHABLE_KEY` | pro billing | — |
| `STRIPE_WEBHOOK_SECRET` | pro billing | Valida assinatura do webhook |
| `STRIPE_PRICE_ID_PRO` | pro billing | Price do plano padrão |
| `STRIPE_PRICE_ID_VOLUME` | A/B | Price usado quando `pricing_strategy == 'volume_based'` |
| `SENTRY_DSN` | não | Ausente = Sentry desligado (no-op silencioso) |
| `SENTRY_TRACES_SAMPLE_RATE` | não | Default `0.0` (só erros) |
| `CALLMEBOT_APIKEY` | não | Sem ela, o alerta de reserva no WhatsApp não dispara (o botão wa.me segue como fallback) |
| `CALLMEBOT_PHONE` | não | Default: `5519999779942` (WhatsApp do Bar da Vila, hardcoded em `publico/views.py`) |
| `ENABLE_ADMIN_ENDPOINTS` | **não setar** | `=1` + config ≠ production registra `/debug-db`, `/seed-vegan`, `/reset-db` |
| `VERCEL`, `RAILWAY_ENVIRONMENT` | auto | Injetadas pela plataforma; forçam `production` |

## Deploy

**Render (recomendado)** — `render.yaml` já descreve o serviço
`aleroprice-bardavila`: Python 3.11.9, `pip install -r requirements.txt`,
`gunicorn run:app --workers 2 --timeout 120`, healthcheck em `/auth/login`.
`SECRET_KEY` e `DATABASE_URL` ficam como secrets (`sync: false`).

**Qualquer container** — `Procfile` funciona igual (Railway, Fly, Heroku-like).
Basta `APP_ENV=production` + `DATABASE_URL`.

**Vercel** — existe (`vercel.json` reescreve tudo pra `api/index.py`), mas é o
caminho ruim: filesystem read-only (daí o hack de `instance_path='/tmp'` no
`create_app`), pandas/numpy pesados e o processo é efêmero. O projeto está
linkado (`.vercel/project.json`) por histórico; o piloto roda em container.
Detalhe histórico: o pacote de rotas se chama `publico/` e não `public/` porque a
Vercel remove diretórios chamados `public`.

## Banco

`run.py` executa `db.create_all()` **no import** (não só no `__main__`) e o
`upgrade()` do Alembic está comentado nesse caminho. Consequências:

- Tabelas nascem do metadata atual, não do histórico de migrations.
- As tabelas do site (`site_*`, `evento`, `promocao`, `reserva`) só existem por
  causa disso — não há migration pra elas.
- Schema em produção pode divergir do que `flask db upgrade` produziria.

Ao mexer em modelo: gere a migration (`flask db migrate` / `flask db upgrade`) e
saiba que o `create_all` pode mascarar o erro em dev.

## Provisionar um cliente

```bash
flask create-tenant --restaurante "Bar da Vila" \
    --email dono@bardavila.com --nome "Gustavo" [--senha SENHA] [--cnpj ...]
```

Idempotente no e-mail (aborta com exit 1 se o usuário já existe). Sem `--senha`,
gera uma de 14 caracteres e imprime **uma única vez**.

Alternativa self-serve: `/cadastro` na landing cria restaurante + admin e já loga.

## Billing — estado real

O fluxo feliz funciona, mas a ativação é otimista:

1. `POST /billing/create-checkout-session` monta a sessão no Stripe (price
   conforme `pricing_strategy`) e redireciona (303).
2. `GET /billing/success` seta `subscription_tier='pro'` e
   `subscription_status='active'` **sem consultar o Stripe**. Quem acessar a URL
   de sucesso logado vira Pro.
3. `POST /billing/webhook` valida a assinatura, mas o branch de
   `checkout.session.completed` é um `pass` — não ativa nem desativa nada.

Não há tratamento de `past_due` / `canceled` / churn. `subscription_status` só é
escrito no `success`.

## Runbook rápido

```bash
# dev local
python run.py                                 # :5000, roda upgrade() antes de subir

# testes
pytest tests/unit tests/integration
pytest tests/e2e                              # Playwright, app precisa estar no ar

# cobertura (config em .coveragerc, saída em htmlcov/)
pytest --cov=app --cov-report=html
```

## Higiene do repo

Coisas que já eram lixo quando este doc foi escrito e podem ser removidas sem dó:
`htmlcov/` versionado, `__pycache__/`, o symlink `AleroPrice`, `de/`, `nf e/`,
`Trabalho/`, os runners de teste legados na raiz (`run_all_tests.py`,
`run_tests*.sh`, `run_tests*.py`, `test_e2e_selenium.py`, `verify_*.py`) e os
templates duplicados `*_fixed.html`.
