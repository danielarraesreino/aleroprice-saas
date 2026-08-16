"""Gera o SQL das três pendências de produção, em pedaços que cabem no editor.

As três, e por que cada uma importa:

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
        '-- 1/3 · CAPAS',
        '-- As imagens já subiram no deploy; isto liga cada uma ao seu bar.',
        '-- Só toca em quem ainda não tem capa: foto que o dono trocou não é',
        '-- sobrescrita por esta carga.',
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
            f"   AND (hero_foto IS NULL OR hero_foto = '');")
        n += 1
    linhas += ['COMMIT;', '',
               '-- Conferência: quantos bares têm capa agora.',
               "SELECT count(*) AS com_capa FROM site_config",
               " WHERE hero_foto IS NOT NULL AND hero_foto <> '';"]
    return '\n'.join(linhas), n


def prazo():
    """Dá prazo às prévias que estão sem."""
    ate = date.today() + timedelta(days=DIAS_DE_PREVIA)
    return '\n'.join([
        '-- 2/3 · PRAZO DAS PRÉVIAS',
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
        '-- 3/3 · PLANO VITALÍCIO',
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


if __name__ == '__main__':
    destino = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(destino, exist_ok=True)
    for nome, gera in (('1-capas', capas), ('2-prazo-das-previas', prazo),
                       ('3-plano-vitalicio', planos)):
        corpo, n = gera()
        caminho = os.path.join(destino, f'{nome}.sql')
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(corpo + '\n')
        print(f'  {caminho}  ({len(corpo) // 1024 + 1} KB, {n} comando(s))')
