---
name: feira-multitenant-deploy
description: Regras de multi-tenant, banco Neon e deploy na Vercel da plataforma Feira de Barão. Use SEMPRE antes de mexer em modelos de dados, migrations, roteamento por domínio, cache de borda, importação de leads, produção, push, deploy, "colocar no ar" ou qualquer pedido que cite tenant, domínio, banco, Neon, Vercel, migration, coluna nova ou produção.
---

# feira-multitenant-deploy

## Tenancy
- Um tenant é um `Restaurante` (tabela `restaurante`). Todo dado do tenant leva `restaurant_id` e o filtro é manual: toda query nova filtra por ele. Teste de vazamento: `tests/integration/test_site_multitenant.py` e `test_contrato_design.py`.
- Host decide o tenant: `app/utils/site_router.py` (`tenant_por_host` compara `Restaurante.dominio` com o host exato; `tenant_por_slug` para `/bar/<slug>`). Subdomínio coringa não existe.
- Tipos: `tipo_conta='demo'` (prévia: `noindex`, faixa de prévia, fora do sitemap) e `cliente`. Ativo = `ativo IS NOT FALSE`; fora do ar = `ativo=false` (botão no Modo Campo), nunca apagar.
- Endpoints que respondem no domínio do cliente ficam em `ENDPOINTS_DO_TENANT` (`app/__init__.py`); o resto redireciona ao domínio do produto quando `SEPARAR_DOMINIOS=1`.
- Preço só em `app/utils/planos.py` (env `FEIRA_*`).

## Banco (produção)
- Neon, projeto `alerosaas` (`lively-queen-96163664`), sa-east-1. Acesso pelo conector Neon (`run_sql`, um statement por chamada). Nunca pedir a `DATABASE_URL` no chat. A Vercel não deixa ler env pelo MCP.
- Coluna nova: migration Alembic idempotente em `migrations/versions/` **e criar as colunas em produção ANTES do push**, senão o deploy novo consulta coluna inexistente e derruba o site (aconteceu). SQL de DDL em produção só com OK explícito do usuário na conversa.
- Dev local usa SQLite: banco antigo sem colunas novas quebra `/feira`. Para pré-visualizar, suba com `DATABASE_URL=sqlite:///<tmp>/x.sqlite` e `db.create_all()`.
- Scripts de captura e de PDF re-executam com SQLite temporário para nunca gravar no banco de dev.

## Deploy
- Vercel, projeto `aleroprice-bardavila`, função em gru1; deploy sai do push em `main` (`git push`). Rodar a suíte antes: `venv/bin/python -m pytest tests/unit tests/integration -q --no-cov -p no:cacheprovider`.
- Cache de borda: `_na_borda` nas páginas públicas; para furar, `?v=<timestamp>`.
- Depois do push, conferir em produção com `curl` e `?v=` (aguardar o build) e relatar o que foi verificado.
- Prévias entram com `GET /bootstrap-demo?token=$SEED_TOKEN&action=demos` (um só: `&slug=`); `action=schema` cria colunas.
- Nunca fazer push, DDL em produção ou mudança de domínio sem o usuário ter pedido naquela conversa.

## Antes de dizer "pronto"
Evidência: testes verdes, página em produção conferida, e o que NÃO foi verificado dito em voz alta (ver verification-before-completion).
