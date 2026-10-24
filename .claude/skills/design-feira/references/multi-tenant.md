# 94 tenants: como manter amarrado

- **Registro único** `app/utils/modelos.py` (`MODELOS_ARTESAO`, `modelo_para_categoria`, `catalogo_de_modelos`).
  Modelo novo = entrada no registro + template + teste parametrizado (`test_hotsite_artesao.py`
  parametriza por `MODELOS_ARTESAO`: o modelo novo entra no teste sozinho).
- **Leads em YAML** (`app/data/leads/<slug>.yml`) são a fonte do conteúdo da prévia; importar com
  `app/scripts/importar_hotsites.py`; aplicar com `/bootstrap-demo` (token temporário, fechar depois).
- **Imagens** por pasta `static/img/demo/<slug>/` (`capa.jpg`, `logo.jpg`, `produto-*.jpg`, `foto-NN.jpg`) +
  `creditos.json`. Entrada de foto real só por `receber_fotos.py` (exige `AUTORIZADO.txt`).
- **Mudança de modelo em massa** (ex.: ajuste em `_base.html`) afeta 94 sites: rode a suíte e capture ao
  menos 1 tenant por modelo, com e sem foto, antes de publicar.
- **Nada específico de cliente** em CSS/HTML. Exceção de um cliente = campo novo em `SiteConfig`/lead, com
  padrão para os demais, nunca um `{% if site.slug == ... %}`.
- **Prévia expira** (`demo_expira_em`); cliente convertido perde a faixa e o `noindex`.
- **Autorização** e **vocabulário**: `docs/documentacao/05_*` e `01_*`.
