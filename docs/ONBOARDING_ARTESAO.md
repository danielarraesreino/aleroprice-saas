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
