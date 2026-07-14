# Dossiê Técnico e Funcional Completo: AleroPrice SaaS
**Versão:** 3.0 (Otimizada para Ingestão de LLMs / NotebookLM)
**Escopo do Sistema:** Gestão de Custos, Estoque e Precificação para Restaurantes e Barracas.

---

## 1. Visão Geral do Produto e Objetivo
O **AleroPrice** é um sistema de Gestão Financeira e Engenharia de Cardápio para pequenos e médios estabelecimentos do ramo alimentício. Diferente de um ERP comum que apenas cadastra produtos, o AleroPrice atua como um analista financeiro: ele cruza o custo flutuante das matérias-primas (insumos) com o histórico de vendas para revelar o **lucro real** e alertar sobre margens negativas (prejuízo).

### Core Business e Valor
- **Engenharia de Cardápio Real-time:** Em vez de recalcular preços manualmente quando a carne ou queijo sobem de preço, o sistema atualiza automaticamente os custos dos pratos inteiros.
- **Operação "Hands-off":** Redução de input manual pelo usuário. Em vez de registrar baixa de insumos, o usuário sobe planilhas de vendas brutas; o sistema deduce tudo usando Fichas Técnicas.
- **Consultor Alimentar Automático:** Prevê demanda futura e sinaliza o quanto comprar para evitar rupturas e desperdícios.

---

## 2. Arquitetura e Stack Tecnológico
O design do AleroPrice é otimizado para ambientes *Serverless* e foi construído com a premissa de um Monolito com "Thin Client e Smart Server".

### Tecnologias Utilizadas
- **Backend/Core:** Python 3.8+ utilizando o microframework **Flask**.
- **Processamento de Visão:** Renderização via Server-Side Rendering (SSR) utilizando **Jinja2**. Não utiliza frameworks reativos pesados (como React/Vue) no núcleo original.
- **Frontend/Estilização:** Bootstrap 5 (Layout responsivo) e Chart.js (Dashboards e gráficos).
- **ORM (Mapeamento Relacional de Objetos):** **SQLAlchemy**. A camada de dados detecta o ambiente para usar banco de dados apropriado (SQLite local, PostgreSQL em produção como Neon ou Supabase).
- **Ambiente de Hospedagem:** Orientado a Serverless via **Vercel** (Time-out strict de execuções).
- **Padrão Arquitetural:** Model-View-Controller (MVC) em estrutura de Blueprints.

### Restrições da Arquitetura (Serverless Constraints)
O fato de rodar em Vercel Functions proíbe rotinas multithread, WebSockets puros não gerenciados e conexões persistentes longas de banco de dados nativas. As consultas são construídas para evitar o problema de "N+1 Queries" (ex: Usando `joinedload` e agregações diretas para o cálculo do Dashboard de desempenho contornando limites de timeout).

---

## 3. Modelo de Dados e Domínio (Tabelas do ERP)
As entidades funcionam em cascata. O custo "sobe" do Insumo para o Prato e o estoque "desce" do Prato vendido para o Insumo estocado.

### 3.1. Núcleo Produtivo e Ficha Técnica
*   **Produto / Insumo (`modelo_produto.py`):** Matéria-prima bruta (Ex: Carne, Tomate, Farinha). Possui preço de custo atual e rastreio de estoque em tempo real.
*   **Prato (`modelo_prato.py`):** O item que é vendido ao consumidor (Ex: Pastel de Carne). Seu custo é derivado dinamicamente pela Ficha Técnica. Possui campos de Preço de Venda Sugerido e Rateio de Custo Indireto.
*   **PratoInsumo (Associação N:M):** Tabela pivot que define a Ficha Técnica. Especifica que no Prato X vai *Y gramas* do Insumo Z.

### 3.2. Estoque e Suprimentos
*   **NFNota e NFItem (`modelo_nfe.py`):** Logs imutáveis de Notas Fiscais Eletrônicas processadas, base para alterar o Preço de Custo de um Produto ao encontrar inflação nas compras.
*   **MovimentacaoEstoque (`modelo_estoque.py`):** Livro-razão e auditoria. Toda grama que aumenta ou diminui passa por um registro (Comercial, Perda, Ajuste, Produção).
*   **RegistroDesperdicio (`modelo_desperdicio.py`):** Módulo para justificar e monetizar descartes (vencimento, erro de preparo).

### 3.3. Inteligência Comercial
*   **HistoricoVendas (`modelo_previsao.py`):** Consolidação de vendas. Otimizado para não lotar o banco: Vendas do mesmo dia/produto são agregadas numa mesma linha.
*   **CustoIndireto (`modelo_custo.py`):** Aluguel, folha de pagamento, internet. Valores rateados entre os Pratos produzidos para chegar à margem de lucro exata.

---

## 4. Funcionalidades Matadoras (Core Features)

### A. Motor de Importação Inteligente de Vendas com Fuzzy Matching
Sistemas de PDVs externos geram nomes com erro (ex: "Pastel Carne", "P. de Carne"). O usuário sobe planilhas despadronizadas de vendas, e o AleroPrice aplica um **Fuzzy Matcher** que varre a distância semântica dos nomes (tolerando ~80% de precisão) e os converte ao formato oficial cadastrado. Vendas do mesmo dia são agregadas para economia de processamento em banco de dados. Ao computar a venda do "Pastel", o sistema percorre a Ficha Técnica e debita gramas de farinha e carne.

### B. Previsão de Demanda ("Consultor" Preditivo)
Analisa a curva histórica para prever as compras da próxima semana usando dois algoritmos combinados:
1.  **Média Móvel Simples:** Verifica o consumo histórico em períodos de calmaria de produtos estáveis.
2.  **Regressão Linear Básica:** Capta as inclinações de crescimento ou queda vertiginosa nos pedidos, identificando tendência.
3.  **Fatores de Sazonalidade:** Permite aos donos parametrizarem multiplicadores (ex: "Sexta vende +50%", "Em época chuva as sopas vendem +20%").

### C. Leitor de NFe Anti-frágil e Atualizador de Custo
Ao realizar o upload de notas XML do Governo, o sistema limpa o namespace (`<ns1:Nfe>` vira apenas Nfe), captura as alíquotas reais usando a biblioteca transicional, e atualiza o PREÇO do insumo no banco, alterando imediatamente a Margem de Lucro projetada no Dashboard Gerencial caso exista defasagem de preço.

---

## 5. Gargalos Técnicos e Débito de Arquitetura em Foco
Ao debater sobre a viabilidade e evolução desta base, a IA deve focar as seguintes restrições inerentes do projeto atual:
1. **Serverless Timeout nas Importações Pesadas:** Uma planilha massiva usando rotinas O(n) e Fuzzy matching logarítmico sem o uso de Workers Assíncronos puros corre risco de Time-Out em ambientes serverless da Vercel.
2. **Histórico Versionado de Preços de Insumos:** Atualmente retrocede o CMV do prato com base no TICKET DE CUSTO ATUAL da matéria-prima. Falta versionar e criar um log no tempo do preço do insumo para que o lucro de 2 meses atrás não mostre "negativo" hoje por causa da inflação de ontem.
3. **Alto Acoplamento Visual no SSR:** A estrutura Jinja2 traz simplicidade dev, mas exige serialização das rotas do modelo caso queira-se transformar numa API em REST robusta para alimentar PWA Mobile no futuro.

---

## 6. Checklist de Qualidade do Sistema AleroPrice SaaS
- [x] Detecção inteligente de colunas em CSV/Excel.
- [x] Pipeline de baixa simultânea de múltiplos insumos compondo um produto.
- [x] Gráficos SSR Chart.js alimentados via propriedades de Contexto do Flask.
- [x] Tolerância em Parsing XML independentemente do software ERP Faturador Brasileiro.
- [x] Mapeamento Relacional e tratamento robusto `db.session.rollback()` contra falhas parciais em importações.
