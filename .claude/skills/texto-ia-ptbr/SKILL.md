---
name: texto-ia-ptbr
description: Detecta e reescreve texto com cara de IA em português do Brasil nas páginas, propostas, hotsites e mensagens da Feira de Barão. Use SEMPRE que escrever, revisar ou publicar texto de venda, título, CTA, descrição de produto, "quem faz", proposta, kit do vendedor ou mensagem de WhatsApp, e quando o pedido citar "texto de IA", "soa genérico", "copy", "proposta", "headline". Complementa copywriting (que é em inglês) e a regra R12 do design-feira.
---

# texto-ia-ptbr

Todo texto novo passa por esta lista antes de ir ao ar. Dois modos: **detectar** (só lista padrão, frase e arquivo:linha) e **reescrever** (troca por frase concreta). Primeiro `copywriting` decide o que dizer; esta skill tira o vício.

## Teste de portabilidade
A frase serviria para qualquer barraca ou bar de qualquer cidade? Então é enchimento. Troque por nome, horário, preço, produto, bairro ou prazo reais (Praça do Coco, sábado 10h às 16h, domingo 10h às 15h).

## Os 15 vícios
1. Contraste binário: "Não é só X, é Y", "Mais do que X, é Y", "Não se trata de X, mas de Y".
2. Abertura de palco: "No mundo atual", "Em um cenário cada vez mais", "Nos dias de hoje".
3. Anúncio da frase: "Vale ressaltar", "É importante destacar", "Cabe mencionar".
4. Vocabulário inflado: jornada, experiência única, mergulhar, desvendar, explorar, universo de sabores, convite, transformador, revolucionário.
5. Tríade automática ("sabor, tradição e afeto") e adjetivos empilhados.
6. Gerúndio decorativo no fim: "garantindo momentos únicos", "refletindo o compromisso".
7. Fecho de efeito: "No fim das contas", "Afinal", "E é isso que faz toda a diferença".
8. Resumo redundante: "Em resumo", "Em suma".
9. Falsa revelação: "O segredo? Ingredientes frescos.", "O melhor de tudo:".
10. Travessão como tempero. Use vírgula, ponto ou dois-pontos.
11. Superlativo sem prova: "o melhor", "autêntico", "artesanal" sem dizer como, "feito com amor", "qualidade premium", "referência na região".
12. Emoji ou marcador decorativo em título, negrito espalhado, Title Case em título ("Nossos Produtos Artesanais").
13. Calques do inglês: "apaixonados por", "no final do dia", "levar para o próximo nível", "soluções", "agregar valor", "descubra o poder de".
14. CTA genérico: "Saiba mais", "Clique aqui", "Venha conhecer!", "Não perca!", exclamação em série. Use verbo mais o que a pessoa ganha ("Pedir a prévia do meu site").
15. Voz de empresa: nós/vocês/clientes/consumidores no lugar de pessoas e lugares. Sem nome, horário, preço ou bairro.

Extras: mistura de você/tu/senhor na mesma página; "outrossim", "a fim de", "de modo a", "dessa forma"; aspas curvas e vírgula Oxford.

## Regras do projeto
- Só promete o que existe (`docs`: 14_OFERTA_DORES_E_PRECOS.md). Não existe pagamento no site nem upload de foto pelo expositor. Nunca prometer posição no Google.
- "Barraca" é o ponto físico, "bar" é casa de bebida, "expositor" é quem vende na Feira (design-feira R12).
- Conta verificável vence adjetivo: "R$ 360 no ano contra R$ 540 em 12 mensais", não "preço imbatível".
- Preço no texto vem de `app/utils/planos.py`, nunca digitado.

## Saída
Detectar: tabela `arquivo:linha | vício nº | frase | por quê`. Reescrever: antes e depois, e o que foi cortado por falta de prova.
