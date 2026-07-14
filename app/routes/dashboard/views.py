from flask import render_template, redirect, url_for, request, jsonify, current_app, Response
from flask_login import login_required
from app.extensions import db
from sqlalchemy import func, desc, extract, and_, or_, case, cast, Float
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_produto import Produto
from app.models.modelo_cardapio import Cardapio, CardapioItem, CardapioSecao
from app.models.modelo_previsao import HistoricoVendas
from app.models.modelo_desperdicio import RegistroDesperdicio
from app.models.modelo_custo import CustoIndireto
from app.routes.dashboard import bp
from datetime import datetime, date, timedelta
from app.utils.tenant import get_current_restaurant_id
import pandas as pd
import numpy as np
import json
import calendar
import io
from app.utils.decorators import pro_required

# Funções auxiliares para cálculos de lucratividade
def calcular_metricas_principais(data_inicio, data_fim, restaurant_id):
    """Calcula as métricas principais de lucratividade para o período - OTIMIZADO"""
    from sqlalchemy.orm import joinedload
    
    # Obter vendas no período com eager loading
    vendas = HistoricoVendas.query.options(
        joinedload(HistoricoVendas.cardapio_item).joinedload(CardapioItem.prato),
        joinedload(HistoricoVendas.prato)
    ).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id
    ).all()
    
    # Calcular receita total
    receita_total = sum(float(v.valor_total or 0) for v in vendas)
    
    # Calcular custos diretos (apenas insumos)
    custo_direto_total = 0
    for venda in vendas:
        # Custo do item vendido (apenas insumos, sem custos indiretos)
        if venda.cardapio_item:
            # Já carregado via eager load
            item = venda.cardapio_item
            if item.prato:
                custo_direto_total += float(item.prato.custo_direto_por_porcao or 0) * venda.quantidade
        elif venda.prato:
            # Já carregado via eager load
            prato = venda.prato
            custo_direto_total += float(prato.custo_direto_por_porcao or 0) * venda.quantidade
    
    # Adicionar custos indiretos do período
    custos_indiretos = CustoIndireto.query.filter(
        CustoIndireto.data_referencia >= data_inicio,
        CustoIndireto.data_referencia <= data_fim,
        CustoIndireto.restaurant_id == restaurant_id
    ).all()
    custo_indireto_total = sum(float(c.valor or 0) for c in custos_indiretos)
    custo_total = custo_direto_total + custo_indireto_total
    
    # Calcular lucro e margem
    lucro_total = receita_total - custo_total
    margem_media = (lucro_total / receita_total * 100) if receita_total > 0 else 0
    
    return receita_total, custo_total, lucro_total, margem_media


def obter_dados_diarios(data_inicio, data_fim, restaurant_id):
    """Obtém dados diários de receitas e custos para gráfico - OTIMIZADO"""
    from sqlalchemy.orm import joinedload

    # Criar dicionários para armazenar os valores por dia
    receitas_por_dia = {}
    custos_por_dia = {}
    lucros_por_dia = {}
    
    # Inicializar todos os dias do período com zero
    data_atual = data_inicio
    while data_atual <= data_fim:
        data_str = data_atual.strftime('%Y-%m-%d')
        receitas_por_dia[data_str] = 0
        custos_por_dia[data_str] = 0
        lucros_por_dia[data_str] = 0
        data_atual += timedelta(days=1)
    
    # Obter vendas no período com eager loading
    vendas = HistoricoVendas.query.options(
        joinedload(HistoricoVendas.cardapio_item).joinedload(CardapioItem.prato),
        joinedload(HistoricoVendas.prato)
    ).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id
    ).all()
    
    # Calcular receitas e custos diretos por dia
    for venda in vendas:
        data_str = venda.data.strftime('%Y-%m-%d')
        if data_str not in receitas_por_dia:
            continue # Data fora do range (improvável dado o filter)
            
        # Adicionar receita
        receitas_por_dia[data_str] += float(venda.valor_total or 0)
        
        # Calcular custo direto
        custo_item = 0
        if venda.cardapio_item:
            item = venda.cardapio_item
            if item.prato:
                custo_item = float(item.prato.custo_total_por_porcao or 0) * venda.quantidade
        elif venda.prato:
            prato = venda.prato
            custo_item = float(prato.custo_total_por_porcao or 0) * venda.quantidade
        
        custos_por_dia[data_str] += custo_item
    
    # Adicionar custos indiretos por dia
    custos_indiretos = CustoIndireto.query.filter(
        CustoIndireto.data_referencia >= data_inicio,
        CustoIndireto.data_referencia <= data_fim,
        CustoIndireto.restaurant_id == restaurant_id
    ).all()
    
    for custo in custos_indiretos:
        data_str = custo.data_referencia.strftime('%Y-%m-%d')
        if data_str in custos_por_dia:  # Verificar se o dia está no período
            custos_por_dia[data_str] += float(custo.valor or 0)
    
    # Calcular lucros por dia
    for data_str in receitas_por_dia.keys():
        lucros_por_dia[data_str] = receitas_por_dia[data_str] - custos_por_dia[data_str]
    
    # Preparar dados para o gráfico
    datas = []
    receitas = []
    custos = []
    lucros = []
    
    for data_str in sorted(receitas_por_dia.keys()):
        data_formatada = datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m')
        datas.append(data_formatada)
        receitas.append(receitas_por_dia[data_str])
        custos.append(custos_por_dia[data_str])
        lucros.append(lucros_por_dia[data_str])
    
    return {
        'datas': datas,
        'receitas': receitas,
        'custos': custos,
        'lucros': lucros
    }


def obter_top_pratos(data_inicio, data_fim, restaurant_id, limite=5):
    """Obtém os pratos mais lucrativos no período"""
    # Consultar vendas de pratos no período
    vendas_pratos = db.session.query(
        Prato.id,
        Prato.nome,
        func.sum(HistoricoVendas.quantidade).label('quantidade_vendida'),
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).join(
        HistoricoVendas,
        HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(
        Prato.id
    ).order_by(
        func.sum(HistoricoVendas.valor_total).desc()
    ).limit(limite).all()
    
    # Preparar dados com cálculo de lucro
    top_pratos = []
    for p in vendas_pratos:
        prato = Prato.query.filter_by(id=p.id, restaurant_id=restaurant_id).first()
        if prato:
            custo_unitario = float(prato.custo_direto_por_porcao or 0)
            custo_total = custo_unitario * p.quantidade_vendida
            lucro = float(p.receita_total or 0) - custo_total
            margem = (lucro / float(p.receita_total)) * 100 if float(p.receita_total) > 0 else 0
            
            top_pratos.append({
                'id': p.id,
                'nome': p.nome,
                'quantidade_vendida': p.quantidade_vendida,
                'receita_total': float(p.receita_total or 0),
                'custo_total': custo_total,
                'lucro': lucro,
                'margem': margem
            })
    
    return top_pratos


def obter_distribuicao_categorias(data_inicio, data_fim, restaurant_id):
    """Obtém a distribuição de vendas por categoria de prato"""
    # Consultar vendas agrupadas por categoria de prato
    vendas_por_categoria = db.session.query(
        Prato.categoria,
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).join(
        HistoricoVendas,
        HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id,
        Prato.categoria.isnot(None)  # Filtrar pratos sem categoria
    ).group_by(
        Prato.categoria
    ).all()
    
    # Preparar dados para o gráfico de pizza
    categorias = []
    valores = []
    cores = []
    
    # Cores padrão para as categorias
    cores_padrao = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
        '#FF9F40', '#8AC249', '#EA5F89', '#00B8D4', '#6D4C41'
    ]
    
    for i, (categoria, receita) in enumerate(vendas_por_categoria):
        categorias.append(categoria or 'Sem Categoria')
        valores.append(float(receita or 0))
        cores.append(cores_padrao[i % len(cores_padrao)])
    
    return {
        'categorias': categorias,
        'valores': valores,
        'cores': cores
    }


def obter_tendencia_lucratividade(restaurant_id, meses=6):
    """Obtém a tendência de lucratividade dos últimos meses de forma otimizada"""
    hoje = date.today()
    
    # Calcular data de início
    mes_atual = hoje.month
    ano_atual = hoje.year
    for _ in range(meses):
        mes_atual -= 1
        if mes_atual == 0:
            mes_atual = 12
            ano_atual -= 1
    inicio_periodo = date(ano_atual, mes_atual, 1)

    # 1. Carregar TODOS os pratos com insumos para calcular custo em memória (evita N+1 e erro de SQL property)
    from sqlalchemy.orm import joinedload
    todos_pratos = Prato.query.options(
        joinedload(Prato.insumos).joinedload(PratoInsumo.produto)
    ).filter_by(restaurant_id=restaurant_id).all()
    
    # Mapa de custos: prato_id -> custo_unitario
    custo_prato_map = {p.id: float(p.custo_direto_por_porcao or 0) for p in todos_pratos}
    
    # 2. Consultar vendas agregadas por Mês e por Item/Prato
    # Detectar dialeto para função de data correta
    is_postgres = False
    try:
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri and ('postgres' in db_uri or 'psycopg' in db_uri):
            is_postgres = True
        elif db.session.bind and 'postgresql' in db.session.bind.dialect.name:
            is_postgres = True
    except:
        is_postgres = False # Fallback para SQLite

    if is_postgres:
        func_mes_ano = func.to_char(HistoricoVendas.data, 'YYYY-MM')
    else:
        func_mes_ano = func.strftime('%Y-%m', HistoricoVendas.data)

    # Agrupamos por mês E por item para podermos aplicar o custo correto em Python
    vendas_detalhadas = db.session.query(
        func_mes_ano.label('mes_ano'),
        HistoricoVendas.cardapio_item_id,
        HistoricoVendas.prato_id,
        CardapioItem.prato_id.label('item_prato_id'),
        func.sum(HistoricoVendas.quantidade).label('qtd_total'),
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).outerjoin(
        CardapioItem, HistoricoVendas.cardapio_item_id == CardapioItem.id
    ).filter(
        HistoricoVendas.data >= inicio_periodo,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(
        func_mes_ano,
        HistoricoVendas.cardapio_item_id,
        HistoricoVendas.prato_id,
        CardapioItem.prato_id
    ).all()
    
    # 3. Processar agregação mensal em Python
    dados_mensais = {} # 'YYYY-MM': {'receita': 0, 'custo': 0}
    
    for v in vendas_detalhadas:
        mes_ano = v.mes_ano
        if mes_ano not in dados_mensais:
            dados_mensais[mes_ano] = {'receita': 0.0, 'custo': 0.0}
            
        # Receita
        dados_mensais[mes_ano]['receita'] += float(v.receita_total or 0)
        
        # Custo
        prato_id = None
        if v.item_prato_id: # Veio via CardapioItem
            prato_id = v.item_prato_id
        elif v.prato_id: # Veio direto via Prato
            prato_id = v.prato_id
            
        if prato_id and prato_id in custo_prato_map:
            custo_unit = custo_prato_map[prato_id]
            custo_total = custo_unit * float(v.qtd_total or 0)
            dados_mensais[mes_ano]['custo'] += custo_total

    # 4. Adicionar Custos Indiretos Mensais
    if is_postgres:
        func_mes_ano_custo = func.to_char(CustoIndireto.data_referencia, 'YYYY-MM')
    else:
        func_mes_ano_custo = func.strftime('%Y-%m', CustoIndireto.data_referencia)

    custos_indiretos = db.session.query(
        func_mes_ano_custo.label('mes_ano'),
        func.sum(CustoIndireto.valor).label('total')
    ).filter(
        CustoIndireto.data_referencia >= inicio_periodo,
        CustoIndireto.restaurant_id == restaurant_id
    ).group_by(
        func_mes_ano_custo
    ).all()
    
    for c in custos_indiretos:
        mes_ano = c.mes_ano
        if mes_ano in dados_mensais:
            dados_mensais[mes_ano]['custo'] += float(c.total or 0)

    # 5. Formatar para retorno (Lista ordenada por mês)
    lista_final = []
    # Reconstruir a lista de meses para garantir ordem cronológica
    mes_iter = mes_atual
    ano_iter = ano_atual
    
    for _ in range(meses):
        mes_str = f"{ano_iter}-{mes_iter:02d}"
        
        dados = dados_mensais.get(mes_str, {'receita': 0.0, 'custo': 0.0})
        receita = dados['receita']
        custo = dados['custo']
        lucro = receita - custo
        margem = (lucro / receita * 100) if receita > 0 else 0
        
        nome_mes = calendar.month_name[mes_iter]
        
        lista_final.append({
            'mes': nome_mes,
            'receita': receita,
            'custo': custo,
            'lucro': lucro,
            'margem': margem
        })
        
        # Avançar mês
        mes_iter += 1
        if mes_iter > 12:
            mes_iter = 1
            ano_iter += 1

    return {
        'meses': [d['mes'] for d in lista_final],
        'receitas': [d['receita'] for d in lista_final],
        'custos': [d['custo'] for d in lista_final],
        'lucros': [d['lucro'] for d in lista_final],
        'margens': [d['margem'] for d in lista_final]
    }


def obter_indicadores_desperdicio(data_inicio, data_fim, restaurant_id):
    """Obtém indicadores de desperdício para o período"""
    # Consultar registros de desperdício no período
    desperdicios = RegistroDesperdicio.query.filter(
        RegistroDesperdicio.data_registro >= data_inicio,
        RegistroDesperdicio.data_registro <= data_fim,
        RegistroDesperdicio.restaurant_id == restaurant_id
    ).all()
    
    # Calcular valor total do desperdício
    valor_total = sum(float(d.valor_estimado or 0) for d in desperdicios)
    
    # Contar registros por categoria
    contagem_por_categoria = {}
    valor_por_categoria = {}
    
    for desp in desperdicios:
        if desp.categoria:
            categoria = desp.categoria.nome
            if categoria not in contagem_por_categoria:
                contagem_por_categoria[categoria] = 0
                valor_por_categoria[categoria] = 0
            
            contagem_por_categoria[categoria] += 1
            valor_por_categoria[categoria] += float(desp.valor_estimado or 0)
    
    # Obter receita total do período (para calcular percentual de desperdício)
    receita_total, _, _, _ = calcular_metricas_principais(data_inicio, data_fim, restaurant_id)
    
    # Calcular percentual de desperdício em relação à receita
    percentual_desperdicio = (valor_total / receita_total * 100) if receita_total > 0 else 0
    
    return {
        'total_registros': len(desperdicios),
        'valor_total': valor_total,
        'percentual_receita': percentual_desperdicio,
        'categorias': contagem_por_categoria,
        'valores_por_categoria': valor_por_categoria
    }


def obter_dados_matriz_bcg(data_inicio, data_fim, restaurant_id):
    """
    Calcula os dados para a Matriz BCG (Engenharia de Cardápio)
    Eixo X: Popularidade (Volume de Vendas)
    Eixo Y: Lucratividade (Margem de Contribuição)
    """
    # 1. Total de vendas no período (para calcular média de popularidade)
    total_itens_vendidos = db.session.query(func.sum(HistoricoVendas.quantidade)).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id
    ).scalar() or 0
    
    # 2. Vendas por prato
    vendas_pratos = db.session.query(
        Prato.id,
        Prato.nome,
        func.sum(HistoricoVendas.quantidade).label('qtde'),
        func.sum(HistoricoVendas.valor_total).label('receita')
    ).join(
        HistoricoVendas, HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= data_inicio,
        HistoricoVendas.data <= data_fim,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(Prato.id).all()
    
    if not vendas_pratos:
        return {'datasets': []}

    # 3. Calcular métricas para cada prato
    dados_grafico = []
    
    # Pre-fetch pratos para custo
    prato_ids = [v.id for v in vendas_pratos]
    pratos_map = {p.id: p for p in Prato.query.filter(Prato.id.in_(prato_ids)).all()}
    
    # Médias para divisão dos quadrantes
    num_pratos = len(vendas_pratos)
    media_popularidade = total_itens_vendidos / num_pratos if num_pratos > 0 else 0
    
    # Calcular margem média ponderada global (ou simples dos pratos vendidos)
    # Vamos usar a margem de contribuição média total
    receita_total_periodo = sum(float(v.receita or 0) for v in vendas_pratos)
    margem_total_periodo = 0
    
    pratos_processados = []
    
    for v in vendas_pratos:
        prato = pratos_map.get(v.id)
        if not prato: continue
        
        custo = float(prato.custo_direto_por_porcao or 0)
        receita_item = float(v.receita or 0)
        qtde = float(v.qtde or 0)
        
        if qtde == 0: continue
        
        preco_medio = receita_item / qtde
        margem_contrib_unit = preco_medio - custo
        # Margem de contribuição total do prato no período
        margem_contrib_total = margem_contrib_unit * qtde
        
        margem_total_periodo += margem_contrib_total
        
        pratos_processados.append({
            'label': prato.nome,
            'x': qtde, # Popularidade
            'y': margem_contrib_unit, # Lucratividade (Margem Unitária)
            'custo': custo,
            'preco': preco_medio
        })
        
    media_lucratividade = margem_total_periodo / total_itens_vendidos if total_itens_vendidos > 0 else 0
    
    # Classificar em Quadrantes
    # Estrela: Alta Popularidade, Alta Lucratividade
    # Burro de Carga: Alta Popularidade, Baixa Lucratividade
    # Quebra-Cabeça: Baixa Popularidade, Alta Lucratividade
    # Cão: Baixa Popularidade, Baixa Lucratividade
    
    datasets = {
        'Estrela': {'data': [], 'backgroundColor': '#28a745'}, # Verde
        'Burro de Carga': {'data': [], 'backgroundColor': '#ffc107'}, # Amarelo
        'Quebra-Cabeça': {'data': [], 'backgroundColor': '#17a2b8'}, # Azul
        'Cão': {'data': [], 'backgroundColor': '#dc3545'} # Vermelho
    }
    
    for p in pratos_processados:
        popularidade = p['x']
        lucratividade = p['y']
        
        quadrante = ''
        if popularidade >= media_popularidade:
            if lucratividade >= media_lucratividade:
                quadrante = 'Estrela'
            else:
                quadrante = 'Burro de Carga'
        else:
            if lucratividade >= media_lucratividade:
                quadrante = 'Quebra-Cabeça'
            else:
                quadrante = 'Cão'
                
        datasets[quadrante]['data'].append(p)

    return {
        'datasets': [
            {'label': k, 'data': v['data'], 'backgroundColor': v['backgroundColor']}
            for k, v in datasets.items() if v['data']
        ],
        'media_popularidade': media_popularidade,
        'media_lucratividade': media_lucratividade
    }

@bp.route('/upgrade')
def upgrade():
    """Página de Upgrade/Planos"""
    return render_template('dashboard/upgrade.html')

@bp.route('/')
@bp.route('/index')
def index():
    """Página principal do dashboard de lucratividade"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    try:
        # --- EMPTY STATE CHECK (ONBOARDING) ---
        total_produtos = Produto.query.filter_by(restaurant_id=restaurant_id).count()
        total_vendas_count = HistoricoVendas.query.filter_by(restaurant_id=restaurant_id).count()
        
        show_onboarding = False
        if total_produtos == 0 and total_vendas_count == 0:
            show_onboarding = True
            # Se for onboarding, não precisamos calcular métricas pesadas
            return render_template('dashboard/index.html', show_onboarding=True)
            
        # --------------------------------------

        # Obter período selecionado
        periodo = request.args.get('periodo', '30dias')  # Padrão: últimos 30 dias
        hoje = date.today()
        
        if periodo == 'hoje':
            inicio_periodo = hoje
            fim_periodo = hoje
            titulo_periodo = f"Hoje - {hoje.strftime('%d/%m/%Y')}"
        elif periodo == 'ontem':
            ontem = hoje - timedelta(days=1)
            inicio_periodo = ontem
            fim_periodo = ontem
            titulo_periodo = f"Ontem - {ontem.strftime('%d/%m/%Y')}"
        elif periodo == '7dias':
            inicio_periodo = hoje - timedelta(days=6)  # Últimos 7 dias incluindo hoje
            fim_periodo = hoje
            titulo_periodo = f"Últimos 7 Dias ({inicio_periodo.strftime('%d/%m')} a {fim_periodo.strftime('%d/%m')})"
        elif periodo == '30dias':
            inicio_periodo = hoje - timedelta(days=29)  # Últimos 30 dias incluindo hoje
            fim_periodo = hoje
            titulo_periodo = f"Últimos 30 Dias ({inicio_periodo.strftime('%d/%m')} a {fim_periodo.strftime('%d/%m')})"
        elif periodo == 'mes_anterior':
            # Mês anterior completo
            if hoje.month == 1:
                mes_anterior = 12
                ano_anterior = hoje.year - 1
            else:
                mes_anterior = hoje.month - 1
                ano_anterior = hoje.year
            inicio_periodo = date(ano_anterior, mes_anterior, 1)
            fim_periodo = date(ano_anterior, mes_anterior, calendar.monthrange(ano_anterior, mes_anterior)[1])
            titulo_periodo = f"Mês Anterior ({inicio_periodo.strftime('%B/%Y')})"
        elif periodo == 'mensal':
            inicio_periodo = date(hoje.year, hoje.month, 1)
            fim_periodo = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
            titulo_periodo = f"Mês de {inicio_periodo.strftime('%B/%Y')}"
        elif periodo == 'trimestral':
            trimestre = (hoje.month - 1) // 3
            inicio_periodo = date(hoje.year, trimestre * 3 + 1, 1)
            fim_periodo = date(hoje.year, (trimestre + 1) * 3, calendar.monthrange(hoje.year, (trimestre + 1) * 3)[1])
            titulo_periodo = f"{trimestre + 1}º Trimestre de {hoje.year}"
        elif periodo == 'anual':
            inicio_periodo = date(hoje.year, 1, 1)
            fim_periodo = date(hoje.year, 12, 31)
            titulo_periodo = f"Ano de {hoje.year}"
        else:  # personalizado
            data_inicio_str = request.args.get('data_inicio')
            data_fim_str = request.args.get('data_fim')
            if data_inicio_str and data_fim_str:
                inicio_periodo = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                fim_periodo = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                titulo_periodo = f"Período de {inicio_periodo.strftime('%d/%m/%Y')} a {fim_periodo.strftime('%d/%m/%Y')}"
            else:
                # Fallback para mês atual
                inicio_periodo = date(hoje.year, hoje.month, 1)
                fim_periodo = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
                titulo_periodo = f"Mês de {inicio_periodo.strftime('%B/%Y')}"
        
        # Calcular métricas principais
        receita_total, custo_total, lucro_total, margem_media = calcular_metricas_principais(inicio_periodo, fim_periodo, restaurant_id)
        
        # --- NOVAS MÉTRICAS DO COCKPIT ---
        
        # 1. Lucro Hoje
        # Reutilio a logica de metricas principais mas apenas para hoje
        receita_hoje, custo_hoje, lucro_hoje, margem_hoje = calcular_metricas_principais(hoje, hoje, restaurant_id)
        
        # 2. Estoque Crítico (Produtos abaixo do mínimo)
        estoque_critico = Produto.query.filter(
            Produto.restaurant_id == restaurant_id,
            Produto.estoque_atual < Produto.estoque_minimo,
            Produto.ativo == True
        ).count()
        
        # 3. Alertas de Custo (Pratos com margem negativa ou muito baixa (< 10%))
        # Precisamos verificar isso em Python pois margem é calculada
        # Mas podemos filtrar por margem no banco se ela estivesse persistida corretamente.
        # O modelo Prato tem campo 'margem'. Vamos confiar nele por hora, mas idealmente recalculariamos.
        alertas_custo = Prato.query.filter(
            Prato.restaurant_id == restaurant_id,
            Prato.margem < 15, # Alerta para margem abaixo de 15%
            Prato.ativo == True
        ).count()
        
        # 4. Alertas de Inflação (Produtos que subiram > 10% nos últimos 30 dias)
        data_limite_alerta = datetime.now() - timedelta(days=30)
        produtos_inflacao = Produto.query.filter(
            Produto.restaurant_id == restaurant_id,
            Produto.variacao_preco_pct > 10,
            Produto.data_alerta_inflacao >= data_limite_alerta
        ).all()
        alertas_inflacao_count = len(produtos_inflacao)
        
        # ---------------------------------

        # Obter dados para gráficos
        dados_diarios = obter_dados_diarios(inicio_periodo, fim_periodo, restaurant_id)
        top_pratos = obter_top_pratos(inicio_periodo, fim_periodo, restaurant_id)
        distribuicao_categorias = obter_distribuicao_categorias(inicio_periodo, fim_periodo, restaurant_id)
        tendencia_lucratividade = obter_tendencia_lucratividade(restaurant_id)
        
        # Matriz BCG
        dados_bcg = obter_dados_matriz_bcg(inicio_periodo, fim_periodo, restaurant_id)
        
        # Calcular valor do desperdício
        desperdicios = RegistroDesperdicio.query.filter(
            RegistroDesperdicio.data_registro >= inicio_periodo,
            RegistroDesperdicio.data_registro <= fim_periodo,
            RegistroDesperdicio.restaurant_id == restaurant_id
        ).all()
        valor_desperdicio = sum(float(d.valor_estimado or 0) for d in desperdicios)
        
        # Calcular impacto do desperdício em relação ao custo total
        impacto_desperdicio = (valor_desperdicio / custo_total * 100) if custo_total > 0 else 0
        
        # Determinar nível de desperdício
        if impacto_desperdicio > 5:
            nivel_desperdicio = 'alto'
        elif impacto_desperdicio > 2:
            nivel_desperdicio = 'medio'
        else:
            nivel_desperdicio = 'baixo'
        
        # Obter categorias de cardápio com pratos
        categorias_cardapio = []
        try:
            categorias = db.session.query(Prato.categoria).filter(
                Prato.restaurant_id == restaurant_id,
                Prato.ativo == True
            ).distinct().all()
            
            for (categoria_nome,) in categorias:
                if not categoria_nome:
                    continue
                    
                pratos_categoria = Prato.query.filter(
                    Prato.restaurant_id == restaurant_id,
                    Prato.categoria == categoria_nome,
                    Prato.ativo == True
                ).limit(5).all()
                
                if pratos_categoria:
                    categorias_cardapio.append({
                        'nome': categoria_nome,
                        'pratos': pratos_categoria
                    })
        except Exception as e:
            print(f"Erro ao buscar categorias de cardápio: {e}")
            categorias_cardapio = []
        
        return render_template('dashboard/index.html',
                            titulo_periodo=titulo_periodo,
                            periodo=periodo,
                            inicio_periodo=inicio_periodo,
                            fim_periodo=fim_periodo,
                            receita_total=receita_total,
                            custo_total=custo_total,
                            lucro_total=lucro_total,
                            margem_media=margem_media,
                            dados_diarios=dados_diarios,
                            top_pratos=top_pratos,
                            distribuicao_categorias=distribuicao_categorias,
                            tendencia_lucratividade=tendencia_lucratividade,
                            valor_desperdicio=valor_desperdicio,
                            impacto_desperdicio=impacto_desperdicio,
                            nivel_desperdicio=nivel_desperdicio,
                            lucro_hoje=lucro_hoje,
                            receita_hoje=receita_hoje,
                            custo_hoje=custo_hoje,
                            estoque_critico=estoque_critico,
                            alertas_custo=alertas_custo,
                            alertas_inflacao_count=alertas_inflacao_count,
                            produtos_inflacao=produtos_inflacao,
                            dados_bcg=dados_bcg,
                            categorias_cardapio=categorias_cardapio,
                            show_onboarding=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Erro processando Dashboard: {str(e)} <br><pre>{traceback.format_exc()}</pre>", 500


@bp.route('/relatorio/pratos')
@login_required
@pro_required
def relatorio_pratos():
    """Relatório detalhado de lucratividade por prato - OTIMIZADO"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    # Obter período para análise
    hoje = date.today()
    data_inicio = request.args.get('data_inicio', (hoje - timedelta(days=30)).strftime('%Y-%m-%d'))
    data_fim = request.args.get('data_fim', hoje.strftime('%Y-%m-%d'))
    
    try:
        inicio_periodo = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim_periodo = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except ValueError:
        inicio_periodo = hoje - timedelta(days=30)
        fim_periodo = hoje
        
    # Consultar vendas agregadas por prato
    vendas_pratos = db.session.query(
        Prato.id,
        Prato.nome,
        Prato.categoria,
        func.sum(HistoricoVendas.quantidade).label('quantidade_vendida'),
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).join(
        HistoricoVendas,
        HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= inicio_periodo,
        HistoricoVendas.data <= fim_periodo,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(
        Prato.id
    ).order_by(
        func.sum(HistoricoVendas.valor_total).desc()
    ).all()
    
    # Pré-cálculo de totais gerais para rateio (Query única)
    totais_periodo = db.session.query(
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).filter(
        HistoricoVendas.data >= inicio_periodo, 
        HistoricoVendas.data <= fim_periodo,
        HistoricoVendas.restaurant_id == restaurant_id
    ).first()
    
    receita_total_periodo = float(totais_periodo.receita_total or 0)

    # Pré-cálculo de custos indiretos totais (Query única)
    total_indiretos = db.session.query(func.sum(CustoIndireto.valor)).filter(
        CustoIndireto.data_referencia >= inicio_periodo,
        CustoIndireto.data_referencia <= fim_periodo,
        CustoIndireto.restaurant_id == restaurant_id
    ).scalar() or 0.0
    
    # Preparar dados detalhados
    pratos_detalhes = []
    
    prato_ids = [p.id for p in vendas_pratos]
    if prato_ids:
        from sqlalchemy.orm import joinedload
        # Carregar pratos com seus insumos e produtos dos insumos em UMA query
        objetos_pratos = {prato.id: prato for prato in Prato.query.options(
            joinedload(Prato.insumos).joinedload(PratoInsumo.produto)
        ).filter(Prato.id.in_(prato_ids), Prato.restaurant_id == restaurant_id).all()}
    else:
        objetos_pratos = {}

    for p in vendas_pratos:
        prato_obj = objetos_pratos.get(p.id)
        
        if prato_obj:
            # Custos diretos (apenas insumos, sem custos indiretos)
            custo_unitario = float(prato_obj.custo_direto_por_porcao or 0)
            custo_direto_total = custo_unitario * p.quantidade_vendida
            
            # Rateio de custos indiretos (proporcionalmente à receita)
            proporcao_receita = float(p.receita_total) / receita_total_periodo if receita_total_periodo > 0 else 0
            custo_indireto_estimado = float(total_indiretos) * proporcao_receita
            
            # Cálculos finais
            custo_total = custo_direto_total + custo_indireto_estimado
            lucro = float(p.receita_total) - custo_total
            margem = (lucro / float(p.receita_total)) * 100 if float(p.receita_total) > 0 else 0
            
            pratos_detalhes.append({
                'id': p.id,
                'nome': p.nome,
                'categoria': p.categoria,
                'quantidade_vendida': p.quantidade_vendida,
                'receita_total': float(p.receita_total),
                'custo_direto_total': custo_direto_total,
                'custo_indireto_estimado': custo_indireto_estimado,
                'custo_total': custo_total,
                'lucro': lucro,
                'margem': margem,
                'custo_unitario': custo_unitario,
                'preco_venda': float(p.receita_total) / p.quantidade_vendida if p.quantidade_vendida > 0 else 0
            })
    
    # Ordenar por margem de lucro (do maior para o menor)
    pratos_detalhes.sort(key=lambda x: x['margem'], reverse=True)
    
    # Calcular totais gerais finais para display
    total_receita_display = sum(p['receita_total'] for p in pratos_detalhes)
    total_custo_display = sum(p['custo_total'] for p in pratos_detalhes)
    total_lucro_display = total_receita_display - total_custo_display
    margem_media_geral = (total_lucro_display / total_receita_display * 100) if total_receita_display > 0 else 0
    
    # Agrupar por categoria
    categorias = {}
    for prato in pratos_detalhes:
        categoria = prato['categoria'] or 'Sem Categoria'
        if categoria not in categorias:
            categorias[categoria] = {
                'receita': 0,
                'custo': 0,
                'lucro': 0,
                'pratos': []
            }
        
        categorias[categoria]['receita'] += prato['receita_total']
        categorias[categoria]['custo'] += prato['custo_total']
        categorias[categoria]['lucro'] += prato['lucro']
        categorias[categoria]['pratos'].append(prato)
    
    # Calcular margens por categoria e preparar lista
    categorias_ordenadas = []
    for cat, dados in categorias.items():
        dados['margem'] = (dados['lucro'] / dados['receita'] * 100) if dados['receita'] > 0 else 0
        categorias_ordenadas.append((cat, dados))
        
    categorias_ordenadas.sort(key=lambda x: x[1]['margem'], reverse=True)
    
    return render_template('dashboard/relatorio_pratos.html',
                          data_inicio=inicio_periodo.strftime('%Y-%m-%d'),
                          data_fim=fim_periodo.strftime('%Y-%m-%d'),
                          pratos=pratos_detalhes,
                          categorias=categorias_ordenadas,
                          total_receita=total_receita_display,
                          total_custo=total_custo_display,
                          total_lucro=total_lucro_display,
                          margem_media=margem_media_geral)


@bp.route('/relatorio/categorias')
@login_required
@pro_required
def relatorio_categorias():
    """Relatório de lucratividade por categoria"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    # Obter período para análise
    hoje = date.today()
    data_inicio = request.args.get('data_inicio', (hoje - timedelta(days=30)).strftime('%Y-%m-%d'))
    data_fim = request.args.get('data_fim', hoje.strftime('%Y-%m-%d'))
    
    try:
        inicio_periodo = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim_periodo = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except ValueError:
        inicio_periodo = hoje - timedelta(days=30)
        fim_periodo = hoje
    
    # Consultar vendas por seção de cardápio
    vendas_secoes = db.session.query(
        CardapioSecao.id,
        CardapioSecao.nome,
        func.sum(HistoricoVendas.quantidade).label('quantidade_vendida'),
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).join(
        CardapioItem,
        CardapioItem.secao_id == CardapioSecao.id
    ).join(
        HistoricoVendas,
        HistoricoVendas.cardapio_item_id == CardapioItem.id
    ).filter(
        HistoricoVendas.data >= inicio_periodo,
        HistoricoVendas.data <= fim_periodo,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(
        CardapioSecao.id
    ).all()
    
    # Consultar vendas por categoria de prato
    vendas_categorias_prato = db.session.query(
        Prato.categoria,
        func.sum(HistoricoVendas.quantidade).label('quantidade_vendida'),
        func.sum(HistoricoVendas.valor_total).label('receita_total')
    ).join(
        HistoricoVendas,
        HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= inicio_periodo,
        HistoricoVendas.data <= fim_periodo,
        Prato.categoria != None,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(
        Prato.categoria
    ).all()
    
    # Combinar dados (seções de cardápio e categorias de pratos)
    categorias_dados = {}
    
    # Processar seções de cardápio
    for secao in vendas_secoes:
        # Obter itens da seção para calcular custos
        # Nota: precisamos garantir que estamos pegando apenas items relevantes ou iterar sobre vendas
        # Mas aqui, como já temos agregados, vamos iterar sobre CardapioItem para o custo.
        # ISSO PODE SER LENTO E INCORRETO SE TIVERMOS ITENS DE OUTROS RESTAURANTES?
        # CardapioSecao deve ser filtrado por tenant?
        # Sim, mas aqui `vendas_secoes` vem de HistoricoVendas filtrado por tenant.
        # Então secao.id é válido para o tenant.
        
        # Agora buscamos itens dessa seção.
        itens = CardapioItem.query.filter_by(secao_id=secao.id).all()
        custo_total = 0
        
        for item in itens:
            # Obter vendas específicas deste item no período
            vendas_item = HistoricoVendas.query.filter(
                HistoricoVendas.cardapio_item_id == item.id,
                HistoricoVendas.data >= inicio_periodo,
                HistoricoVendas.data <= fim_periodo,
                HistoricoVendas.restaurant_id == restaurant_id
            ).all()
            
            # Calcular custo
            if item.prato:
                for venda in vendas_item:
                    custo_total += float(item.prato.custo_total_por_porcao or 0) * venda.quantidade
        
        # Adicionar aos dados por categoria
        categorias_dados[f'Seção: {secao.nome}'] = {
            'tipo': 'Seção',
            'nome': secao.nome,
            'quantidade': secao.quantidade_vendida,
            'receita': float(secao.receita_total),
            'custo': custo_total,
            'lucro': float(secao.receita_total) - custo_total
        }
    
    # Processar categorias de pratos
    for cat in vendas_categorias_prato:
        categoria = cat.categoria or 'Sem Categoria'
        nome_categoria = f'Categoria: {categoria}'
        
        # Obter pratos desta categoria do tenant
        pratos = Prato.query.filter_by(categoria=categoria, restaurant_id=restaurant_id).all()
        custo_total = 0
        
        for prato in pratos:
            # Obter vendas específicas deste prato no período
            vendas_prato = HistoricoVendas.query.filter(
                HistoricoVendas.prato_id == prato.id,
                HistoricoVendas.data >= inicio_periodo,
                HistoricoVendas.data <= fim_periodo,
                HistoricoVendas.restaurant_id == restaurant_id
            ).all()
            
            # Calcular custo
            if prato:
                for venda in vendas_prato:
                    custo_total += float(prato.custo_total_por_porcao or 0) * venda.quantidade
        
        # Adicionar aos dados por categoria
        if nome_categoria not in categorias_dados:
            categorias_dados[nome_categoria] = {
                'tipo': 'Categoria',
                'nome': categoria,
                'quantidade': 0,
                'receita': 0,
                'custo': 0,
                'lucro': 0
            }
        
        categorias_dados[nome_categoria]['quantidade'] += cat.quantidade_vendida
        categorias_dados[nome_categoria]['receita'] += float(cat.receita_total)
        categorias_dados[nome_categoria]['custo'] += custo_total
        categorias_dados[nome_categoria]['lucro'] += float(cat.receita_total) - custo_total
    
    # Calcular margens
    for nome, dados in categorias_dados.items():
        dados['margem'] = (dados['lucro'] / dados['receita'] * 100) if dados['receita'] > 0 else 0
    
    # Converter para lista e ordenar por margem de lucro
    categorias_lista = []
    for nome, dados in categorias_dados.items():
        categorias_lista.append({
            'nome': nome,
            'tipo': dados['tipo'],
            'categoria': dados['nome'],
            'quantidade': dados['quantidade'],
            'receita': dados['receita'],
            'custo': dados['custo'],
            'lucro': dados['lucro'],
            'margem': dados['margem']
        })
    
    # Ordenar por margem (maior para menor)
    categorias_lista.sort(key=lambda x: x['margem'], reverse=True)
    
    # Calcular totais gerais
    total_receita = sum(c['receita'] for c in categorias_lista)
    total_custo = sum(c['custo'] for c in categorias_lista)
    total_lucro = total_receita - total_custo
    margem_media_geral = (total_lucro / total_receita * 100) if total_receita > 0 else 0
    
    # Preparar dados para gráficos
    dados_grafico = {
        'categorias': [c['nome'] for c in categorias_lista],
        'receitas': [c['receita'] for c in categorias_lista],
        'lucros': [c['lucro'] for c in categorias_lista],
        'margens': [c['margem'] for c in categorias_lista]
    }
    
    return render_template('dashboard/relatorio_categorias.html',
                          data_inicio=inicio_periodo.strftime('%Y-%m-%d'),
                          data_fim=fim_periodo.strftime('%Y-%m-%d'),
                          categorias=categorias_lista,
                          dados_grafico=json.dumps(dados_grafico),
                          total_receita=total_receita,
                          total_custo=total_custo,
                          total_lucro=total_lucro,
                          margem_media=margem_media_geral)

@bp.route('/api/bcg-matrix')
@login_required
@pro_required
def api_bcg_matrix():
    """API para obter dados da Matriz BCG"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify({'datasets': []})
        
    # Reutilizar lógica existente
    hoje = date.today()
    periodo = request.args.get('periodo', 'mensal')
    
    if periodo == 'mensal':
        inicio_periodo = date(hoje.year, hoje.month, 1)
        fim_periodo = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    # ... outros períodos ...
    else:
        inicio_periodo = date(hoje.year, hoje.month, 1)
        fim_periodo = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
        
    dados_bcg = obter_dados_matriz_bcg(inicio_periodo, fim_periodo, restaurant_id)
    return jsonify(dados_bcg)
