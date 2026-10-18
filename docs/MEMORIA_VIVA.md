# Memória viva — Feira de Barão

Documento para retomar o projeto sem reler as conversas. Atualize no fim de
cada sessão: o que foi feito, o que ficou pendente e os próximos passos.
Última atualização: 18/10/2026.

## O que o projeto é hoje

- **feiradebarao.com.br** — portal da Feira de Barão (Barão Geraldo,
  Campinas): vitrine das barracas digitais (prévias noindex de 22–23 bares) e
  venda do pacote para donos de bar (site + cardápio + reserva + Google).
- **bardavila.bar** — cliente pagante da **Vila Lemos**. Usa a mesma
  plataforma, mas **não faz parte da Feira**: não aparece na vitrine, no
  sitemap nem no `llms.txt` do portal, e `/bar/bar-da-vila` redireciona (301)
  para o domínio dele.
- Stack: Flask monolito na Vercel (projeto `aleroprice-bardavila`, região
  `gru1`), banco Neon `alerosaas` (sa-east-1). A gestão de custos está desligada
  (`GESTAO_ATIVA`). Guia técnico: [`CLAUDE.md`](../CLAUDE.md).

## Linha do tempo (15–18/10/2026)

**Sessão 1 (desktop, 15–17/10)**
- Barracas fora do ar (404) → publicadas de novo. Botão ON/OFF manual no Modo
  Campo no lugar da expiração automática.
- Lentidão: região `gru1`, cache de borda na home, `pool_pre_ping`, schema fora
  do boot. Home ~0,2 s, bares ~0,17 s.
- Gestão de custos desligada, com avaliação em
  [`AVALIACAO_GESTAO_2026-10.md`](AVALIACAO_GESTAO_2026-10.md).
- Superadmin `coletivoaruatemvoz@gmail.com` com botão "ADMIN" para entrar no
  painel de qualquer bar.
- Recuperação de senha por e-mail (Brevo), com olho no campo de senha.
- **Brevo**: conta da Feira (empresa "Cantina do Código"), domínio autenticado,
  remetente `contato@feiradebarao.com.br` e encaminhamento ImprovMX para o
  Gmail. Lista 3 = Comunidade Barão, lista 4 = Donos de bar, template 1 =
  dupla confirmação (tag `optin`).
- Formulário "Receba as novidades" na home e nos bares, com dupla confirmação
  (LGPD). `/cadastro` vira lead em "Donos de bar".
- **Avaliações no Google**: menu Avaliações no painel. O dono cola o place_id
  e ganha o link curto `/bar/<slug>/avaliar` (conta cliques), o QR e a mensagem
  de WhatsApp por reserva. A mesma mensagem vai para todos (o Google proíbe
  pedir só a quem gostou).
- Skill `google-meu-negocio` (~/.claude/skills) com o kit do perfil e as regras
  de avaliação.
- **Auditoria total** com notas de 5 a 7, detalhada em
  [`AUDITORIA_2026-10.md`](AUDITORIA_2026-10.md) e [`auditoria/`](auditoria/).
  Correções feitas no ramo `auditoria-correcoes`:
  - segurança: open redirect, limite de login, conta desativada, IP real,
    senhas fora do código, código-fonte fora do ar;
  - SEO: schema local, sem coordenadas falsas;
  - UX e acessibilidade: menus, foco, contraste, 44 px, dock da prévia;
  - desempenho: WebP, cache de borda nos bares, estáticos direto da Vercel;
  - 663 testes.

**Sessão 2 (CLI, 18/10 madrugada)**
- `auditoria-correcoes` juntado no `main` e publicado (`10d9f34`), sem os leads
  jurídicos.
- `eb6410c`: Bar da Vila fora do portal, sitemap limpo (sem demo, com
  cardápios), `llms.txt` com a cidade certa, bairro no title ("· Vila Lemos").
  672 testes.
- Pesquisa de palavras-chave:
  [`auditoria/seo-keywords-2026-10-18.md`](auditoria/seo-keywords-2026-10-18.md).
- A reauditoria com os plugins (6 frentes) **falhou por falta de crédito**; foi
  retomada na sessão 3.

**Sessão 3 (desktop, 18/10)**
- Estado da sessão 2 recuperado e conferido em produção: `/run.py` e
  `/CLAUDE.md` dão 404, WebP no ar, 301 do Bar da Vila.
- Esta memória criada. Reauditoria com os plugins relançada (ver abaixo).

## Pendências que dependem do dono do projeto

1. **Urgente:** desativar no Neon as contas com senha que vazou no GitHub
   público.
   ```sql
   UPDATE usuario SET ativo=false WHERE email IN ('ze@bardoze.com','demo@alero.com.br');
   ```
   `admin@teste.com` já está inativa e, com o código novo, não entra mais.
2. **Revogar a chave da NVIDIA** que ficou no histórico do git (commit `d61d507`).
3. **Google Search Console e Bing Webmaster:** verificar os dois domínios e
   enviar os sitemaps. Hoje nenhum dos dois aparece indexado.
4. **Vercel:** ligar o Web Analytics e redirecionar www para o domínio sem www
   nos dois domínios.
5. **Bar da Vila:**
   - horário estruturado (ex.: "Qua–Dom 11h–21h");
   - cardápio real com preços;
   - place_id na tela Avaliações.
6. **Mural da home:** confirmar a origem dos depoimentos (os nomes foram
   anonimizados; o "Seu Valdir dos Santos" do capítulo V continua lá).
7. **Guia da feira:** dados confirmados da Feira de Barão / Praça do Coco
   (dias, horário, endereço, agenda), necessários antes de criar o guia.

## Próximos passos (ordem)

1. Consolidar a reauditoria com os plugins e corrigir o que ela apontar.
2. LP B2B "Site + cardápio + reserva + Google para bar em Campinas", com o caso
   do Bar da Vila. É a keyword local sem concorrência.
3. Guia "Feira de Barão / Praça do Coco" com schema Event (depende da pendência 7).
4. Hub "Bares em Barão Geraldo" indexável, à medida que as prévias virarem
   clientes.
5. Campanha A/B de WhatsApp com os 23 bares
   (`FEIRA_DE_BARAO_COMERCIAL/campanha-2026-10/`) e sequência de e-mail no Brevo
   (plugins Marketing / Product Marketing).
