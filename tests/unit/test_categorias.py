"""Categorias de produto: sugerir e reconhecer, sem regravar o que o expositor escreveu."""
import pytest

from app.utils import categorias


@pytest.mark.parametrize('texto, sub', [
    ('Geleias', 'geleias-molhos-e-conservas'),
    ('geléia de jabuticaba', 'geleias-molhos-e-conservas'),
    ('Pão de fermentação natural', 'paes-e-fermentados'),
    ('Kokedama', 'terrarios-e-kokedamas'),
    ('Amigurumi', 'croche-trico-e-amigurumi'),
    ('Brincos de madeira', 'bijuteria-autoral'),   # o núcleo abre a frase
    ('Luminárias de madeira', 'madeira'),
    ('Sabonetes', 'saboaria-e-cosmeticos'),
    ('Empadas', 'salgados-e-lanches'),
    ('Mel', 'cafes-mel-e-emporio'),
    ('Madeira, resina e vidro', 'materiais-mistos'),  # nome canônico vence a palavra
])
def test_reconhece_o_que_o_expositor_escreve(texto, sub):
    assert categorias.subcategoria_de(texto)[1] == sub


@pytest.mark.parametrize('texto', ['Tarô', 'Outros', '', None, 'Melancia'])
def test_nao_inventa_categoria(texto):
    assert categorias.subcategoria_de(texto) is None


def test_todo_nome_da_lista_volta_para_ele_mesmo():
    for cat, sub, nome in categorias.SUBCATEGORIAS:
        assert categorias.subcategoria_de(nome) == (cat, sub, nome)


def test_slugs_unicos_e_categorias_iguais_as_da_feira():
    from app.utils.feira import CATEGORIAS_DA_FEIRA
    subs = [sub for _, sub, _ in categorias.SUBCATEGORIAS]
    assert len(subs) == len(set(subs))
    assert {c for c, _, _ in categorias.TAXONOMIA} == {c for c, _, _ in CATEGORIAS_DA_FEIRA}


def test_opcoes_poem_as_do_expositor_primeiro_e_sem_repetir():
    ops = categorias.opcoes(['Geleias', 'Cerâmica'])
    assert ops[:2] == ['Geleias', 'Cerâmica']
    assert sum(1 for o in ops if o.lower().startswith('cerâm')) == 1


def test_canonizar_unifica_grafia_mas_aceita_novo():
    conhecidas = ['Geleias', 'Doces e confeitaria']
    assert categorias.canonizar('  geleias ', conhecidas) == 'Geleias'
    assert categorias.canonizar('DOCES E CONFEITARIA', conhecidas) == 'Doces e confeitaria'
    assert categorias.canonizar('Licores  da casa', conhecidas) == 'Licores da casa'
    assert categorias.canonizar('   ', conhecidas) is None
