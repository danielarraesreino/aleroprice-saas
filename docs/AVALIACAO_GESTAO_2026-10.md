# Avaliação da gestão — outubro/2026

Por que a gestão (custos, estoque, NF-e, previsão) foi desligada do produto
(`GESTAO_ATIVA=0`), e o que falta para religar. Avaliação feita lendo o código,
com conferência pontual das afirmações principais.

## Veredito por módulo

| Módulo | Veredito | Motivo principal |
|---|---|---|
| NF-e → produto → prato → preço | **3/10, não pronto** | ver lista abaixo |
| promoções, agenda | manter | CRUD correto, isolado por tenant, testado |
| billing, `utils/planos.py` | manter | verifica pagamento, webhook ativa plano, testado |
| dashboard | consertar | stack trace devolvida ao usuário (`views.py` ~761), excepts silenciosos |
| desperdício | consertar | `criar_registro` renderiza template inexistente; templates órfãos |
| previsão + `utils/importacao.py` | consertar ou desligar | horizonte errado (>7 dias repete), "sazonalidade" não existe, reimportar duplica vendas e baixa estoque de novo, data BR lida como mês/dia, importação não atômica, exclusão por GET |
| agentes ("X-Men IA") | desligar | respostas fixas/falsas, sem testes; rota aceitava qualquer tenant (custo de LLM) — fechada para o operador |

## Núcleo de custos e preço — o que está quebrado

- Faltam templates: `templates/produtos/` e `templates/fornecedores/` não existem; também `pratos/{adicionar_insumo,editar_insumo,ficha_tecnica,relatorio_custos}` e `estoque/{saida,relatorio}` — essas rotas dão 500.
- Código usa `Produto.unidade_medida`, mas o campo é `unidade` (TypeError/AttributeError em produtos, estoque e pratos).
- `Produto.preco_unitario` é `Numeric(10,2)`: custo por g/ml arredonda para R$0,00. Não há conversão de unidade de compra → unidade de uso.
- A média ponderada da NF-e nunca é aplicada (o preço é sobrescrito antes do cálculo). Importação da NF-e não é atômica.
- "Margem" é markup em um lugar e margem sobre preço em outro; não há CMV%. Custo indireto tem duas regras diferentes.
- Preço sugerido não aparece em tela nenhuma; editar prato descarta ingredientes; "atualizar preço" não faz commit; rateio sobrescreve o preço que o dono definiu.
- Sem teste de ponta a ponta XML → custo → preço.

## Para um gestor de preço que valha a pena (dentro do admin do site)

1. Custo com 4+ casas e conversão de unidade por produto.
2. Uma fórmula só em `utils/calculos.py`: markup × margem × CMV%, nomes claros.
3. Sugerido ao lado do preço atual; aplicar só com clique — nunca sobrescrever o manual.
4. Teste de ponta a ponta com valores conhecidos antes de qualquer tela.

## Religar a gestão

`GESTAO_ATIVA=1` **e** instalar `requirements-gestao.txt` no deploy (pandas e
numpy estouram o limite de 250 MB da Vercel e voltam a reinstalar dependências
a cada cold start — foi o que deixava a primeira visita em ~21s).
