# Auditoria de segurança e operação (Vercel) — 17/10/2026

Escopo: o que está registrado em produção com `GESTAO_ATIVA` desligada (site público, auth,
admin do site, Modo Campo, billing, `bootstrap-demo`) + projeto Vercel `aleroprice-bardavila`.
Somente leitura. Nenhum segredo é reproduzido aqui (só arquivo e tipo).

| | Nota |
|---|---|
| **Segurança** | **5/10** — o isolamento entre tenants e o CSRF estão bem feitos; os pontos fracos são segredos e credenciais em repositório **público** e um rate limit que não funciona |
| **Operação** | **6/10** — boot rápido (~0,9 s) e região certa; faltam observabilidade (logs de 1 h, sem Analytics) e há 500 recorrente de conexão com o Neon |

O repositório `github.com/danielarraesreino/aleroprice-saas` é **público**: a API do GitHub responde 200 sem autenticação. Isso agrava os achados S1 e S2.

---

## Segurança — achados (≥80% de confiança), do mais grave ao menos grave

### S1 · CRÍTICO (condicional) — Senha do admin do Bar da Vila (cliente real) está no código público
- **Evidência:** `run.py:481-485` (`/bootstrap-demo?action=demos`) cria `Usuario` **admin** do tenant `bar-da-vila` (domínio `bardavila.bar`) com e-mail e senha fixos no código. O mesmo vale para o Bar do Zé em `run.py:497-499`. Também `app/scripts/seed_demo_avaliacao.py:26-27` (EMAIL/SENHA fixos).
- **Cenário:** qualquer pessoa lê o repositório público, entra em `feiradebarao.com.br/auth/login` com essas credenciais e passa a ser dona do site do Bar da Vila: muda telefone/WhatsApp do bar, desliga reservas e lê `/reservas`, com nome e telefone dos clientes (dado pessoal, LGPD).
- **Não verificado:** a consulta ao banco de produção para confirmar se a conta existe foi bloqueada pela política de leitura em produção. **Para confirmar:** `SELECT email, tipo, ativo FROM usuario WHERE email IN ('<os dois e-mails do run.py>');`. Se a conta existir, trate como incidente.
- **Correção:** trocar já a senha dessas contas (ou desativá-las e criar o login real do Gustavo); tirar as senhas do código (gerar com `secrets.token_urlsafe` e mostrar uma vez no JSON). **Esforço: P**

### S2 · ALTO — Chave da API da NVIDIA no histórico git público
- **Evidência:** commit `d61d507` (22/08/2026) adicionou a chave fixa (tipo `nvapi-…`) em `app/utils/ai_copy.py` e `app/utils/nfe_ocr.py`. Ela saiu do código em `048b0c4`, mas continua no histórico do repositório público.
- **Cenário:** qualquer pessoa clona o repositório, pega a chave e gasta a cota ou o crédito da conta NVIDIA no nome do projeto.
- **Correção:** **revogar e trocar a chave** no painel da NVIDIA. Reescrever o histórico é opcional, porque a chave já vazou. Ligar o secret scanning e o push protection do GitHub. **Esforço: P**

### S3 · MÉDIO — Open redirect no login (`//dominio`)
- **Evidência:** `app/routes/auth/views.py:44-47` aceita qualquer `next` que comece com `/`. Testei localmente com a config `testing_site`: `POST /auth/login?next=//evil.example/x` devolve `302 Location: //evil.example/x`. O form de login não tem `action`, então o `next` da URL vai junto no POST.
- **Cenário:** o golpista manda ao dono do bar `https://feiradebarao.com.br/auth/login?next=//golpe.com/auth/login`. A vítima entra com a senha certa e cai numa cópia da tela dizendo "senha incorreta", que captura a senha.
- **Correção:** aceitar só `next.startswith('/') and not next.startswith('//') and '\\' not in next` (ou `urlsplit(next).netloc == ''`). **Esforço: P**

### S4 · MÉDIO — Os rate limits não separam clientes: todo mundo é `127.0.0.1`
- **Evidência:** o log da Vercel registra todas as requisições como `127.0.0.1 - - [...]` (ex.: 18/10 01:30:59, `GET /bar/bar-do-guiu`). Portanto `request.remote_addr` é constante, e as chaves `cadastro:`/`esqueci:`/`reservar:`/`novidades:` (`app/routes/publico/views.py:683, 913, 776`; `auth/views.py:99`) são **uma só para todos os visitantes** de cada instância.
- **Cenário:** um script pega um token em `/novidades/token` e faz 8 POSTs em `/reservar` a cada 5 min. Com isso, todo cliente real que tenta reservar recebe 429 ("Muitas tentativas"). O mesmo vale para `/cadastro` (5/15 min) e `/auth/esqueci`. Na prática, o limite derruba o serviço para todos sem conter o abuso.
- **Correção:** tirar o IP de `X-Forwarded-For`/`X-Real-IP` (com `werkzeug.middleware.proxy_fix.ProxyFix(x_for=1)`) ou ler `request.headers['x-real-ip']`. Para abuso real, usar uma regra de rate limit no Vercel Firewall. **Esforço: P**

### S5 · MÉDIO — `/auth/login` sem nenhum limite de tentativas
- **Evidência:** `app/routes/auth/views.py:30-37` não chama `limite_excedido`. A senha mínima no cadastro é de 6 caracteres (`publico/views.py:698`).
- **Cenário:** força bruta ou credential stuffing contra donos de bar e, principalmente, contra a conta `superadmin`, que pela personificação (`campo.abrir_admin`) controla todos os tenants.
- **Correção:** limite por e-mail **e** por IP real (depois do S4), mais uma regra no Vercel Firewall para `POST /auth/login`. 2FA para superadmin a médio prazo. **Esforço: P/M**

### S6 · BAIXO — Endpoint de IA público sem limite (`/api/concierge-voz`)
- **Evidência:** `app/routes/publico/views.py:1049-1077` é público, sem `limite_excedido` e sem limite de tamanho de `texto`, e chama a NVIDIA (`ai_copy._chamar_nvidia`) com a chave do projeto. O CSRF não segura script, porque o token sai de `/novidades/token`.
- **Cenário:** um script em loop consome a cota da `NVIDIA_API_KEY` de produção, se ela estiver configurada. Não consegui confirmar: listar as variáveis de ambiente deu 403.
- **Correção:** `limite_excedido` por IP real, `texto[:300]` e, se o recurso não estiver em uso, desligar a rota. **Esforço: P**

### S7 · BAIXO — `SEED_TOKEN` na query string vai para o log
- **Evidência:** `run.py:243` lê o token de `request.args`, e o werkzeug loga o path inteiro (`"GET /bootstrap-demo?token=… HTTP/1.1"`).
- **Correção:** ler de um header (`X-Seed-Token`) e remover `SEED_TOKEN` da Vercel quando não estiver em uso, como o comentário já pede. **Esforço: P**

### Conferido e OK (sem achado)
- **Tenancy:** todas as queries de `configsite`, `conteudo`, `reservas`, `agenda`, `promocoes` e `campo.remover` filtram por `restaurant_id`. `campo.*` e `campanha.*` exigem `e_operador()` (superadmin) em **todas** as rotas, conferido por script. O `operador_id` vive na sessão assinada, e `voltar` revalida o perfil.
- **CSRF** ligado globalmente. Só há duas exceções, e as duas se justificam (webhook com HMAC; bootstrap com token).
- **Billing:** `success` valida no Stripe se a sessão foi paga e se `client_reference_id` bate (o CLAUDE.md ainda descreve o fluxo antigo, otimista, e precisa ser atualizado). O webhook recusa se não houver segredo configurado.
- **XSS:** o JSON-LD é escapado (`seo.serializar`), e os `|safe` só recebem textos fixos de `copy_site`. O upload aceita só jpg/png/webp.
- **Redefinição de senha:** o token é assinado, expira em 30 min e só funciona uma vez. A tela de "esqueci" não revela se o e-mail existe.
- **Cookies:** `session` com `Secure; HttpOnly; SameSite=Lax`. HSTS está ligado (2 anos). Em produção o `SECRET_KEY` é obrigatório (fail fast em `app/__init__.py:32`); o fallback só vale em dev.

### Endurecimento recomendado (não é vulnerabilidade comprovada)
- Faltam `Content-Security-Policy` (`frame-ancestors 'self'`), `X-Content-Type-Options: nosniff` e `Referrer-Policy` nos dois domínios. O `SameSite=Lax` já segura clickjacking no admin. Dá para adicionar via `headers` no `vercel.json`. **P**
- `instagram_url`/`facebook_url` vão para `href` sem validar o esquema (`site/landing.html:962`): aceitar só `https://`. **P**
- `Usuario.ativo=False` não bloqueia login: `UserMixin.is_active` é sempre True. Sobrescrever `is_active`. **P**

---

## Operação (Vercel) — achados

Fontes: `get_project`, `get_runtime_errors` (grupos desde set/2026), `get_runtime_logs` (só a última 1 h, ver O3) e `curl` com `Server-Timing`. Listar as variáveis de ambiente deu **403**. O Firewall não tem configuração customizada (404 "config not found").

### O1 · ALTO — 500 recorrente: "SSL connection has been closed unexpectedly" (Neon)
- **Evidência:** são 11 grupos de erro, e todos os 10 com causa são `psycopg2.OperationalError: SSL connection has been closed unexpectedly`, apesar de `pool_pre_ping`. Os maiores: `GET /` em `bardavila.bar` (18×, último 16/10 00:38 UTC), `GET /sitemap.xml` (11×, último 16/10 11:38), `/sitemap.xml` (10×) e `/bar/<slug>` (emporio-do-nono, barbieri, bar-do-ademir…, até 16/10 13:24). O compute do Neon suspende por inatividade (`suspend_timeout_seconds: 0` = padrão de 5 min). O `DB_CONNECT` sobe para 0,76–1,17 s quando o banco está acordando (18/10 00:52, 01:04, 01:23).
- **Impacto:** a primeira visita depois de um período parado recebe a página de erro, inclusive o Googlebot no sitemap.
- **Correção:** usar a URL **pooled** do Neon (`-pooler`) com `NullPool` no serverless, ou repetir uma vez a requisição em `OperationalError` antes do primeiro query. **Esforço: P/M**

### O2 · MÉDIO — Bug que gera 500 em `/config-site/testar-callmebot`
- **Evidência:** `app/routes/configsite/views.py:145` usa `os.environ` sem `import os`, então dá `NameError` sempre que o bar ainda não tem apikey salva. As linhas 139-140 também têm precedência errada: o `... if request.is_json else None` vale para a expressão inteira, então um POST de form ignora o número e a chave digitados.
- **Correção:** `import os` e parênteses em `(request.form.get(x) or (request.json or {}).get(x))`. **Esforço: P**

### O3 · MÉDIO — Observabilidade quase nula
- O plano Hobby guarda logs de runtime por **1 h** (não deu para consultar 7 dias: a API retorna 400 de retenção). Ninguém vê o 500 da madrugada.
- **Web Analytics: desligado** (`/_vercel/insights/script.js` → 404). **Speed Insights: ligado no projeto** (`/_vercel/speed-insights/script.js` → 200), mas **nenhum template carrega o script**, então não coleta nada.
- Não deu para confirmar se o Sentry está ativo, porque as variáveis de ambiente deram 403.
- **Correção:** confirmar o `SENTRY_DSN` em Production (gratuito, guarda os erros); incluir `<script defer src="/_vercel/speed-insights/script.js">` nos `base` do site e ligar o Web Analytics. Para reter logs, configurar um log drain (Pro) ou usar o próprio Sentry. **Esforço: P**

### O4 · BAIXO — Arquivos estáticos passam pela função Python (cold start em imagem)
- **Evidência:** o rewrite `/(.*)` → `api/index.py` (`vercel.json`) faz cada `/static/...` executar Flask. O log mostra `BOOT_TIMING ... total=0.83–1.00s` disparado por `GET /static/img/bar/foto-3.jpg` (18/10 01:29:39) e `/static/img/dossie/*.jpg` (01:30:21). O `s-maxage` ajuda depois do primeiro hit, mas cada MISS custa invocação e cold start. Varreduras (`/wp-admin/install.php`, 01:26:29) também acordam a função.
- **Correção:** servir `app/static` como saída estática (copiar para `public/` no build, ou `routes` com `handle: filesystem` antes do rewrite). Bloquear `/wp-*` e `*.php` no Firewall. **Esforço: M**

### O5 · INFO — Latência e cold start
- Cold start (`BOOT_TIMING`): **0,83–1,00 s** (já sem `create_all`). `DB_CONNECT` com o banco quente: 36–126 ms.
- Rotas medidas (`Server-Timing app;dur`): `/barao` **229 ms** (a mais lenta), `/` 275 ms quando gerada (mas sai da borda, `HIT`, TTFB 0,12 s), `/auth/login` 69 ms, `/bar/bar-da-vila/cardapio` 35 ms, `/bar/bar-da-vila` 27 ms, `/sitemap.xml` 17 ms.
- O site do bar em `bardavila.bar` sempre grava cookie (token CSRF da reserva), então fica `Vary: Cookie` e nunca é cacheado na borda. Toda visita depois de um tempo parado paga cold start + Neon acordando.
- A proteção de deploy (SSO/senha) está desligada. Os aliases `*.vercel.app` servem o app completo contra o banco de produção, inclusive `/auth/login`. É aceitável, mas vale ligar a proteção dos previews.

---

## Ordem sugerida
1. Hoje: S1 (trocar as senhas e conferir a conta no banco) e S2 (revogar a chave NVIDIA).
2. Esta semana: S3, S4, S5, O1, O2 — todos P.
3. Depois: O3 (Sentry + Speed Insights), S6, O4 e os cabeçalhos de segurança.
