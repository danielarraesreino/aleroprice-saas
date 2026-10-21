# Contrato de design (Feira de Barão + sites de expositor)

Fonte única para as skills de design. Se uma skill sugerir algo fora daqui, vence este arquivo.

## Princípios
1. Mobile primeiro (320 → 390 → 768 → 1440). Texto ≥ 16 px, alvos ≥ 44 px, sem rolagem horizontal.
2. Foto do produto manda. Sem foto, não aparece. Cartaz promocional é mostrado inteiro, nunca cortado.
3. Só fatos que o expositor confirmou (legendas, formulário). Sem preço sem confirmação.
4. Claro e escuro com o mesmo cuidado; contraste AA calculado, não estimado.
5. Desempenho é restrição: ≤ 2 famílias de fonte, imagens com `width`/`height`, JS mínimo, sem ícone-fonte novo.

## Tokens (nomes dos presets de tema em `temas.py`)
| Token | Papel | Escuro | Claro |
|---|---|---|---|
| `--ink` | fundo | #15100d | #f6f0e6 |
| `--ink-2` | superfície | #1f1814 | #ece3d5 |
| `--wood` | linhas, placeholder | #35291f | #d6c9b6 |
| `--cream` | texto | #f5ede2 | #1d1511 |
| `--cream-dim` | texto secundário | #bdaf9f | #5b4d41 |
| `--amber` | acento em texto | #f0715f | #a51f27 |
| `--ember` | ação (botão, bloco) | #c0262d | #b3202a |

Sites de expositor trocam só `--ember`/`--amber` e a fonte de título (variáveis por tenant).
A home da Feira usa a paleta própria de `feira.css` (`--papel`, `--tinta`, `--tomate`).

## Escalas
- Espaço: 4 px (`--s1…`): 4, 8, 12, 16, 24, 32, 48, 64.
- Tipo: 13 (rótulo) · 16 (corpo) · 18 (lead) · 24 · 32 · 48 (fluido com `clamp`). Corpo ≤ 65 caracteres de largura.
- Raio: um só por superfície (`--r`). Sem sombra decorativa.

## Componentes
- Botão: altura ≥ 48, rótulo em verbo ("Pedir pelo WhatsApp"). Primário `--ember`; secundário contorno.
- Chip de filtro: ≥ 44 px, `aria-pressed`.
- Card de produto: foto com proporção fixa e `height:auto`, nome, categoria, ação. Destaque ocupa 2 colunas.
- Selo "Na feira hoje": cor + texto (nunca só cor).
- Barra fixa mobile: ação principal + contador da encomenda, respeita `safe-area-inset-bottom`.

## Texto (pt-BR)
Frase curta, sentence case, sem exclamação em série, sem superlativo vazio. Reticências com `…`.

## Portão de entrega por superfície
Capturas 320/390/768/1440 claro e escuro · audit (impeccable) · guidelines (Vercel, local) ·
`ui-quality-baseline` · suíte de testes verde · commit local · deploy só com OK do usuário.
