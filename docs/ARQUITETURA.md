# Arquitetura — AleroPrice SaaS

## Visão geral

Monólito Flask com renderização server-side. Sem SPA, sem API pública versionada
(existem endpoints `/api/*` internos que servem os gráficos e autocompletes do
próprio front). Um processo, um banco, blueprints por domínio.

```
                        ┌──────────────────────────────┐
   visitante ──────────►│ blueprint `public` (url '/') │  landing, cardápio digital,
   (sem login)          │ app/routes/publico/          │  reservas, /cadastro, ROI
                        └──────────────┬───────────────┘
                                       │ cria tenant + loga
                        ┌──────────────▼───────────────┐
   dono do              │ before_request: require_login│
   restaurante ────────►│ (app/__init__.py)            │
                        └──────────────┬───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   OPERAÇÃO                       INTELIGÊNCIA                    SITE (CMS)
   estoque, produtos,             dashboard, previsao,           configsite,
   fornecedores, nfe,             custos (rateio)                conteudo, agenda,
   pratos, cardapios,                                            promocoes, reservas
   desperdicio
```

## Camadas

**1. Rotas (`app/routes/<dominio>/views.py`)** — recebem form/querystring, chamam
utils/modelos, renderizam Jinja. Não há camada de serviço formal: regra de
negócio mora ou no model (métodos como `Prato.custo_total`) ou no próprio view.
Views grandes (`dashboard`, `previsao`, `desperdicio`, `nfe`) concentram lógica
pesada em funções module-level acima das rotas.

**2. Modelos (`app/models/modelo_*.py`)** — SQLAlchemy declarativo. Carregam
propriedades calculadas (custo do prato, margem, valor da meta) além do schema.
`app/models/__init__.py` importa todos para registro no metadata.

**3. Utils (`app/utils/`)**

| Módulo | Responsabilidade |
|---|---|
| `tenant.py` | `get_current_restaurant_id()` — lê `current_user.restaurant_id` |
| `decorators.py` | `@pro_required` — gate de plano |
| `calculos.py` | preço médio ponderado, custo direto, custo/porção, preço de venda por margem, rateio de custos indiretos, estoque mínimo |
| `nfe_parser.py` | XML → modelos pydantic (`NFeData`), valida chave de acesso (44 díg.) e CNPJ |
| `nfe_importer.py` | orquestra parse → persistência (`NFNota`, `NFItem`) |
| `importacao.py` | `ImportadorVendas`: detecta colunas do CSV/XLSX, casa nome de prato com `thefuzz` (threshold configurável), agrega vendas, baixa estoque |
| `formatacao_br.py` + `template_filters.py` | moeda/peso/percentual/data no padrão BR |

## Ciclo de vida da requisição

1. `run.py` escolhe o config: `APP_ENV` explícito > `VERCEL`/`RAILWAY_ENVIRONMENT` (⇒ `production`) > `default` (dev).
2. `create_app()` monta o Flask, inicia Sentry (se `SENTRY_DSN`), extensões, locale pt-BR, filtros Jinja e registra os blueprints.
3. `@before_request require_login` roda em **toda** requisição: se o endpoint não está na allowlist (`static`, `auth.login`, `auth.logout`, `billing.webhook`, `public.*`) e não há usuário autenticado → redirect pra `auth.login?next=<path>`.
4. `CSRFProtect` (flask-wtf) roda **depois** do `require_login`, de propósito: sessão expirada leva o usuário de volta pro login em vez de dar 400 seco. Todo POST/PUT/PATCH/DELETE precisa de token — no campo `csrf_token` do form ou no header `X-CSRFToken`. Exceções, marcadas com `@csrf.exempt`: `billing.webhook` (autentica por assinatura HMAC do Stripe) e `bootstrap_demo` (curl de manutenção, gated por `SEED_TOKEN`).
5. A view filtra por `restaurant_id` na mão. Isso não é enforçado por nada — é convenção.
6. Template renderiza com filtros BR.

Prefixos registrados: `/estoque`, `/fornecedores`, `/nfe`, `/pratos`, `/produtos`,
`/cardapios`, `/desperdicio`, `/previsao`, `/custos`, `/reservas`, `/agenda`,
`/promocoes`, `/config-site`, `/conteudo`, `/billing`, `/auth`, `/app`
(dashboard) e `/` (blueprint público).

Nota: o dashboard fica em **`/app`**, não na raiz — a raiz é a landing do tenant.

## Fluxos principais

### Importação de NF-e
`nfe.importar` (upload XML) → `processar_xml_nfe` / `app.utils.nfe_parser`
(xmltodict + pydantic, namespaces removidos) → `importar_nfe`: cria/atualiza
`Fornecedor`, cria `NFNota` + `NFItem`, casa ou cria `Produto`, gera
`EstoqueMovimentacao` de entrada e recalcula preço médio ponderado. O XML
original fica em `NFNota.xml_data`.

Efeito colateral relevante: atualizar preço de produto grava
`ultimo_custo_anterior`, `variacao_preco_pct` e `data_alerta_inflacao` — é a base
do alerta de inflação.

### Precificação
`Prato` tem N `PratoInsumo` (produto + quantidade). Custo direto = Σ(quantidade ×
`Produto.preco_unitario`). Custo por porção = custo total / `porcoes_rendimento`.
Preço sugerido = custo / (1 − margem). `CustoIndireto` entra por rateio
(`custos.rateio`), gravando `Prato.custo_indireto`.

### Importação de vendas / previsão
CSV ou XLSX → `ImportadorVendas` detecta colunas, casa nome de prato por
similaridade (fuzzy), agrega por prato/data, grava `HistoricoVendas` e dá baixa
no estoque via ficha técnica. `MapeamentoProduto` memoriza correções manuais de
nome ("Xis Salada" → prato 12) e conta reuso. `ImportacaoHistorico` registra
cada rodada (totais, não encontrados, tempo).

Previsão (`previsao.gerar_previsao`) usa média móvel e regressão linear sobre
`HistoricoVendas`, aplica `FatorSazonalidade` e grava `PrevisaoDemanda` com
`valores_previstos` em JSON e uma `confiabilidade` 0–1.

### Dashboard
`app/routes/dashboard/views.py` agrega métricas do período (faturamento, custo,
lucro, margem), séries diárias, top pratos, distribuição por categoria, tendência
de lucratividade (6 meses), indicadores de desperdício e **matriz BCG** de pratos
(popularidade × rentabilidade). Relatórios detalhados e a API BCG são `@pro_required`.

Há tratamento explícito para diferença de dialeto SQL (Postgres vs SQLite) nas
agregações por data.

### Site público (camada Bar da Vila)
`public.landing` pega o **primeiro** `Restaurante` por id e renderiza
`site/landing.html` com dados de `SiteConfig` (marca, hero, contato, redes),
`DishCard`, `Review`, `TeamMember`, `GalleryItem`, `Evento` e `Promocao` vigente.
`/s/<rid>` renderiza a landing de um tenant específico (preview até existir
subdomínio).

`public.reservar` grava uma `Reserva` (status `pendente`) e dispara alerta
best-effort no WhatsApp via CallMeBot (só se `CALLMEBOT_APIKEY` estiver setada;
falha é engolida e logada). O dono confirma/cancela em `/reservas`.

O CMS desse site é o blueprint `conteudo` (`/conteudo/<tipo>`, tipos: pratos,
reviews, time, galeria) + `configsite` (`/config-site`).

### Billing
`billing.create_checkout_session` → Stripe Checkout (price id varia conforme
`Restaurante.pricing_strategy`: `standard` ou `volume_based`) → `billing.success`
marca `pro` de forma otimista. O webhook está registrado e valida assinatura, mas
o handler de `checkout.session.completed` não faz nada ainda.

## Testes

- `tests/unit/` — cálculos de lucro, valoração de NF-e, estoque, modelos, seed
- `tests/integration/` — smoke de rotas, previsão, desperdício (usa `auth_client` do `conftest.py`)
- `tests/e2e/` — Playwright contra app real
- `app/tests/test_nfe_integration.py` — integração de NF-e dentro do pacote

Na raiz ainda existem runners legados (`run_all_tests.py`, `run_tests*.sh`,
`verify_*.py`, `test_e2e_selenium.py`). O caminho vivo é `pytest`.
