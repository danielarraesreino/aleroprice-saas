"""Números do site de cada cliente: o que prova que o plano vale o que custa.

A página pública sai da borda da Vercel (`_na_borda`), então o servidor não vê
cada visita. Quem conta é o navegador: `site/_metricas.html` manda um beacon
para `public.metrica` ao abrir a página e ao tocar em WhatsApp, mapa, Instagram
ou telefone.
"""
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.modelo_metrica import MetricaDiaria
from app.utils.feira import hoje_br

# Ordem = ordem em que aparecem na tela e no relatório.
TIPOS = {
    'visita': 'visitas no seu site',
    'encomenda': 'pedidos de produto pelo WhatsApp',
    'whatsapp': 'cliques para falar no WhatsApp',
    'mapa': 'pessoas abriram o mapa para chegar',
    'instagram': 'foram para o seu Instagram',
    'telefone': 'tocaram para ligar',
}

MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


def registrar(restaurant_id, tipo, dia=None):
    """Soma 1 no contador do dia. Best-effort: nunca derruba quem chamou."""
    if tipo not in TIPOS:
        return False
    dia = dia or hoje_br()
    filtro = dict(restaurant_id=restaurant_id, dia=dia, tipo=tipo)
    try:
        # UPDATE atômico primeiro: dois beacons ao mesmo tempo não se perdem.
        if MetricaDiaria.query.filter_by(**filtro).update(
                {MetricaDiaria.total: MetricaDiaria.total + 1}, synchronize_session=False):
            db.session.commit()
            return True
        db.session.add(MetricaDiaria(total=1, **filtro))
        try:
            db.session.commit()
        except IntegrityError:
            # Outro beacon criou a linha entre o UPDATE e o INSERT.
            db.session.rollback()
            MetricaDiaria.query.filter_by(**filtro).update(
                {MetricaDiaria.total: MetricaDiaria.total + 1}, synchronize_session=False)
            db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def totais(restaurant_id, inicio, fim):
    """{tipo: soma} entre `inicio` e `fim` (inclusive), com zero no que faltar."""
    linhas = (db.session.query(MetricaDiaria.tipo, db.func.sum(MetricaDiaria.total))
              .filter(MetricaDiaria.restaurant_id == restaurant_id,
                      MetricaDiaria.dia >= inicio, MetricaDiaria.dia <= fim)
              .group_by(MetricaDiaria.tipo).all())
    soma = dict.fromkeys(TIPOS, 0)
    soma.update({tipo: int(total or 0) for tipo, total in linhas if tipo in TIPOS})
    return soma


def por_dia(restaurant_id, dias=30, hoje=None):
    """Últimos `dias` dias, do mais antigo ao de hoje: [(data, {tipo: total})]."""
    hoje = hoje or hoje_br()
    inicio = hoje - timedelta(days=dias - 1)
    serie = {inicio + timedelta(days=i): dict.fromkeys(TIPOS, 0) for i in range(dias)}
    for m in (MetricaDiaria.query
              .filter(MetricaDiaria.restaurant_id == restaurant_id,
                      MetricaDiaria.dia >= inicio, MetricaDiaria.dia <= hoje)):
        if m.tipo in TIPOS and m.dia in serie:
            serie[m.dia][m.tipo] = m.total
    return sorted(serie.items())


def mes_anterior(hoje=None):
    """(primeiro dia, último dia) do mês fechado antes de `hoje`."""
    hoje = hoje or hoje_br()
    fim = hoje.replace(day=1) - timedelta(days=1)
    return fim.replace(day=1), fim


def texto_relatorio(nome, soma, inicio, reservas=0, avaliacoes=0, link=''):
    """Mensagem do relatório mensal, pronta para mandar no WhatsApp do cliente.

    Só entra linha com número maior que zero: "0 pessoas abriram o mapa" não
    ajuda ninguém a renovar.
    """
    mes = f'{MESES[inicio.month - 1]} de {inicio.year}'
    linhas = [f'Olá! Aqui é a Feira de Barão. O resumo do site de {nome} em {mes}:', '']
    for tipo, rotulo in TIPOS.items():
        if soma.get(tipo):
            linhas.append(f'• {soma[tipo]} {rotulo}')
    if reservas:
        linhas.append(f'• {reservas} reservas pelo site')
    if avaliacoes:
        linhas.append(f'• {avaliacoes} pessoas abriram a tela de avaliação no Google')
    if len(linhas) == 2:
        linhas.append('• O site ainda teve pouco movimento. Vamos divulgar o link juntos este mês?')
    if link:
        linhas += ['', f'Seu site: {link}']
    return '\n'.join(linhas)


def whatsapp_do_dono(numero):
    """Número cadastrado no site → formato do wa.me (com 55 se faltar)."""
    digitos = ''.join(c for c in (numero or '') if c.isdigit())
    if len(digitos) in (10, 11):
        digitos = '55' + digitos
    return digitos if len(digitos) >= 12 else ''
