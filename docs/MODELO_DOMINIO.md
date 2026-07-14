# Modelo de domínio

21 tabelas. Todas as tabelas de negócio têm `restaurant_id → restaurante.id`
(non-nullable desde a migration `7fc1334eef20`). Filtro por tenant é **manual**
em toda query.

## Tenant e identidade

**`restaurante`** (`Restaurante`) — o tenant.
`nome`, `cnpj` (unique), `endereco`, `telefone`, `ativo`, `data_cadastro`,
`subscription_status` (`free|active|past_due|canceled`), `subscription_tier`
(`free|pro`), `stripe_customer_id`, `stripe_subscription_id`, `pricing_strategy`
(`standard` = 97/mês vs `volume_based`, usado no A/B).

**`usuario`** (`Usuario`, `UserMixin`) — `nome`, `email` (unique global), `senha`
(hash werkzeug), `tipo` (`admin|gerente|usuario`), `ativo`, `restaurant_id`.
`__init__` já hasheia a senha passada em `senha=`.

## Cadeia de custo

**`fornecedor`** — `cnpj` (indexado, **não** unique após `b17a080954d4`),
`razao_social`, `nome_fantasia`, endereço, `inscricao_estadual`. Relações:
`produtos`, `notas_fiscais`.

**`produto`** — `codigo` (unique **global**), `nome`, `unidade`, `preco_unitario`
(preço médio ponderado, atualizado pelas entradas), `estoque_minimo`,
`estoque_atual`, `categoria`, `marca`, `fornecedor_id`.
Campos de inflação (`ddfd44a3a37e`): `ultimo_custo_anterior`,
`variacao_preco_pct`, `data_alerta_inflacao`.

**`estoque_movimentacao`** — `produto_id`, `quantidade`, `tipo`
(`entrada|saída`), `referencia` (ex.: "NF 1234"), `ref_id`, `valor_unitario`.
Fonte de verdade do estoque; `Produto.estoque_atual` é o acumulado.

**`nf_nota`** — `chave_acesso` (44, unique), `numero`, `serie`, `data_emissao`,
valores (total, produtos, frete, seguro, desconto, impostos), `fornecedor_id`,
`xml_data` (XML original). Cascata para `nf_item`.

**`nf_item`** — `nf_nota_id`, `produto_id`, `quantidade`, `valor_unitario`
(4 casas), `valor_total`, `unidade_medida`, `cfop`, `ncm`, ICMS e IPI (% e valor).

## Ficha técnica e cardápio

**`pratos`** (`Prato`) — `nome` (unique **global**), `categoria`, `rendimento` +
`unidade_rendimento` + `porcoes_rendimento`, `tempo_preparo`, `preco_venda`,
`margem` (default 30%), `custo_indireto` (por porção, vem do rateio).

**`prato_insumo`** — junção `prato_id` × `produto_id` + `quantidade`, `ordem`,
`obrigatorio`. Cascade delete nos dois lados.

**`cardapio`** — `nome`, `data_inicio`/`data_fim`, `tipo` (diário/semanal/
sazonal/eventos), `temporada`, `ativo`.
**`cardapio_secao`** — `cardapio_id`, `nome`, `ordem`.
**`cardapio_item`** — `secao_id`, `prato_id`, `ordem`, `preco_venda` (override
opcional do preço do prato neste cardápio), `destaque`, `disponivel`.

## Custos indiretos

**`custo_indireto`** — `descricao`, `valor`, `data_referencia` (mês/ano), `tipo`
(aluguel, energia, salários…), `recorrente`. O rateio distribui esses valores
entre os pratos e grava `Prato.custo_indireto`.

## Desperdício

**`categoria_desperdicio`** — `nome` (unique), `cor` (hex, pros gráficos).
**`registro_desperdicio`** — `categoria_id`, `produto_id` ou `prato_id`,
`quantidade` + `unidade`, `valor_estimado`, `motivo`, `responsavel`, `local`,
`acoes_corretivas`.
**`meta_desperdicio`** — janela (`data_inicio`/`data_fim`), alvo por categoria/
produto/prato, `valor_inicial`, `valor_meta`, `meta_reducao_percentual`,
`acoes_propostas`, `responsavel`.

## Vendas e previsão

**`historico_vendas`** — `data`, `prato_id` ou `cardapio_item_id`, `quantidade`,
`valor_unitario`, `valor_total` e features contextuais: `periodo_dia`,
`dia_semana` (0–6), `semana_mes`, `mes`, `feriado`, `evento_especial`, `clima`,
`temperatura`.

**`previsao_demanda`** — `data_inicio`/`data_fim`, alvo (prato ou item de
cardápio), `metodo` (`media_movel` | `regressao_linear`), `parametros` (JSON),
`valores_previstos` (JSON dia a dia), `confiabilidade` (0–1).

**`fator_sazonalidade`** — multiplicador (`fator`, ex.: 1.2 = +20%) aplicável por
`mes`, `dia_semana`, `periodo_dia` ou `evento`, opcionalmente restrito a um
prato/item/categoria.

## Importação de vendas

**`importacao_historico`** — `nome_arquivo`, `tipo_arquivo` (csv/xlsx/xls),
totais (`total_linhas`, `total_agregados`, `total_importados`,
`total_ignorados`), `produtos_nao_encontrados` (JSON), `mapeamentos_manuais`
(JSON), `status`, `mensagem_erro`, `tempo_processamento`, `usuario_id`.

**`mapeamento_produto`** — memória do fuzzy match: `nome_original` (indexado) →
`prato_id`, `criado_por_id`, `vezes_usado`.

## Site público (camada Bar da Vila)

**`site_config`** (1:1 com restaurante, `restaurant_id` unique) — identidade da
landing: `nome`, `kicker`, `tagline`, `subline`, `selo_estrelas`, `hero_foto`,
`whatsapp` (só dígitos com DDI), `telefone_exibicao`, `endereco`, `cidade_uf`,
`horario`, `maps_query`, `instagram_url`, `facebook_url`.

**`site_dish`** (`DishCard`) — cardápio visual: `nome`, `descricao`, `imagem`,
`tag` (selo, ex.: "★ O MAIS PEDIDO"), `destaque`, `ordem`, `ativo`.
**`site_review`** (`Review`) — `autor`, `texto`, `estrelas`, `ordem`, `ativo`.
**`site_team`** (`TeamMember`) — `nome`, `papel`, `emoji`, `ordem`, `ativo`.
**`site_gallery`** (`GalleryItem`) — `imagem`, `legenda`, `ordem`, `ativo`.

**`evento`** — `titulo`, `descricao`, `data` (indexada), `hora` ("HH:MM"), `ativo`.
**`promocao`** — `titulo`, `descricao`, `validade` (nulo = sem prazo), `ativo`;
propriedade `vigente` filtra por validade na exibição.
**`reserva`** — `nome`, `telefone`, `data`, `hora`, `num_pessoas`, `observacao`,
`status` (`pendente|confirmada|cancelada`), `origem` (default `site`).

## Migrations

| Revisão | O quê |
|---|---|
| `955fcb29fa81` | initial |
| `b17a080954d4` | remove unique de `fornecedor.cnpj` |
| `6e1b821db935` | `prato_id` em `MetaDesperdicio` |
| `9075edfa6a5b` | campos de assinatura em `restaurante` |
| `877fb41b68a1` | `pricing_strategy` (A/B) |
| `ddfd44a3a37e` | campos de inflação em `produto` |
| `7fc1334eef20` | `restaurant_id` non-nullable em tudo |

⚠️ As tabelas do site (`site_*`, `evento`, `promocao`, `reserva`) **não têm
migration** — são criadas pelo `db.create_all()` que roda no import de `run.py`.
