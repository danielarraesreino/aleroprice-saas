# Precificação — o que se cobra e por quê

Pesquisa de mercado feita em **16/08/2026**. Os números do mercado estão
datados de propósito: preço de agência muda, e uma tabela sem data vira lenda
interna em seis meses.

Todo valor aqui vive em variável de ambiente (`FEIRA_*`), nunca no template.
A landing e a tela de planos já divergiram sozinhas uma vez — mostravam R$ 97 e
R$ 197 para o mesmo plano.

## O que se cobra

| Item | Valor | Env |
|---|---|---|
| Mensalidade (Site) | R$ 147,90 | `FEIRA_PRECO_SITE` |
| Mensalidade (Pro) | R$ 247,90 | `FEIRA_PRECO_PRO` |
| Montagem (setup) | R$ 349 | `FEIRA_TAXA_SETUP` |
| Compra do site | R$ 1.400 | `FEIRA_COMPRA_SITE` |
| Renovação após o 1º ano | R$ 390/ano | `FEIRA_COMPRA_RENOVACAO` |
| Teste grátis | **0 dias** | `FEIRA_DIAS_TRIAL` |

O setup entrega **design exclusivo** (não um dos seis modelos prontos) e a
**configuração do Perfil da Empresa no Google** — horário, fotos, cardápio e
link do site na ficha. A compra inclui **um ano de domínio e um ano de
hospedagem**.

Cardápio digital com QR é de **todo mundo**, em qualquer plano, sem teto de
itens. Não é isca cortada pela metade: um QR na mesa que abre cinco de trinta
itens queima o produto na frente do cliente do cliente.

## Onde isso cai no mercado

**Mensalidade — R$ 147,90.** Plataforma de cardápio digital cobra de R$ 59,94 a
R$ 299,90/mês só pelo cardápio; com pedido integrado, de R$ 200 a R$ 800/mês.
Manutenção de site em agência fica entre R$ 300 e R$ 1.000/mês, e isso é só a
manutenção — hospedagem avulsa custa de R$ 30 a R$ 500/mês, e domínio .com.br
de R$ 40 a R$ 80/ano.

Ou seja: cobra-se preço de cardápio digital e entrega-se site, cardápio,
reservas, hospedagem e domínio. É posicionamento agressivo de propósito — o
concorrente real destes bares não é uma agência, é não ter nada.

**Setup — R$ 349.** Criação de site começa em R$ 500 no mercado brasileiro
(página única, template, sem SEO) e vai a R$ 15.000 em agência. Gestão de
Perfil da Empresa no Google custa de R$ 500 a R$ 1.500 **por mês** em agência —
para restaurante, de R$ 800 a R$ 1.500/mês, porque exige postagem semanal.

R$ 349 cobrindo design exclusivo **e** a configuração do Google, uma única vez,
está **abaixo do piso de mercado dos dois serviços separados**. É preço de
entrada, não de mercado. Há espaço para R$ 497 sem sair da faixa barata.

**Compra — R$ 1.400.** Criação de site fica entre R$ 800 e R$ 15.000; R$ 1.400
com domínio e hospedagem inclusos está na parte baixa da faixa. Custo real por
cliente: domínio de R$ 40 a R$ 80/ano, hospedagem praticamente zero na
infraestrutura atual. Margem alta.

## A canibalização, e a decisão tomada

Conta do primeiro ano, com os valores de hoje:

| Caminho | Ano 1 | Ano 2 |
|---|---|---|
| Assinar | R$ 349 + 12 × R$ 147,90 = **R$ 2.123,80** | R$ 1.774,80 |
| Comprar | **R$ 1.400** | R$ 390 |

Comprar sai **R$ 723,80 mais barato no primeiro ano**, e o bar ainda fica dono
do site. Se os dois caminhos entregassem a mesma coisa, todo dono que fizesse a
conta compraria, e a receita recorrente — que é o que faz o negócio valer
alguma coisa — morreria no primeiro ano.

**Decisão: separar o escopo, não subir o preço.**

Subir seria o reflexo óbvio: licença perpétua no mercado de software custa de 2
a 3 anuidades, o que aqui daria R$ 3.549 (24 × R$ 147,90). Só que o comprador é
bar de bairro em Barão, e nesse valor a venda simplesmente não acontece — troca
uma canibalização por uma prateleira parada.

O que decide é o que cada coisa **é**:

- **Site pronto** é entregável. Tem começo, meio e fim, e o mercado brasileiro
  cobra de R$ 800 a R$ 15.000 por ele. R$ 1.400 está na faixa e é honesto.
- **Software que roda todo dia** — reserva caindo no WhatsApp, painel que edita
  do celular, agenda, atualização — tem custo recorrente de verdade. Não se
  vende por preço único porque não acaba.

Então a compra entrega o site, o cardápio com QR, o Google configurado, um ano
de domínio e um ano de hospedagem. **Não** entrega reserva, agenda, promoções
nem o painel. Isso está escrito na landing, antes da venda, e não descoberto
depois.

Com escopos diferentes os dois deixam de ser comparáveis: um leva um site, o
outro leva um sistema. E quem compra e depois quer o painel assina — a compra
vira porta de entrada em vez de fuga.

**O que observar na rua:** se muita gente comprar e voltar pedindo reserva, o
preço da compra está barato demais para o que ela abre — aí sim sobe para a
faixa de R$ 2.800. Se ninguém comprar, a objeção "não quero assinatura" era
menor do que parecia, e a linha pode sair.

## Por que zero dias de teste

A prévia já é o teste. O bar vê o próprio site montado — com foto, nota e
cardápio — antes de qualquer conversa sobre dinheiro. Dar mais 14 dias de
produto completo depois disso adiava a conversa e enchia o banco de contas
abertas sem ninguém para cobrar.

`FEIRA_DIAS_TRIAL=0` desliga. `planos.fim_do_trial()` devolve `None` nesse caso,
e não uma data: `hoje + 0 dias` é hoje, e a comparação `hoje <= trial_termina_em`
daria um dia inteiro de Pro para quem não tem teste nenhum.

Reabrir é mudar a env — sem deploy.

## Fontes

- [Melhores Sistemas de Cardápio Digital 2026 — Rei do Delivery](https://reidodelivery.com.br/blog/melhores-sistemas-de-cardapio-digital)
- [Cardápio digital com QR Code: vale a pena em 2026? — Nola](https://usenola.com.br/blog/cardapio-digital-para-restaurante-com-qr-code-vale-a-pena-em-2026)
- [Quanto custa criar um site em 2026 — InfinitePay](https://www.infinitepay.io/blog/quanto-custa-criar-um-site)
- [Quanto custa um site em 2026? Tabela: R$ 500 a R$ 50 mil — Agência Colors](https://agenciacolors.digital/quanto-custa-site/)
- [Quanto custa manter um site em 2026 — Wix](https://pt.wix.com/blog/quanto-custa-manter-um-site)
- [Quanto custa Otimização Google Meu Negócio — FocusArts](https://focusarts.com.br/preco-otimizacao-google-meu-negocio/)
- [Gestão de Google Meu Negócio — Veritas Comunicações](https://veritascomunicacoes.com.br/gestao-de-google-meu-negocio/)
