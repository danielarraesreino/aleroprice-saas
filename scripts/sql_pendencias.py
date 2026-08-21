"""Gera o SQL das pendências de produção, em pedaços que cabem no editor.

As quatro, e por que cada uma importa:

1. **Capas** — as imagens dos 23 bares de Barão estão no repositório e sobem no
   deploy, mas o `hero_foto` de cada `site_config` só existe no YAML local. Sem
   este UPDATE, as prévias em produção continuam abrindo sem foto — que é
   exatamente o que a rodada inteira tentou resolver.

2. **Prazo da prévia** — as 76 estão com `demo_expira_em` nulo. O corte que
   entrou em `site_router._publicavel` só derruba prévia COM data; sem data,
   elas ficam no ar indefinidamente com nome, foto e nota de bar real. Era a
   mitigação combinada: mostrar sem contrato, mas com prazo.

3. **Plano vitalício** — `plano_efetivo` lê `plano_ate` nulo como "sem corte
   conhecido, vale o tier". Bar da Vila e Bar do Zé estão em `pro` com data
   nula: plano pago, de graça, para sempre. O código novo já nasce `free`
   (`converter_demo`), mas quem converteu antes ficou assim.

4. **Modelos** — nenhum lead definia `modelo`, e sem valor o site cai no
   `classico`: 71 em `classico` e 12 nulos, ou seja, os 83 bares servindo a
   mesma página. Os outros cinco modelos existiam e só apareciam com `?modelo=`
   na URL, que só o vendedor usa.

Como usar
---------
    python3 scripts/sql_pendencias.py /caminho/de/saida
    # cola um arquivo por vez no SQL Editor do Neon

Um arquivo por pendência, cada um abaixo de 8 KB — o arquivo único de 38 KB foi
truncado na colagem e devolveu `syntax error at or near "estaurante"`.

Idempotente: rodar duas vezes não muda nada além do que já mudou.
"""
import glob
import os
import re
import sys
from datetime import date, timedelta

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')

# Quantos dias uma prévia fica no ar sem ninguém fechar. 30 é o combinado: dá
# tempo de uma segunda visita e de uma ligação, e não vira permanente.
DIAS_DE_PREVIA = 30


def txt(v):
    if v is None:
        return 'NULL'
    return "'" + str(v).replace("'", "''") + "'"


def capas():
    """UPDATE do hero_foto de quem tem capa em disco."""
    linhas = [
        '-- 1/4 · CAPAS',
        '-- As imagens já subiram no deploy; isto liga cada uma ao seu bar.',
        '--',
        '-- Protege quem tem foto própria: upload do dono vira URL do Vercel Blob',
        '-- (https://…) e nunca é sobrescrito. Caminho local é carga nossa e pode',
        '-- ser recarregado — a primeira versão só gravava onde estava vazio, e',
        '-- nove bares (Bronco Burger entre eles) ficaram sem capa nenhuma.',
        'BEGIN;',
    ]
    n = 0
    for caminho in sorted(glob.glob(os.path.join(DIR_LEADS, '*.yml'))):
        slug = os.path.basename(caminho)[:-4]
        bruto = open(caminho, encoding='utf-8').read()
        if 'NÃO VISITAR' in bruto:
            continue
        d = yaml.safe_load(bruto) or {}
        hero = (d.get('site') or {}).get('hero_foto')
        if not hero:
            continue
        linhas.append(
            f"UPDATE site_config SET hero_foto = {txt(hero)}\n"
            f" WHERE restaurant_id = (SELECT id FROM restaurante WHERE slug = {txt(slug)})\n"
            f"   AND (hero_foto IS NULL OR hero_foto = ''"
            f" OR hero_foto NOT LIKE 'http%');")
        n += 1
    linhas += ['COMMIT;', '',
               '-- Conferência: quantos bares têm capa agora, e quem ficou sem.',
               "SELECT count(*) AS com_capa FROM site_config",
               " WHERE hero_foto IS NOT NULL AND hero_foto <> '';",
               '',
               'SELECT r.slug FROM restaurante r',
               '  LEFT JOIN site_config sc ON sc.restaurant_id = r.id',
               " WHERE coalesce(sc.hero_foto, '') = '' ORDER BY r.slug;"]
    return '\n'.join(linhas), n


def prazo():
    """Dá prazo às prévias que estão sem."""
    ate = date.today() + timedelta(days=DIAS_DE_PREVIA)
    return '\n'.join([
        '-- 2/4 · PRAZO DAS PRÉVIAS',
        '--',
        '-- `demo_expira_em` estava nulo em todas, e o corte em `_publicavel` só',
        '-- derruba prévia COM data. Sem isto elas ficam no ar pra sempre com o',
        '-- nome, a foto e a nota de um bar que não fechou contrato.',
        '--',
        '-- Só prévia (`tipo_conta = demo`). Cliente não tem prazo, e quem já',
        '-- tem data marcada mantém a dele.',
        'BEGIN;',
        f"UPDATE restaurante SET demo_expira_em = DATE {txt(ate.isoformat())}",
        " WHERE tipo_conta = 'demo' AND demo_expira_em IS NULL;",
        'COMMIT;',
        '',
        '-- Conferência: nenhuma prévia sem prazo.',
        "SELECT count(*) AS sem_prazo FROM restaurante",
        " WHERE tipo_conta = 'demo' AND demo_expira_em IS NULL;",
    ]), 1


def planos():
    """Tira o plano pago vitalício de quem nunca pagou."""
    return '\n'.join([
        '-- 3/4 · PLANO VITALÍCIO',
        '--',
        '-- `plano_efetivo` lê `plano_ate` nulo como "sem corte conhecido, vale o',
        '-- tier" — regra que existe pra proteger tenant antigo. Bar da Vila e Bar',
        '-- do Zé ficaram em `pro` com data nula: plano pago, de graça, pra sempre.',
        '--',
        '-- Vira `free`. O acesso de quem está em teste continua vindo de',
        '-- `trial_termina_em`, e quem pagar sobe pelo botão "8 · Recebi" do Modo',
        '-- Campo, que grava tier E data.',
        '--',
        '-- NÃO mexe em quem tem `plano_ate` preenchido: esse pagou.',
        'BEGIN;',
        "UPDATE restaurante SET subscription_tier = 'free'",
        " WHERE subscription_tier IN ('site', 'pro')",
        '   AND plano_ate IS NULL;',
        'COMMIT;',
        '',
        '-- Conferência: ninguém mais com plano pago sem data.',
        'SELECT nome, subscription_tier, plano_ate, trial_termina_em',
        '  FROM restaurante',
        " WHERE subscription_tier IN ('site', 'pro') ORDER BY id;",
    ]), 1


def modelos():
    """Espalha os bares pelos seis modelos.

    Os seis modelos existem, são de verdade diferentes (nenhuma fonte em comum
    entre dois deles, ordens de seção distintas) e ninguém os via: **nenhum lead
    definia `modelo`**, e sem valor o site cai no `classico`. Em produção eram
    71 em `classico` e 12 nulos — ou seja, os 83 bares serviam a mesma página.
    Abrir três prévias seguidas mostrava três vezes o mesmo site.

    `scripts/atribuir_modelos.py` já escolheu o modelo de cada um pelo que o
    próprio lead diz (espeto vai pra `brasa`, chope pra `craft`, palco pra
    `noturno`); isto leva a escolha pro banco.

    Sobrescreve `classico` de propósito: `classico` aqui não é escolha de
    ninguém, é o valor que sobrou de não ter valor. Quem trocou o modelo pelo
    painel gravou outra coisa e não é tocado.
    """
    pares = []
    for caminho in sorted(glob.glob(os.path.join(DIR_LEADS, '*.yml'))):
        slug = os.path.basename(caminho)[:-4]
        bruto = open(caminho, encoding='utf-8').read()
        if 'NÃO VISITAR' in bruto:
            continue
        d = yaml.safe_load(bruto) or {}
        modelo = ((d.get('site') or {}).get('modelo') or '').strip()
        # Quem já vai ficar no `classico` não precisa de UPDATE: é o valor que
        # o banco tem hoje.
        if modelo and modelo != 'classico':
            pares.append((slug, modelo))

    # Um UPDATE ... FROM (VALUES ...) em vez de um UPDATE por bar. Setenta
    # comandos separados davam 15 KB, quase o dobro do tamanho que já truncou
    # numa colagem e devolveu `syntax error at or near "estaurante"`.
    valores = ',\n  '.join(f'({txt(s)}, {txt(m)})' for s, m in pares)
    return '\n'.join([
        '-- 4/4 · OS SEIS MODELOS',
        '-- Sem isto, os 83 bares continuam servindo a mesma página.',
        '--',
        '-- Sobrescreve `classico` de propósito: ali `classico` não é escolha de',
        '-- ninguém, é o que sobrou de não ter valor. Quem trocou o modelo pelo',
        '-- painel gravou outra coisa e não é tocado.',
        'BEGIN;',
        'UPDATE site_config SET modelo = v.modelo',
        f'  FROM (VALUES\n  {valores}\n  ) AS v(slug, modelo)',
        ' WHERE site_config.restaurant_id ='
        ' (SELECT id FROM restaurante WHERE slug = v.slug)',
        "   AND (site_config.modelo IS NULL OR site_config.modelo = ''"
        " OR site_config.modelo = 'classico');",
        'COMMIT;',
        '',
        '-- Conferência: a campanha tem que aparecer espalhada, não num modelo só.',
        "SELECT coalesce(modelo, '(nulo)') AS modelo, count(*)",
        '  FROM site_config GROUP BY 1 ORDER BY 2 DESC;',
    ]), len(pares)


def coluna_do_selo():
    """A coluna do selo de apoio ao Caminhos, ANTES do deploy que a lê.

    Esta ordem não é preferência: já derrubou o site do cliente pagante nesta
    mesma base. Subiu-se código que lia `site_dish.preco` antes da coluna
    existir e a produção respondeu 500 até o rollback. Coluna nova entra no
    banco primeiro, deploy depois — sempre.

    `IF NOT EXISTS` porque rodar duas vezes tem que ser inofensivo, e
    `DEFAULT false` porque o selo nasce desligado: é declaração pública em nome
    do bar, e ninguém declara apoio por ele.
    """
    return '\n'.join([
        '-- 5/5 · COLUNA DO SELO (rodar ANTES do deploy)',
        '--',
        '-- Sem esta coluna, o código novo quebra toda página que lê SiteConfig',
        '-- — o que inclui o site de todo cliente pagante.',
        'ALTER TABLE site_config',
        '  ADD COLUMN IF NOT EXISTS apoia_caminhos BOOLEAN DEFAULT false;',
        '',
        '-- Conferência: a coluna existe e ninguém está com o selo ligado ainda.',
        "SELECT count(*) AS total,",
        "       count(*) FILTER (WHERE apoia_caminhos) AS com_selo",
        '  FROM site_config;',
    ]), 1


if __name__ == '__main__':
    destino = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(destino, exist_ok=True)
    for nome, gera in (('1-capas', capas), ('2-prazo-das-previas', prazo),
                       ('3-plano-vitalicio', planos), ('4-modelos', modelos),
                       ('5-coluna-do-selo', coluna_do_selo)):
        corpo, n = gera()
        caminho = os.path.join(destino, f'{nome}.sql')
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(corpo + '\n')
        print(f'  {caminho}  ({len(corpo) // 1024 + 1} KB, {n} comando(s))')
