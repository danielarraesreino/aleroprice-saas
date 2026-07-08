# Deploy — Piloto (Bar da Vila)

Stack: Flask + gunicorn + Postgres. Recomendado rodar em **host de container**
(Railway ou Render), não serverless — a app usa pandas/numpy e rotas que podem
passar de 10s, o que briga com o modelo serverless.

## 1. Banco (Postgres dedicado)

Crie um Postgres gerenciado (com backup automático):
- **Neon** (https://neon.tech) → novo projeto → copie a connection string
  (`postgresql://user:senha@host/db?sslmode=require`), OU
- Novo projeto **Supabase** → Settings → Database → Connection string (URI).

Guarde a URL — é o `DATABASE_URL`.

## 2. Variáveis de ambiente (produção)

| Variável | Valor |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | aleatória: `python -c "import secrets;print(secrets.token_hex(32))"` |
| `DATABASE_URL` | a connection string do passo 1 |
| `ENABLE_ADMIN_ENDPOINTS` | **não definir** (mantém `/reset-db`, `/seed-vegan`, `/debug-db` desligados) |

Stripe fica adiado (billing off no piloto) — não precisa das chaves `STRIPE_*` ainda.

## 3. Deploy

### Railway (recomendado — deploy por git)
1. https://railway.app → New Project → Deploy from GitHub → `aleroprice-saas`.
2. Railway detecta o `Procfile` (gunicorn). Ele define `RAILWAY_ENVIRONMENT`,
   então a config `production` já ativa.
3. Variables → adicione `SECRET_KEY` e `DATABASE_URL` (APP_ENV opcional aqui).
4. Deploy. Pegue a URL pública gerada.

### Render (alternativa)
1. https://render.com → New → Blueprint → aponte para o repo (usa `render.yaml`).
2. Preencha os secrets `SECRET_KEY` e `DATABASE_URL` (marcados `sync:false`).
3. Create. Render builda e sobe com gunicorn.

## 4. Tabelas + tenant Bar da Vila

Na primeira subida, as tabelas são criadas automaticamente (`db.create_all()`
no boot) contra o `DATABASE_URL`. Depois, provisione o cliente rodando o CLI
com o mesmo `DATABASE_URL` (localmente ou num shell do host):

```bash
export DATABASE_URL="postgresql://..."   # o mesmo do deploy
export APP_ENV=production FLASK_APP=run.py
flask create-tenant --restaurante "Bar da Vila" --email dono@bardavila.com --nome "Bar da Vila"
# a senha é gerada e impressa uma única vez — anote e entregue ao cliente
```

## 5. Smoke test

- Acesse a URL → deve redirecionar para `/auth/login`.
- Login com o e-mail/senha do passo 4 → cai no dashboard.
- `/reset-db` e `/seed-vegan` devem dar **404** (gated) em produção.

## 6. Piloto → produção

Rode o Bar da Vila uns dias com dados reais (importe NF-e, cadastre pratos,
acompanhe precificação/dashboard), observe os logs do host. Só depois de estável
declare "produção". Próximos hardenings: monitoramento de erro (Sentry), rotina
de backup verificada, e o overhaul dos testes de integração de rota (skips
documentados em `tests/integration/`).
