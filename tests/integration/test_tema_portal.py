"""Portal com modo escuro e botão de tema (DESIGN.md, princípio 4; R5)."""


def test_home_e_memoria_tem_modo_escuro_e_botao_de_tema(client, session):
    for url in ('/', '/memoria', '/presentes'):
        html = client.get(url).get_data(as_text=True)
        assert 'class="tema-auto"' in html
        assert "localStorage.getItem('feira-tema-portal')" in html  # aplica antes de pintar
        assert html.count('aria-label="Alternar tema claro ou escuro"') == 2  # topo + gaveta
