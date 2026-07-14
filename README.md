# AleroPrice - Sistema de Gestão para Restaurantes

O AleroPrice é um sistema modularizado para gestão de custos, estoque e precificação para restaurantes, desenvolvido com Flask e SQLAlchemy.

## Funcionalidades

- **Gestão de Fornecedores**: Cadastro e consulta de fornecedores
- **Gestão de Produtos/Insumos**: Cadastro, consulta e movimentação de estoque
- **Importação de NFe**: Leitura de arquivos XML de Notas Fiscais Eletrônicas
- **Controle de Estoque**: Registro de entradas/saídas e alertas de estoque mínimo
- **Ficha Técnica de Pratos**: Cálculo de custos diretos por porção
- **Controle de Custos Indiretos**: Rateio de custos fixos e indiretos
- **Precificação Automática**: Sugestão de preços baseados em custos e margem de lucro

## Camada SaaS

Esta versão adiciona, sobre o núcleo de gestão, os recursos que a tornam um SaaS multi-cliente:

- **Autenticação**: login de usuários via Flask-Login (modelo `Usuario`, senha com hash).
  O acesso é forçado globalmente por um `before_request` no factory (`app/__init__.py`):
  toda rota exige login, exceto `static`, `auth.login`/`auth.logout`, o webhook do
  Stripe (`billing.webhook`) e o blueprint `public` (landing / calculadora de ROI).
- **Multi-tenancy**: cada cliente é um `Restaurante` (tenant). Todos os modelos de negócio
  carregam `restaurant_id` (NOT NULL) e as queries filtram por
  `get_current_restaurant_id()` (`app/utils/tenant.py`). O isolamento depende de disciplina
  nas queries — ainda não há teste automatizado garantindo isolamento entre tenants.
- **Billing (Stripe)**: assinatura com planos free/pro, checkout, webhook e um A/B de
  estratégia de preço (`standard` vs `volume_based`) em `app/routes/billing/`.

## Estrutura do Projeto

```
app/
    __init__.py           # Fábrica de aplicação e registro de Blueprints
    config.py             # Configurações do sistema
    extensions.py         # Instâncias de extensões (SQLAlchemy, etc.)
    models/               # Modelos de dados
        modelo_fornecedor.py
        modelo_produto.py
        modelo_nfe.py
        modelo_estoque.py
        modelo_prato.py
        modelo_custo.py
    routes/               # Blueprints e rotas
        estoque/
        fornecedores/
        nfe/
        pratos/
        produtos/
    utils/                # Funções auxiliares
        nfe_parser.py
        calculos.py
    scripts/              # Scripts de inicialização
        create_db.py
        seed_data.py
requirements.txt
run.py
```

## Modelo de Dados

O sistema utiliza um banco de dados relacional normalizado com as seguintes tabelas principais:

- **Fornecedor**: Informações de fornecedores de insumos
- **Produto**: Produtos/insumos utilizados nos pratos
- **NFNota**: Notas fiscais importadas
- **NFItem**: Itens das notas fiscais
- **EstoqueMovimentacao**: Registro de movimentações de estoque
- **Prato**: Receitas/pratos do cardápio
- **PratoInsumo**: Composição dos pratos (produtos e quantidades)
- **CustoIndireto**: Registro de custos fixos para rateio

## Instalação e Configuração

### Pré-requisitos

- Python 3.9+
- pip (gerenciador de pacotes Python)

### Instalação

1. Clone o repositório ou extraia os arquivos

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente:
   ```
   cp .env.example .env
   # edite .env: SECRET_KEY, DATABASE_URL (opcional em dev) e chaves Stripe
   ```
   Veja [`.env.example`](.env.example) para a lista completa e o que cada variável faz.
   Sem `DATABASE_URL` o app usa SQLite local (`instance/alerodb.sqlite`) em dev.

4. Execute a aplicação:
   ```
   python run.py
   ```
   Ao rodar via `python run.py`, as migrações Alembic são aplicadas automaticamente
   (`upgrade()` no início). Para aplicar manualmente: `FLASK_APP=run.py flask db upgrade`.

### Dados de exemplo (dev)

O seed cria um `Restaurante` (tenant) e popula fornecedores, insumos, 30 pratos,
cardápio e histórico de vendas. Habilite os endpoints administrativos e chame `/seed-vegan`:

```
ENABLE_ADMIN_ENDPOINTS=1 python run.py
# depois acesse http://localhost:5000/seed-vegan
```

> ⚠️ **Endpoints perigosos**: `/debug-db`, `/seed-vegan` e `/reset-db` (este faz
> `db.drop_all()` e apaga tudo) só são registrados quando `ENABLE_ADMIN_ENDPOINTS=1`
> **e** o ambiente não é produção. Nunca defina essa variável em ambiente compartilhado.

### Testes

```
python -m pytest tests/unit          # unitários (rápidos, SQLite in-memory)
python -m pytest tests                # suíte completa
```

## Funcionalidades Principais

### Importação de NFe

O sistema permite importar arquivos XML de Notas Fiscais Eletrônicas, extraindo automaticamente:

- Dados do fornecedor (criando novo se necessário)
- Produtos/insumos (criando novos se necessário)
- Valores fiscais e totais
- Registro automático de entrada no estoque

### Controle de Estoque

- Registro de todas as movimentações (entradas e saídas)
- Cálculo de estoque atual
- Alertas de estoque mínimo
- Relatórios de produtos em falta

### Ficha Técnica de Pratos

- Cadastro detalhado de receitas/pratos
- Registro de insumos com quantidades
- Cálculo automático de custos diretos
- Rateio de custos indiretos
- Sugestão de preço de venda baseado na margem desejada

### Gestão de Desperdício (Novo)

- **Monitoramento**: Registro de desperdícios por categoria, motivo e responsável
- **Metas**: Definição e acompanhamento de metas de redução
- **Relatórios**: Dashboards visuais e relatórios detalhados por período

### Previsão de Demanda (Novo)

- **Análise Histórica**: Utiliza dados passados para identificar padrões
- **Sazonalidade**: Ajustes automáticos para períodos de alta/baixa
- **Planejamento de Compras**: Sugestão de reposição baseada na previsão de vendas

## Cálculos de Custo

### Custo Direto

Calculado como a soma dos custos dos insumos utilizados na receita:

```
custo_direto_total = ∑(quantidade_insumo * preco_unitario_insumo)
custo_direto_por_porcao = custo_direto_total / rendimento
```

### Custo Indireto

Rateio dos custos fixos (aluguel, energia, salários, etc.):

```
custo_indireto_por_porcao = total_custos_indiretos / total_porcoes_produzidas
```

### Preço de Venda Sugerido

Calculado com base nos custos e na margem desejada:

```
preco_venda = (custo_direto_por_porcao + custo_indireto_por_porcao) * (1 + margem/100)
```

## Extensões Futuras

- Interface para definição de cardápios
- Integração com sistemas de PDV
- Dashboard para análise de lucratividade (Expandido)
- Controle de validade de produtos perecíveis (Melhorias)
