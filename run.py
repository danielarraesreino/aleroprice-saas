from app import create_app, db
from flask_migrate import upgrade

import os

# Import INCONDICIONAL e no topo: o builder da Vercel traça os imports rodando o
# entrypoint no build (quando SEED_TOKEN não existe), então um import dentro de
# `if _seed_token:` nunca é empacotado. Aqui fora, o tracer sempre o inclui.
# try/except pra não derrubar o cold start se o bundling falhar mesmo assim.
try:
    from app.scripts import (
        seed_bardavila as _seed_vila,
        seed_bardoze as _seed_ze,
        seed_movimento as _seed_mov,
        seed_site_bardavila as _seed_site_vila,
    )
    _seed_import_error = None
except Exception as _imp_err:  # pragma: no cover
    _seed_vila = _seed_ze = _seed_mov = _seed_site_vila = None
    _seed_import_error = repr(_imp_err)

# Seleção de configuração.
# Prioridade: APP_ENV explícito > detecção de plataforma (Vercel/Railway) > default (dev).
# Em qualquer host de container, basta setar APP_ENV=production.
_app_env = os.environ.get('APP_ENV')
if _app_env:
    config_name = _app_env
elif os.environ.get('VERCEL') or os.environ.get('RAILWAY_ENVIRONMENT'):
    config_name = 'production'
else:
    config_name = 'default'
app = create_app(config_name)

if __name__ == '__main__':
    with app.app_context():
        upgrade() # Auto-migrate database
    app.run(debug=True, host='0.0.0.0', port=5000)

# Vercel entry point
# This part is executed by Vercel's WSGI server
# We also want to ensure migrations run here
with app.app_context():
    try:
        # Emergency fix: Create tables if they don't exist
        # This is needed because initial migration seems to assume tables exist
        db.create_all()
        print("db.create_all() executed successfully.")
        
        try:
            # upgrade()
            print("Database migration skipped (using create_all).")
        except Exception as e:
            print(f"Migration step failed (might conflict with create_all, but tables should be there): {e}")

        # Debug: List tables to confirm migration worked
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        print(f"Tables in DB: {inspector.get_table_names()}")
    except Exception as e:
        print(f"Database initialization failed: {e}")

# Ferramentas destrutivas (/admin-dev/db, /seed-vegan, /reset-db) vivem em um
# blueprint isolado, que só é registrado fora de produção, com
# ENABLE_ADMIN_ENDPOINTS=1 e ADMIN_DEV_TOKEN definidos. Habilitar em produção
# levanta erro no boot em vez de passar despercebido — ver app/routes/admin_dev.
from app.routes.admin_dev import registrar as _registrar_admin_dev

with app.app_context():
    _registrar_admin_dev(app, config_name)


# ---------------------------------------------------------------------------
# Bootstrap das demos (Bar da Vila + Bar do Zé) em produção.
#
# Existe porque a DATABASE_URL de produção não sai do Vercel: a única forma de
# semear o Postgres é rodando DENTRO do runtime, onde a string já está injetada.
#
# Fica invisível (404) enquanto SEED_TOKEN não estiver setada. Para usar: cria a
# env var SEED_TOKEN no Vercel, faz deploy, chama a URL com o token, e DEPOIS
# remove a env var (o endpoint some de novo). Token comparado em tempo constante.
#
#   /bootstrap-demo?token=SEGREDO&action=status   -> só leitura, diz o estado
#   /bootstrap-demo?token=SEGREDO&action=seed      -> escreve (idempotente, sem drop)
#
# Nunca dropa nada. Os seeds são idempotentes; o movimento é regerado só na
# janela dos tenants de demo (bar-da-vila / bar-do-ze), sem tocar em mais nada.
# ---------------------------------------------------------------------------
_seed_token = os.environ.get('SEED_TOKEN')

if _seed_token:
    import hmac
    from flask import request, abort, jsonify

    def _contagens(tem_slug):
        # Defensivo: se a coluna slug ainda não existe (banco divergido), não dá
        # pra achar por slug — lista todos os tenants por id/nome.
        from sqlalchemy import text
        db.session.rollback()
        conta = lambda tab, rid: db.session.execute(
            text(f'SELECT count(*) FROM {tab} WHERE restaurant_id = :r'), {'r': rid}
        ).scalar()
        cols = 'id, nome, slug, dominio' if tem_slug else 'id, nome'
        out = []
        for row in db.session.execute(text(f'SELECT {cols} FROM restaurante ORDER BY id')):
            rid = row[0]
            info = {'id': rid, 'nome': row[1]}
            if tem_slug:
                info['slug'] = row[2]
                info['dominio'] = row[3]
            info.update({
                'pratos': conta('pratos', rid), 'produtos': conta('produto', rid),
                'vendas': conta('historico_vendas', rid), 'notas': conta('nf_nota', rid),
            })
            # Plano efetivo: sem isto não dá pra saber, olhando de fora, se um
            # cliente foi rebaixado sem querer por uma mudança de paywall.
            try:
                from app.models.modelo_restaurante import Restaurante
                from app.utils.planos import plano_efetivo
                rest = Restaurante.query.get(rid)
                info['plano'] = plano_efetivo(rest)
                info['tier'] = rest.subscription_tier
                info['tipo_conta'] = rest.tipo_conta
            except Exception as e:
                info['plano'] = f'? ({type(e).__name__})'
            out.append(info)
        return out

    @app.route('/bootstrap-demo', strict_slashes=False)
    def bootstrap_demo():
        if not hmac.compare_digest(request.args.get('token', ''), _seed_token):
            abort(404)  # token errado = endpoint não existe

        acao = request.args.get('action', 'status')
        from sqlalchemy import inspect, text

        if acao == 'status':
            insp = inspect(db.engine)
            cols_rest = {c['name'] for c in insp.get_columns('restaurante')} \
                if insp.has_table('restaurante') else set()
            try:
                ver = db.session.execute(text('SELECT version_num FROM alembic_version')).scalar()
            except Exception:
                db.session.rollback()
                ver = None
            tem_slug = 'slug' in cols_rest
            return jsonify({
                'mode': 'status',
                'alembic_version': ver,
                'tem_coluna_slug': tem_slug,
                'tem_coluna_dominio': 'dominio' in cols_rest,
                'total_tenants': db.session.execute(
                    text('SELECT count(*) FROM restaurante')).scalar(),
                'tabelas': sorted(insp.get_table_names()),
                'tenants': _contagens(tem_slug),
            })

        def _sincronizar_schema():
            """Alinha o banco ao modelo. Prod foi construído por create_all sobre
            um modelo antigo, então tabelas velhas (restaurante, promocao,
            site_config...) não têm as colunas adicionadas depois. Ao invés de
            caçar coluna a coluna, reflete o banco e adiciona TODA coluna que
            estiver faltando.

            Também **alarga** coluna de texto que ficou curta (ex.: hero_foto
            nasceu VARCHAR(120) para caminho em static e passou a receber URL
            de Vercel Blob). Só alarga, nunca estreita: aumentar o limite não
            pode truncar dado existente, diminuir pode.

            Idempotente e não destrutivo."""
            registro = []
            db.create_all()  # cria tabelas que faltam inteiras
            insp_local = inspect(db.engine)
            add_col = db.engine.dialect.type_compiler.process
            n = alargadas = 0
            for tabela in db.metadata.sorted_tables:
                if not insp_local.has_table(tabela.name):
                    continue
                no_banco = {c['name']: c for c in insp_local.get_columns(tabela.name)}
                for coluna in tabela.columns:
                    atual = no_banco.get(coluna.name)
                    if atual is None:
                        # Sempre NULL (sem default/constraint): seguro pra dado que
                        # já está na tabela; os seeds preenchem o valor certo.
                        tipo = add_col(coluna.type)
                        try:
                            db.session.execute(text(
                                f'ALTER TABLE "{tabela.name}" ADD COLUMN "{coluna.name}" {tipo}'))
                            db.session.commit()
                            n += 1
                            registro.append(f'  + {tabela.name}.{coluna.name} {tipo}')
                        except Exception as ddl_e:
                            db.session.rollback()
                            registro.append(f'  ! {tabela.name}.{coluna.name}: {type(ddl_e).__name__}')
                        continue

                    quero = getattr(coluna.type, 'length', None)
                    tenho = getattr(atual.get('type'), 'length', None)
                    if not (isinstance(quero, int) and isinstance(tenho, int) and quero > tenho):
                        continue
                    tipo = add_col(coluna.type)
                    try:
                        # SQLite não impõe largura de VARCHAR e não tem ALTER
                        # COLUMN TYPE — lá o modelo novo já vale sem DDL.
                        if db.engine.dialect.name != 'sqlite':
                            db.session.execute(text(
                                f'ALTER TABLE "{tabela.name}" '
                                f'ALTER COLUMN "{coluna.name}" TYPE {tipo}'))
                            db.session.commit()
                        alargadas += 1
                        registro.append(
                            f'  ~ {tabela.name}.{coluna.name} {tenho} -> {quero}')
                    except Exception as ddl_e:
                        db.session.rollback()
                        registro.append(f'  ! {tabela.name}.{coluna.name}: {type(ddl_e).__name__}')
            registro.append(
                f'schema: {n} colunas adicionadas, {alargadas} alargadas '
                f'(reflexão model vs banco)')
            return registro

        if acao == 'migrate':
            # Alembic sob demanda. Não roda no boot de propósito: em serverless,
            # N cold starts simultâneos = N `upgrade` na mesma alembic_version.
            # O advisory lock do Postgres serializa isso de forma nativa.
            from flask_migrate import stamp as alembic_stamp, upgrade as alembic_upgrade

            e_postgres = db.engine.dialect.name == 'postgresql'
            TRAVA = 728145  # constante arbitrária, só precisa ser estável
            if e_postgres:
                obteve = db.session.execute(
                    text('SELECT pg_try_advisory_lock(:k)'), {'k': TRAVA}).scalar()
                if not obteve:
                    return jsonify({'mode': 'migrate',
                                    'erro': 'outra migration em andamento'}), 409
            def _versao_atual():
                """None quando o Alembic nunca rodou aqui — a tabela pode nem
                existir, e consultá-la aborta a transação no Postgres."""
                try:
                    v = db.session.execute(
                        text('SELECT version_num FROM alembic_version')).scalar()
                    return v
                except Exception:
                    db.session.rollback()
                    return None

            try:
                versao_antes = _versao_atual()
                log_mig = [f'version_num antes: {versao_antes}']

                # Baseline: prod nasceu de create_all(), então o schema já
                # equivale ao head da cadeia — mas alembic_version está vazia.
                # Stampar declara isso e dá de onde partir, sem reexecutar
                # migrations antigas contra um banco que já as tem.
                base = request.args.get('stamp')
                if versao_antes is None and base:
                    alembic_stamp(revision=base)
                    log_mig.append(f'stamp {base}')

                alembic_upgrade()
                log_mig.append(f'version_num depois: {_versao_atual()}')
                return jsonify({'mode': 'migrate', 'log': log_mig})
            except Exception as e:
                db.session.rollback()
                return jsonify({'mode': 'migrate',
                                'erro': f'{type(e).__name__}: {e}'}), 500
            finally:
                if e_postgres:
                    db.session.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': TRAVA})
                    db.session.commit()

        if acao == 'constraints':
            # Leitura pura. Prod nasceu de create_all() sobre modelos antigos,
            # então um unique que existe no SQLite de dev pode não existir aqui.
            # Sem olhar, qualquer migration de constraint é chute.
            insp = inspect(db.engine)
            alvo = ['pratos', 'produto', 'categoria_desperdicio', 'usuario',
                    'restaurante', 'fornecedor', 'nf_nota']
            out = {}
            for tabela in alvo:
                if not insp.has_table(tabela):
                    out[tabela] = 'tabela não existe'
                    continue
                out[tabela] = {
                    'uniques': [
                        {'nome': u.get('name'), 'colunas': u.get('column_names')}
                        for u in insp.get_unique_constraints(tabela)
                    ],
                    'indices_unicos': [
                        {'nome': i.get('name'), 'colunas': i.get('column_names')}
                        for i in insp.get_indexes(tabela) if i.get('unique')
                    ],
                }
            # Duplicatas que a mudança liberaria. Se já houver, o unique não
            # existe em prod e metade do problema evapora.
            dups = {}
            for tabela, coluna in (('pratos', 'nome'), ('produto', 'codigo'),
                                   ('categoria_desperdicio', 'nome')):
                try:
                    linhas = db.session.execute(text(
                        f'SELECT {coluna}, count(*) c FROM {tabela} '
                        f'GROUP BY {coluna} HAVING count(*) > 1 LIMIT 5')).fetchall()
                    dups[f'{tabela}.{coluna}'] = [list(r) for r in linhas]
                except Exception as e:
                    db.session.rollback()
                    dups[f'{tabela}.{coluna}'] = f'erro: {type(e).__name__}'
            return jsonify({'mode': 'constraints', 'dialeto': db.engine.dialect.name,
                            'tabelas': out, 'duplicatas': dups})

        if acao == 'schema':
            # Só alinha o schema. Separado de 'seed' porque seed também insere
            # dados de demonstração, que colidem quando já existem — e aí um
            # ajuste de coluna ficava refém de um seed que falha.
            return jsonify({'mode': 'schema', 'log': _sincronizar_schema()})

        if acao == 'demos':
            # Publica as prévias comerciais de app/data/leads/*.yml.
            # Idempotente: reaplicar atualiza, não duplica — importa porque esta
            # rota pode dar timeout no meio e ser chamada de novo.
            from app.utils.demos import aplicar_todos
            log_schema = _sincronizar_schema()   # colunas novas antes de gravar
            resultado = aplicar_todos(slug=request.args.get('slug'))
            return jsonify({
                'mode': 'demos',
                'aplicados': len(resultado['ok']),
                'falhas': len(resultado['erros']),
                'schema': log_schema[-1],
                **resultado,
            }), (200 if not resultado['erros'] else 207)

        if acao != 'seed':
            return jsonify(
                {'error': "action deve ser 'status', 'schema', 'seed' ou 'demos'"}), 400

        log = _sincronizar_schema()

        from app.models.modelo_restaurante import Restaurante
        from app.models.usuario import Usuario
        from app.utils.site_router import slug_unico

        # Demos com acesso total: os relatórios avançados são @pro_required, e um
        # bar de demonstração precisa mostrar tudo.
        def _tornar_pro(rest):
            rest.subscription_tier = 'pro'
            rest.subscription_status = 'active'

        # 2. Bar da Vila. Em produção o tenant já existe (o site é dele): só
        #    garante slug/domínio/nome. Se o banco estiver vazio, cria do zero.
        vila = Restaurante.query.filter_by(slug='bar-da-vila').first()
        if vila is None:
            vila = Restaurante.query.order_by(Restaurante.id).first()
            if vila is not None:
                vila.slug = 'bar-da-vila'
                if not vila.dominio:
                    vila.dominio = 'bardavila.bar'
                if vila.nome in (None, 'Restaurante Teste'):
                    vila.nome = 'Bar da Vila'
                db.session.commit()
                log.append(f'bar-da-vila: adotado tenant existente id={vila.id}')
            else:
                vila = Restaurante(nome='Bar da Vila', slug='bar-da-vila',
                                   dominio='bardavila.bar')
                db.session.add(vila)
                db.session.commit()
                log.append(f'bar-da-vila: tenant criado id={vila.id}')
        _tornar_pro(vila)
        db.session.commit()
        if Usuario.query.filter_by(email='admin@teste.com').first() is None:
            db.session.add(Usuario(nome='Gustavo', email='admin@teste.com',
                                   senha='bardavila123', tipo='admin',
                                   restaurant_id=vila.id))
            db.session.commit()
            log.append('bar-da-vila: admin admin@teste.com criado')

        # 3. Bar do Zé: cria tenant + admin se não existir (não há CLI em prod).
        ze = Restaurante.query.filter_by(slug='bar-do-ze').first()
        if ze is None:
            ze = Restaurante(nome='Bar do Zé', slug=slug_unico('Bar do Zé'))
            db.session.add(ze)
            db.session.commit()
            log.append(f'bar-do-ze: tenant criado id={ze.id}')
        _tornar_pro(ze)
        db.session.commit()
        if Usuario.query.filter_by(email='ze@bardoze.com').first() is None:
            db.session.add(Usuario(nome='José', email='ze@bardoze.com',
                                   senha='bardoze123', tipo='admin', restaurant_id=ze.id))
            db.session.commit()
            log.append('bar-do-ze: admin ze@bardoze.com criado')

        # 4. Catálogo + movimento dos dois. Seeds idempotentes; movimento com
        #    reset só limpa a janela do próprio tenant.
        if _seed_vila is None:
            return jsonify({'log': log,
                            'error': f'seeds não empacotados: {_seed_import_error}'}), 500

        # Granularidade: o movimento (centenas de inserts) pode estourar o tempo
        # de UMA função serverless contra o Postgres remoto. `?parte=` deixa
        # rodar em pedaços que cabem no limite:
        #   parte=base         -> só schema + tenants + catálogo (rápido)
        #   parte=mov&slug=X   -> só o movimento de um bar
        #   (sem parte)        -> tudo (bom pra banco local/rápido)
        parte = request.args.get('parte', 'tudo')
        dias = int(request.args.get('dias', 30))

        if parte in ('tudo', 'base', 'site'):
            # Conteúdo do site público do Bar da Vila (pratos, reviews, equipe,
            # galeria). A migration que faz isso nunca rodou em prod, então sem
            # este passo a landing fica sem conteúdo.
            _seed_site_vila.seed('bar-da-vila')
            log.append('bar-da-vila: conteúdo do site ok')

        if parte in ('tudo', 'base'):
            _seed_vila.seed('bar-da-vila')
            log.append('bar-da-vila: catálogo ok')
            _seed_ze.seed()
            log.append('bar-do-ze: catálogo ok')

        if parte == 'mov':
            slug = request.args.get('slug')
            if slug not in ('bar-da-vila', 'bar-do-ze'):
                return jsonify({'log': log,
                                'error': "mov exige ?slug=bar-da-vila|bar-do-ze"}), 400
            _seed_mov.seed(slug, dias, True)
            log.append(f'{slug}: movimento de {dias} dias gerado')
        elif parte == 'tudo':
            _seed_mov.seed('bar-da-vila', dias, True)
            _seed_mov.seed('bar-do-ze', dias, True)
            log.append(f'movimento: {dias} dias gerados para os dois')

        return jsonify({'mode': 'seed', 'parte': parte, 'log': log,
                        'tenants': _contagens(True)})
