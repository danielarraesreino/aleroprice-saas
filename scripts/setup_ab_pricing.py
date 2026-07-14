from app import create_app, db
from app.models.modelo_restaurante import Restaurante
import random

app = create_app('default')

def setup_ab_test():
    with app.app_context():
        print("Starting A/B Pricing Setup...")
        restaurantes = Restaurante.query.all()
        
        count_std = 0
        count_vol = 0
        
        for r in restaurantes:
            # Simple random distribution
            # In a real scenario, could be deterministic based on ID (ID % 2)
            if r.id % 2 == 0:
                strategy = 'volume_based'
                count_vol += 1
            else:
                strategy = 'standard'
                count_std += 1
                
            r.pricing_strategy = strategy
            print(f"Restaurante {r.nome} -> {strategy}")
            
        db.session.commit()
        print(f"SETUP COMPLETE. Standard: {count_std}, Volume: {count_vol}")

if __name__ == '__main__':
    setup_ab_test()
