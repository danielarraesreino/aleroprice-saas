# Skills de design: origem, commits e adaptações

Instaladas em `.claude/skills/`. Nenhuma foi instalada com `npm i -g` nem `npx skills add`:
cada pasta foi lida inteira e copiada à mão. Data da revisão: 2026-10-21.

| Skill | Repositório @ commit | O que foi tirado / mudado |
|---|---|---|
| frontend-design | anthropics/skills @ dbd4588 | nada (só SKILL.md e licença) |
| webapp-testing | anthropics/skills @ dbd4588 | nada |
| ui-ux-pro-max | nextlevelbuilder/ui-ux-pro-max-skill @ 56ea9cf | sem `tests/`; caminho `${CLAUDE_PLUGIN_ROOT}` trocado por relativo. Scripts Python sem rede; só criam `design-system/` |
| impeccable | pbakaus/impeccable @ dad8dbb | **sem `scripts/`**: o launcher baixa e executa um binário do GitHub Releases. Comandos puramente textuais seguem valendo |
| web-design-guidelines | vercel-labs/agent-skills @ 063bee9 | regras **fixadas** em `guidelines.md` (o original busca por URL a cada uso). Hash em `SOURCE.txt` |
| design-taste-frontend | Leonxlnx/taste-skill @ 6010f91 | sem `scripts/` e `assets/` (Node de terceiros, `assets.mjs` usa rede); dials do projeto abaixo |

## Dials do taste-skill neste projeto

Variação 5, movimento 3, densidade 6. Motivo: público em celular, artesãos sem equipe de
design e nota móvel baixa. Sem animação decorativa; `prefers-reduced-motion` respeitado.

## Precedência quando discordam

palavra do usuário > `docs/DESIGN.md` > frontend-design > impeccable > ui-ux-pro-max >
design-taste-frontend > web-design-guidelines > ui-quality-baseline.

## Atualizar

Um humano baixa o commit novo, relê o diff e refaz a cópia. Nunca buscar regra por URL em tempo de uso.

## Como as skills foram usadas (registro de 21/10/2026)

Ordem aplicada em cada superfície: `impeccable` (modo Persuade, método de `new-work.md` e piso de
`craft-floor.md`) → `frontend-design` (plano de cor/tipo/layout antes de codar) → `ui-ux-pro-max`
(`search.py --design-system` com dials 5/3/6) → `design-taste-frontend` (tabela de "tells" do
`references/tells.md`) → `web-design-guidelines` (checagem local) → `ui-quality-baseline`.

O que valeu na prática, por skill:

| Skill | Efeito concreto no projeto |
|---|---|
| impeccable | Proibiu cabeçalho em caixa alta espaçada, `border-left` grosso, cartão-dentro-de-cartão, glifo/emoji como ícone. Exigiu uma única cena física para decidir claro/escuro |
| frontend-design | Plano em 4 blocos (cor, tipo, layout, princípios) antes de escrever; revisão do plano contra o óbvio |
| ui-ux-pro-max | Checklist de entrega (alvo 44 px, contraste 4,5:1, `prefers-reduced-motion`, 375/768/1024/1440). A paleta/fonte que a ferramenta sugeriu (azul + Outfit) **não serviu** e foi descartada: a marca da Berga é preto, vermelho e letra didone |
| design-taste-frontend | Banimento de hairline em caixa, numeração em seção, mono como "técnico", serifa gigante em itálico. Scripts Node dele não instalados |
| web-design-guidelines | Imagens com `width`/`height`, `color-scheme`, `touch-action`, `overscroll-behavior` no diálogo |
| webapp-testing | Não usada: o projeto já tem Playwright com o Chrome do sistema (`/usr/bin/google-chrome`) |

Limites conhecidos (não esconder): o `impeccable` roda sem `scripts/` (sem sorteio de direção, sem
página de decisão, sem gates de comparação com imagem, sem detector). A direção de cada superfície
foi decidida à mão a partir da marca e dos materiais reais, e conferida em capturas
320/390/768/1440, claro e escuro.

## Superfícies feitas (todas com `docs/DESIGN.md` como contrato)

| Superfície | Arquivos | Commit |
|---|---|---|
| Site do artesão (Berga) | `site/modelos/artesao.html`, `routes/publico/views.py` (`_proporcao`) | `155c9a2` (no ar) |
| `/feira` | `produto/feira.html`, `static/css/feira-expositores.css` | `4f661c6` |
| Home da Feira | `produto/landing.html`, `static/css/feira.css` (bloco `hm-*`), `views.py` (`_vitrine_de_expositores`) | `3048ce3` |
| Memória Viva | `produto/memoria/*`, `static/css/feira-memoria.css` | `57b5dec` |

Pendências de design: 71 `style=` inline ainda na home (dossiê com mapa, linha do tempo, tecnologia,
ROI, planos, modal), `produto/_topo.html` (Font Awesome + estilos inline), `produto/barao.html`,
6 modelos de bar e `site/landing.html`. Etapa de desempenho (nota móvel 42% na Vercel) segue
adiada até o usuário trazer os dados do Speed Insights.

## Armadilha da instalação (aconteceu)

O Claude Code procura skills de projeto a partir da **pasta raiz da sessão**. Esta sessão abre em
`GASTRONOMIA_ALERO_ECOSYSTEM/`, mas as skills ficam em
`GASTRONOMIA_ALERO_ECOSYSTEM/FEIRA_DE_BARAO_PLATAFORMA/.claude/skills/`. Por isso o `/reload-skills`
dizia "no changes" até existir o link
`GASTRONOMIA_ALERO_ECOSYSTEM/.claude/skills -> FEIRA_DE_BARAO_PLATAFORMA/.claude/skills`
(criado em 21/10/2026). Se algum dia as skills sumirem, refaça o link (caminho absoluto) e rode
`/reload-skills`.

## Como rodar as capturas (conferência visual)

```bash
# servidor local com banco de teste (nunca o de produção)
PYTHONPATH=$PWD DATABASE_URL=sqlite:///caminho/berga.db venv/bin/python serve.py
# Playwright com o Chrome do sistema: viewport 320/390/768/1440, color_scheme dark/light,
# rolar a página antes do screenshot para carregar as imagens lazy
```
