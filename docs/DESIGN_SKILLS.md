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
