# DIRETRIZES DO PROJETO ALEROPRICE SAAS

## 1. Perfil do Produto (The Vibe)
- **Identidade:** SaaS B2B para gestão de restaurantes focado em lucro real e engenharia de cardápio.
- **UX:** Minimalista, "Zero Cliques", focada em dashboards visuais e alertas vermelhos/verdes para prejuízo/lucro.
- **Público:** Donos de restaurantes sem tempo. A interface deve ser "Mobile-First" e tolerante a falhas de conexão.

## 2. Trilhos Técnicos (Tech Rails - NÃO DESVIAR)
- **Backend:** Python 3.9+ com Flask.
- **ORM:** SQLAlchemy (Uso estrito de `session` com escopo).
- **Banco de Dados:** PostgreSQL (Produção) / SQLite (Dev).
- **Frontend:** Jinja2 (Server-side rendering) + Bootstrap 5 (mantenha simples) + Chart.js para gráficos.
- **Segurança (CRÍTICO):** Arquitetura Multi-Tenant Obrigatória. Toda query deve ter `WHERE restaurant_id = current_user.restaurant_id`.

## 3. Comportamento do Agente (Rules)
- **Planejamento:** Antes de codar, gere um "Implementation Plan" (Artifact).
- **Verificação:** Após alterar o código, use o "Browser Agent" para logar e verificar se a tela carrega sem erro 500.
- **Diffs:** Mostre diffs estilo Git. Não reescreva arquivos inteiros se puder apenas editar blocos.
- **Dependências:** Não adicione novas libs (pip) sem permissão explícita. Use `requirements.txt` como verdade absoluta.
2. Estratégia de "Mission Control" (Usando o Agent Manager)
O Antigravity brilha no Agent Manager View (a visão de gerenciamento), onde você pode rodar agentes em paralelo. Vamos dividir o trabalho do AleroPrice em três frentes assíncronas para você comandar:
Agente 01: O Arquiteto de Backend (Refatoração Multi-Tenant)
• Prompt Inicial: "Refatore os modelos Produto, Prato e Usuario para incluir restaurant_id. Garanta que a coluna seja Foreign Key não nula. Crie a migração do Alembic. Use o modo de Planejamento."
• Por que no Antigravity: O Gemini 3 Pro tem uma janela de contexto gigante (1M+ tokens). Ele consegue ler todo o seu repositório atual e entender onde cada query SQL precisa ser alterada para não vazar dados entre restaurantes.
Agente 02: O Designer de Frontend (Vibe Coding)
• Prompt Inicial: "Analise o arquivo dashboard.html. Quero que ele tenha uma 'vibe' de cockpit financeiro. Crie 3 cartões no topo: 'Lucro Hoje', 'Alertas de Custo' e 'Estoque Crítico'. Use Chart.js para um gráfico de tendência de custos. Gere o código e verifique no browser."
• O Diferencial: O Antigravity vai abrir o navegador, renderizar o HTML e "ver" se ficou bonito ou quebrado. Se ficar feio, você comenta no screenshot (Artifact) e ele arruma.
Agente 03: O Auditor de Qualidade (Testes)
• Prompt Inicial: "Crie um teste de integração que simule um upload de XML de Nota Fiscal (NFE). Verifique se o sistema cadastra os produtos e atualiza o estoque automaticamente. Use o terminal para rodar pytest."
• Autonomia: Ele vai usar o terminal para rodar os testes e te dar o log de sucesso ou falha.
3. Aproveitando o MCP (Model Context Protocol)
O texto menciona o MCP como uma "porta USB-C para IA". No Antigravity, você pode conectar o agente diretamente ao seu banco de dados local ou nuvem (PostgreSQL/Supabase).
• Ação: Vá na aba "MCP Servers" do Antigravity e instale o conector para PostgreSQL (se estiver usando banco local) ou Firebase/Google Cloud se já migrou.
• Benefício: O agente não vai "alucinar" nomes de tabelas. Ele vai ler o esquema real do banco antes de escrever as queries SQL do dashboard de lucratividade.
4. O Prompt de "Liftoff" (Copie e Cole no Agent Manager)
Agora, vá para o Agent Manager do Antigravity e lance este comando para iniciar a transformação para SaaS:
@Codebase Estamos migrando este projeto (AleroPrice) para um modelo SaaS Multi-Tenant.
Sua Missão:
1. Analise a estrutura atual do banco de dados em app/models.
2. Crie um Plano de Implementação (Artifact) para adicionar a tabela Restaurantes e vincular todos os dados a ela.
3. Segurança: Identifique todas as rotas em app/routes que fazem queries ao banco e liste quais precisam ser blindadas com filter_by(restaurant_id=...).
Restrições: Siga estritamente as regras definidas em .agent/rules/rules.md. Não execute código destrutivo no terminal sem pedir revisão (Policy: Request Review).
Inicie o modo Planning e me mostre o plano.
Resumo da Orientação Sênior
Não trate o Antigravity como um editor de texto. Trate-o como um Gerente de Projetos que coda.
1. Defina as Regras (o arquivo .md).
2. Use o Agent Manager para tarefas paralelas.
3. Exija Artifacts (Planos e Screenshots) antes de aceitar código.
4. Use o Browser para ele se auto-corrigir visualmente.
Se ele travar ou entrar em loop (o que os reviews dizem que pode acontecer), mude o modelo para Claude 3.5 Sonnet (se disponível na sua preview) para tarefas de lógica backend, e use o Gemini 3 Pro para tarefas de UI e multimodais.
