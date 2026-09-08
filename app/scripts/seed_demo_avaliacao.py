"""Cria o tenant 'demo-avaliacao' com catálogo + 90 dias de movimento + login fixo.

Serve para avaliação: um tenant completo (plano Pro), com catálogo de bar,
90 dias de vendas/estoque/NF-e/desperdício e um login fixo de demonstração.

Uso:
    python scripts/seed_demo_avaliacao.py

Idempotente: roda de novo sem duplicar; recria o movimento com --reset.
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario

SLUG = 'demo-avaliacao'
NOME = 'Demo Avaliação'
CNPJ = '00000000000191'
EMAIL = 'demo@alero.com.br'
SENHA = 'Alero#Demo2026'
DIAS = 90


def seed():
    db.create_all()  # cria o schema se o banco estiver vazio (dev/primeira execução)
    rest = Restaurante.query.filter_by(slug=SLUG).first()
    if rest is None:
        rest = Restaurante(
            nome=NOME,
            cnpj=CNPJ,
            slug=SLUG,
            tipo_conta='cliente',
            subscription_tier='pro',
            subscription_status='active',
            plano_ate=date.today() + timedelta(days=365),
            ativo=True,
        )
        db.session.add(rest)
        db.session.commit()
        print(f'tenant criado: {rest.nome} (id={rest.id}, slug={rest.slug})')
    else:
        # garante plano Pro + ativo, mesmo em re-execução
        rest.nome = NOME
        rest.tipo_conta = 'cliente'
        rest.subscription_tier = 'pro'
        rest.subscription_status = 'active'
        rest.plano_ate = date.today() + timedelta(days=365)
        rest.ativo = True
        db.session.commit()
        print(f'tenant já existia: {rest.nome} (id={rest.id}) — plano pro garantido')

    # Usuário admin com login fixo
    user = Usuario.query.filter_by(email=EMAIL).first()
    if user is None:
        user = Usuario(
            nome='Avaliador Demo',
            email=EMAIL,
            senha=SENHA,
            tipo='admin',
            restaurant_id=rest.id,
        )
        db.session.add(user)
        db.session.commit()
        print(f'usuário admin criado: {EMAIL}')
    else:
        user.restaurant_id = rest.id
        user.tipo = 'admin'
        user.ativo = True
        user.set_senha(SENHA)
        db.session.commit()
        print(f'usuário admin atualizado: {EMAIL}')

    # Catálogo (fornecedores, insumos, pratos, fichas, cardápio, promoções)
    from app.scripts.seed_bardavila import seed as seed_catalogo
    seed_catalogo(SLUG, 1.0)

    # 90 dias de movimento (vendas, consumo de ficha, compras NF-e, desperdício)
    from app.scripts.seed_movimento import seed as seed_movimento
    seed_movimento(SLUG, DIAS, True)

    print('\n=== DEMO PRONTA ===')
    print(f'  Tenant      : {NOME} (slug={SLUG})')
    print(f'  Painel      : /app  (login abaixo)')
    print(f'  Site público: /bar/{SLUG}')
    print(f'  Login       : {EMAIL}')
    print(f'  Senha       : {SENHA}')
    print(f'  Movimento   : {DIAS} dias')
    return 0


if __name__ == '__main__':
    app = create_app(os.environ.get('APP_ENV', 'development'))
    with app.app_context():
        sys.exit(seed())
