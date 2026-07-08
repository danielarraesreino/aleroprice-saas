# AleroPrice: Dossiê Técnico Completo e Profundo (Para Análise de IA)

Este documento foi especialmente formatado para fornecer o máximo de contexto possível a modelos de linguagem, como o NotebookLM, com o intuito de estruturar discussões estratégicas sobre o desenvolvimento, arquitetura e escala do **AleroPrice**, um sistema de engenharia de cardápio focado em gestão de restaurantes e barracas.

---

## 1. Visão Geral do Produto e Regras de Negócio

O AleroPrice não é apenas um simples sistema de cadastro de cardápios; é um analista financeiro operando com base nas regras da **Engenharia de Cardápio**. 

### 1.1 Objetivo Principal
Determinar o custo real dos pratos (Custo Direto + Custo Indireto), atualizar automaticamente o estoque a cada venda, alertar sobre margens de lucro negativas causadas pela inflação de insumos (compras em NFe) e gerar previsões de demanda usando dados históricos.

### 1.2 Core Business (Diferenciais)
- **Importação Inteligente de Vendas:** O sistema engole planilhas cruas/despadronizadas e usa **Fuzzy Matching** (Busca Aproximada) para vincular nomes inconsistentes ("Pastel de carne", "P. Carne") às Fichas Técnicas cadastradas. O sistema agrega dados diários para evitar inflar o banco de dados.
- **Parser de NFe Resiliente:** Processa notas fiscais eletrônicas brasileiras ignorando as armadilhas de namespaces inválidos no XML provindos de diversos ERPs. Adiciona fornecedores e atualiza custos de insumo transparentemente.
- **Baixa de Estoque Transparente:** Ao processar X vendas reais no mês de um determinado prato, o AleroPrice consulta a Ficha Técnica atrelada àquele prato e abate do estoque físico cada grama de matéria prima que o compôs.

---

## 2. Arquitetura e Stack Tecnológico

A aplicação está estruturada sob o paradigma monolítico com "Thin Client e Smart Server". O design é otimizado para ambientes *Serverless*.

- **Backend / Core:** Python 3.8+, framework web **Flask**.
- **Processamento de Visão:** Renderização Server-Side (SSR) usando templates **Jinja2**. Não há framework reativo (React/Vue) para simplificar a stack. Uso de **Bootstrap 5** (Layout) e **Chart.js** (Visualização gráfica).
- **ORM e Banco de Dados:** 
  - Usamos **SQLAlchemy** para mapeamento relacional. 
  - Trata o dialeto via detecção automática: *SQLite* em desenvolvimento local e *PostgreSQL* para produção (Neon, Supabase).
- **Ambiente de Deploy (Crítico):** A plataforma roda primariamente em **Vercel** usando Serverless Functions.
  - *Constraint Arquitetônico:* Serverless significa ausência de threads infinitas, long connections persistentes e state local. Funções expiram rápido (time-out >10s). Assim, rotinas extremamente pesadas sofrem limitações.

---

## 3. Topologia do Modelo de Dados (`app/models/`)

O diagrama de classes reflete o coração do ERP.

### 3.1. Núcleo Produtivo e Ficha Técnica
*   **Produto / Insumo (`modelo_produto.py`)**: A matéria-prima elementar (massa, carne moída). Propriedades: peso/unidade, preço de custo mais recente, estoque em tempo real.
*   **Prato (`modelo_prato.py`)**: A receita ou composição vendida. Possui atrelado o Custo Indireto (rateio) e calcula dinamicamente a `Margem de Lucro` se cruzando frente ao preço de venda atual e do Custo dos insumos atual.
*   **PratoInsumo (N:M)**: A tabela pivot que estipula quantas gramas ou unidades do `Produto` X vão no `Prato` Y.

### 3.2. Estoque e Suprimentos
*   **NFNota e NFItem (`modelo_nfe.py`)**: Armazenam log da NFe importada. Responsáveis por flutuar o custo de aquisição do `Produto`.
*   **MovimentacaoEstoque (`modelo_estoque.py`)**: Livro razão (ledger) de todo grama que entra ou sai. Usado em auditoria retrospectiva.
*   **RegistroDesperdicio (`modelo_desperdicio.py`)**: Tabela para contabilizar e tipificar a quebra de insumos (vencibilidade, queda, refugo).

### 3.3. Inteligência Administrativa
*   **HistoricoVendas (`modelo_previsao.py`)**: Log de vendas concretizadas extraídas de importações (PDVs). O SQLAlchemy cuida de unificar o cálculo e fazer roll-ups de vendas mensais/semanais.
*   **CustoIndireto (`modelo_custo.py`)**: Aluguel, Pro-labore, Conta de Energia. É base para o algoritmo de *Rateio* por Prato (distribuição do custo fixo nas vendas projetadas, atingindo lucro real da operação).

---

## 4. Algoritmos Específicos e Soluções Adotadas

### 4.1 Motor de Performance (Dashboard)
Painéis gerenciais frequentemente matam bancos relacionais com problemas de *"N+1 Queries"*. 
No AleroPrice, a leitura de custos/venda usa `joinedload` e agregação SQL pura. O cruzamento dos montantes é processado em massa na memória via Python, convertendo de ~2.000 queries que derrubariam um banco serverless para meras 4 requisições.

### 4.2 Inteligência em Previsão de Demanda ("Consultor")
Implementação para sugerir compras baseado no uso pregresso:
1.  **Média Móvel**: Base segura para consumos constantes.
2.  **Regressão Linear Básica**: Identifica padrões de curva de subida ou descida ao longo do último trimestre.
3.  **Fatores de Sazonalidade**: Permite input do usuário para "turbinar" o cálculo de preenchimento (ex.: +50% às sextas-feiras ou -20% em chuvas).

### 4.3 XML NFe "Anti-frágil"
Sistemas contábeis costumam falhar quando faturadores alteram levemente o namespace do XML (ex.: `<ns1:Nfe>` x `<Nfe>`). Nós removemos namespaces estruturais dinamicamente pelo interpretador (`xmltodict` stripped defaults) e injetamos uma recursão pesada que perambula a árvore até encontrar os arrays dos itens.

---

## 5. Dificuldades Técnicas Existentes (Tech Debt e Gargalos)

Se for auxiliar no planejamento, o NotebookLM deve levar estas restrições em conta:

1. **Gestão do Tempo e CPU em Nuvem (Serverless Timeout):**
   - Importar planilhas com 20 mil linhas processando "fuzzy matching" consome tempo logarítmico. Atualmente está mitigado limitando o batching ou agregando fora, mas eventualmente necessitará de "Background Workers" genuínos (Celery/Redis ou Lambdas em SQS/EventBridge), o que destoa do monólito atual.
   
2. **Versionamento de Custos de Insumo:**
   - O modelo usa o custo atual para todo retroativo. Se um queijo custava R$ 30 e agora custa R$ 60, as contas do mês passado (se processadas hoje) calcularão uma margem falsa. A arquitetura precisará no futuro de logs versionados de custo por timestamp.

3. **Arquitetura Acoplada de Views:**
   - Não somos baseados em APIs REST limpas / JSON puro. Estamos em SSR padrão Jinja2. Transições para "Mobile" ou interfaces altamente dinâmicas exigirão refatorar o back-end para um modelo padrão de API (Blueprint Rest).

---

## 6. Rotas de Crescimento Futuro (Roadmap de Inteligência)

*   **Aplicabilidade de ML/IA (Previsões):** Elevar a regressão atual para modelos Random Forest básicos para considerar flutuação complexa de PDV e intempéries (se chove, vende menos).
*   **Integração REST com APIs de PDVs modernizados:** Mudar de envio de CSV para Webhooks do iFood / Sistemas Totvs.
*   **Alerta e Gatilhos de WhatsApp:** Notificar proativamente os sócios: "Alerta de Inflação! O Fornecedor X acabou de entregar Tomate 20% mais caro. Sua Fatoração do Prato (Salada) agora gera lucro negativo. Atualizar cardápio!".

---

**Nota para os Modelos (LLMs):** A partir deste arquivo de contexto, trate desafios técnicos propondo soluções em Python `Flask/SQLAlchemy`, respeite a adoção de views Jinja2 do lado do cliente para poupar tempo com recodificação desnecessária (exceto quando pedido explicitamente), e priorize velocidade e "zero config" devidos aos constraints de nuvem limitados. Use este dossiê completo para correlacionar ideias e guiar o projeto AleroPrice ao próximo nível.
