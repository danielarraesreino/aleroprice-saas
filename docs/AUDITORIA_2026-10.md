# Auditoria total — feiradebarao.com.br + bardavila.bar (17/10/2026)

Feita por especialistas em paralelo, só leitura, em produção. Os detalhes com
evidência (URL, viewport, métrica e arquivo:linha) estão em:

- [`auditoria/seo.md`](auditoria/seo.md)
- [`auditoria/ux-a11y-perf.md`](auditoria/ux-a11y-perf.md)
- [`auditoria/seguranca-vercel.md`](auditoria/seguranca-vercel.md)

## Notas

| Área | Nota |
|---|---|
| Segurança | 5/10 |
| SEO local e IA | 5,5/10 |
| Acessibilidade | 6/10 |
| Operação (Vercel) | 6/10 |
| UI/UX | 6,5/10 |
| Responsividade | 7/10 |
| Desempenho | 7/10 |

## Os 10 problemas mais caros, em ordem

| # | Problema | Onde | Esforço |
|---|---|---|---|
| 1 | Admin do Bar da Vila criado pelo `/bootstrap-demo` com e-mail e senha fixos no código, e o repositório no GitHub é **público**. Se a conta existir, qualquer um lê as reservas (nome e telefone dos clientes). Trocar a senha, apagar a conta e tirar a senha do código. | `run.py:481-485`, `:497-499`, `app/scripts/seed_demo_avaliacao.py` | P |
| 2 | Chave da API NVIDIA no histórico público do git: **revogar no painel da NVIDIA**. | commit `d61d507` | P (usuário) |
| 3 | Schema local errado: coordenadas e área de "Barão Geraldo" fixas para todo bar (o Bar da Vila fica na Vila Lemos). Endereço não estruturado e horário fora do schema. É o que o Maps e as IAs leem. | `app/utils/seo.py:724-730`, `:382` | P |
| 4 | Prévias com "None" 13× (wa.me/None, Endereço "None"), justamente a página que se manda ao lead. | `site/landing.html:661-979` | P |
| 5 | Open redirect no login (`next=//site-malicioso`). | `auth/views.py:44-47` | P |
| 6 | Limites por IP inúteis: a Vercel entrega todo visitante como 127.0.0.1. Um script bloqueia as reservas de todos. O login não tem limite, e o superadmin controla todos os bares. | `utils/tenant.py`, `auth/views.py` | P |
| 7 | Sitemap com página de teste e domínio de outro; `bardavila.bar/llms.txt` redireciona para o portal; o cardápio fica fora do sitemap. | `app/__init__.py:245`, sitemap | P |
| 8 | Bar da Vila baixa 1,36 MB no celular (fotos de 1200 px em cards de 157 px) e não é cacheado, então paga o cold start. | `site/landing.html:722` | M |
| 9 | Menu da home a 1280 px esconde "Planos"/"23 Barracas"; a home não linka `/cadastro` nem o login; preço só a 78% da página. | `produto/landing.html:132-139` | P |
| 10 | Prévia: a barra de troca de modelo cobre o botão de WhatsApp no celular. Menus fechados recebem foco do teclado. Há contraste abaixo do mínimo. | `site/_demo_dock.html`, modelos clássico e noturno | M |

## Também apareceu

- **CallMeBot:** `/config-site/testar-callmebot` dá 500 por falta de `import os` (`configsite/views.py`).
- **Erros intermitentes:** "SSL connection closed" do Neon até 16/10 13:24. Pararam com o `pool_pre_ping` que publicamos depois.
- **Métricas:** Web Analytics desligado. O Speed Insights está ligado, mas nenhum template carrega o script, então não coleta nada.
- **Cabeçalhos:** faltam CSP, nosniff e Referrer-Policy.

## O que está bom

- Isolamento entre bares (`restaurant_id`) em todas as rotas do admin.
- Operador exigido no Modo Campo.
- CSRF e escape de XSS.
- Cookies seguros.
- Canonical entre os dois domínios do Bar da Vila.
- http redireciona para https.
- Prévias com noindex.
- Robots libera os robôs de IA.
- JSON-LD válido.
- Sem rolagem horizontal em nenhum tamanho de tela.
- CLS perto de 0.
- Home servida da borda da Vercel em ~80 ms.
