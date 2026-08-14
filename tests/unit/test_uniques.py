"""Nome de prato e código de produto são únicos por bar, não no mundo.

Com um cliente só isso nunca doeu. Com dois, quebra no primeiro dia:
"Caipirinha" existe em toda casa, e `produto.codigo` é EAN — o segundo bar que
importar uma NF-e com o mesmo produto batia no unique global.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.modelo_prato import Prato
from app.models.modelo_produto import Produto
from app.models.modelo_restaurante import Restaurante


@pytest.fixture
def dois_bares(session):
    a = Restaurante(nome='Bar A', slug='bar-a')
    b = Restaurante(nome='Bar B', slug='bar-b')
    session.add_all([a, b])
    session.commit()
    return a, b


def _prato(rid, nome='Caipirinha'):
    return Prato(nome=nome, rendimento=1, unidade_rendimento='un',
                 porcoes_rendimento=1, restaurant_id=rid)


def test_dois_bares_podem_ter_o_mesmo_prato(session, dois_bares):
    a, b = dois_bares
    session.add_all([_prato(a.id), _prato(b.id)])
    session.commit()

    assert Prato.query.filter_by(nome='Caipirinha').count() == 2


def test_prato_repetido_no_mesmo_bar_ainda_falha(session, dois_bares):
    a, _ = dois_bares
    session.add(_prato(a.id))
    session.commit()

    session.add(_prato(a.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_mesmo_ean_em_bares_diferentes(session, dois_bares):
    """O caso que quebrava no import de NF-e."""
    a, b = dois_bares
    for rid in (a.id, b.id):
        session.add(Produto(codigo='7891000100103', nome='Leite',
                            unidade='l', preco_unitario=5, restaurant_id=rid))
    session.commit()

    assert Produto.query.filter_by(codigo='7891000100103').count() == 2


def test_mesmo_ean_no_mesmo_bar_ainda_falha(session, dois_bares):
    a, _ = dois_bares
    session.add(Produto(codigo='7891000100103', nome='Leite', unidade='l',
                        preco_unitario=5, restaurant_id=a.id))
    session.commit()

    session.add(Produto(codigo='7891000100103', nome='Leite outro', unidade='l',
                        preco_unitario=6, restaurant_id=a.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_constraint_declarada_no_modelo():
    """Trava a intenção: se alguém voltar `unique=True`, este teste cai."""
    for Model, coluna, nome in (
        (Prato, 'nome', 'uq_prato_nome_restaurant'),
        (Produto, 'codigo', 'uq_produto_codigo_restaurant'),
    ):
        uniques = {
            c.name: sorted(x.name for x in c.columns)
            for c in Model.__table__.constraints
            if c.__class__.__name__ == 'UniqueConstraint'
        }
        assert uniques.get(nome) == sorted([coluna, 'restaurant_id'])
        assert not Model.__table__.c[coluna].unique, f'{coluna} voltou a ser unique global'


def test_checks_do_modelo_sobreviveram():
    """As UniqueConstraints entraram no mesmo __table_args__ dos CheckConstraints;
    duas atribuições do atributo fariam a segunda apagar a primeira."""
    for Model, esperado in ((Prato, 3), (Produto, 3)):
        checks = [c for c in Model.__table__.constraints
                  if c.__class__.__name__ == 'CheckConstraint']
        assert len(checks) == esperado
