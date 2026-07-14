# Inventário de rotas

Todas exigem login por causa do `before_request` global, **exceto** as marcadas
como PÚBLICAS. `@pro_required` está marcado onde existe.

## PÚBLICAS — `public` (`app/routes/publico/views.py`, prefixo `/`)

| Rota | Método | O quê |
|---|---|---|
| `/` | GET | Landing do tenant principal (primeiro `Restaurante` por id) |
| `/s/<rid>` | GET | Landing de um tenant específico (preview) |
| `/cadastro` | GET/POST | Self-serve: cria restaurante + admin e já loga |
| `/reservar` | POST | Cria `Reserva` (pendente) + alerta WhatsApp best-effort (CallMeBot) |
| `/calculadora-roi` | GET/POST | Calculadora de ROI (marketing) |

## Auth — `/auth`

| Rota | Método | Nota |
|---|---|---|
| `/auth/login` | GET/POST | PÚBLICA. Valida `next` (só aceita path começando com `/`) |
| `/auth/logout` | GET | PÚBLICA na allowlist, mas tem `@login_required` |

## Dashboard — `/app`

| Rota | Nota |
|---|---|
| `/app/` , `/app/index` | Métricas do período, séries diárias, top pratos, BCG, desperdício |
| `/app/upgrade` | Página de upsell do plano Pro |
| `/app/relatorio/pratos` | **@pro_required** |
| `/app/relatorio/categorias` | **@pro_required** |
| `/app/api/bcg-matrix` | **@pro_required** — JSON da matriz BCG |

## Billing — `/billing`

| Rota | Método | Nota |
|---|---|---|
| `/billing/create-checkout-session` | POST | Stripe Checkout; price id depende de `pricing_strategy` |
| `/billing/success` | GET | Ativa `pro` de forma **otimista**, sem verificar no Stripe |
| `/billing/cancel` | GET | Volta pro upgrade |
| `/billing/webhook` | POST | PÚBLICA (allowlist). Valida assinatura; handler de `checkout.session.completed` é `pass` |

## Operação

**`/produtos`** — `/`, `/criar`, `/editar/<id>`, `/visualizar/<id>`,
`/ajustar-estoque/<id>`, `/em-falta`, `/api/listar`, `/api/buscar/<termo>`

**`/estoque`** — `/`, `/entrada`, `/saida`, `/detalhe_produto/<id>`,
`/relatorio`, `/exportar_relatorio`, `/novo_produto`,
`/api/movimentacoes/<produto_id>`, `/api/em_falta`

**`/fornecedores`** — `/`, `/criar`, `/editar/<id>`, `/visualizar/<id>`,
`/deletar/<id>` (POST), `/api/listar`, `/api/buscar/<termo>`

**`/nfe`** — `/`, `/importar` (upload XML), `/visualizar/<id>`, `/item/<id>`,
`/api/notas`, `/api/nota/<id>`

**`/pratos`** — `/`, `/criar`, `/editar/<id>`, `/visualizar/<id>`,
`/adicionar_insumo/<id>`, `/editar_insumo/<id>`, `/remover_insumo/<id>`,
`/atualizar_preco/<id>`, `/definir_preco/<id>`, `/ficha_tecnica/<id>`,
`/exportar_ficha/<id>`, `/relatorio_custos`, `/api/listar`,
`/api/ficha_tecnica/<id>`, `/api/sugerir_ingredientes`, `/api/verificar_estoque`

**`/cardapios`** — `/`, `/criar`, `/editar/<id>`, `/visualizar/<id>`,
`/adicionar_secao/<id>`, `/editar_secao/<id>`, `/remover_secao/<id>`,
`/adicionar_item/<secao_id>`, `/editar_item/<id>`, `/remover_item/<id>`,
`/exportar/<id>`, `/imprimir/<id>`, `/sugestao`, `/api/listar`,
`/api/cardapio/<id>`

**`/custos`** — `/`, `/criar`, `/excluir/<id>`, `/rateio`

**`/desperdicio`** — `/`, `/categorias`, `/categoria/criar`,
`/categoria/editar/<id>`, `/registros`, `/registro/criar`,
`/registro/visualizar/<id>`, `/registrar`, `/metas`, `/meta/criar`,
`/meta/editar/<id>`, `/meta/visualizar/<id>`, `/relatorios`,
`/exportar/registros`

**`/previsao`** — `/`, `/historico`, `/historico/registrar`,
`/historico/importar` (CSV/XLSX + fuzzy match), `/historico/exportar`,
`/previsoes`, `/previsao/gerar`, `/previsao/visualizar/<id>`, `/sazonalidade`,
`/sazonalidade/criar`, `/sazonalidade/excluir/<id>`

## Site / CMS (área logada que alimenta a landing)

**`/config-site`** — `/` (GET/POST): edita `SiteConfig` do tenant

**`/conteudo`** — `/`, `/<tipo>`, `/<tipo>/novo`, `/<tipo>/<id>/editar`,
`/<tipo>/<id>/toggle`, `/<tipo>/<id>/excluir`.
`<tipo>` mapeia pros modelos de site (pratos/reviews/time/galeria).

**`/agenda`** — eventos: `/`, `/novo`, `/<id>/editar`, `/<id>/toggle`,
`/<id>/excluir`

**`/promocoes`** — `/`, `/nova`, `/<id>/editar`, `/<id>/toggle`, `/<id>/excluir`

**`/reservas`** — `/`, `/<id>/confirmar` (POST), `/<id>/cancelar` (POST)

## Endpoints administrativos (só em dev, gated)

Registrados em `run.py` apenas se `ENABLE_ADMIN_ENDPOINTS=1` **e** config ≠ `production`:

| Rota | Perigo |
|---|---|
| `/debug-db` | Lista tabelas, versão do alembic, host do DB mascarado |
| `/seed-vegan` | Popula dados de demo |
| `/reset-db` | **`db.drop_all()`** — apaga tudo, de todos os tenants |
