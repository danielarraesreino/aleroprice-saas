# Auditoria UI/UX, acessibilidade, responsividade e desempenho — produção

Data: 2026-10-17 · Método: navegador embutido (viewports 375×812, 768×1024, 1280×800), medição via
`performance.*`/DOM em `javascript_tool`, `curl -w` para TTFB, leitura dos templates. Somente leitura:
nenhum formulário enviado, nenhum login. Referências: skills design-critique, accessibility-review
(WCAG 2.1 AA) e web-perf. Limitações: sem trace do DevTools (sem TBT/INP), rede rápida (não houve
throttling 3G), sem leitor de tela real e sem teste de zoom 200%.

## Notas

| Área | Nota | Resumo |
|---|---|---|
| UI/UX | 6,5 | Identidade forte e coerente por modelo; mas a vitrine esconde a oferta (Planos a 78% da página, menu desktop cortado) e o site do cliente mistura área administrativa com navegação do freguês. |
| Acessibilidade | 6,0 | Labels, `lang`, alt e inputs 16px estão bons. Falham: menus fechados focáveis/`aria-hidden` com foco, contraste de pílulas e kickers, alvos < 44px, modais sem `role="dialog"`, galeria sem teclado. |
| Responsividade | 7,0 | Nenhuma rolagem horizontal em 375/768/1280. Problemas: dock da prévia cobre 20% da tela e esconde o WhatsApp; nav desktop da vitrine é um carrossel sem barra. |
| Desempenho | 7,0 | TTFB 80–240 ms, CLS ≈ 0, prévias com ~75 KB. Bar da Vila baixa 1,36 MB no 1º acesso mobile (fotos 1200 px em cards de 157 px) e não é cacheado na borda. |

## Medições

| Página (mobile 375) | TTFB curl | HTML | Total / req | LCP (elemento) | CLS |
|---|---|---|---|---|---|
| feiradebarao.com.br/ | 80–108 ms (edge HIT) | 22 KB | 465 KB / 21 | 180–520 ms (texto do hero) | 0 |
| bardavila.bar/ | 149–153 ms (MISS, `max-age=0`) | 20 KB | **1.361 KB / 8** | 604 ms (texto) | 0,001 |
| /bar/bar-do-guiu (5 modelos) | 175–240 ms | 23–26 KB | 72–77 KB / 2–4 | 440–852 ms | 0–0,001 |
| bardavila.bar/bar/bar-da-vila/cardapio | — | 3 KB | 326 KB / 1 (+lazy) | 256 ms | 0 |
| /auth/login | 140–155 ms | 2 KB | 78 KB / 8 (4 CSS + 4 JS) | 336 ms | 0 |
| /cadastro | 135–144 ms | 3 KB | ~3 KB + fonte / 0 | 216 ms | 0 |

Observação: `/bar/bar-do-guiu/cardapio` responde **404** (a prévia não tem pratos — comportamento
intencional em `app/routes/publico/views.py:609-610`); nenhuma página linka para ele.

## Achados (ordenados por impacto)

### 1. Vitrine: menu desktop corta "Planos", "Calculadora", "Infraestrutura IA" e "23 Barracas" — UI/UX · Alto · P
- Evidência: https://feiradebarao.com.br/ em 1280×800. `nav.nav-dossie` tem 597 px visíveis para 1083 px
  de conteúdo; "PLANOS" fica em x=1297–1369 (fora da viewport), com barra de rolagem escondida.
- Código: `app/templates/produto/landing.html:132-139` (`overflow-x:auto; scrollbar-width:none`),
  `:674-677`, `:870`.
- Correção: reduzir para 4–5 itens (Dossiê, Barracas, Planos, Contato) e mover o resto para o rodapé
  ou para o menu "MENU" também no desktop até ~1400 px. Nunca esconder a barra sem um indicador.

### 2. Bar da Vila (cliente pagante): 1 MB de fotos de pratos fora da dobra baixadas na hora — Desempenho · Alto · M
- Evidência: bardavila.bar mobile — `foto-5.jpg` 323 KB, `foto-20.jpg` 315 KB, `foto-3.jpg` 245 KB,
  `foto-17.jpg` 152 KB baixadas no load; são `background-image` de cards de 157×~110 px (266×190 no
  desktop). Galeria: `<img>` 1200 px exibidos a 157 px. Cardápio QR: miniaturas de 84 px com fonte de
  1200 px (`foto-5.jpg` 323 KB eager).
- Código: `app/templates/site/landing.html:722` (`div.photo` com `background-image`), `:856`,
  `app/templates/site/cardapio.html` (miniaturas); pasta `app/static/img/bar/` (4,1 MB).
- Correção: gerar derivados 400/800 px em WebP/AVIF (≤ 40 KB), trocar `div.photo` por
  `<img loading="lazy" width height srcset sizes>` mantendo o `alt` do `aria-label`. Ganho estimado:
  ~1,2 MB → ~0,25 MB no 1º acesso mobile.

### 3. Site do cliente e prévias não usam cache de borda (risco de cold start ~9 s) — Desempenho · Alto · M
- Evidência: `curl -I https://bardavila.bar/` → `cache-control: public, max-age=0, must-revalidate`,
  `set-cookie: session=…` (CSRF do form de reserva), `vary: Cookie`, `x-vercel-cache: MISS`. A vitrine
  já resolve isso (`x-vercel-cache: HIT`, `app/routes/publico/views.py:200-214`, que cita cold start ~9 s).
- Correção: servir a landing do bar sem sessão (token CSRF buscado por `fetch` só ao focar o form de
  reserva, ou rota POST isenta com honeypot + rate limit, como o form de novidades) e aplicar o mesmo
  `s-maxage=300, stale-while-revalidate`.

### 4. Menus fechados continuam focáveis e/ou `aria-hidden` com foco dentro — A11y · Alto · P
- Evidência (Tab percorre links invisíveis; WCAG 2.4.3 / 4.1.2):
  - Vitrine: drawer fechado só sai da tela (`right:-100%`), `visibility:visible`, 8 links + "×" no tab
    order — `app/templates/produto/landing.html:784-792`, `:900-903`.
  - Bar da Vila / modelo clássico: `.mobile-menu` fechado só com `translateY(-101%)`, 7 links
    focáveis — `app/templates/site/landing.html:228-235`, `:624`.
  - Noturno: `.painel` com `aria-hidden="true"` mas visível e focável (inclusive no desktop) —
    `app/templates/site/modelos/noturno.html:365-371`, `:847`.
- Correção: copiar o padrão já correto de craft/brasa/autoral (`visibility:hidden` +
  transição de `visibility`, ex. `craft.html:339-345`, `brasa.html:289-295`) ou `inert` no fechado;
  mover o foco para o 1º link ao abrir e devolver ao botão ao fechar (já feito em `brasa.html:1309`).

### 5. Dock da prévia cobre 20% da tela e esconde o botão de WhatsApp — Responsividade/UX · Alto · P
- Evidência: /bar/bar-do-guiu em 375×812: `#demo-dock-root` fixo, 167 px de altura (z-index 99999);
  `a.wa` (z-index 60) em y=732–792 fica inteiramente sob o dock (`elementFromPoint` → `dock-pill`).
  `body` recebe só 140 px de `padding-bottom` (27 px do rodapé ficam cobertos). Desktop: 107 px (13%).
- Código: `app/templates/site/_demo_dock.html:10-14`, `:275-279`.
- Correção: dock recolhível (chip "Personalizar ▲" de ~48 px que expande), `padding-bottom` igual à
  altura real (via `ResizeObserver`/CSS var) e subir `.wa` com `bottom: calc(var(--dock-h) + 16px)`.

### 6. Contraste insuficiente em elementos recorrentes — A11y · Médio · P
| Onde | Cores | Razão | Exigido | Código |
|---|---|---|---|---|
| Pílula ativa do dock (todas as prévias) | #fff / #ff6a2b, 12 px | 2,86 | 4,5 | `_demo_dock.html:178-181` |
| Vitrine "Trem Funilense · Ferrovia" | #f59e0b / #fff, 12,5 px | 2,15 | 4,5 | `produto/landing.html:46`, `:1240` |
| Craft, kicker do hero sem foto ("VINHEDO–SP") | #f0b357 sobre véu ~45%, 10,5 px | ~2,8 | 4,5 | `modelos/craft.html:239`, `:373` |
| Craft, rótulos `--amber` claro | #9c5c0b / #e7e3d8, 10,5–11,5 px | 4,15 | 4,5 | `modelos/craft.html:227`, `:253` |
| Brasa claro, "OUT"/"resenha" | #b8480a / #d3bd95 | 2,89 | 4,5 / 3 | `modelos/brasa.html:178`, `:198` |
| Noturno claro, "Próximo show", "DE SEG A SEX" | #f1ede2 / #4c6a00; #cf0b52 / #e7e2d4, 12,8 px | 4,12 / 4,24 | 4,5 | `modelos/noturno.html:187-190`, `:208-209` |
- Correção: escurecer a pílula para #c2410c (≥ 4,5 com branco), âmbar da vitrine para #b45309,
  e subir os tons `--amber` do modo claro em ~10% de luminosidade inversa; revalidar com o script.

### 7. Texto muito pequeno nos modelos — A11y/UX · Médio · P
- Evidência: mínimos medidos em 375 px — craft 9,6 px ("ONDE", `.hero-specs .k` 0,6rem), 10,56 px
  (kicker, "role e sente o cheiro"); "EXEMPLO" 10 px em todos; Bar da Vila 11,5 px ("★ O MAIS PEDIDO").
- Código: `modelos/craft.html:373`, `:385`, `:405`, `:413`.
- Correção: piso de 12 px (0,75rem) para microtextos e 14 px para qualquer texto informativo.

### 8. Alvos de toque < 44 px — A11y/Responsividade · Médio · P
- Evidência (375 px): vitrine "×" do drawer 23×37, "Sugerir Correção"/"Enviar Meu Relato" 29 px de
  altura, pinos do mapa 34×34, zoom +/− 30×30; dock: 9 pílulas com 26 px; checkbox de consentimento
  13×13 (todas as páginas com `_novidades.html`); modelos: "Área do lojista" 20–23 px, botões de tema
  34–38 px, links do nav em tablet 26 px.
- Código: `produto/landing.html:903`; `_demo_dock.html:157-170`; `_novidades.html` (checkbox).
- Correção: `min-height:44px` em botões/pílulas, `padding` no "×", checkbox 20 px com label clicável.

### 9. Login/esqueci carregam o pacote do painel e mostram o menu interno ao visitante — UX/Perf · Médio · P
- Evidência: /auth/login com 8 requisições bloqueantes: Bootstrap, FA 6.0, DataTables CSS+JS, animate.css,
  jQuery — nenhuma tabela na página. A navbar exibe "Dashboard, Reservas, Avaliações, Agenda, Promoções,
  Site, Conteúdo" para quem não está logado; a marca leva a `/dashboard`. Sem `<h1>` (título é `<h4>`),
  sem `<main>`, `navbar-toggler` sem nome acessível. Visual Bootstrap genérico, diferente do /cadastro.
- Código: `app/templates/base.html:10-16`, `:38-60`, `:177-180`; `auth/login.html:10`, `auth/esqueci.html:9`.
- Correção: bloco `{% block nav %}` vazio para telas de auth (ou `{% if current_user.is_authenticated %}`),
  carregar DataTables/animate só nas telas que usam, `<h1>` + `<main>`, `aria-label="Abrir menu"`
  no toggler e link "← voltar pra feira" como no cadastro.

### 10. Vitrine não leva o dono de bar até a compra — UX · Médio · M
- Evidência: em 768 px a página tem 15,5 mil px; `#preco` começa a 78% da altura, "Quero o Plano Site"
  a 83%. Hero oferece "Iniciar Jornada no Mapa", "Contar uma Memória" e "Ver as 23 Barracas"; o banner
  "Dossiê Aberto à Comunidade" ocupa a 1ª dobra no mobile. Não há link para `/cadastro` nem `/auth/login`
  em lugar nenhum da home (0 ocorrências).
- Correção: CTA secundário fixo "Sou dono de bar →" no header (para `#preco` ou `/cadastro`), link
  "Entrar" discreto no rodapé, e mover o banner comunitário para depois do hero.

### 11. "Entrar no sistema" em destaque no menu do site do cliente — UX · Médio · P
- Evidência: bardavila.bar, nav desktop: 7º item com estilo de CTA (`.nav-cta`), competindo com
  "Reservar"; também no menu mobile (`.mm-cta`) e no rodapé. O freguês não tem conta.
- Código: `app/templates/site/landing.html:207-211`, `:608`, `:632`.
- Correção: manter só o link discreto do rodapé ("Área do lojista") e dar o estilo de CTA a "Reservar".

### 12. Recursos bloqueantes de terceiros no `<head>` — Desempenho · Médio · P
- Vitrine: Leaflet CSS + JS síncronos (`produto/landing.html:22-23`) para um mapa a ~40% da página;
  Font Awesome 6.4 completo (`:20`) para ~20 ícones; família Work Sans pedida e não usada (`:19`).
- Noturno e craft: `motion.js` (47 KB, jsDelivr) síncrono no head (`modelos/noturno.html:109`,
  `modelos/craft.html:132`); os demais modelos já o carregam no fim do `<body>`.
- Correção: Leaflet com `defer` + inicializar por `IntersectionObserver`; subset de ícones em SVG inline;
  remover Work Sans; `motion.js` com `defer` e estado inicial do hero por classe aplicada no `<head>`
  (já existe o gate `.js-anim`).

### 13. Imagens sem dimensões e sem lazy na vitrine — Desempenho · Baixo · P
- Evidência: 39/39 `<img>` sem `width/height`; 4 fotos do dossiê (64–156 KB, 800 px exibidas a 371 px)
  sem `loading="lazy"` — `produto/landing.html:995`, `:1061`, `:1085`, `:1109`. CLS medido ainda é 0
  (altura fixa via CSS `.chapter-photo`), então o ganho é de bytes (~250 KB), não de layout.
- Correção: `loading="lazy" decoding="async" width height` + versão 480 px WebP.

### 14. Modais e galeria sem semântica de diálogo / teclado — A11y · Médio · P
- Vitrine `#modal-colaboracao` sem `role="dialog"`/`aria-modal`/foco inicial; "×" sem `aria-label`
  (`produto/landing.html:1525-1527`). Dock: "✕" dos modais Voz/Maps sem nome (`_demo_dock.html:353`, `:391`).
- Bar da Vila: galeria `<figure onclick="lb(this)">` não é focável nem ativável por teclado; lightbox
  sem `role="dialog"` e sem botão de fechar real (`site/landing.html:855`, `:975-976`).
- Mapa: pinos `role="button"` com nome "📍" (Leaflet `divIcon` sem `title`/`alt`) —
  `produto/landing.html:1626-1636`. Sliders da calculadora de ROI sem label associado
  (`produto/landing.html:1365-1367`).
- Correção: `<button>` envolvendo cada foto; `<dialog>` nativo com `showModal()`; `aria-label="Fechar"`;
  `L.marker(..., {title: p.nome, alt: p.nome})`; `<label for="roi-mesas">`.

### 15. Indicadores de foco fracos em campos — A11y · Baixo · P
- Bar da Vila: `outline:none` + `box-shadow` âmbar com alpha .18 (`site/landing.html:476`).
- Noturno: `outline:none` e só muda a cor da borda inferior (`modelos/noturno.html:674`).
- Vitrine: `.form-control:focus{outline:none}` (`produto/landing.html:656`). Cadastro idem (`cadastro.html:108`).
- Correção: `:focus-visible{outline:3px solid currentColor; outline-offset:2px}` como já fazem
  brasa (`:734`) e tradicional (`:259`).

### 16. Menor — Baixo · P
- Bar da Vila: o botão de menu mobile é o logo-caneca (`#mugBtn`, `site/landing.html:612`); padrão pouco
  descobrível — acrescentar a palavra "Menu".
- Nenhuma página tem link "pular para o conteúdo".
- Vitrine: `html{scroll-behavior:smooth}` sem `prefers-reduced-motion` (`produto/landing.html:57`).
- 404 do cardápio do bar oferece só "Ir para a home"/"Criar meu site"; deveria voltar ao site do bar.
- Bar do Guiu: título "Bar de encontro em Vinhedo" numa vitrine de Barão Geraldo (conferir dado do lead).

## O que está bom
- Inputs com 16 px em todos os formulários (sem zoom no iOS), `label` associada, `autocomplete` correto,
  `role="status" aria-live` nas mensagens de reserva e de novidades, honeypot fora da árvore de acessibilidade.
- Zero rolagem horizontal em 375/768/1280 em todas as páginas; CLS ≈ 0 em todas.
- Prévias extremamente leves (72–77 KB, 2–4 requisições); vitrine cacheada na borda (TTFB ~80 ms).
- Autoral, craft e brasa implementam menu mobile correto (visibility, `aria-expanded`, foco, 44 px).
- `prefers-reduced-motion` respeitado nos modelos e no Bar da Vila; `lang="pt-BR"` e títulos únicos.

## Prioridade sugerida
1. Itens 4, 6 e 8 (a11y, todos P) — um PR só, padronizando menu/contraste/alvos nos templates.
2. Item 2 + 13 (imagens) — maior ganho de bytes para o cliente pagante.
3. Itens 1, 5, 10, 11 (conversão e UX da vitrine/prévia).
4. Item 3 (cache de borda do site do cliente) — exige mudar o fluxo de CSRF da reserva.
5. Itens 9, 12, 14, 15, 16.
