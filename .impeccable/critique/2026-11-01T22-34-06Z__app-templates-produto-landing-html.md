---
target: portal Feira de Barão (home + 6 páginas), produção 624e62a vs efd1a5a
total_score: 20
max_score: 32
na_heuristics: 7,10
p0_count: 0
p1_count: 3
target_identity: "file:/mnt/armazenamento/Projetos/GASTRONOMIA_ALERO_ECOSYSTEM/FEIRA_DE_BARAO_PLATAFORMA/app/templates/produto/landing.html"
target_fingerprint: "sha256:194a31e4d2ea454a2e947cf727e448cf49c6ee8a6b9e162a6be8a688054c3cc8"
target_path: /mnt/armazenamento/Projetos/GASTRONOMIA_ALERO_ECOSYSTEM/FEIRA_DE_BARAO_PLATAFORMA/app/templates/produto/landing.html
timestamp: 2026-11-01T22-34-06Z
slug: app-templates-produto-landing-html
---
Method: dual-agent (A: sub-agente design-review isolado · B: sub-agente detector+navegador isolado, em paralelo)

# Critique impeccable: portal Feira de Barão, produção `624e62a` vs. `efd1a5a`

Impeccable v4.7.0 (engine 0.1.16), rodada completa: `impeccable context`, Assessments A e B em sub-agentes isolados e paralelos, `impeccable detect --json` nos 6 alvos + landing de `efd1a5a`, injeção do `detect.js` em 7 páginas de produção + home do "antes". Alvo do snapshot: `app/templates/produto/landing.html`.

**Ressalva do método:** a injeção do `detect.js` no painel do navegador visível falhou (`net::ERR_BLOCKED_BY_CLIENT` no `<script src=http://localhost:8400/detect.js>`, `Failed to fetch` no fetch; o arquivo tem 2,96 MB, grande demais para colar inline). Funcionou em Chrome headless (Playwright, `add_script_tag(path=…)`). **Não há overlay visível para o usuário.** A aba aberta em https://feiradebarao.com.br/ tem o título "[Human]", mas está sem overlay.

## Design Health Score (produção, 624e62a)

| # | Heurística | Nota | Problema principal |
|---|---|---|---|
| 1 | Visibilidade do status | 2 | Nada diz se a feira está aberta agora; em 390 o card "Quando e onde" começa em y=922, abaixo da dobra |
| 2 | Correspondência com o mundo real | 3 | Vocabulário certo (expositor, barraca, Praça do Coco); mas em /presentes o único "presente feito à mão" são 4 risotos de uma barraca |
| 3 | Controle e liberdade | 3 | Gaveta fecha com Esc, × e fundo; em /feira os filtros deixaram de grudar no celular, sem volta rápida |
| 4 | Consistência e padrões | 2 | Domingo "9h–15h" em `presentes.html:76` contra 10h–15h no resto; dois links seguidos para /memoria na gaveta (`_topo.html:52-53`) |
| 5 | Prevenção de erros | 3 | Faixa "R$ 604" corrigida; /presentes ainda mostra H2 + "Nenhum presente nesta faixa" 3× (`presentes.html:62-68`) |
| 6 | Reconhecer em vez de lembrar | 3 | Subcategorias visíveis com "Ver as N": melhorou |
| 7 | Flexibilidade e eficiência | n/a | Superfície Persuade |
| 8 | Estética e minimalismo | 2 | Trocou conteúdo identitário por chips; em doces, 16 chips empurram o 1º produto de y=715 para y=1287 |
| 9 | Recuperação de erros | 2 | Estado vazio repetido 3× com a mesma frase em /presentes |
| 10 | Ajuda e documentação | n/a | Persuade; "Como encomendar" cobre o mínimo |
| **Total** | | **20/32 (62,5%)** | **Acceptable** |

n/a: 7 e 10 (regra de modo Persuade). O "antes" ficaria em cerca de 20/32 também, mas com outros defeitos. A nota igual esconde uma troca: o `517ebf6` corrigiu engenharia e quebrou identidade.

## Veredito de especificidade

**Avaliação do LLM (A, feita sem ver o detector).**

- **Antes:** era inconfundivelmente a Feira de Barão. Tinha o sobretítulo de lugar no H1 e o trio da Memória Viva:
  - o dossiê com mapa e Street View;
  - o mural com relatos assinados por moradores;
  - a linha do tempo de 1870 até hoje, numa faixa escura.

  A alternância creme / faixa escura / creme / CTA escuro dava ritmo.
- **Defeitos reais do antes:**
  - o dossiê ocupava cerca de 7.000 px em 1440, com o mapa preso em 100vh;
  - o header vazava a tela em 1440;
  - a faixa de preço lia "R$ 604".
- **Depois:** a home virou busca + chips + grade + dois parágrafos de história + bares + CTA. Trocando o nome, serve para qualquer marketplace de feira. A especificidade caiu de forte para fraca: o que foi cortado era o diferencial do lugar, não enfeite.

**Varredura determinística (B).**

| Alvo | Exit | Achados |
|---|---|---|
| `produto/landing.html` | 2 | 1 · `flat-type-hierarchy` (falso positivo, ver abaixo) |
| `produto/feira.html`, `presentes.html`, `memoria/`, `_topo.html` | 0 | 0 (calculado sem CSS, então incompleto) |
| `site/modelos/artesao/` | 2 | 11, todos em `_base.html`: `broken-image` (:825), `tight-leading` ×3 (ex. :286), `all-caps-body`, `wide-tracking` (:99, 220, 286, 412), `cramped-padding`, `kicker-above-heading` (:683-684), `side-tab` (:400), `marquee` (:218, 227), `repeating-stripes-gradient` (:402) |
| landing de `efd1a5a` | 2 | 3 · `low-contrast` ×2 + `flat-type-hierarchy` (todos com fundo #fff presumido) |

**No navegador (detect.js injetado, Chrome headless, 1440×900):**

- `/` produção: **9** achados.
  - `straggler` ×6;
  - `line-length` de ~93 caracteres;
  - `unbalanced-heading` (17%);
  - de página inteira: `overused-font` (Plus Jakarta Sans em 67%), `cream-palette`, `dark-glow` (#ffba00), `repeating-stripes-gradient`.
- `/` antes (`efd1a5a`): **17** achados. Além dos acima:
  - `hero-eyebrow-chip` (o sobretítulo "Praça do Coco · Barão Geraldo · Campinas");
  - `kicker-above-heading` ×5 (Feito à Mão em Barão, Território & Raízes, Vozes do Bairro, Cronologia Documental, Rede Comunitária);
  - mais 1 `line-length` e 1 `unbalanced-heading`.
- `/feira`: 1 · `/feira/.../doces-e-confeitaria`: 1 (só os achados de página inteira).
- `/presentes`: 3 (`line-length` de ~89 caracteres, `unbalanced-heading` 34%).
- `/memoria`: 12 (`unbalanced-heading` ×6, `straggler` ×6).
- `/expositor/afazeres-arts`: 11.
  - `low-contrast` ×3: 4,4:1 em #a0a7cf/#283692; **3,9:1 em #706e72/#e7e2d8; 3,5:1 em #777578/#e7e2d8**;
  - `hero-eyebrow-chip`, `kicker-above-heading` ×5, `nested-cards`, `side-tab`, `pulsing-dot`, `marquee`, `cream-palette`.

**Onde LLM e detector concordam e divergem:**

- **A descoberta central.** O detector "melhora" a home de 17 para 9 achados exatamente por ter removido o sobretítulo de lugar e os 5 rótulos da Memória Viva. Ou seja, o `517ebf6` otimizou contra regras genéricas de anti-padrão (eyebrow, kicker) e apagou justamente o que a revisão A identifica como a identidade.

  Pela hierarquia do projeto (palavra do dono > bardavila.bar > DESIGN.md > design-feira > impeccable), essas regras do detector não podiam ter vencido. Uma contagem menor de achados aqui **não** é design melhor.
- **O que o detector pegou e A não pegou:**
  - linhas de ~93 caracteres na home e de ~89 em /presentes (DESIGN.md manda ≤ 65);
  - 6 stragglers por página na home e na /memoria;
  - **dois pares de contraste reprovados em AA no hotsite** (3,5:1 e 3,9:1 sobre #e7e2d8, texto secundário do afazeres-arts).
- **Falsos positivos:**
  - `flat-type-hierarchy` na CLI: o detector não resolve `{{ url_for() }}`, então não carrega o CSS e mede tudo como 16 px. No navegador, o achado não aparece.
  - Os `low-contrast` da landing de `efd1a5a` na CLI: o fundo #fff é presumido, mas o fundo real é creme.
  - `broken-image` em `_base.html:825`: o lightbox fica com `src=""` de propósito.
  - `cream-palette` e `overused-font`: são a paleta papel/tinta/tomate e a fonte definidas no DESIGN.md. O brief vence.
  - `kicker-above-heading` e `marquee` no hotsite: são padrões dos modelos de bar do design-feira.

**Overlays visuais:** a injeção no navegador visível falhou (motivo acima). Não há overlay na aba [Human]. Os achados vieram do console do Chrome headless.

## Impressão geral
O `517ebf6` resolveu problemas reais de engenharia: overflow em 1440, faixa "R$ 604", mapa que prendia o toque, foto primeiro. Mas, em nome de "home mais curta", cortou a alma da página: a Memória Viva e o sobretítulo de lugar. Ao mesmo tempo, trocou chips escondidos por chips em coluna, o que piorou o celular. O dono tem razão no diagnóstico. A maior oportunidade é devolver a Memória numa forma compacta, sem desfazer as correções.

## O que funciona
1. **Busca como ação primária da home** (`landing.html:55-75`): é a ação real de quem procura um expositor.
2. **Correções de engenharia certas:**
   - header sem overflow em 1440;
   - faixa de preço separada;
   - `dragging: !L.Browser.mobile` em `memoria/hub.html:64`;
   - expositores com foto primeiro (`views.py:404-406`).
3. **Base visual preservada:**
   - paleta com contraste AA calculado (taupe/papel 5,91; tomate/papel 5,37; branco/tomate 6,21);
   - fonte de cartaz;
   - `:focus-visible` global (`feira.css:28`) e "Pular para o conteúdo".

## Problemas prioritários

**[P1] A home perdeu a Memória Viva, que era a identidade.**
- **Evidência:** em 390, a home passou de 20.152 para 10.541 px. Sumiram os H2 "A história de Barão Geraldo no mapa", "Mural da Memória Viva" e "A Linha do Tempo", junto com o modal "Contar história". O detector confirma que os rótulos e o sobretítulo foram removidos.
- **Por que importa:** é o único conteúdo que nenhuma outra feira tem. É o que convida o morador a participar.
- **Correção:** um revert seletivo de conteúdo vindo de `efd1a5a`:
  - a linha do tempo escura (6 cards);
  - 3 relatos do mural;
  - 1 cartão "mapa histórico" com miniatura estática linkando `/memoria#dossie` (sem Leaflet de 100vh na home);
  - o botão "Contar história".

  Meta: cerca de 13–14 mil px em 390.
- **Comando:** `/impeccable shape` e depois `/impeccable polish`.

**[P1] Chips em coluna empurram o conteúdo no celular.**
- **Evidência:**
  - em `/feira/comida-artesanal/doces-e-confeitaria` (390), os filtros passaram de 44+44 para 200+460 px, e o 1º produto foi de y=715 para y=1287;
  - na home, o CTA "Ver expositores e mapa" começa em y=794 numa tela de 844 e fica cortado;
  - a barra de /feira deixou de grudar.
- **Por que importa:** quem está na praça com o celular rola mais de 1.200 px antes de ver um produto.
- **Correção:** fileira rolável com máscara de degradê e último chip "+N", ou 1–2 linhas com `<details>` "Mais filtros". Na home, 3 atalhos curtos.
- **Comando:** `/impeccable adapt`.

**[P1] /presentes com 3 seções vazias, horário divergente e "presente" que é risoto.**
- **Evidência:**
  - "Nenhum presente nesta faixa" 3× (`presentes.html:62-68`);
  - "domingo 9h–15h" (`presentes.html:76`, vindo de `350aba6`, anterior ao `517ebf6`) contra 10h–15h no resto;
  - o único conteúdo são 4 risotos.
- **Por que importa:** é a página de intenção de compra, e parece abandonada. Quem confia no 9h chega com a feira fechada.
- **Correção:** aplicar `if f.itens` no laço de seções, ler o horário de `feira.*` e revisar o critério de "presente feito à mão".
- **Comando:** `/impeccable harden` + `/impeccable clarify`.

**[P2] Sobretítulo de lugar removido do H1.**
- **Evidência:** "Praça do Coco · Barão Geraldo · Campinas – SP" saiu do H1. O detector chama isso de `hero-eyebrow-chip`, mas aqui ele é a âncora do lugar, e a R11 do design-feira condena o rótulo "em todo bloco", não este uso único.
- **Correção:** restaurar só o sobretítulo do H1.
- **Comando:** `/impeccable typeset`.

**[P2] Portal sem modo escuro, linhas longas e contraste reprovado no hotsite.**
- **Evidência:**
  - nenhuma regra `prefers-color-scheme` em `feira*.css` (nas duas versões), contra o princípio 4 do DESIGN.md;
  - linhas de ~93 caracteres na home e de ~89 em /presentes (DESIGN.md pede ≤ 65);
  - no afazeres-arts, texto #706e72 e #777578 sobre #e7e2d8 (3,9:1 e 3,5:1, abaixo do AA).
- **Comando:** `/impeccable colorize` (modo escuro do portal) + `/impeccable typeset` (medida) + `/impeccable audit` no hotsite.

## Alertas por persona

- **Jordan (primeira vez):**
  - na dobra de 390 não sabe quando a feira acontece;
  - na gaveta, "Memória Viva: mapa, mural e linha do tempo" e "Acervo da Memória Viva" levam ao mesmo lugar;
  - em /presentes encontra três "Nenhum presente" e conclui que o site está abandonado.
- **Riley (stress tester):**
  - categoria com 9 subcategorias vira 460 px de chips;
  - uma faixa só de preço faz a seção Presentes sumir da home sem aviso (`landing.html:139`);
  - horários conflitantes (9h e 10h);
  - presentes que são risotos.
- **Casey (celular, uma mão):**
  - o CTA primário fica cortado no rodapé;
  - os filtros de /feira não grudam e voltar a eles exige rolar 1.287 px;
  - o logo tem 123×28 px, abaixo de 44 px.
- **Morador de Barão (persona do projeto):** era quem mais ganhava com a home antiga (mural com nomes, "mande sua memória"). Agora não é convidado a nada na home: o "Contar história" saiu do header e virou um link de texto.
- **Visitante de domingo (persona do projeto):** quer saber se está aberta, onde e o que tem. A dobra responde só "o que tem". Em /presentes lê que abre às 9h.

## Observações menores
- Gaveta com dois links seguidos para /memoria (`_topo.html:52-53`).
- "Quero receber" com 320×43 px, quase no limite de 44.
- A home ficou em creme contínuo até o CTA e perdeu o ritmo tonal da faixa escura.
- `/memoria` e o hotsite estão visualmente iguais. Só mudaram o arrasto do mapa e o `alt` da galeria.
- O detector acusa `dark-glow` #ffba00 e `straggler` ×6 na home: polimento de quebra de linha (`text-wrap: balance/pretty`).
- As capturas `-dobra` de 390 do material de apoio estão quebradas (área vazia no meio da rolagem). Refazer antes de mostrar ao dono.
- Foco por teclado: há `:focus-visible` global, mas não foi verificado ao vivo.

## Perguntas para refletir
- Se a Memória é o que só a Feira de Barão tem, por que foi a primeira coisa cortada quando a home "ficou comprida"?
- Uma home de 10 mil px só com chips é mais curta para quem quer comprar. E para o morador?
- O visitante de domingo deve ver primeiro a busca ou a hora em que a feira abre?
- /presentes com risoto é guia de presentes ou cardápio?
