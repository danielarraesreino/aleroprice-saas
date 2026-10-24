# Checklist de entrega (todos os itens, com evidência)

- [ ] Capturas Playwright (`/usr/bin/google-chrome`): 320, 390, 768, 1440 × claro/escuro × **com foto e sem nenhuma foto**.
- [ ] Lado a lado com bardavila.bar: o modelo não perde em textura, hero, ritmo, fallback.
- [ ] R1 identidade própria (fonte, paleta, hero, ornamento) — não só `:root`.
- [ ] R2 nenhum dado de tenant no template/CSS (`grep` pelo nome do piloto: zero).
- [ ] R4 tenant sem imagem alguma: hero, cartões e galeria desenhados (nada cinza, nada quebrado).
- [ ] R5 contraste AA nos dois modos (texto sobre hero incluído); foco visível; `aria-label` no tema.
- [ ] R6 320 px sem rolagem horizontal; alvos ≥ 44 px; imagens com `width/height` ou `aspect-ratio`.
- [ ] R7 `prefers-reduced-motion` testado; página legível com JS desligado.
- [ ] R9 faixa de prévia presente em `eh_demo`, ausente em cliente; `noindex` só em prévia.
- [ ] R10 toda imagem tem origem em `creditos.json` ou `AUTORIZADO.txt`; nenhuma < 800 px no hero.
- [ ] R12 frase-padrão e vocabulário conferidos.
- [ ] Peso: ≤ 2 famílias de fonte por modelo; sem imagem > 300 KB sem necessidade.
- [ ] `<h1>` único, `<title>`/descrição com o nome e a Praça do Coco, JSON-LD válido.
- [ ] Testes: suíte completa verde + teste do que mudou.
- [ ] Dono viu as capturas e deu OK antes de commit/deploy.
