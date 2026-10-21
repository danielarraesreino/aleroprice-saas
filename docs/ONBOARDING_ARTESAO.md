# Onboarding de artesão (e de qualquer expositor da Feira)

Do formulário ao site no ar, no mesmo pipeline das prévias de bar. Uma barraca
por vez ou em lote.

## 1. Formulário → lead

Exporte as respostas do Google Forms ("Form Feira Expositores") como CSV ou XLSX.

```bash
python -m app.scripts.importar_expositores respostas.xlsx --dry-run   # só mostra
python -m app.scripts.importar_expositores respostas.xlsx             # grava
```

Gera `app/data/leads/<slug>.yml` por barraca (`tipo_negocio: artesao`, vibe
`artesanal`, WhatsApp, redes, horário, lista de produtos). Cada resposta imprime
avisos: WhatsApp inválido, sem produtos, **links de fotos para baixar**.
Não sobrescreve `.yml` existente (use `--force`). E-mail e nome da pessoa
**não** vão para o arquivo: o `.yml` é versionado no git.

## 2. Fotos

Baixe para `app/static/img/demo/<slug>/` (reduza para ~1000 px, JPEG):

| Arquivo | Vira |
|---|---|
| `capa.jpg` | foto do topo |
| `logo.jpg` | marca no menu, ícone da aba e imagem de compartilhamento |
| `produto-<nome>.jpg` | um produto da vitrine (nome tirado do arquivo) |
| qualquer outro `.jpg` | galeria |

**Produto sem foto não aparece na vitrine** (continua na lista do `.yml` e entra
sozinho quando a foto chegar). Sem nenhum produto com foto, o site mostra
"Catálogo em montagem" com o botão de WhatsApp. Peça a autorização de imagem
do expositor antes de publicar.

## 3. Publicar a prévia

Commit do `.yml` e das fotos, push, e depois:

`GET /bootstrap-demo?token=$SEED_TOKEN&action=demos` (um bar só: `&slug=<slug>`)

A prévia nasce `noindex`, com banner de "não é o site oficial", em
`/bar/<slug>`. Aparece em `/feira` para quem é artesão, mesmo sem ponto no mapa.

## 4. Ponto no mapa (Modo Campo, na feira)

Em `/campo/<slug>`, bloco **Ponto na feira**: fique parado na barraca, toque em
**Usar minha localização**, escreva a referência ("Barraca 12, ao lado do
palco") e **Salvar ponto**. Coordenada fora de Campinas é recusada. O pino
aparece em `/feira`, e o JSON-LD do site ganha `geo`.

Pré-requisito: o cabeçalho `Permissions-Policy` do `vercel.json` precisa liberar
`geolocation=(self)` (já liberado), senão o navegador bloqueia o GPS.

## 5. Dia a dia do expositor

Em `/config-site`, **Estou na feira hoje**: o site dele ganha o selo "Na feira
hoje" em `/feira`. Vale só no dia (guarda a data, no fuso de São Paulo) e some
sozinho.

## 6. Converter em cliente

Igual ao bar: Modo Campo → **Fechar** (`converter_demo`). O site sai de
`noindex`, entra no sitemap e o domínio próprio pode ser apontado (a Vercel
precisa do domínio no projeto `aleroprice-bardavila`).

## Schema em produção

Esta funcionalidade adiciona colunas em `site_config` (`lat`, `lng`,
`ponto_na_feira`, `na_feira_em`). Aplique antes do deploy (SQL idempotente na
seção "Schema em produção" de `OPERACOES.md`).

## Modelos de hotsite de artesão (como os dos bares)

Cinco esqueletos, cada um com claro e escuro (automático pelo aparelho, ou fixado em
"Claro ou escuro" no painel / `?modo=claro|escuro`). Todos estendem
`site/modelos/artesao/_base.html` (menu, encomenda por WhatsApp, contato). Registro em
`app/utils/modelos.py` (`MODELOS_ARTESAO`).

| Modelo | Para quem | Jeito |
|---|---|---|
| `vitrine` | charcutaria, conservas, quem tem foto forte | foto inteira, rótulo por cima, grade por categoria, cartaz vertical inteiro |
| `atelie` | peça feita à mão: crochê, cerâmica, madeira, joia, costura, mosaico | nome gigante, bloco de cor com o que faz, catálogo editorial; não depende de foto |
| `cozinha` | pão, pizza, empada, risoto, biscoito, vegano | campo de mostarda, horário em destaque, cardápio em linhas |
| `jardim` | plantas, terrários, kokedamas | verdes, cantos macios, etiquetas |
| `ritual` | incenso, cristais, tarô, terapias | noite e dourado, centralizado, serviços em lista |

- A categoria sugere o modelo (`modelo_para_categoria`); o operador troca no Modo Campo
  (cartões "Modelo") ou o dono em `/config-site`. `?modelo=<nome>` espia sem gravar.
- Sem foto de produto nenhuma, a página mostra o que a pessoa faz em texto (cartão
  `sem-foto` / linha). Com ao menos uma foto, só aparecem os produtos com foto.
- Sem WhatsApp, o contato vira Instagram e some o "Montar encomenda".
- Vibe `artesanal-feira`: texto neutro, sem afirmação que o expositor não fez (a
  `artesanal` é a da Berga e fala de "sem química").

## Importar o pacote de hotsites (expositores.json)

```bash
python -m app.scripts.importar_hotsites /caminho/expositores.json --dry-run
python -m app.scripts.importar_hotsites /caminho/expositores.json
```

Gera `app/data/leads/<slug>.yml` (`tipo_negocio: artesao`, modelo pela categoria,
prévia `noindex` que expira em 60 dias). **Fotos do pacote não entram**: são capturas de
tela do Instagram, sem autorização. WhatsApp com dois números diferentes no pacote é
omitido até validar. Depois, como as demais prévias:
`GET /bootstrap-demo?token=$SEED_TOKEN&action=demos` (um só: `&slug=<slug>`).
