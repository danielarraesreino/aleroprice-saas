from app import create_app, db
from flask_migrate import upgrade

import os

# Detect Vercel environment
config_name = 'production' if os.environ.get('VERCEL') or os.environ.get('RAILWAY_ENVIRONMENT') else 'default'
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
