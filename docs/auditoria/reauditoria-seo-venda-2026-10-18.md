# Reauditoria — SEO, visibilidade em IA e posicionamento de venda

Data: 18/10/2026, depois do deploy das correções (`10d9f34`, `eb6410c`). Somente leitura.
Método: `curl` em produção com UA Googlebot, extração do JSON-LD e do texto visível, leitura do código. Skills usadas: `marketing:seo-audit`, `marketing:competitive-brief`, `marketing:brand-review`, `searchfit-seo` (technical-seo, schema-markup, ai-visibility).
Escopo: `feiradebarao.com.br` (/, sitemap, robots, llms, `/bar/bar-do-guiu`) e `bardavila.bar` (/, `/bar/bar-da-vila/cardapio`, sitemap, llms). Premissa: o Bar da Vila não faz parte da feira, então é correto ele não aparecer no portal.

## Notas

| Frente | Antes (17/10) | Agora | Leitura |
|---|---|---|---|
| SEO técnico + IA | 5,5 | **7,0** | A base está limpa. Falta conteúdo indexável e falta o sinal de horário/preço. |
| Posicionamento de venda | — (não avaliado) | **4,5** | O preço está claro, mas a oferta aparece no fim de um dossiê histórico, sem prova e com promessa de recurso desligado. |

## O que melhorou (conferido em produção)

- **Schema do Bar da Vila:** `PostalAddress` agora estruturado (`addressLocality` Campinas, `addressRegion` SP, `postalCode` 13100-486, `addressCountry` BR). As coordenadas falsas de Barão sumiram e `areaServed` passou a "Campinas, SP" (achados 1 e 2).
- **Sitemaps:** o do portal não tem mais `demo-avaliacao` nem URL de outro host. `bardavila.bar/sitemap.xml` lista a home e o cardápio, com `lastmod` (achado 3).
- **`bardavila.bar/llms.txt`** responde 200 com conteúdo do próprio bar e a localidade "Vila Lemos, Campinas–SP", sem o 302 para o portal (achado 7).
- **Prévia do Guiu:** zero ocorrências de "None" e o `h1` vem antes dos `h3` (achados 4 e 16).
- **Home do portal:** title "Bares e botecos de Barão Geraldo (Campinas) · Feira de Barão" e meta description focada. O schema virou `WebSite` + `Organization` + `ItemList` (23 `BarOrPub`). Ganhou `og:locale` e `twitter:card` (achados 12 e 13).
- **Landing do Bar da Vila** linka `/bar/bar-da-vila/cardapio` (2x) (achado 10). O título leva o bairro ("· Vila Lemos").
- **Infra:** `www.feiradebarao.com.br` dá 308 para o apex. `bardavila.bar` e as páginas de bar saem com `cache-control: public`, sem `set-cookie` e com `x-vercel-cache` HIT/STALE (achado 17). TTFB entre 0,15 e 0,21 s (`gru1`).
- **Mural:** a contagem usa `{{ total_bares }}` (`produto/landing.html:1229, 1384`).

## Achados restantes — SEO e IA (por impacto)

**S1. ALTO — Nenhum dos dois domínios está verificado no Search Console nem no Bing.** Esforço: P (é tarefa do dono)
- Evidência: pendência 3 da `docs/MEMORIA_VIVA.md:79`. Sem isso, as correções acima não chegam ao índice com rapidez, e o Bing é a fonte do ChatGPT Search.
- Correção: verificar os dois domínios por DNS, enviar os dois sitemaps e pedir indexação da home e do cardápio.

**S2. ALTO — O Bar da Vila continua sem horário e sem preço estruturados.** Esforço: P (dados) + P (código)
- Evidência: o JSON-LD de `https://bardavila.bar/` não tem `openingHours*` nem `offers`. O `llms.txt` diz "Horário de Funcionamento: Aberto até as 21:00 · Quarta é o dia de pico".
- Evidência: `https://bardavila.bar/bar/bar-da-vila/cardapio` tem cerca de 121 palavras e 4 itens, dois deles genéricos ("Porções pra dividir", "Prato do dia").
- Impacto: o bar fica de fora das respostas a "aberto agora" e "quanto custa", no Maps e nas IAs.
- Correção: cadastrar o horário no formato "Qua–Dom 11h–21h" e o cardápio real com preço (pendência 5 da memória).

**S3. MÉDIO — `llms.txt` do portal está vazio e com marca trocada.** Esforço: P
- Evidência: `https://feiradebarao.com.br/llms.txt` (684 B) tem o título "Feira de Barão & AleroPrice" e a seção "Bares e Restaurantes em Destaque" vazia. `/llms-full.txt` é idêntico ao `/llms.txt`.
- Causa: `app/routes/publico/views.py:536-545`. O laço usa `_tenants_do_sitemap(None)`, que agora volta vazio.
- Impacto: um LLM que ler o arquivo não fica sabendo o que é a feira nem que existe um pacote para donos de bar.
- Correção:
  - tirar "AleroPrice" do título;
  - trocar a seção vazia por "Para donos de bar" (o que o pacote inclui, os preços, o link `#preco`) e por um resumo do guia do bairro;
  - no `-full`, acrescentar a FAQ e os planos.

**S4. MÉDIO — `/bar/demo-avaliacao` continua indexável.** Esforço: P
- Evidência: responde 200, sem meta robots, com canonical próprio e title "Demo Avaliação — Bar e restaurante". Ela saiu do sitemap, mas o Google ainda pode indexar a página.
- Correção: marcar a conta como `eh_demo`, o que liga o `noindex` dos modelos, ou desativá-la. É a mesma conta da pendência 1 (contas de teste).

**S5. MÉDIO — O `ItemList` da home aponta para 23 URLs `noindex,nofollow`.** Esforço: P
- Evidência: o JSON-LD da home lista `BarOrPub` com `url` `feiradebarao.com.br/bar/<slug>`, e todas essas prévias são `noindex`. O portal tem uma única URL indexável (o sitemap tem 1 `<loc>`).
- Correção a curto prazo: tirar o `url` dos itens, ou apontar para o perfil do Google de cada bar (via `sameAs`).
- Correção a médio prazo: criar as páginas indexáveis previstas no plano, que são a LP B2B, o guia da Praça do Coco e o hub "Bares em Barão Geraldo".

**S6. BAIXO — `https://www.bardavila.bar/` responde 200 em vez de 308.** Esforço: P (painel da Vercel). O canonical reduz o dano.

**S7. BAIXO — A prévia `bar-do-guiu/cardapio` ainda dá 404.** Esforço: P
- Evidência: rota sem pratos. Não afeta o SEO (é `noindex`), mas atrapalha a demonstração de venda.
- Correção: mostrar um cardápio de exemplo marcado como tal.

**S8. BAIXO — `AggregateRating` 4,9/39 e 6 `Review` autodeclarados no Bar da Vila.** Isso não gera estrelas na SERP. O número só deve ficar se estiver sincronizado com o Google.

## Achados — posicionamento de venda (a home convence um dono de bar de Campinas?)

O que funciona:
- Há 3 planos com preço explícito: R$ 147,90/mês, R$ 247,90/mês, e R$ 1.400 à vista + R$ 390/ano. A taxa de montagem de R$ 349 está declarada.
- Os textos "sem fidelidade" e "sem comissão" estão na página.
- O CTA "Sou dono de bar →" fica fixo no topo (`landing.html:991`).
- Há uma calculadora de ROI e um contato humano ("Eu sou o Daniel, moro em Barão…"), com WhatsApp.

**V1. CRÍTICO — A home vende recursos que estão desligados em produção.** Esforço: P
- Evidência: o Plano Pro (R$ 247,90, "MAIS ESCOLHIDO") e a compra à vista prometem:
  - "Leitor OCR de Notas por Foto (NVIDIA)";
  - "Cálculo de CMV";
  - "Alerta de aumento de insumos" (`produto/landing.html:1585-1600, 1618`);
  - os mesmos itens aparecem na seção de tecnologia (`:1463-1478`).
- Mas `GESTAO_ATIVA` está desligada por padrão (`app/config.py:18-22`), por decisão registrada em `docs/AVALIACAO_GESTAO_2026-10.md`.
- Impacto: risco de reclamação ou estorno com base no CDC (oferta vincula). É o pior sinal de confiança da página.
- Correção: tirar esses itens, ou marcá-los como "em breve", até a gestão voltar. Conferir também se o "Concierge de Voz" funciona ponta a ponta (rota em `views.py:1086`).

**V2. ALTO — Afirmações sem lastro.** Esforço: P
1. "Cada bar agora tem presença no Google Maps, cardápio digital próprio e reservas sem intermediários" (`:1229`). Os 23 bares são prévias não contratadas. Um LLM pode repetir isso como fato, e um dono de bar listado pode contestar. Reescrever como "Preparamos uma prévia digital para cada casa".
2. "★ MAIS ESCOLHIDO" (`:1585`) com um único cliente pagante. Trocar por "Recomendado".
3. "R$ 900 de lucro limpo" (`:1542`). R$ 1.169 é faturamento, não lucro. Além disso, o texto diz "1 mesa extra **na semana**", mas a conta usa 1 mesa por noite cheia × 2 noites. Corrigir para "1 mesa a mais em cada noite cheia" e "sobra R$ ~900 de faturamento extra".
4. "lucro auditado" e "sistema operacional próprio" (`:1448`). Remover.

**V3. ALTO — A oferta está enterrada e o público está misturado.** Esforço: M
- Evidência: o `h1` é "A Feira que Não Desmonta. A Memória Viva de Barão Geraldo". Os planos só aparecem depois de cerca de 2.000 palavras de história, mural e 23 barracas.
- Impacto: o dono de bar que chega por anúncio ou WhatsApp não vê em 5 s o que ganha nem quanto custa.
- Correção: criar a LP B2B própria e indexável (`/para-bares`), com:
  - title "Site, cardápio, reserva e Google para bar em Campinas";
  - um `h1` de benefício e o preço acima da dobra;
  - o caso real, a FAQ (com `FAQPage`) e o schema `Service` com `Offer`.
- A home continua como portal do bairro, com um bloco curto que leva à LP. Isso já é o passo 2 da memória.

**V4. ALTO — Não há nenhuma prova social de cliente.** Esforço: P
- Evidência: não há caso, print, depoimento de dono nem número de resultado. O único cliente (Bar da Vila) não é citado em lugar nenhum.
- Correção: na LP B2B (não na vitrine da feira), um caso "Bar da Vila, Vila Lemos" com print do site, do cardápio e do perfil do Google, mais uma frase do dono (com autorização). Isso não contraria a regra de separar o Bar da Vila do portal.

**V5. MÉDIO — Não há diferencial explícito frente aos concorrentes.** Esforço: P
- Referência de preço: o Goomer tem plano básico de cardápio digital a cerca de R$ 99,90/mês no mensal, ou R$ 59,94 no anual (guia da Saipos, out/2026).
- Diferença de propósito:
  - o Anota AI é atendente de pedidos/delivery no WhatsApp;
  - o Wix é um construtor genérico, em que o dono faz tudo sozinho.
- O que só a Feira tem: entrega feita por um morador do bairro, domínio próprio, Google Meu Negócio configurado, reserva sem comissão e página que já nasce pronta (a prévia).
- Correção: uma tabela de 4 linhas "Feira × cardápio digital × construtor de site", sem citar marca. A justificativa dos R$ 147,90 frente aos R$ 99,90 do Goomer está no serviço feito por alguém, não no software.

**V6. MÉDIO — O CTA principal não é de compra direta.** Esforço: P
- Evidência: "Quero o Plano Site" e "Ativar Plano Pro" levam ao contato. Isso é aceitável para venda consultiva.
- Correção: deixar o próximo passo explícito ("Te mando a prévia do seu bar no WhatsApp em 24 h") e oferecer um link pré-preenchido com o nome do bar.

**V7. BAIXO — Tom e jargão.** "Arsenal IA", "NVIDIA Riva", "DeepSeek" e "visão computacional" falam com quem é técnico, não com o dono de boteco. Trocar por benefícios: "manda áudio e a mesa fica reservada", "tira foto da nota e o custo atualiza".

## Ordem sugerida

1. **Hoje:** V1 e V2. São só remoções e ajustes de texto em `produto/landing.html` e protegem contra problema jurídico.
2. **Dono do projeto:** S1 (Search Console e Bing), S2 (horário e cardápio com preço), S6 (www) e S4 (desativar a demo).
3. **Esta semana:** S3 (reescrever o `llms.txt` do portal) e S5 (ajustar o `ItemList`).
4. **Próxima entrega:** a LP B2B com o caso do Bar da Vila, a FAQ e a tabela de diferenciais (V3, V4, V5, V6). É a única página nova que soma SEO e venda ao mesmo tempo.
