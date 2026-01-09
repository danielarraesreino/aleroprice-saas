from app import create_app, db
from sqlalchemy import inspect
import os

app = create_app()
with app.app_context():
    print(f"Metadata Tables: {db.metadata.tables.keys()}")
    inspector = inspect(db.engine)
    print("Inspecting database tables...")
    all_tables = inspector.get_table_names()
    print(f"Tables found: {all_tables}")
    
    for table_name in all_tables:
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        if 'restaurant_id' in columns:
             print(f"  -> restaurant_id FOUND in {table_name}")
        else:
             print(f"  -> restaurant_id MISSING in {table_name}")
