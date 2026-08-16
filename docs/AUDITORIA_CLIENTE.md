# O que o cliente encontra — auditoria do percurso real

Percurso feito em produção como cliente novo, do zero: criar conta, configurar o
site, cadastrar conteúdo, ver o resultado. Conta de teste: **Barlly**
(`pontocomumtus@gmail.com`), site em `/bar/barlly`.

Cada item é o que aconteceu, não o que deveria acontecer.

---

## 1. Onboarding fala do produto errado — ALTO

Logo após criar a conta, a tela de boas-vindas diz:

> **Bem-vindo ao AleroPrice!** Siga os passos abaixo para destravar o poder da
> sua gestão financeira.
> Cadastro ✓ → **Importar XML** (Ação Necessária) → Lucro Real (Bloqueado)
> *Dica de ROI: importe uma nota para descobrir se você pagou mais caro no
> tomate esta semana.*

Quem entrou pra ter um site cai numa trilha de gestão de custos, com "Importar
XML" marcado como a ação necessária. O caminho dele — Site → Conteúdo → ver o
site — não aparece em lugar nenhum.

**Consertar:** trilha por objetivo. Cliente que veio pelo site vê
"1. Identidade → 2. Cardápio e fotos → 3. Seu site no ar".

## 2. Não existe upload de foto para o cliente — CRÍTICO

O campo do hero é:

> **Foto do topo** *(caminho em static, ex: img/bar/foto-18.jpg)*

Um campo de texto esperando um **caminho de arquivo no servidor**. Não há botão
de escolher arquivo, não há arrastar-e-soltar. O dono do bar não tem como pôr
foto nenhuma pelo painel.

O upload existe e funciona — mas só no **Modo Campo**, que é ferramenta do
operador (`e_operador()`, 404 pro cliente). Ou seja: a única pessoa que pode
colocar foto no site do bar é quem vendeu, não quem comprou.

É o item que mais compromete a promessa: sem foto, o site abre com o fundo do
tema e parece um modelo com o nome trocado — exatamente o que a campanha quer
evitar.

**Consertar:** portar o uploader do Modo Campo (`campo/foto`, já com redução no
navegador e Vercel Blob) para o painel do cliente.

## 3. O cliente não escolhe o modelo do site — ALTO

A tela "Identidade do site" oferece **Cara do site** (4 paletas) e **Jeito de
falar** (4 tons). Os **6 modelos de layout** — clássico, craft, tradicional,
autoral, noturno, brasa — não estão lá.

Quem troca o modelo é o operador, em `/campo/<slug>/visual`. O cliente fica com
o `classico` para sempre, sem saber que existem outros cinco.

**Consertar:** levar o seletor de modelo (com a prévia ao vivo que já existe no
Modo Campo) para `/config-site`.

## 4. Menu com 14 itens, dos quais o cliente do site usa 6 — MÉDIO

Barra do painel: Dashboard, Reservas, Agenda, Promoções, Site, Conteúdo,
Pratos, Cardápios, Estoque, Notas Fiscais, Previsão, Desperdício, Custos.

Quem comprou o plano `site` não usa Pratos, Cardápios, Estoque, Notas Fiscais,
Previsão, Desperdício nem Custos. Sete itens que não levam a lugar nenhum útil
pra ele — e dois deles (Estoque, Notas Fiscais) parecem obrigatórios.

**Consertar:** filtrar o menu por `plano_efetivo` — o gate já existe em
`app/utils/planos.py`, só não é usado na navegação.

---

*(auditoria em andamento — próximos: Conteúdo, Agenda, Promoções, Reservas,
importação de NF-e, e o site publicado)*

## 5. Promoção recusa dia da semana por texto — BAIXO (funciona como deveria)

`dia_semana` é número (0–6). Mandar "quarta" devolve *"Dia da semana inválido."*
com o formulário preenchido. Foi erro do script de auditoria, não do app — fica
registrado porque a mensagem é boa e o comportamento é o correto.

## 6. Login por cliente HTTP exige Referer — BAIXO (informativo)

Todo POST em HTTPS precisa do header `Referer` da mesma origem, senão o
Flask-WTF devolve *400 The referrer header is missing*. O navegador manda
sozinho; `curl` e scripts não. Vale saber ao automatizar ou integrar.

---

# Percurso completo, medido

Conta **Barlly** criada do zero em produção e percorrida por HTTP
(`scripts/auditar_cliente.py`).

| Etapa | Resultado |
|---|---|
| Criar conta | ok — conta, tenant e site em `/bar/barlly` |
| 13 telas do menu | todas abrem, nenhum 500 |
| Salvar identidade do site | ok — 16 campos |
| Cadastrar prato | ok, e aparece no site |
| Cadastrar avaliação | ok, e aparece no site |
| Cadastrar equipe | ok |
| Cadastrar evento | ok, e aparece no site |
| Cadastrar promoção | recusada por dia inválido (correto) |
| JSON-LD no site | presente |

**Nada quebra.** O que falta é de produto, não de estabilidade: o dono não
consegue pôr foto, não escolhia o modelo, e a trilha inicial fala de outro
produto.

## Corrigido nesta rodada

O item 3 (cliente não escolhe o modelo): `/config-site` agora abre com os **6
modelos** em cartões, cada um com "pra quem é" e link de prévia (`?modelo=`, que
não grava), mais o seletor claro/escuro. Antes o painel só tinha as 4 paletas de
cor — que o dono lia como "os designs disponíveis".
