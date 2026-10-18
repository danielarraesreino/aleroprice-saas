# Reauditoria UI/UX, acessibilidade e responsividade — produção, 18/10/2026

Depois das correções publicadas em 18/10 (`10d9f34`, `eb6410c`). Base de comparação:
[`ux-a11y-perf.md`](ux-a11y-perf.md) (17/10). Método: navegador embutido em 375×812, 768×1024
e 1280×800; medições por script no DOM (rolagem horizontal, alvos < 44 px, contraste WCAG,
textos < 12 px, foco em menus fechados, landmarks, nomes acessíveis), menus abertos/fechados
por clique + Escape, leitura dos templates. Skills: design-critique e accessibility-review
(WCAG 2.1 AA). Só leitura: nada enviado, sem login.
Limitações: o contraste ignora texto sobre foto/gradiente (conferido a olho no hero do craft);
o Escape foi disparado por script (sem teclado físico); sem leitor de tela real; sem zoom 200%.

## Notas

| Área | Antes | Agora | Resumo |
|---|---|---|---|
| UI/UX | 6,5 | **7,5** | Menu da vitrine cabe inteiro, "Sou dono de bar →" no header, dock recolhido, login limpo. Faltam: "Entrar no sistema" nos menus de 4 modelos, cardápio sem preços, prévia "em Vinhedo". |
| Acessibilidade | 6,0 | **8,0** | 5 de 6 menus corretos (inert/visibility, foco entra e volta, Escape), contraste zerado nas medições, diálogos com `role="dialog"`, skip link em todas as páginas. Faltam: menu do tradicional, foco/estrutura do /cadastro, estado ativo do dock. |
| Responsividade | 7,0 | **8,5** | Zero rolagem horizontal nas 9 páginas × 3 larguras; dock nasce como chip de 60 px; nav desktop sem carrossel. Restam alvos de 33–41 px na vitrine e no login. |

## O que melhorou (verificado em produção)

- **Vitrine, menu desktop** (achado 1): `nav.nav-dossie` com 4 itens, 347/347 px, nada fora da tela em 1280.
- **Menus fechados fora do Tab** (achado 4): vitrine (`visibility:hidden`), Bar da Vila/clássico,
  noturno, craft, brasa e autoral com 0 links focáveis fechados; foco vai ao 1º link ao abrir e volta
  ao botão no Escape (vitrine, clássico, noturno, craft, brasa). Painel do noturno sem `aria-hidden` com foco.
- **Dock da prévia** (achado 5): nasce recolhido num chip "Prévia · Personalizar ▲" (204×48, `aria-expanded`),
  dock com 60 px no mobile; `--dock-h` por ResizeObserver; estado lembrado só na sessão.
  Nenhum modelo tem mais botão flutuante coberto.
- **Contraste** (achado 6): nenhuma falha nas 9 páginas (escuro e claro de noturno, craft e brasa).
  Pílula ativa agora #fff/#c2410c (5,2:1); "Trem Funilense" em #b45309.
- **Texto pequeno** (achado 7): nenhum texto < 12 px nos modelos e no Bar da Vila (craft era 9,6 px).
- **Alvos** (achado 8): pílulas do dock 44 px, checkbox 20 px dentro de label de 44 px, botões de menu 44 px.
- **Login** (achado 9): navbar só com "Feira de Barão" e "← voltar pra feira", `<h1>`, `<main>`,
  sem DataTables/animate (2 CSS + 4 JS), olho da senha com `aria-label` e `aria-pressed`.
- **Vitrine → compra** (achado 10): CTA "Sou dono de bar →" (para `#preco`) no header em todas as
  larguras; "Entrar" (`/auth/login`) presente.
- **Bar da Vila** (achados 11, 14, 16): "Entrar no sistema" saiu do nav (só "Área do lojista" no rodapé);
  "Reservar" é o CTA; galeria com `<button>` + lightbox `role="dialog"` com "Fechar" e retorno de foco;
  botão do menu diz "Menu"; fotos `<img srcset>` WebP 400/800 com `lazy`.
- **Modais/mapa da vitrine** (achado 14): `role="dialog" aria-modal aria-labelledby`, "×" com
  `aria-label="Fechar"`, pinos com `title`, sliders da calculadora com label.
- **Movimento** (achado 16): `scroll-behavior:smooth` só em `prefers-reduced-motion: no-preference`
  (`produto/landing.html:74-75`).

## Achados restantes (por impacto)

### 1. Tradicional: menu fechado continua no Tab e não fecha no Escape — A11y · Alto · P
- Evidência: /bar/bar-do-guiu?modelo=tradicional, 375×812. `#folha` fechado tem `max-height:0;
  overflow:hidden` mas `visibility:visible` → 6 links invisíveis focáveis (WCAG 2.4.3/2.4.7). Ao abrir
  o foco não entra; o Escape só fecha a lupa.
- Código: `app/templates/site/modelos/tradicional.html:291-297` (CSS), `:1382-1386` (`abrirMenu`), `:1394-1398`.
- Correção: `visibility:hidden` + `transition: max-height .45s, visibility 0s .45s` no fechado (como
  `craft.html`), foco no 1º link ao abrir, Escape fecha e devolve foco ao `#btn-menu`.

### 2. "Entrar no sistema" no menu do freguês em 4 modelos — UX · Médio · P
- Evidência: nav/menu de brasa (`.entrar`), craft (`.nav-entrar`), tradicional (nav e folha) e noturno
  (painel). O achado 11 foi corrigido só no clássico (Bar da Vila). Freguês não tem conta; compete com "Reservar".
- Código: `modelos/brasa.html:812`, `modelos/craft.html:879`, `modelos/tradicional.html:806` e `:827`,
  `modelos/noturno.html:881`.
- Correção: remover dos menus; deixar só o "Área do lojista" do rodapé, que todos já têm.

### 3. /cadastro: foco fraco, sem `<main>`, rótulos de 11,8 px e erro sem anúncio — A11y · Médio · P
- Evidência (375 e 1280): `input:focus{outline:none}` + sombra com alpha .13 (pouco visível);
  0 landmarks `main`; labels 11,84 px em caixa alta; `.flash` sem `role="alert"`; "← voltar pra feira"
  121×21 e "Entrar" 45×16.
- Código: `app/templates/site/cadastro.html:99-100`, `:108`, `:135-139`, `:157-160`, `:197`.
- Correção: `input:focus-visible{outline:3px solid var(--tomate);outline-offset:2px}`; `<main>` no
  cartão; labels ≥ 0,8125rem (13 px); `role="alert"` nas mensagens de erro; links com
  `display:inline-block;padding:12px 4px`.

### 4. Cardápio do Bar da Vila sem preços — UX · Médio · P (depende do dono)
- Evidência: bardavila.bar/bar/bar-da-vila/cardapio mostra 4 pratos só com descrição. Num QR de mesa
  a primeira pergunta é o preço. Já está nas pendências (MEMORIA_VIVA, item 5).
- Correção: cadastrar preços no painel; enquanto isso, frase "Preços no balcão / pergunte ao garçom".

### 5. Alvos de toque ainda < 44 px na vitrine e no login — A11y/Responsividade · Médio · P
- Vitrine 375: "Iniciar Jornada no Mapa" 213×39, "Contar uma Memória" 249×33, "Ver as 23 Barracas" 199×41,
  "Adicionar Foto…" 287×35, planos 39–41 px, campos do novidades 40 px, pinos do mapa 34×34.
  Código: `produto/landing.html:211` (`.btn`), `:1063-1066`, `:1390`, `:1604`, `:1804` (`iconSize`).
- Login: campos e "Entrar" 38 px, checkbox "lembrar" 16×16, "Esqueci minha senha"/"Criar grátis" 18 px
  de altura (`auth/login.html:13-27`).
- Correção: `.btn{min-height:44px}`; `iconSize:[44,44]`; no login `form-control-lg` ou `min-height:44px`
  e checkbox 20 px; inputs do `_novidades.html` com `min-height:44px`.

### 6. Dock: modelo/tema ativo só pela cor — A11y · Baixo · P
- Evidência: as 9 pílulas não têm `aria-pressed`/`aria-current`; o leitor de tela não sabe qual está
  ativo (WCAG 1.3.1/4.1.2). Escape não recolhe o dock aberto.
- Código: `site/_demo_dock.html:382-399` (pílulas), `:569-573` (Escape).
- Correção: `aria-pressed="{{ 'true' if modelo_atual == 'x' else 'false' }}"` (idem Claro/Escuro);
  no handler de Escape chamar `alternarDock(false)` quando aberto.

### 7. Autoral: foco não entra no índice aberto — A11y · Baixo · P
- Evidência: ?modelo=autoral 375: após abrir "ÍNDICE" (89×44) o foco fica no botão; Escape fecha e
  devolve certo. Código: `modelos/autoral.html:1352-1356`.
- Correção: em `abrirIndice()` focar o 1º link de `#indice`.

### 8. Tradicional: lupa da galeria sem semântica de diálogo — A11y · Baixo · P
- Evidência: `figure role="button"` com teclado ok, mas `#lupa` é `div` com `onclick`, "✕" `aria-hidden`
  sem botão real, foco não vai nem volta. Código: `modelos/tradicional.html:1335-1339`, `:1388-1393`.
- Correção: repetir o padrão do clássico (`site/landing.html:1129-1136`): `role="dialog"`, `<button aria-label="Fechar">`, foco ida/volta.

### 9. Menores — Baixo · P
- Vitrine: "Sou dono de bar →" a 11,84 px no mobile (`produto/landing.html:967`) — subir para 0,8125rem.
- Autoral 1280: links do nav com 23 px de altura; craft: logo "BAR DO GUIU" 122×20 (`craft.html:308`) — padding vertical.
- Login ainda carrega jQuery + Bootstrap JS completos para um formulário (`base.html`); custo baixo, sem urgência.
- Prévia do Bar do Guiu continua "Bar de encontro em Vinhedo" (dado do lead, `modelo_siteconfig.py:38`).
- Cardápio: "Ver o site do bar" aponta para `/bar/bar-da-vila`, que faz 301 para a raiz — usar `/` no domínio próprio.

## O que está bom e deve ser mantido
- Skip link "Pular para o conteúdo" em todas as páginas; 1 `<h1>` e `<main>` (exceto /cadastro).
- Inputs 16 px, `autocomplete` certo, honeypot fora do Tab (`tabindex=-1`, `aria-hidden`).
- Bar da Vila é hoje a melhor página da plataforma: 0 falhas de contraste/foco, menu e galeria exemplares.

## Prioridade sugerida (um PR, tudo P)
1. Achados 1, 2 e 3 (menu do tradicional, "Entrar no sistema" nos modelos, /cadastro).
2. Achado 5 (`min-height:44px` em `.btn`, pinos e login).
3. Achados 6, 7, 8 e 9. O 4 depende do dono do Bar da Vila.
