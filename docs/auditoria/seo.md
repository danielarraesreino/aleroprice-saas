# Auditoria de SEO e visibilidade em IA — Feira de Barão / Bar da Vila / Bar do Guiu

Data: 2026-10-17 · Método: `curl` em produção (UA Googlebot e bots de IA) + leitura do código. Somente leitura.
Páginas: `feiradebarao.com.br/`, `bardavila.bar/`, `feiradebarao.com.br/bar/bar-da-vila`, `/bar/bar-do-guiu`, `/bar/bar-do-guiu/cardapio`, robots/sitemap/llms dos dois domínios, as 23 `/bar/<slug>` linkadas na home.

## Nota: 5,5 / 10

A base técnica é boa: HTTPS com 308, canonical certo entre os dois endereços do Bar da Vila, prévias com `noindex`, robots aberto a bots de IA, JSON-LD em grafo, `llms.txt`. O que segura a nota são **dados locais errados ou incompletos no schema do cliente pagante** (coordenadas, endereço, horário), **conteúdo raso para buscas por prato**, **lixo no sitemap/llms** e **links quebrados na prévia comercial**.

## Achados por impacto

### CRÍTICO

**1. Coordenadas e área de atendimento fixas no código, iguais para todo bar.** Esforço: P
- Evidência: o JSON-LD de `https://bardavila.bar/` traz `"geo": {"latitude": -22.8277, "longitude": -47.0818}` e `"areaServed": "Barão Geraldo, Campinas - SP"`, mas o endereço é "R. Madalena Barbosa Ferreira, 178 — Vila Lemos, Campinas–SP · 13100-486" (CEP 131xx, fora de Barão Geraldo, que usa 13083–13085).
- Código: `app/utils/seo.py:724-730`. Valores constantes ("Coordenadas geográficas padrão de Barão Geraldo") aplicados a qualquer bar com endereço.
- Impacto: o NAP diverge do Google Business Profile. Google e LLMs recebem uma localização falsa, o que atrapalha o pack local do Maps e as respostas do tipo "bar perto de X".
- Correção: só emitir `geo` quando houver lat/long reais por tenant (novo campo em `SiteConfig`, ou extraídos do link do GBP). Remover `areaServed` fixo, ou derivar do bairro real.

**2. Endereço do Bar da Vila não é estruturado.** Esforço: P
- Evidência: `"address": {"streetAddress": "R. Madalena ... 178 — Vila Lemos, Campinas–SP · 13100-486"}`, sem `addressLocality`, `addressRegion`, `postalCode` nem `addressCountry`.
- Causa: em `app/utils/seo.py:382` o `strip(' ,;-–—')` não remove o "·" que sobra depois de tirar o CEP. Com isso, `_UF_NO_FIM` (`seo.py:352`) não casa e a função cai em `inteiro` (`seo.py:386`).
- Correção: incluir `·` no strip e aceitar "Cidade–UF" sem vírgula antes. Ou, melhor, guardar o endereço em campos separados em `SiteConfig`. Validar no Rich Results Test.

**3. Sitemap do produto lista uma página de teste e uma URL de outro domínio, e omite o cardápio.** Esforço: P
- Evidência: `https://feiradebarao.com.br/sitemap.xml` tem `https://bardavila.bar/` (host diferente: o Search Console rejeita, a menos que os dois domínios estejam na mesma conta verificada) e `https://feiradebarao.com.br/bar/demo-avaliacao`. Essa página responde 200, é indexável (sem `noindex`) e tem title "Demo Avaliação — Bar e restaurante".
- `https://bardavila.bar/sitemap.xml` tem só a home. Falta `https://bardavila.bar/bar/bar-da-vila/cardapio` (200, canonical próprio).
- Código: `app/routes/publico/views.py:388-404` (`Restaurante.clientes()` está tratando `demo-avaliacao` como cliente) e `views.py:429-431` (só a home de cada tenant).
- Correção: desativar ou marcar `demo-avaliacao` como demo no banco, e tirar do sitemap do produto as URLs de outros hosts. No sitemap do domínio do bar, acrescentar a página de cardápio quando houver pratos.

**4. Prévia do Bar do Guiu com 13 ocorrências de "None" e links quebrados.** Esforço: P
- Evidência (`https://feiradebarao.com.br/bar/bar-do-guiu`): `href="https://wa.me/None?..."` (3x), `maps/search/?api=1&query=None` (2x), `href="None"` nos ícones de Instagram e Facebook, e na tela "Endereço None / Horário None / Telefone None".
- Código: `app/templates/site/landing.html:661-662, 878, 940-942, 948-949, 962, 965, 979`. Sem `{% if %}`. Os modelos novos já fazem certo (`site/modelos/brasa.html:1193-1194`).
- Impacto: a página é `noindex`, então o dano no Google é baixo. O dano está na venda: o dono abre a prévia e vê "None" e botões que não funcionam. Pelo mesmo motivo, `https://feiradebarao.com.br/bar/bar-do-guiu/cardapio` dá **404** (`views.py:609-610`, sem pratos).
- Correção: proteger cada campo com `{% if site.x %}`. Na prévia sem pratos, mostrar um cardápio de exemplo marcado como tal, em vez de 404.

### ALTO

**5. O conteúdo do Bar da Vila é raso para buscas por prato ("bolinho de feijoada Barão Geraldo").** Esforço: M
- Evidência: a landing tem cerca de 680 palavras. O cardápio (`/bar/bar-da-vila/cardapio`) tem cerca de 120 palavras e 4 itens, dois deles genéricos ("Porções pra dividir", "Prato do dia"). Nenhum item tem preço, então não há `offers` (`seo.py:536-539`). As fotos dos pratos no cardápio têm `alt=""` (4 de 4). O title é "Bar da Vila — Buteco de família em Campinas" e não cita bairro nem prato.
- Correção: cadastrar o cardápio real com preço (cada `MenuItem` com `offers`) e um parágrafo por prato-assinatura com nome + bairro. Usar alt descritivo com o nome do prato. Title sugerido: "Bar da Vila — Buteco em Vila Lemos, Campinas | Croquete e costelinha". Uma página por prato-assinatura (`/cardapio#croquete`, ou página própria) é o que permite ranquear por prato.

**6. Horário de funcionamento fora do schema.** Esforço: P
- Evidência: a página mostra "Aberto até as 21:00 · Quarta é o dia de pico". O JSON-LD não traz `openingHours` nem `openingHoursSpecification`, porque `horario_schema`/`abertura_schema` (`seo.py:313`, `seo.py:270`) não interpretam esse texto.
- Impacto: Maps e LLMs respondem muito "está aberto agora?". Sem horário estruturado, o bar fica de fora dessas respostas.
- Correção: preencher o horário no formato "Qua–Dom 11h–21h" no `/config-site`, ou criar um campo estruturado por dia.

**7. `llms.txt` do domínio do bar redireciona para o do portal.** Esforço: P
- Evidência: `https://bardavila.bar/llms.txt` responde **302** para `https://feiradebarao.com.br/llms.txt`. Mesmo assim, a página do bar declara `<link rel="alternate" type="text/markdown" href="/llms.txt">`.
- Causa: `public.llms_txt` não está em `ENDPOINTS_DO_TENANT` (`app/__init__.py:245-255`). Por isso o ramo do tenant em `views.py:461-499`, que lista os pratos com preço, nunca roda em produção.
- Correção: adicionar `'public.llms_txt'` ao conjunto. Corrigir também o cabeçalho fixo "— Barão Geraldo" (`views.py:474`), que fica errado para bar fora de Barão.

**8. O `llms.txt` do portal está desatualizado ou errado.** Esforço: P
- Evidência: anuncia "Demo Avaliação" como bar em destaque e aponta o cardápio do Bar da Vila para `https://bardavila.bar/#cardapio` em vez de `/bar/bar-da-vila/cardapio`. Os 23 bares da vitrine da home não aparecem. `/llms-full.txt` é idêntico ao `/llms.txt` (1165 bytes).
- Código: `views.py:502-524`.
- Correção: excluir demos, usar a URL real do cardápio, e no `-full` incluir pratos, horários e endereços.

**9. A home (vitrine) não linka o cliente pagante.** Esforço: P
- Evidência: `https://feiradebarao.com.br/` tem 24 links internos `/bar/<slug>`, todos para prévias `noindex,nofollow`. Não há nenhum link para `bardavila.bar` e nenhuma menção a "Bar da Vila". A lista vem só dos leads YAML (`views.py:219-287`).
- Impacto: a página com mais autoridade do projeto passa link apenas para páginas que o Google não indexa. O cliente que paga não aparece.
- Correção: incluir os clientes ativos na vitrine (como destaque) com link para a URL canônica de cada um.

**10. A landing do Bar da Vila não linka a própria página de cardápio.** Esforço: P
- Evidência: só há `href="#cardapio"`. A URL `/bar/bar-da-vila/cardapio` aparece apenas no `Menu.url` do JSON-LD.
- Código: `app/templates/site/landing.html:599, 625`.
- Correção: link "Ver cardápio completo" para `url_cardapio`.

### MÉDIO

**11. www responde 200 em vez de redirecionar.** Esforço: P
- Evidência: `https://www.bardavila.bar/` e `https://www.feiradebarao.com.br/` dão 200. O canonical salva, mas em www o `og:image` sai como `https://www.bardavila.bar/...`.
- Correção: no painel da Vercel, configurar www para redirecionar com 308 ao apex, nos dois domínios.

**12. Schema da home inadequado.** Esforço: P
- Evidência: `ReportageNewsArticle` sem `image`, `author`, `datePublished` (campos exigidos para rich result de Article). Não há `WebSite`/`Organization` com `sameAs` nem `ItemList` dos bares. Também não há tags `twitter:*` nem `og:locale`.
- Código: `app/templates/produto/landing.html:12, 25-26`.
- Correção: trocar por `WebSite` + `Organization` + `ItemList` de `BarOrPub` (nome, URL, nota). É o formato que LLMs citam para "bares em Barão Geraldo".

**13. Title da home não mira a busca de interesse.** Esforço: P
- Evidência: "Feira de Barão · O Dossiê Cultural & Memória Viva de Barão Geraldo". As palavras "bares" e "onde comer" não aparecem.
- Correção: "Bares e botecos de Barão Geraldo (Campinas) · Feira de Barão".

**14. Depoimentos do "Mural da Memória" escritos direto no template.** Esforço: P
- Evidência: "Dona Helena Santos", "Prof. Marcos Ribeiro" e "Seu Antonio Moretti" estão no código (`produto/landing.html:1203` e seguintes). A contagem "As 23 Barracas" também é fixa (`:1268`), apesar de existir `total_bares`.
- Impacto: se forem fictícios, são um risco de confiança (E-E-A-T) e podem acabar citados por IA como fato.
- Correção: confirmar a origem ou remover. Usar `{{ total_bares }}` no lugar do 23.

**15. AggregateRating autodeclarado.** Esforço: P
- Evidência: `ratingValue 4.9 / reviewCount 39` e `Review`s colados no próprio site do bar.
- Impacto: o Google não exibe estrelas para avaliações "self-serving" de LocalBusiness. Não há penalidade, mas não gera rich result.
- Correção: manter só se o número estiver sincronizado com o Google. Não contar com as estrelas na SERP.

### BAIXO

**16. Hierarquia de headings e imagens.**
- Evidência: na prévia do Guiu, 4 `h3`/`h4` do `_demo_dock.html:350` aparecem antes do `h1`. Na home há saltos de `h2` para `h4`.
- Evidência: o hero `foto-18.jpg` tem 257 KB, recebe preload e as `<img>` da galeria vão sem `width`/`height` (risco de CLS). Os alts da galeria são genéricos ("foto da casa 1").
- Esforço: P.

**17. Cache do Bar da Vila.**
- Evidência: `bardavila.bar/` sai com `set-cookie: session`, `Vary: Cookie` e `max-age=0`, por causa do token CSRF do formulário de reserva. Cada visita (bots incluídos) roda a função. A home do produto já resolve isso (`views.py:209-215`).
- Correção: carregar o token via fetch e cachear o HTML na borda.
- Esforço: M.

## O que está funcionando
- `http` → `https` com 308. HSTS ativo.
- `feiradebarao.com.br/bar/bar-da-vila` e `/bar/BAR-DA-VILA` têm canonical `https://bardavila.bar/`. `og:url` coerente. Sem conteúdo duplicado indexável.
- As 23 prévias e o Guiu têm `noindex,nofollow,noarchive` e ficam fora do sitemap. `/cadastro` é `noindex` e está bloqueado no robots.
- O robots não bloqueia `/bar/` e libera GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot e Google-Extended (todos receberam 200).
- O JSON-LD é válido e organizado em grafo `@id` (BarOrPub, Menu, MenuItem, Review, BreadcrumbList, WebSite com `dateModified`), com `sameAs` (Instagram, Facebook) e `hasMap`.
- Há `lang="pt-BR"`, viewport, um `h1` por página, alt presente em todas as `<img>` da landing, OG e Twitter completos no Bar da Vila e uma página 404 real para slug inexistente.

## Próximos passos (ordem sugerida)
1. Corrigir geo, areaServed, endereço e horário no schema (achados 1, 2 e 6). Validar no Rich Results Test e conferir se o NAP bate com o Google Business Profile do Bar da Vila.
2. Limpar o sitemap e o llms (`demo-avaliacao`, URL de outro host, incluir o cardápio). Liberar `llms_txt` no domínio do tenant (achados 3, 7 e 8).
3. Proteger os campos vazios no `site/landing.html`, o que também conserta a prévia do Guiu (achado 4).
4. Cadastrar o cardápio real do Bar da Vila com preços e textos por prato, e linkar a página de cardápio (achados 5 e 10).
5. Pôr os clientes na vitrine da home e trocar o schema e o title da home (achados 9, 12 e 13).
