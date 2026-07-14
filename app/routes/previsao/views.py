from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, Response, abort
from app.extensions import db
from sqlalchemy import func, and_, or_
from app.models.modelo_previsao import HistoricoVendas, PrevisaoDemanda, FatorSazonalidade
from app.models.modelo_cardapio import CardapioItem, Cardapio, CardapioSecao
from app.models.modelo_prato import Prato
from app.routes.previsao import bp
from datetime import datetime, date, timedelta
from app.utils.tenant import get_current_restaurant_id
import pandas as pd
import numpy as np
import io
import json
import csv

# Funções de algoritmos de previsão
def calcular_media_movel(dados, janela=7):
    """Calcula previsão por média móvel simples"""
    if len(dados) < janela:
        return dados, 0.5  # baixa confiabilidade se poucos dados
    
    # Calcular médias móveis
    medias = []
    for i in range(len(dados) - janela + 1):
        medias.append(sum(dados[i:i+janela]) / janela)
    
    # Projetar para dias futuros (usamos a última média calculada)
    ultima_media = medias[-1] if medias else sum(dados) / len(dados)
    previsao = dados + [ultima_media] * janela
    
    # Calcular confiabilidade (usando desvio padrão como indicador)
    if len(dados) > 1:
        std = np.std(dados)
        mean = np.mean(dados)
        if mean > 0:
            cv = std / mean  # coeficiente de variação
            confiabilidade = max(0, min(1, 1 - cv))
        else:
            confiabilidade = 0.5
    else:
        confiabilidade = 0.5
    
    return previsao, confiabilidade

def calcular_regressao_linear(dados, dias_projecao=7):
    """Calcula previsão por regressão linear"""
    if len(dados) < 3:  # precisamos de um mínimo de pontos
        return dados + dados[-1:] * dias_projecao, 0.3
    
    # Criar arrays para X (dias) e Y (valores)
    x = np.array(range(len(dados)))
    y = np.array(dados)
    
    # Calcular coeficientes da regressão (y = mx + b)
    n = len(dados)
    m = (n * np.sum(x*y) - np.sum(x) * np.sum(y)) / (n * np.sum(x*x) - np.sum(x) ** 2)
    b = (np.sum(y) - m * np.sum(x)) / n
    
    # Calcular R² (coeficiente de determinação) para medir confiabilidade
    y_pred = m * x + b
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    confiabilidade = max(0, min(1, r2))  # limitar entre 0 e 1
    
    # Projetar valores futuros
    dias_futuros = np.array(range(len(dados), len(dados) + dias_projecao))
    valores_futuros = m * dias_futuros + b
    valores_futuros = [max(0, v) for v in valores_futuros]  # não permitir valores negativos
    
    return list(dados) + list(valores_futuros), confiabilidade


# Rotas do blueprint
@bp.route('/')
@bp.route('/index')
def index():
    """Página principal do módulo de previsão de demanda"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    # Obter estatísticas básicas (filtradas por tenant)
    total_registros = HistoricoVendas.query.filter_by(restaurant_id=restaurant_id).count()
    total_previsoes = PrevisaoDemanda.query.filter_by(restaurant_id=restaurant_id).count()
    
    # Verificar se há registros suficientes para previsões
    hoje = date.today()
    um_mes_atras = hoje - timedelta(days=30)
    registros_recentes = HistoricoVendas.query.filter(
        HistoricoVendas.data >= um_mes_atras,
        HistoricoVendas.restaurant_id == restaurant_id
    ).count()
    
    # Dados para gráfico de vendas recentes
    vendas_ultimos_dias = db.session.query(
        HistoricoVendas.data, 
        func.sum(HistoricoVendas.quantidade).label('total_vendas')
    ).filter(
        HistoricoVendas.data >= hoje - timedelta(days=30),
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(HistoricoVendas.data).order_by(HistoricoVendas.data).all()
    
    dados_grafico = {
        'datas': [venda.data.strftime('%d/%m') for venda in vendas_ultimos_dias],
        'valores': [float(venda.total_vendas) for venda in vendas_ultimos_dias]
    }
    
    # Itens mais vendidos (Top Pratos)
    top_pratos = db.session.query(
        Prato.nome,
        func.sum(HistoricoVendas.quantidade).label('total')
    ).join(
        HistoricoVendas, HistoricoVendas.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= um_mes_atras,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(Prato.id).order_by(func.sum(HistoricoVendas.quantidade).desc()).limit(5).all()
    
    # Top Itens de Cardápio
    # Nota: Precisamos filtrar também CardapioItem e Prato pelo restaurant_id para garantir consistência, 
    # embora o HistoricoVendas.restaurant_id já devesse ser suficiente.
    # Mas como o join é feito, é bom garantir.
    top_itens_cardapio = db.session.query(
        Prato.nome,
        func.sum(HistoricoVendas.quantidade).label('total')
    ).join(
        CardapioItem, HistoricoVendas.cardapio_item_id == CardapioItem.id
    ).join(
        Prato, CardapioItem.prato_id == Prato.id
    ).filter(
        HistoricoVendas.data >= um_mes_atras,
        HistoricoVendas.restaurant_id == restaurant_id
    ).group_by(Prato.id).order_by(func.sum(HistoricoVendas.quantidade).desc()).limit(5).all()
    
    # Últimas previsões geradas
    ultimas_previsoes = PrevisaoDemanda.query.filter_by(restaurant_id=restaurant_id).order_by(
        PrevisaoDemanda.data_criacao.desc()
    ).limit(5).all()
    
    return render_template('previsao/index.html',
                          total_registros=total_registros,
                          total_previsoes=total_previsoes,
                          dados_grafico=json.dumps(dados_grafico),
                          top_pratos=top_pratos,
                          top_itens_cardapio=top_itens_cardapio,
                          ultimas_previsoes=ultimas_previsoes,
                          registros_suficientes=registros_recentes > 14)  # precisa de pelo menos 2 semanas de dados


@bp.route('/historico')
def listar_historico():
    """Lista o histórico de vendas com opções de filtro"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo_item = request.args.get('tipo_item')  # 'cardapio_item' ou 'prato'
    item_id = request.args.get('item_id', type=int)
    
    # Construir query tenant-aware
    query = HistoricoVendas.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        query = query.filter(HistoricoVendas.data >= data_inicio)
    
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        query = query.filter(HistoricoVendas.data <= data_fim)
    
    if tipo_item == 'cardapio_item':
        query = query.filter(HistoricoVendas.cardapio_item_id != None)
        if item_id:
            query = query.filter(HistoricoVendas.cardapio_item_id == item_id)
    elif tipo_item == 'prato':
        query = query.filter(HistoricoVendas.prato_id != None)
        if item_id:
            query = query.filter(HistoricoVendas.prato_id == item_id)
    
    # Ordenar e paginar
    registros = query.order_by(HistoricoVendas.data.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter listas para os filtros (do tenant)
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    
    # Complex join filter for tenant items
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    return render_template('previsao/historico.html',
                          registros=registros,
                          pratos=pratos,
                          itens_cardapio=itens_cardapio)


@bp.route('/historico/registrar', methods=['GET', 'POST'])
def registrar_venda():
    """Registra uma nova venda no histórico"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        data = request.form.get('data')
        tipo_item = request.form.get('tipo_item')  # 'cardapio_item' ou 'prato'
        item_id = request.form.get('item_id', type=int)
        quantidade = request.form.get('quantidade', type=int)
        valor_unitario = request.form.get('valor_unitario', type=float)
        periodo_dia = request.form.get('periodo_dia')
        clima = request.form.get('clima')
        temperatura = request.form.get('temperatura', type=float)
        evento_especial = request.form.get('evento_especial')
        
        # Validações básicas
        if not data or not tipo_item or not item_id or not quantidade or not valor_unitario:
            flash('Data, tipo de item, item, quantidade e valor unitário são obrigatórios!', 'danger')
            pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
            itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
                Cardapio.ativo == True,
                Cardapio.restaurant_id == restaurant_id
            ).order_by(Prato.nome).all()
            return render_template('previsao/registrar_venda.html', pratos=pratos, itens_cardapio=itens_cardapio)
        
        # Verificar se o item existe e pertence ao tenant
        if tipo_item == 'cardapio_item':
            item = CardapioItem.query.join(CardapioSecao).join(Cardapio).filter(
                CardapioItem.id == item_id,
                Cardapio.restaurant_id == restaurant_id
            ).first()
            if not item:
                flash('Item de cardápio não encontrado ou inválido!', 'danger')
                return redirect(url_for('previsao.registrar_venda'))
        elif tipo_item == 'prato':
            p = Prato.query.filter_by(id=item_id, restaurant_id=restaurant_id).first()
            if not p:
                flash('Prato não encontrado ou inválido!', 'danger')
                return redirect(url_for('previsao.registrar_venda'))
        
        # Registrar a venda
        venda = HistoricoVendas.registrar_venda(
            data=data,
            item_id=item_id,
            tipo_item=tipo_item,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            periodo_dia=periodo_dia,
            evento_especial=evento_especial,
            clima=clima,
            temperatura=temperatura,
            restaurant_id=restaurant_id # Passar tenant ID
        )
        
        flash('Venda registrada com sucesso no histórico!', 'success')
        return redirect(url_for('previsao.listar_historico'))
    
    # GET: formulario para registrar venda
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    return render_template('previsao/registrar_venda.html',
                          pratos=pratos,
                          itens_cardapio=itens_cardapio,
                          data_hoje=date.today().strftime('%Y-%m-%d'))


@bp.route('/historico/importar', methods=['GET', 'POST'])
def importar_historico():
    """Importa histórico de vendas a partir de um arquivo CSV ou Excel com fuzzy matching"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        if 'arquivo_csv' not in request.files:
            flash('Nenhum arquivo enviado!', 'danger')
            return redirect(url_for('previsao.importar_historico'))
        
        arquivo = request.files['arquivo_csv']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado!', 'danger')
            return redirect(url_for('previsao.importar_historico'))
        
        # Verificar extensão do arquivo
        extensao = arquivo.filename.rsplit('.', 1)[-1].lower()
        if extensao not in ['csv', 'xlsx', 'xls']:
            flash('Por favor, envie um arquivo CSV ou Excel válido!', 'danger')
            return redirect(url_for('previsao.importar_historico'))
        
        # Processar o arquivo
        try:
            from app.utils.importacao import ImportadorVendas
            
            # Ler arquivo baseado na extensão
            if extensao == 'csv':
                # Tentar diferentes delimitadores
                try:
                    df = pd.read_csv(arquivo, delimiter=';', encoding='utf-8')
                except:
                    arquivo.seek(0)
                    try:
                        df = pd.read_csv(arquivo, delimiter=',', encoding='utf-8')
                    except:
                        arquivo.seek(0)
                        df = pd.read_csv(arquivo, delimiter=';', encoding='latin-1')
            else:  # Excel
                df = pd.read_excel(arquivo)
            
            # Verificar se o DataFrame não está vazio
            if df.empty:
                flash('O arquivo está vazio!', 'warning')
                return redirect(url_for('previsao.importar_historico'))
            
            # Inicializar importador
            importador = ImportadorVendas(restaurant_id)
            
            # Detectar colunas automaticamente
            mapeamento = importador.detectar_colunas(df)
            
            # Verificar se todas as colunas necessárias foram detectadas
            colunas_necessarias = ['data', 'produto', 'quantidade', 'valor']
            colunas_faltantes = [col for col in colunas_necessarias if col not in mapeamento]
            
            if colunas_faltantes:
                flash(f'Não foi possível detectar as seguintes colunas: {", ".join(colunas_faltantes)}. '
                      f'Certifique-se de que o arquivo contém colunas com nomes como: data, produto/item, quantidade, valor.', 
                      'danger')
                return redirect(url_for('previsao.importar_historico'))
            
            # Agregar vendas por data e produto
            df_agregado = importador.agregar_vendas(df, mapeamento)
            
            # Contadores para feedback
            total_linhas_originais = len(df)
            total_registros_agregados = len(df_agregado)
            total_importados = 0
            total_ignorados = 0
            produtos_nao_encontrados = []
            
            # Processar cada linha agregada
            for _, row in df_agregado.iterrows():
                try:
                    data = row['data']
                    nome_produto = row['produto']
                    quantidade = int(row['quantidade'])
                    valor_unitario = float(row['valor_unitario'])
                    
                    # Usar fuzzy matching para encontrar o prato
                    prato_id, score = importador.encontrar_prato_por_nome(nome_produto)
                    
                    if prato_id is None:
                        total_ignorados += 1
                        if nome_produto not in produtos_nao_encontrados:
                            produtos_nao_encontrados.append(nome_produto)
                        continue
                    
                    # Verificar se já existe registro para esta data e prato
                    registro_existente = HistoricoVendas.query.filter_by(
                        data=data,
                        prato_id=prato_id,
                        restaurant_id=restaurant_id
                    ).first()
                    
                    if registro_existente:
                        # Atualizar registro existente
                        registro_existente.quantidade += quantidade
                        registro_existente.valor_total = registro_existente.quantidade * valor_unitario
                    else:
                        # Criar novo registro
                        HistoricoVendas.registrar_venda(
                            data=data,
                            item_id=prato_id,
                            tipo_item='prato',
                            quantidade=quantidade,
                            valor_unitario=valor_unitario,
                            restaurant_id=restaurant_id
                        )
                    
                    # Processar baixa de estoque
                    importador.processar_baixa_estoque(prato_id, quantidade)
                    
                    total_importados += 1
                    
                except Exception as e:
                    total_ignorados += 1
                    current_app.logger.error(f'Erro ao importar linha: {str(e)}')
            
            # Commit final
            db.session.commit()
            
            # Mensagem de sucesso com estatísticas
            mensagem = f'✅ Importação concluída! {total_linhas_originais} linhas → {total_registros_agregados} registros agregados → {total_importados} importados com sucesso.'
            
            if total_ignorados > 0:
                mensagem += f' {total_ignorados} registros ignorados.'
            
            if produtos_nao_encontrados:
                mensagem += f' Produtos não encontrados: {", ".join(produtos_nao_encontrados[:5])}'
                if len(produtos_nao_encontrados) > 5:
                    mensagem += f' e mais {len(produtos_nao_encontrados) - 5}...'
            
            flash(mensagem, 'success' if total_ignorados == 0 else 'warning')
            return redirect(url_for('previsao.listar_historico'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar o arquivo: {str(e)}', 'danger')
            current_app.logger.error(f'Erro na importação: {str(e)}', exc_info=True)
            return redirect(url_for('previsao.importar_historico'))
    
    return render_template('previsao/importar_historico.html')


@bp.route('/historico/exportar')
def exportar_historico():
    """Exporta histórico de vendas para CSV"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    # Filtros opcionais
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    tipo_item = request.args.get('tipo_item')
    item_id = request.args.get('item_id', type=int)
    
    # Construir query tenant-aware
    query = HistoricoVendas.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        query = query.filter(HistoricoVendas.data >= data_inicio)
    
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        query = query.filter(HistoricoVendas.data <= data_fim)
    
    if tipo_item == 'cardapio_item':
        query = query.filter(HistoricoVendas.cardapio_item_id != None)
        if item_id:
            query = query.filter(HistoricoVendas.cardapio_item_id == item_id)
    elif tipo_item == 'prato':
        query = query.filter(HistoricoVendas.prato_id != None)
        if item_id:
            query = query.filter(HistoricoVendas.prato_id == item_id)
    
    # Executar a query
    registros = query.order_by(HistoricoVendas.data).all()
    
    # Preparar dados para exportação
    dados = []
    for registro in registros:
        item_nome = registro.cardapio_item.prato.nome if registro.cardapio_item else ''
        tipo_item = ''
        item_id = 0
        
        if registro.cardapio_item_id:
            item_nome = registro.cardapio_item.prato.nome if registro.cardapio_item else ''
            tipo_item = 'cardapio_item'
            item_id = registro.cardapio_item_id
        elif registro.prato_id:
            item_nome = registro.prato.nome if registro.prato else ''
            tipo_item = 'prato'
            item_id = registro.prato_id
        
        dados.append({
            'ID': registro.id,
            'Data': registro.data.strftime('%Y-%m-%d'),
            'Tipo Item': tipo_item,
            'Item ID': item_id,
            'Item Nome': item_nome,
            'Quantidade': registro.quantidade,
            'Valor Unitário': float(registro.valor_unitario),
            'Valor Total': float(registro.valor_total),
            'Período do Dia': registro.periodo_dia or '',
            'Dia da Semana': registro.dia_semana,
            'Clima': registro.clima or '',
            'Temperatura': registro.temperatura or '',
            'Evento Especial': registro.evento_especial or ''
        })
    
    # Criar DataFrame e exportar para CSV
    df = pd.DataFrame(dados)
    
    # Criar um buffer de memória para o CSV
    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
    csv_data = output.getvalue()
    
    # Criar resposta para download
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=historico_vendas_{timestamp}.csv'}
    )


@bp.route('/previsoes')
def listar_previsoes():
    """Lista todas as previsões de demanda"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    tipo_item = request.args.get('tipo_item')  # 'cardapio_item' ou 'prato'
    item_id = request.args.get('item_id', type=int)
    metodo = request.args.get('metodo')  # método de previsão
    
    # Construir query tenant-aware
    query = PrevisaoDemanda.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if tipo_item == 'cardapio_item':
        query = query.filter(PrevisaoDemanda.cardapio_item_id != None)
        if item_id:
            query = query.filter(PrevisaoDemanda.cardapio_item_id == item_id)
    elif tipo_item == 'prato':
        query = query.filter(PrevisaoDemanda.prato_id != None)
        if item_id:
            query = query.filter(PrevisaoDemanda.prato_id == item_id)
    
    if metodo:
        query = query.filter(PrevisaoDemanda.metodo == metodo)
    
    # Ordenar e paginar
    previsoes = query.order_by(PrevisaoDemanda.data_criacao.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter listas para os filtros
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    # Listar métodos disponíveis de previsão
    metodos_disponiveis = [
        {'id': 'media_movel', 'nome': 'Média Móvel'},
        {'id': 'regressao_linear', 'nome': 'Regressão Linear'},
        {'id': 'sazonalidade', 'nome': 'Modelo com Sazonalidade'}
    ]
    
    return render_template('previsao/previsoes.html',
                          previsoes=previsoes,
                          pratos=pratos,
                          itens_cardapio=itens_cardapio,
                          metodos_disponiveis=metodos_disponiveis)


@bp.route('/previsao/gerar', methods=['GET', 'POST'])
def gerar_previsao():
    """Gera uma nova previsão de demanda com base no histórico"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        tipo_item = request.form.get('tipo_item')  # 'cardapio_item' ou 'prato'
        item_id = request.form.get('item_id', type=int)
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        metodo = request.form.get('metodo')
        dias_projecao = request.form.get('dias_projecao', type=int, default=7)
        usar_sazonalidade = 'usar_sazonalidade' in request.form
        
        # Validações básicas
        if not tipo_item or not item_id or not data_inicio or not data_fim or not metodo:
            flash('Tipo de item, item, período de previsão e método são obrigatórios!', 'danger')
            pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
            itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
                Cardapio.ativo == True,
                Cardapio.restaurant_id == restaurant_id
            ).order_by(Prato.nome).all()
            return render_template('previsao/gerar_previsao.html', pratos=pratos, itens_cardapio=itens_cardapio)
        
        # Verificar se o item existe e é do tenant
        if tipo_item == 'cardapio_item':
            if not CardapioItem.query.join(CardapioSecao).join(Cardapio).filter(
                CardapioItem.id == item_id,
                Cardapio.restaurant_id == restaurant_id
            ).first():
                flash('Item de cardápio não encontrado!', 'danger')
                return redirect(url_for('previsao.gerar_previsao'))
        elif tipo_item == 'prato':
            if not Prato.query.filter_by(id=item_id, restaurant_id=restaurant_id).first():
                flash('Prato não encontrado!', 'danger')
                return redirect(url_for('previsao.gerar_previsao'))
        
        # Converter datas
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').date()
            
            if data_fim_dt <= data_inicio_dt:
                flash('A data final deve ser posterior à data inicial!', 'danger')
                return redirect(url_for('previsao.gerar_previsao'))
        except ValueError:
            flash('Formato de data inválido!', 'danger')
            return redirect(url_for('previsao.gerar_previsao'))
        
        # Obter histórico de vendas para gerar previsão
        hoje = date.today()
        # lógica melhorada: usar dados com mesmo dia da semana ou similar se possível, mas aqui estamos fazendo projeção simplificada
        # Pega dados de um período equivalente no passado para treinar o modelo
        data_passado_inicio = hoje - (data_fim_dt - data_inicio_dt) - timedelta(days=dias_projecao)
        data_passado_fim = hoje - timedelta(days=1)  # até ontem
        
        # Construir query do histórico tenant-aware
        if tipo_item == 'cardapio_item':
            query = HistoricoVendas.query.filter(
                HistoricoVendas.cardapio_item_id == item_id,
                HistoricoVendas.data >= data_passado_inicio,
                HistoricoVendas.data <= data_passado_fim,
                HistoricoVendas.restaurant_id == restaurant_id
            )
        else:  # prato
            query = HistoricoVendas.query.filter(
                HistoricoVendas.prato_id == item_id,
                HistoricoVendas.data >= data_passado_inicio,
                HistoricoVendas.data <= data_passado_fim,
                HistoricoVendas.restaurant_id == restaurant_id
            )
        
        historico = query.order_by(HistoricoVendas.data).all()
        
        # Verificar se há dados suficientes
        if len(historico) < 5:  # Requer pelo menos 5 pontos de dados
            flash('Não há dados históricos suficientes para gerar uma previsão confiável!', 'warning')
            return redirect(url_for('previsao.gerar_previsao'))
        
        # Preparar dados para o algoritmo de previsão
        datas = []
        valores = []
        
        # Agrupar por data (somar quantidades)
        dados_por_data = {}
        for reg in historico:
            data_str = reg.data.isoformat()
            if data_str not in dados_por_data:
                dados_por_data[data_str] = 0
            dados_por_data[data_str] += reg.quantidade
        
        # Ordenar por data
        for data_str in sorted(dados_por_data.keys()):
            datas.append(datetime.fromisoformat(data_str).date())
            valores.append(dados_por_data[data_str])
        
        # Aplicar fatores de sazonalidade se solicitado
        if usar_sazonalidade:
            # Obter fatores de sazonalidade aplicaveis ao item E ao tenant
            if tipo_item == 'cardapio_item':
                fatores = FatorSazonalidade.query.filter(
                    FatorSazonalidade.restaurant_id == restaurant_id,
                    or_(
                        FatorSazonalidade.cardapio_item_id == item_id,
                        and_(
                            FatorSazonalidade.cardapio_item_id == None,
                            FatorSazonalidade.prato_id == None
                        )
                    )
                ).all()
            else:  # prato
                fatores = FatorSazonalidade.query.filter(
                    FatorSazonalidade.restaurant_id == restaurant_id,
                    or_(
                        FatorSazonalidade.prato_id == item_id,
                        and_(
                            FatorSazonalidade.cardapio_item_id == None,
                            FatorSazonalidade.prato_id == None
                        )
                    )
                ).all()
            
            # Aplicar fatores
            for i, data in enumerate(datas):
                # Verificar cada fator
                for fator in fatores:
                    aplica_fator = False
                    
                    # Verificar mes
                    if fator.mes and fator.mes == data.month:
                        aplica_fator = True
                    
                    # Verificar dia da semana
                    if fator.dia_semana is not None and fator.dia_semana == data.weekday():
                        aplica_fator = True
                    
                    # Se algum criterio satisfeito, aplicar fator
                    if aplica_fator:
                        valores[i] = valores[i] / fator.fator  # Normalizar removendo o efeito sazonal
        
        # Executar algoritmo de previsão
        valores_previstos = {}
        confiabilidade = 0
        
        if metodo == 'media_movel':
            previsao, confiabilidade = calcular_media_movel(valores, janela=min(7, len(valores)))
        elif metodo == 'regressao_linear':
            previsao, confiabilidade = calcular_regressao_linear(valores, dias_projecao=(data_fim_dt - data_inicio_dt).days + 1)
        else:  # sazonalidade ou outro método futuro
            # Implementar outros métodos conforme necessário
            previsao, confiabilidade = calcular_regressao_linear(valores, dias_projecao=(data_fim_dt - data_inicio_dt).days + 1)
        
        # Criar dicionário de previsões por data
        # Primeiro, criar lista de datas para o período de previsão
        datas_previsao = []
        data_atual = data_inicio_dt
        while data_atual <= data_fim_dt:
            datas_previsao.append(data_atual)
            data_atual += timedelta(days=1)
        
        # Mapear valores previstos para as datas
        for i, data in enumerate(datas_previsao):
            if i < len(previsao):
                valor = previsao[len(valores) + i]  # pegar os valores da previsão (após dados históricos)
                
                # Aplicar fatores de sazonalidade de volta se foram usados
                if usar_sazonalidade:
                    for fator in fatores:
                        aplica_fator = False
                        
                        # Verificar mes
                        if fator.mes and fator.mes == data.month:
                            aplica_fator = True
                        
                        # Verificar dia da semana
                        if fator.dia_semana is not None and fator.dia_semana == data.weekday():
                            aplica_fator = True
                        
                        # Se algum criterio satisfeito, aplicar fator
                        if aplica_fator:
                            valor = valor * fator.fator  # Reaplica o efeito sazonal
                
                valores_previstos[data.isoformat()] = round(max(0, valor))  # arredondar e garantir não negativo
        
        # Criar registro de previsão
        previsao_obj = PrevisaoDemanda(
            data_inicio=data_inicio_dt,
            data_fim=data_fim_dt,
            metodo=metodo,
            parametros=json.dumps({
                'dias_projecao': dias_projecao,
                'usar_sazonalidade': usar_sazonalidade
            }),
            confiabilidade=confiabilidade,
            restaurant_id=restaurant_id
        )
        
        # Definir item da previsão
        if tipo_item == 'cardapio_item':
            previsao_obj.cardapio_item_id = item_id
        else:  # prato
            previsao_obj.prato_id = item_id
        
        # Salvar valores previstos
        previsao_obj.set_valores_previstos(valores_previstos)
        
        db.session.add(previsao_obj)
        db.session.commit()
        
        flash('Previsão de demanda gerada com sucesso!', 'success')
        return redirect(url_for('previsao.visualizar_previsao', id=previsao_obj.id))
    
    # GET: formulario para gerar previsão
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    # Data padrão para previsão (próximos 7 dias)
    hoje = date.today()
    data_inicio_padrao = hoje.strftime('%Y-%m-%d')
    data_fim_padrao = (hoje + timedelta(days=7)).strftime('%Y-%m-%d')
    
    return render_template('previsao/gerar_previsao.html',
                          pratos=pratos,
                          itens_cardapio=itens_cardapio,
                          data_inicio=data_inicio_padrao,
                          data_fim=data_fim_padrao)


@bp.route('/previsao/visualizar/<int:id>')
def visualizar_previsao(id):
    """Visualiza detalhes de uma previsão de demanda"""
    restaurant_id = get_current_restaurant_id()
    previsao = PrevisaoDemanda.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Obter nome do item
    item_nome = ''
    if previsao.cardapio_item_id:
        item = CardapioItem.query.get(previsao.cardapio_item_id)
        item_nome = item.prato.nome if item else 'Item de Cardápio'
    elif previsao.prato_id:
        item = Prato.query.get(previsao.prato_id)
        item_nome = item.nome if item else 'Prato'
    
    # Obter valores previstos
    valores_previstos = previsao.get_valores_previstos()
    
    # Preparar dados para gráfico
    datas = []
    valores = []
    for data_str, valor in sorted(valores_previstos.items()):
        data_obj = datetime.fromisoformat(data_str).date()
        datas.append(data_obj.strftime('%d/%m/%Y'))
        valores.append(valor)
    
    dados_grafico = {
        'datas': datas,
        'valores': valores
    }
    
    # Obter parâmetros do modelo
    parametros = {}
    if previsao.parametros:
        try:
            parametros = json.loads(previsao.parametros)
        except:
            parametros = {}
    
    # Traduzir nome do método
    nome_metodo = ''
    if previsao.metodo == 'media_movel':
        nome_metodo = 'Média Móvel'
    elif previsao.metodo == 'regressao_linear':
        nome_metodo = 'Regressão Linear'
    elif previsao.metodo == 'sazonalidade':
        nome_metodo = 'Modelo com Sazonalidade'
    else:
        nome_metodo = previsao.metodo
    
    return render_template('previsao/visualizar_previsao.html',
                          previsao=previsao,
                          item_nome=item_nome,
                          dados_grafico=json.dumps(dados_grafico),
                          parametros=parametros,
                          nome_metodo=nome_metodo,
                          valores_previstos=valores_previstos)


@bp.route('/sazonalidade')
def listar_fatores_sazonalidade():
    """Lista todos os fatores de sazonalidade"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return redirect(url_for('auth.login'))

    # Filtros opcionais
    tipo_item = request.args.get('tipo_item')  # 'cardapio_item', 'prato' ou 'geral'
    item_id = request.args.get('item_id', type=int)
    
    # Construir query tenant-aware
    query = FatorSazonalidade.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if tipo_item == 'cardapio_item':
        query = query.filter(FatorSazonalidade.cardapio_item_id != None)
        if item_id:
            query = query.filter(FatorSazonalidade.cardapio_item_id == item_id)
    elif tipo_item == 'prato':
        query = query.filter(FatorSazonalidade.prato_id != None)
        if item_id:
            query = query.filter(FatorSazonalidade.prato_id == item_id)
    elif tipo_item == 'geral':
        query = query.filter(
            FatorSazonalidade.cardapio_item_id == None,
            FatorSazonalidade.prato_id == None
        )
    
    # Ordenar fatores
    fatores = query.all()
    
    # Obter listas para os filtros
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    return render_template('previsao/fatores_sazonalidade.html',
                          fatores=fatores,
                          pratos=pratos,
                          itens_cardapio=itens_cardapio)


@bp.route('/sazonalidade/criar', methods=['GET', 'POST'])
def criar_fator_sazonalidade():
    """Cria um novo fator de sazonalidade"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        tipo_item = request.form.get('tipo_item')  # 'cardapio_item', 'prato' ou 'geral'
        item_id = request.form.get('item_id', type=int)
        tipo_sazonalidade = request.form.get('tipo_sazonalidade')  # 'mes', 'dia_semana' ou 'evento'
        mes = request.form.get('mes', type=int)
        dia_semana = request.form.get('dia_semana', type=int)
        evento = request.form.get('evento')
        fator = request.form.get('fator', type=float)
        descricao = request.form.get('descricao')
        
        # Validações básicas
        if not tipo_sazonalidade or not fator:
            flash('Tipo de sazonalidade e fator são obrigatórios!', 'danger')
            pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
            itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
                Cardapio.ativo == True,
                Cardapio.restaurant_id == restaurant_id
            ).order_by(Prato.nome).all()
            return render_template('previsao/criar_fator_sazonalidade.html', pratos=pratos, itens_cardapio=itens_cardapio)
        
        # Verificar tipo de sazonalidade
        if tipo_sazonalidade == 'mes' and not mes:
            flash('O mês é obrigatório para sazonalidade mensal!', 'danger')
            return redirect(url_for('previsao.criar_fator_sazonalidade'))
        elif tipo_sazonalidade == 'dia_semana' and dia_semana is None:
            flash('O dia da semana é obrigatório para sazonalidade semanal!', 'danger')
            return redirect(url_for('previsao.criar_fator_sazonalidade'))
        elif tipo_sazonalidade == 'evento' and not evento:
            flash('O nome do evento é obrigatório para sazonalidade por evento!', 'danger')
            return redirect(url_for('previsao.criar_fator_sazonalidade'))
        
        # Verificar item se não for geral E SE PERTENCE AO TENANT
        cardapio_item_id = None
        prato_id = None
        
        if tipo_item == 'cardapio_item':
            if not item_id:
                flash('Item de cardápio é obrigatório!', 'danger')
                return redirect(url_for('previsao.criar_fator_sazonalidade'))
            if not CardapioItem.query.join(CardapioSecao).join(Cardapio).filter(
                CardapioItem.id == item_id,
                Cardapio.restaurant_id == restaurant_id
            ).first():
                flash('Item inválido!', 'danger')
                return redirect(url_for('previsao.criar_fator_sazonalidade'))
            cardapio_item_id = item_id
        elif tipo_item == 'prato':
            if not item_id:
                flash('Prato é obrigatório!', 'danger')
                return redirect(url_for('previsao.criar_fator_sazonalidade'))
            if not Prato.query.filter_by(id=item_id, restaurant_id=restaurant_id).first():
                flash('Prato inválido!', 'danger')
                return redirect(url_for('previsao.criar_fator_sazonalidade'))
            prato_id = item_id
            
        # Criar o fator
        novo_fator = FatorSazonalidade(
            mes=mes if tipo_sazonalidade == 'mes' else None,
            dia_semana=dia_semana if tipo_sazonalidade == 'dia_semana' else None,
            evento=evento if tipo_sazonalidade == 'evento' else None,
            cardapio_item_id=cardapio_item_id,
            prato_id=prato_id,
            categoria_id=None, # Não implementado na UI ainda
            fator=fator,
            descricao=descricao,
            restaurant_id=restaurant_id
        )
        
        db.session.add(novo_fator)
        db.session.commit()
        
        flash('Fator de sazonalidade criado com sucesso!', 'success')
        return redirect(url_for('previsao.listar_fatores_sazonalidade'))
    
    # GET: formulario
    pratos = Prato.query.filter_by(restaurant_id=restaurant_id).order_by(Prato.nome).all()
    itens_cardapio = CardapioItem.query.join(CardapioSecao).join(Cardapio).join(Prato).filter(
        Cardapio.ativo == True,
        Cardapio.restaurant_id == restaurant_id
    ).order_by(Prato.nome).all()
    
    return render_template('previsao/criar_fator_sazonalidade.html',
                          pratos=pratos,
                          itens_cardapio=itens_cardapio)


@bp.route('/sazonalidade/excluir/<int:id>')
def excluir_fator_sazonalidade(id):
    """Exclui um fator de sazonalidade"""
    restaurant_id = get_current_restaurant_id()
    fator = FatorSazonalidade.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    db.session.delete(fator)
    db.session.commit()
    
    flash('Fator de sazonalidade excluído com sucesso!', 'success')
    return redirect(url_for('previsao.listar_fatores_sazonalidade'))
