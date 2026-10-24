---
name: design-feira
description: Regras DURAS de design e entrega dos hotsites de expositor da Feira de Barão (modelos vitrine, cozinha, atelie, jardim, ritual em app/templates/site/modelos/artesao/) e de qualquer modelo novo de site. Use SEMPRE que for criar, editar, revisar, corrigir ou publicar um hotsite/modelo/prévia de expositor, trocar fotos, cores ou fontes de um modelo, importar leads de expositor, ou quando o pedido citar "hotsite", "modelo de artesão", "prévia", "expositor", "barraca", "tenant" ou "bardavila.bar como referência" — mesmo que o usuário não peça "design". Vale para os 94 tenants previstos: nenhuma exceção por cliente.
---

# design-feira — um padrão só, para 94 tenants

**Referência de qualidade: bardavila.bar** (`app/templates/site/landing.html`) e os 6 modelos de bar
(`site/modelos/{craft,tradicional,autoral,noturno,brasa}.html`). Um hotsite de expositor que parece menos
trabalhado que esses **não está pronto**, mesmo com o teste verde. O dono já rejeitou duas vezes modelos que
eram "cor trocada sobre base plana": se o modelo só difere dos outros em variável CSS, refaça.

## Hierarquia (quando as regras brigam)
palavra do usuário > bardavila.bar (o que ele faz) > `docs/DESIGN.md` > esta skill > skills genéricas
(`impeccable`, `frontend-design`, `ui-ux-pro-max`, `design-taste-frontend`, `web-design-guidelines`).
`docs/DESIGN_SKILLS.md` fala em "movimento 3, sem animação decorativa": para hotsite de expositor isso
**está superado** pelo pedido de nível-bar (efeitos e recursos, uma cena orquestrada + textura + marquee).

## Regras duras (R1–R13). Violou uma, não entregue.
1. **Peça própria por modelo.** Cada modelo tem identidade distinta: fonte display própria, paleta própria
   nos dois modos, composição de hero própria, ornamento próprio (ver `references/receitas.md`). Mudar só
   `:root` não conta.
2. **Dados, nunca cliente.** Nenhum nome, cor, foto ou texto de tenant dentro de template/CSS. Tudo vem de
   `site.*`, `produtos`, `rotulo()`; o tenant escolhe `site.modelo`. Se 94 tenants precisam de 94 edições de
   HTML, a arquitetura está errada.
3. **Base compartilhada em `_base.html` (blocos) e `_produtos.html` (macros).** Peça nova vai para um include
   `site/_*.html` quando usada por 2+ modelos. Não copie 10 KB de JS entre modelos.
4. **Fallback sem foto desenhado em TODO modelo** (monograma/inicial gigante sobre listras, régua, duotone).
   Teste com o tenant sem nenhuma imagem antes de entregar. Produto sem foto nunca vira retângulo cinza.
5. **Claro e escuro completos** (`prefers-color-scheme` + `data-theme`), contraste AA, botão de tema com
   `aria-label`. O hero pode ser sempre escuro; o texto sobre ele, não.
6. **Grade de 4 px** (`--s1..--s9`), tokens semânticos (`--line`, `--shadow-card`), largura 1160 px, 320 px
   sem rolagem horizontal, alvo de toque ≥ 44 px.
7. **Movimento com gate**: Motion 13.1.0 só depois de `.js-anim` em aba visível; `prefers-reduced-motion`
   desliga; **conteúdo nunca nasce escondido** sem JS (thumbnail e crawler veem a página completa).
8. **Uma cena orquestrada por página** (entrada do hero em cascata) + efeitos contínuos discretos (grão,
   Ken Burns, marquee). Sem fade-slide em cada seção "porque sim".
9. **Prévia óbvia**: todo tenant `eh_demo` mostra `site/_faixa_previa.html` ("Prévia para {Nome}. As imagens
   são ilustrativas…" + "Quero ativar meu site") e `noindex`. Nunca remova a faixa de um modelo.
10. **Imagem só com origem registrada.** Foto de expositor exige `AUTORIZADO.txt` (ver
    `app/scripts/receber_fotos.py`); foto de prévia fica em `static/img/demo/<slug>/` com `creditos.json`
    (origem + quem autorizou ou "ilustrativa"). Lado menor ≥ 800 px para hero/produto. Foto borrada ou
    ampliada não entra: prefira o fallback desenhado.
11. **Sem os tells de IA**: cabeçalho em caixa alta espaçada em todo bloco, `border-left` grosso, cartão
    dentro de cartão, emoji/glifo como ícone, gradiente roxo, 3 colunas iguais com ícone.
12. **Texto**: pt-BR, frase-padrão da Feira (Praça do Coco, Barão Geraldo, Campinas; sáb 10–16h, dom
    10–15h) onde `docs/documentacao/01_VOCABULARIO_E_TEXTOS.md` mandar; "barraca" = ponto físico, "bar" =
    casa de bebida, "expositor" = quem vende na Feira. Nada de promessa que o expositor não fez.
13. **Paridade com os bares.** Todo recurso marcado "replicar" em
    `~/Documentos/FEIRADEBARAO/documentacao/11_PARIDADE_BAR_X_EXPOSITOR.md` existe em todo modelo de
    expositor (head de SEO, newsletter, fallback, contador com dado real…). Recurso novo num bar entra
    nessa tabela no mesmo dia, para os 94 tenants não ficarem para trás.

## O que prende estas regras (não dependa só da memória)
- Hook de projeto `.claude/hooks/design_feira_lembrete.py`: avisa ao editar `app/templates/site/**`,
  `produto/**` e CSS; configurado em `.claude/settings.json` (na raiz do repo e na raiz de trabalho).
- `tests/integration/test_contrato_design.py`: piso de h1, SEO, claro/escuro, reduced-motion, imagem
  quebrada, vazamento de tenant, faixa de prévia, em TODOS os modelos, com e sem foto.
- `python -m app.scripts.capturar_modelos`: capturas de todos os modelos (modo × largura × foto).

## Fluxo obrigatório para criar ou alterar um modelo
1. Ler o modelo de bar-fonte (tabela em `references/receitas.md`) e `_base.html`. Não escrever de memória.
2. Plano curto: cena do hero, fonte, paleta claro/escuro, ornamento, fallback sem foto.
3. Implementar nos blocos de `_base.html`; efeitos copiados dos bares citam `arquivo:linha` no comentário.
4. Rodar `references/checklist.md` inteiro; capturas com `python -m app.scripts.capturar_modelos`.
5. `venv/bin/python -m pytest tests/unit tests/integration -q --no-cov -p no:cacheprovider` verde.
6. Mostrar as capturas ao dono ao lado de bardavila.bar. **Sem deploy sem OK.**

## Arquivos
- `references/receitas.md` — cada efeito dos bares com `arquivo:linha` e onde já existe no artesão.
- `references/checklist.md` — checklist de entrega e capturas.
- `references/multi-tenant.md` — regras para escalar a 94 tenants (dados, imagens, testes, importação).
