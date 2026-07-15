from app import create_app, db
from flask_migrate import upgrade

import os

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

# Dangerous admin/debug endpoints (/debug-db, /seed-vegan, /reset-db).
# These are only registered when ENABLE_ADMIN_ENDPOINTS=1 is explicitly set,
# and never when running in the Vercel/Railway production environment.
# /reset-db in particular calls db.drop_all() and would wipe all tenant data.
_admin_endpoints_enabled = (
    os.environ.get('ENABLE_ADMIN_ENDPOINTS') == '1'
    and config_name != 'production'
)

if _admin_endpoints_enabled:
    @app.route('/debug-db', strict_slashes=False)
    def debug_db():
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            # Check alembic version
            try:
                version = db.session.execute(text("SELECT * FROM alembic_version")).fetchall()
            except:
                version = "Table alembic_version not found"

            return {
                "status": "online",
                "tables": tables,
                "alembic_version": str(version),
                "db_url_masked": app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if app.config['SQLALCHEMY_DATABASE_URI'] else "None"
            }
        except Exception as e:
            return {"error": str(e)}

    @app.route('/seed-vegan', strict_slashes=False)
    def seed_vegan_route():
        try:
            from app.scripts.seed_vegan import seed_vegan_data
            msg = seed_vegan_data()
            return {
                "status": "success",
                "message": msg,
                "info": "Refresh the Dashboard to see data."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.route('/reset-db', strict_slashes=False)
    def reset_db_route():
        try:
            # Nuclear option: Recreate schema
            db.drop_all()
            db.create_all()
            return {
                "status": "success",
                "message": "Database reset successfully. Schema is now clean.",
                "next_step": "Go to /seed-vegan to populate data."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


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

        if acao != 'seed':
            return jsonify({'error': "action deve ser 'status' ou 'seed'"}), 400

        log = []

        # 1. Schema. Prod foi construído por create_all sobre um modelo antigo,
        #    então tabelas velhas (restaurante, promocao, site_config...) não têm
        #    as colunas adicionadas depois. Ao invés de caçar coluna a coluna,
        #    reflete o banco e adiciona TODA coluna do modelo que estiver
        #    faltando. Idempotente e não destrutivo (só ADD COLUMN).
        db.create_all()  # cria tabelas que faltam inteiras
        insp = inspect(db.engine)
        add_col = db.engine.dialect.type_compiler.process
        n_cols = 0
        for tabela in db.metadata.sorted_tables:
            if not insp.has_table(tabela.name):
                continue
            existentes = {c['name'] for c in insp.get_columns(tabela.name)}
            for coluna in tabela.columns:
                if coluna.name in existentes:
                    continue
                # Adiciona sempre como NULL (sem default/constraint): seguro pra
                # dado que já está na tabela; os seeds preenchem o valor certo.
                tipo = add_col(coluna.type)
                try:
                    db.session.execute(text(
                        f'ALTER TABLE "{tabela.name}" ADD COLUMN "{coluna.name}" {tipo}'))
                    db.session.commit()
                    n_cols += 1
                    log.append(f'  + {tabela.name}.{coluna.name} {tipo}')
                except Exception as ddl_e:
                    db.session.rollback()
                    log.append(f'  ! {tabela.name}.{coluna.name}: {type(ddl_e).__name__}')
        log.append(f'schema: {n_cols} colunas adicionadas (reflexão model vs banco)')

        from app.models.modelo_restaurante import Restaurante
        from app.models.usuario import Usuario
        from app.utils.site_router import slug_unico

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
        if Usuario.query.filter_by(email='ze@bardoze.com').first() is None:
            db.session.add(Usuario(nome='José', email='ze@bardoze.com',
                                   senha='bardoze123', tipo='admin', restaurant_id=ze.id))
            db.session.commit()
            log.append('bar-do-ze: admin ze@bardoze.com criado')

        # 4. Catálogo + movimento dos dois. Seeds idempotentes; movimento com
        #    reset só limpa a janela do próprio tenant.
        # Import lazy: só aqui dentro, nunca no carregamento do módulo — um
        # problema de bundling não pode derrubar o app inteiro no cold start.
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from scripts import seed_bardavila, seed_bardoze, seed_movimento

        seed_bardavila.seed('bar-da-vila')
        log.append('bar-da-vila: catálogo ok')
        seed_bardoze.seed()
        log.append('bar-do-ze: catálogo ok')
        seed_movimento.seed('bar-da-vila', 30, True)
        seed_movimento.seed('bar-do-ze', 30, True)
        log.append('movimento: 30 dias gerados para os dois')

        return jsonify({'mode': 'seed', 'log': log, 'tenants': _contagens(True)})
