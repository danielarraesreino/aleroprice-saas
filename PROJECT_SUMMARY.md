# AleroPrice SaaS

## Identificação
- Tipo: SaaS (B2B, gestão de restaurantes)
- Stack técnica: Python 3.9+ / Flask 2.3.3, SQLAlchemy 2.0 + Flask-SQLAlchemy + Flask-Migrate/Alembic (7 migrações), Flask-Login (autenticação), Stripe (billing), pandas/numpy/matplotlib (previsão de demanda e relatórios), xmltodict (parser de NFe), Jinja2 + Bootstrap 5 + Chart.js (frontend server-side), SQLite (dev, `instance/alerodb.sqlite`) / PostgreSQL em produção (Neon/Supabase, conforme dossiê técnico), deploy serverless na Vercel (`vercel.json` roteia tudo para `api/index.py`), gunicorn disponível para deploy tradicional. Testes com pytest/pytest-flask/pytest-playwright.
- Última modificação relevante: último commit git em 2026-01-08 ("feat: complete V1.0 (Billing, Inflation, Vercel Support)"), mas há trabalho substancial não commitado — 54 arquivos modificados e 18 novos (`git status`), incluindo quase todas as rotas e templates. Arquivo mais recentemente modificado no disco: `AleroPrice_Dossie_NotebookLM.md` (2026-04-08), indicando atividade de documentação/refatoração posterior ao último commit.

## Status
- Maturidade: funcional (em uso real, com histórico de ~48 commits, muitos deles correções de bugs de produção — erros 500 na Vercel, timeouts, N+1 queries, parsing de XML de NFe). Não está pronto para produção multi-cliente sem hardening de segurança.
- Tem autenticação? Parcial. Existe modelo `Usuario` (Flask-Login, hash de senha) e blueprint `auth`, mas `@login_required` só é usado em 3 dos 13 blueprints de rotas (`auth`, `billing`, `dashboard`). Não há enforcement global (`before_request`) de login — rotas de produtos, estoque, pratos, fornecedores, NFe, custos, previsão, desperdício e cardápios parecem acessíveis sem login.
- Tem billing/pagamento? Sim. Integração com Stripe (`app/routes/billing/views.py`): checkout de assinatura, webhook, planos free/pro, e até um A/B test de estratégia de preço (`pricing_strategy`: standard vs volume_based). Chaves via variáveis de ambiente com fallback para placeholders de teste.
- Tem multi-tenancy? Sim. Modelo `Restaurante` como tenant, `Usuario.restaurant_id` como FK obrigatória, helper `get_current_restaurant_id()` em `app/utils/tenant.py`. Uso de `restaurant_id` está presente na maioria das rotas de negócio (contagens de 14 a 79 ocorrências por arquivo), mas não há um teste automatizado ou middleware centralizado que garanta isolamento entre tenants em 100% das queries — depende de disciplina manual do desenvolvedor (conforme alertado nas próprias regras do projeto em `.agent/rules/rules.md`).
- Tem testes? Parcial. Estrutura completa (`tests/unit`, `tests/integration`, `tests/e2e` com Playwright, plus scripts `verify_*.py` ad-hoc na raiz). Rodando `pytest tests/unit`: 16 passaram, 7 falharam (cálculos de lucro e seed de dados). Cobertura de código geral em ~22% (relatório `htmlcov`/`.coveragerc` presentes).
- Tem documentação de deploy? Parcial. Não há README de deploy formal nem `.env.example`. Existe `vercel.json` (rewrite simples) e lógica de detecção de ambiente Vercel/Railway em `run.py`, além de dois documentos extensos voltados a IA/NotebookLM (`AleroPrice_Dossie_NotebookLM.md`, `CONTEXTO_NOTEBOOKLM_V2.md`) que descrevem arquitetura e stack, mas não são um guia operacional de deploy passo a passo.

## Resumo funcional
O AleroPrice é um sistema de gestão financeira e "engenharia de cardápio" para restaurantes: importa XML de Notas Fiscais Eletrônicas para atualizar custos de insumos e estoque automaticamente, calcula o custo real de cada prato (direto + rateio de custos indiretos) e sugere preços de venda com base na margem desejada. Além disso oferece controle de desperdício, previsão de demanda/sazonalidade e um dashboard financeiro. Na versão SaaS, o sistema ganhou autenticação de usuários, arquitetura multi-tenant (um "Restaurante" por cliente) e cobrança via Stripe com plano free/pro.

## Gaps para empacotamento comercial
- Segurança: ausência de enforcement global de login (a maioria das rotas de negócio não exige `@login_required`) — risco alto de vazamento/edição de dados entre tenants ou por usuários anônimos.
- Endpoints de debug/administração perigosos expostos publicamente em `run.py` (`/debug-db`, `/reset-db` que faz `db.drop_all()`, `/seed-vegan`) — sem autenticação, sem flag de ambiente, prontos para uso indevido em produção.
- Sem `.env.example` nem documentação clara de variáveis de ambiente exigidas (SECRET_KEY, DATABASE_URL, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_PRICE_ID_PRO, etc.) — dificulta onboarding de novos devs ou deploy por terceiros.
- Sem branding configurável (nome do produto/cores parecem fixos ao "AleroPrice"/AleroVeg) — não está pronto como white-label.
- Sem fluxo de onboarding guiado para novos tenants (cadastro de restaurante, convite de usuários, planos) — parece assumir setup manual/seed scripts.
- Testes falhando (7/23 no módulo unit) e cobertura baixa (~22%) — risco de regressão ao vender/escalar.
- Grande volume de mudanças não commitadas (54 modificados + 18 novos) — repositório git não reflete o estado real do código, dificultando auditoria e rollback.
- README.md desatualizado: não menciona SaaS, billing, multi-tenancy nem autenticação, apenas a versão original mono-tenant.
- Falta de testes de isolamento multi-tenant automatizados (ex.: garantir que usuário A nunca acessa dados do Restaurante B).

## Análise comercial (estimativa)
- Modelo de venda sugerido: assinatura SaaS mensal (já tem multi-tenancy e billing parcial implementados)
- Público comprador provável: pequenos comércios/varejo que precisam de precificação, ou revenda via contadores/consultores
- Faixa de preço sugerida (BRL): R$150-400/mês por tenant — só depois de corrigir a falha de segurança crítica (endpoints /reset-db e /debug-db sem login)
- Esforço estimado até venda-ready: médio — segurança é bloqueador (crítico), resto é polish (testes, .env.example, README)

## Observações
- Dependências externas: Stripe (billing/assinaturas), Vercel (hosting serverless, com Postgres externo tipo Neon/Supabase conforme dossiê), possivelmente Railway como alternativa de deploy (detectado em `run.py` via `RAILWAY_ENVIRONMENT`).
- Projeto foi documentado deliberadamente para consumo por LLMs (arquivos `AleroPrice_Dossie_NotebookLM.md`, `CONTEXTO_NOTEBOOKLM_V2.md`, `notebooklm_info.md`), sugerindo uso de ferramentas de IA (ex. Google Antigravity/Gemini, conforme `.agent/rules/rules.md`) no processo de desenvolvimento.
- Regras internas do projeto (`.agent/rules/rules.md`) já identificam a arquitetura multi-tenant como "CRÍTICA" e pedem que toda query tenha `WHERE restaurant_id = current_user.restaurant_id` — alinhado com o gap de segurança encontrado acima.
- Existe uma pasta irmã `AleroPrice` (symlink) e uma pasta `Trabalho/AleroPriceSaaS`, além de pastas soltas `de/` e `nf e/` na raiz do projeto, sugerindo artefatos de trabalho/anexos não organizados.
- Histórico de commits mostra iteração intensa para corrigir problemas específicos de ambiente serverless (timeouts de 10s na Vercel, N+1 queries, parsing de datas Postgres vs SQLite, parsing de XML de NFe sem namespace) — indício de que o produto já rodou em produção real com usuários/dados reais.
