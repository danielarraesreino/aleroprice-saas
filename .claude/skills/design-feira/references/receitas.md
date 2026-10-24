# Receitas dos modelos de bar (fonte de verdade: leia o arquivo, estas linhas são âncoras de 21/10/2026)

Se a linha mudou, procure o termo. Nunca copie de memória.

| Dispositivo | Bar-fonte | Já no artesão | Para quê |
|---|---|---|---|
| Ruído SVG `feTurbulence` + grão | landing.html:172-183 (svg l.181) | _base.html:78 | tira o chapado do fundo |
| Brasas/luz radial no `body::before` | landing.html:172-183 (`body::before`/`::after`) | `body::before` do _base | atmosfera por modelo |
| Ken Burns no hero | landing.html:285-288 | hero de cada modelo | foto viva, sem JS |
| Marquee de categorias | landing.html:342; craft:454; noturno:320 | _base.html:206-225 | ritmo; usa categorias reais |
| Motion + `.js-anim` + `.reveal` + stagger | landing.html:567-572, 1160-1222 | _base.html:517-540, 760, 824 | entrada orquestrada |
| Contador animado (só com dado real) | landing.html:822, 1203 | — | nota/ano; nunca inventar número |
| Lightbox acessível | landing.html:423-425, 1119-1142 | _base.html:494 | foto ampliada |
| Menu mobile temático | landing.html:216-269; brasa:285; craft:341 | _base (nav) | trocar o símbolo por modelo |
| Sombra dura `8px 8px 0` + hover em translate | noturno.html:442, 468 | cozinha | cartaz/serigrafia |
| Rasgo de papel com `mask` | brasa.html:251-252 | cozinha (`.serra`) | borda serrilhada |
| Etiqueta `clip-path` (seta) | brasa.html:487 | cozinha (`.fita`) | selo |
| Nome autoajustado `--n` | noturno.html:420; brasa:344 | — | título que cabe em 320 px |
| Foto duotone `mix-blend-mode:multiply` | noturno.html:599 | **falta no ritual** | unifica foto ruim |
| Grade 4 px `--s-1..--s-10` | craft.html:202-203 | `--s1..--s9` | ritmo vertical |
| 5 eixos no `<body>` | craft.html:853 (`data-heroina/leitura/foto`) | `body.modelo-*` | variar sem forkar CSS |
| Densidade `--sec-y` | tradicional.html:158, 424 | `--sec-y` | respiro por modelo |
| Fallback sem foto (listras, régua, inicial) | craft:369; brasa:377-383 (`.solo`); autoral:554 | `.marca-mono`, modo texto | **obrigatório** |
| Mosaico denso `grid-auto-flow:dense` | brasa.html:623 | galeria | galeria sem buraco |
| `prefers-reduced-motion` | landing.html:519; brasa:730 | _base.html:540 | acessibilidade |

## Modelo de artesão ← bar-fonte
| Modelo | Para quem | Parte de | Fonte display |
|---|---|---|---|
| vitrine | charcutaria, queijo, conserva | craft + clássico | Bodoni Moda |
| cozinha | comida na feira, pão, doce | brasa | Alfa Slab One |
| atelie | cerâmica, crochê, mosaico | autoral/tradicional | Bricolage Grotesque |
| jardim | planta, terrário, mel | tradicional | Young Serif |
| ritual | tarô, incenso, cristal | noturno | Abril Fatface |

Modelo novo: escolha a fonte-bar mais próxima, **leia-a inteira**, extraia o conceito (não só a cor).
