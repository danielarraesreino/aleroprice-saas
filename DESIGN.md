---
name: Modelo tradicional (sites de bar)
description: Balcão de empório antigo — papel, madeira, esmalte vermelho e foto emoldurada.
colors:
  papel: "#f6eddd"
  papel-2: "#efe2ca"
  papel-3: "#e6d5b6"
  moldura: "#fffaf0"
  tinta: "#2d1e13"
  tinta-suave: "#6d5540"
  madeira: "#6b4526"
  madeira-forte: "#43290f"
  esmalte: "#b32a1e"
  esmalte-texto: "#fff6ec"
  ornamento: "#a9803a"
  papel-escuro: "#191009"
  papel-2-escuro: "#22160d"
  moldura-escuro: "#2d1e12"
  tinta-escuro: "#f3e6cf"
  tinta-suave-escuro: "#bda688"
  madeira-escuro: "#c99a63"
  esmalte-escuro: "#e85b49"
  esmalte-texto-escuro: "#1a0e08"
typography:
  display:
    fontFamily: "Playfair Display, Georgia, serif"
    fontSize: "clamp(2.5rem, 12.5vw, 5.6rem)"
    fontWeight: 900
    lineHeight: 0.93
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Playfair Display, Georgia, serif"
    fontSize: "clamp(1.85rem, 7vw, 3.1rem)"
    fontWeight: 900
    lineHeight: 1.04
  title:
    fontFamily: "Playfair Display, Georgia, serif"
    fontSize: "1.22rem"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.66
  label:
    fontFamily: "Alegreya Sans SC, Lora, serif"
    fontSize: "0.75rem"
    fontWeight: 400
    letterSpacing: "0.14em"
rounded:
  placa: "2px"
spacing:
  s-1: "4px"
  s-2: "8px"
  s-3: "12px"
  s-4: "16px"
  s-5: "24px"
  s-6: "32px"
  s-7: "48px"
  s-8: "64px"
  s-9: "96px"
components:
  button-primary:
    backgroundColor: "{colors.esmalte}"
    textColor: "{colors.esmalte-texto}"
    typography: "{typography.label}"
    rounded: "{rounded.placa}"
    padding: "13px 26px"
    height: "48px"
  button-vazado:
    textColor: "{colors.tinta}"
    rounded: "{rounded.placa}"
    padding: "13px 26px"
    height: "48px"
---

# Design System: Modelo tradicional

Escopo: `app/templates/site/modelos/tradicional.html`, usado hoje por 10 leads de bar (Empório do Nono, Armazém Rural, Botequim de Barão, entre outros). Os outros modelos (craft, autoral, noturno, brasa, artesão) e o portal têm mundo próprio e não seguem este arquivo. O contrato comum de todos continua em `docs/DESIGN.md` e na skill `design-feira`.

## Overview

**Ideia-guia: balcão de empório antigo.** A casa que está ali há décadas: madeira, papel de embrulho, placa pintada à mão, retrato pendurado na parede. O tempo é o argumento: o ano de fundação vira placa logo abaixo do nome, e a página termina na história.

Antirreferência: o site de bar genérico com banner sangrando, cartões iguais e sobretítulo em caixa alta acima de cada título.

## Colors

Uma superfície quente de papel e um único acento, o esmalte vermelho de placa.

- **Papel** (`papel`, `papel-2`, `papel-3`): fundo e faixas alternadas das seções. Escuro: madeira queimada (`#191009` / `#22160d`).
- **Tinta** (`tinta`, `tinta-suave`): texto principal e secundário, castanho e nunca cinza.
- **Madeira** (`madeira`): segunda linha do nome e as palavras em itálico dos títulos.
- **Esmalte** (`esmalte`): ação, preço, ano e estrela. No escuro, `#e85b49`, que dá 4,6:1 sobre a moldura.
- **Ornamento** (`--gold`, que o tema do tenant pode trocar): filetes e nós da linha do tempo.

### Named Rules

- O tenant troca o acento pelo tema (`--gold`, `--esmalte`); papel e tinta ficam.
- Contraste AA calculado nos dois modos, nunca estimado.

## Typography

Três vozes: Playfair Display para letreiro (nome, títulos, números), Lora para leitura e Alegreya Sans SC para carimbo (rótulos curtos, botões, legenda).

### Hierarchy

- Display: o nome da casa, com a segunda linha em itálico e na cor madeira.
- Headline: títulos de seção, com uma palavra em `<em>` itálico.
- Title: nome de prato, título de cartaz ou de evento.
- Body: 17px, entrelinha 1,66, medida até 36em.
- Label: caixa alta espaçada, **só** em rótulo curto de dado (data, tag, legenda, botão), nunca acima de título.

## Layout

- Largura de 1120px, gutter fluido, seções com `--sec-y` (de 5,5 a 11rem).
- Faixas alternadas declaradas no HTML (`data-band="alt"`), não por `nth-of-type`.
- No desktop, um fio duplo à esquerda costura as seções como linha do tempo; no celular ele some.
- Ordem: topo → salão → cardápio → promoções → agenda → avaliações → álbum → reserva → contato → história.

## Elevation & Depth

Papel sobre papel: sombra macia e com deslocamento (`0 12px 30px var(--sombra)`) nas molduras e cartazes; botão com sombra curta e borrada. Nada de sombra dura sem desfoque.

## Shapes

- Canto quase reto (2px): placa e carimbo, não pílula.
- Foto sempre em moldura de papel, inclinada de ±1,4°, com fita crepe e legenda em small caps, em sépia leve.
- Faixa de azulejo em treliça desenhada em CSS abaixo da barra.
- Filetes e bordas em linha dupla (`3px double`).

## Components

### Buttons
Primário: esmalte cheio, rótulo em small caps, altura de 48px. Secundário vazado: contorno de linha-forte, que fica esmalte no hover.

### Cards / Containers
Cartaz (promoção) e moldura (foto) são as únicas caixas. Nada de cartão dentro de cartão.

### Navigation
Barra de papel com linha dupla embaixo; no celular, folha que desdobra. A marca da casa (`site.logo`) aparece pequena na barra do celular e como placa inclinada acima do nome.

### Cardápio (componente-assinatura)
Lista de tabuleta pontilhada: miniatura de 74px em moldura, nome à esquerda, preço encostado na direita em `tabular-nums`, carimbo da tag. O destaque ganha fundo de esmalte translúcido.

## Do's and Don'ts

### Do:
- Texto da casa vem de `site.sobre`, tagline e subline; a vibe só cobre quem não tem texto próprio.
- Toda foto entra emoldurada, com legenda.
- Alvo de toque com pelo menos 44px, inclusive campos do formulário e o selo de nota.

### Don't:
- Sobretítulo em caixa alta acima de título (de seção, do nome ou de cartaz).
- Emoji como ícone: os ícones são SVG de traço único.
- Afirmação que a casa não fez (samba, "família", prêmio, preço).
- Banner de foto sangrando a tela inteira.
