# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Dono do bar ou expositor (decide):** recebe uma prévia já montada com as fotos e os dados reais da casa e decide se ativa o site. A prévia é peça de venda: precisa parecer pronta, não um molde.
- **Cliente da casa (usa):** morador de Barão Geraldo, estudante da Unicamp, visitante da Feira. Abre no celular para ver o que tem, quando abre, onde fica e como pedir ou reservar (WhatsApp, Maps, telefone).
- Os dois pesam: sem o sim do dono o site não existe; sem servir o cliente o dono não renova.

## Product Purpose

Plataforma multi-tenant (Flask/Jinja) que dá a cada bar e a cada expositor da Feira de Barão um site próprio: landing, cardápio digital, álbum, reservas, eventos e promoções, com admin para o dono. Sucesso = dono ativa e mantém o site; cliente acha o horário, o cardápio e o contato em segundos.

A gestão de custos (NF-e, estoque, pratos, previsão) existe no código mas está desligada em produção (`GESTAO_ATIVA=0`).

## Positioning

Rede local de Barão Geraldo, ligada à Feira da Praça do Coco: o site chega pronto com as fotos e os dados reais da casa, sem comissão por pedido (o pedido vai para o WhatsApp da casa), ligado ao Google Maps / Perfil da Empresa e à vitrine da Feira. Um construtor genérico (Wix, Linktree) ou um marketplace (iFood) não tem nem o conteúdo local nem a vitrine da Feira.

## Operating Context

- Prévia por lead em `app/data/leads/<slug>.yml`, aplicada por `app/utils/demos.py`; o tenant escolhe um modelo (`site.modelo`) e o template lê tudo de `site.*`.
- Prévia (`eh_demo`) sempre com faixa "Prévia para {Nome}" e `noindex`; vira site real com o OK e o pagamento do dono.
- Feira: Praça do Coco, Barão Geraldo, Campinas; sábado 10–16h, domingo 10–15h.
- Deploy na Vercel (`aleroprice-bardavila`, gru1) a partir de `main`, só com OK do dono do projeto.

## Capabilities and Constraints

- Modelos de bar em `app/templates/site/modelos/` (craft, tradicional, autoral, noturno, brasa) e de expositor em `modelos/artesao/`; base em `_base.html` e macros em `_produtos.html`.
- Nada específico de um tenant em template ou CSS: um modelo serve muitos tenants (94 expositores previstos).
- Campos de site limitados às colunas de `SiteConfig`; campo novo exige migração e passo manual de schema em produção.
- Vocabulário: expositor (quem vende na Feira), barraca (ponto físico), bar (casa de bebida).
- Texto em pt-BR; formatação brasileira pelos filtros Jinja.
- Regras de design obrigatórias: `docs/DESIGN.md` e a skill `design-feira` (precedência: palavra do dono > bardavila.bar > docs/DESIGN.md > design-feira > skills genéricas).

## Brand Commitments

- **A casa na frente:** nome, logo, fotos e voz do bar ou expositor mandam; a Feira de Barão aparece só no rodapé e na faixa de prévia.
- Referência de qualidade: bardavila.bar (`app/templates/site/landing.html`). Hotsite menos trabalhado que os modelos de bar não está pronto.

## Evidence on Hand

- Fotos reais por tenant em `app/static/img/demo/<slug>/`, com origem em `creditos.json` (ou `AUTORIZADO.txt` para expositor). Nada de foto ampliada de miniatura.
- Nota e número de avaliações do Google por lead, quando coletados.
- **Não inventar:** preço, depoimento, prêmio, número de clientes, nome de prato não confirmado. Nome de prato tirado de foto fica marcado "CONFIRMAR com o dono".

## Product Principles

1. Só fato confirmado pela casa; o que falta fica de fora ou marcado, nunca inventado.
2. Celular primeiro: o cliente decide em pé, na rua, com uma mão.
3. Um modelo, muitos tenants: toda melhoria vale para todos e todo tenant funciona sem foto.
4. A prévia tem que parecer o site pronto da casa, não um molde com o nome trocado.
5. O pedido é da casa: WhatsApp, telefone e Maps antes de qualquer intermediário.

## Accessibility & Inclusion

Contraste AA calculado nos dois modos (claro e escuro), texto ≥ 16 px, alvos de toque ≥ 44 px, 320 px sem rolagem horizontal, `prefers-reduced-motion` respeitado, conteúdo visível sem JS.
