"""Gera o SQL que põe os bares-vitrine no banco, pra colar no SQL Editor.

Por que existe
--------------
`flask aplicar-demos` é o caminho normal, mas ele precisa da `DATABASE_URL` de
produção na mão de quem roda — e essa URL está marcada como sensível na Vercel
(o `env pull` devolve vazio) e não é revelável no painel. O console do Neon, por
outro lado, já está aberto e autenticado: colar SQL lá não passa credencial por
lugar nenhum.

Como usar
---------
    python3 scripts/sql_dos_vitrines.py > /tmp/vitrines.sql

Abra o arquivo, copie tudo, cole no SQL Editor do Neon (projeto `alerosaas`,
branch `production`, database `neondb`) e rode.

Idempotente: rodar duas vezes não duplica nada. Cada bar é localizado pelo slug;
se já existir, o conteúdo dele é substituído pelo do arquivo (que é a fonte da
verdade da vitrine). Bar que não é vitrine nunca é tocado — o `WHERE` casa por
slug e por `demo_fonte`, então um erro de digitação não alcança bar de cliente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')
FONTE = 'vitrine-da-campanha'

VITRINES = ('bar-do-ze', 'vitrine-tap-cinco', 'vitrine-armazem-1948',
            'vitrine-fogo-e-sal', 'vitrine-sala-vermelha', 'vitrine-brasa-velha')

# Colunas de SiteConfig que a vitrine preenche. Fora daqui o YAML não manda.
CAMPOS_SITE = ('nome', 'hero_linha1', 'hero_linha2', 'kicker', 'tagline',
               'subline', 'whatsapp', 'telefone_exibicao', 'endereco',
               'cidade_uf', 'horario', 'descritor', 'tema', 'vibe',
               'nota_google', 'qtd_avaliacoes')


def txt(valor):
    """Literal SQL. Aspas simples dobradas — é o escape do Postgres, e sem ele
    um nome com apóstrofo (Grainne's) fecharia a string no meio."""
    if valor is None or valor == '':
        return 'NULL'
    if isinstance(valor, bool):
        return 'TRUE' if valor else 'FALSE'
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def preco(valor):
    """"38,00" -> 38.00. Vírgula decimal não é número em SQL."""
    if not valor:
        return 'NULL'
    return str(valor).replace('.', '').replace(',', '.')


def emitir(slug):
    caminho = os.path.join(DIR_LEADS, f'{slug}.yml')
    d = yaml.safe_load(open(caminho, encoding='utf-8')) or {}
    site = d.get('site') or {}
    nome = d.get('nome') or slug

    L = [f'\n-- ================= {nome} ({slug})']
    # O bar. Sem ON CONFLICT no slug porque nem todo banco tem o índice único
    # com o mesmo nome; o INSERT ... WHERE NOT EXISTS funciona em qualquer um.
    L.append(f"""INSERT INTO restaurante (nome, slug, tipo_conta, demo_fonte, ativo,
                         subscription_tier, subscription_status)
SELECT {txt(nome)}, {txt(slug)}, 'demo', {txt(FONTE)}, TRUE, 'free', 'free'
WHERE NOT EXISTS (SELECT 1 FROM restaurante WHERE slug = {txt(slug)});""")

    # Marca como vitrine o bar que já existia (o `bar-do-ze` nasceu como demo de
    # teste, antes desta lista). Sem isto os DELETE abaixo — que filtram por
    # `demo_fonte` — não o alcançam, e rodar o script duas vezes duplicaria o
    # cardápio inteiro dele. O `tipo_conta = 'demo'` é a trava: cliente com slug
    # coincidente nunca é reetiquetado.
    L.append(f"""UPDATE restaurante SET demo_fonte = {txt(FONTE)}
 WHERE slug = {txt(slug)} AND tipo_conta = 'demo' AND demo_fonte IS DISTINCT FROM {txt(FONTE)};""")

    campos = [(c, site.get(c)) for c in CAMPOS_SITE]
    campos = [(c, v) for c, v in campos if v not in (None, '')]
    if not any(c == 'nome' for c, _ in campos):
        campos.insert(0, ('nome', nome))
    colunas = ', '.join(c for c, _ in campos)
    valores = ', '.join(txt(v) for _, v in campos)
    atualiza = ', '.join(f'{c} = {txt(v)}' for c, v in campos)

    L.append(f"""INSERT INTO site_config (restaurant_id, {colunas})
SELECT r.id, {valores} FROM restaurante r WHERE r.slug = {txt(slug)}
  AND NOT EXISTS (SELECT 1 FROM site_config s WHERE s.restaurant_id = r.id);
UPDATE site_config SET {atualiza}
 WHERE restaurant_id = (SELECT id FROM restaurante WHERE slug = {txt(slug)});""")

    # Conteúdo: apaga e regrava. O arquivo é a fonte da verdade da vitrine, e
    # sem o DELETE uma segunda execução duplicaria o cardápio inteiro.
    for tabela in ('site_dish', 'site_review', 'site_team', 'site_gallery'):
        L.append(f"DELETE FROM {tabela} WHERE restaurant_id = "
                 f"(SELECT id FROM restaurante WHERE slug = {txt(slug)} "
                 f"AND demo_fonte = {txt(FONTE)});")

    for i, p in enumerate(d.get('cardapio') or []):
        L.append(f"""INSERT INTO site_dish (restaurant_id, nome, descricao, preco, tag, destaque, ordem, ativo)
SELECT id, {txt(p.get('nome'))}, {txt(p.get('descricao'))}, {preco(p.get('preco'))},
       {txt(p.get('tag'))}, {txt(bool(p.get('destaque')))}, {i}, TRUE
  FROM restaurante WHERE slug = {txt(slug)};""")

    for i, a in enumerate(d.get('avaliacoes') or []):
        L.append(f"""INSERT INTO site_review (restaurant_id, autor, texto, estrelas, ordem, ativo)
SELECT id, {txt(a.get('autor'))}, {txt(a.get('texto'))}, {a.get('estrelas') or 5}, {i}, TRUE
  FROM restaurante WHERE slug = {txt(slug)};""")

    for i, e in enumerate(d.get('equipe') or []):
        L.append(f"""INSERT INTO site_team (restaurant_id, nome, papel, emoji, ordem, ativo)
SELECT id, {txt(e.get('nome'))}, {txt(e.get('papel'))}, {txt(e.get('emoji'))}, {i}, TRUE
  FROM restaurante WHERE slug = {txt(slug)};""")

    return '\n'.join(L)


if __name__ == '__main__':
    print('-- Bares-vitrine da campanha. Gerado por scripts/sql_dos_vitrines.py')
    print('-- Idempotente: pode rodar de novo sem duplicar.')
    print('BEGIN;')
    for slug in VITRINES:
        print(emitir(slug))
    print('\nCOMMIT;')
    print('\n-- Conferência: 6 linhas, cada uma com 8 pratos.')
    print("SELECT r.slug, r.nome, count(d.id) AS pratos")
    print("  FROM restaurante r LEFT JOIN site_dish d ON d.restaurant_id = r.id")
    print(f" WHERE r.demo_fonte = {txt(FONTE)}")
    print(" GROUP BY r.slug, r.nome ORDER BY r.slug;")
