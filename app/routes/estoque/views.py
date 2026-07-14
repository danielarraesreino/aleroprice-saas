from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from app.extensions import db
from app.models.modelo_estoque import EstoqueMovimentacao
from app.models.modelo_produto import Produto
from app.models.modelo_fornecedor import Fornecedor
from app.routes.estoque import bp
from datetime import datetime, timedelta
from app.utils.tenant import get_current_restaurant_id
import pandas as pd
import io

@bp.route('/')
@bp.route('/index')
def index():
    """Lista movimentações de estoque"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))
        
    page = request.args.get('page', 1, type=int)
    
    # Parâmetros de filtro
    produto_id = request.args.get('produto_id', type=int)
    tipo = request.args.get('tipo')  # 'entrada' ou 'saída'
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Construir a query base com filtro de tenant
    query = EstoqueMovimentacao.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if produto_id:
        query = query.filter_by(produto_id=produto_id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        query = query.filter(EstoqueMovimentacao.data_movimentacao >= data_inicio)
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim = data_fim + timedelta(days=1)  # Incluir o dia completo
        query = query.filter(EstoqueMovimentacao.data_movimentacao < data_fim)
    
    # Ordenar e paginar
    movimentacoes = query.order_by(EstoqueMovimentacao.data_movimentacao.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter lista de produtos para filtro
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
    
    return render_template('estoque/index.html', 
                          movimentacoes=movimentacoes, 
                          produtos=produtos)

@bp.route('/entrada', methods=['GET', 'POST'])
def entrada():
    """Registra entrada manual de estoque"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        produto_id = request.form.get('produto_id', type=int)
        quantidade = request.form.get('quantidade', type=float)
        valor_unitario = request.form.get('valor_unitario', type=float)
        referencia = request.form.get('referencia')
        observacao = request.form.get('observacao')
        
        if not produto_id or not quantidade or quantidade <= 0:
            flash('Produto e quantidade válida são obrigatórios!', 'danger')
            produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
            return render_template('estoque/entrada.html', produtos=produtos)
        
        # Verificar se produto pertence ao tenant (defesa em profundidade)
        produto_check = Produto.query.filter_by(id=produto_id, restaurant_id=restaurant_id).first()
        if not produto_check:
             flash('Produto inválido.', 'danger')
             return redirect(url_for('estoque.index'))

        # Registrar movimento de entrada
        try:
            movimento = EstoqueMovimentacao.registrar_entrada(
                produto_id=produto_id,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                referencia=referencia or 'Entrada Manual',
                observacao=observacao
            )
            
            produto = Produto.query.get(produto_id) # Já validado tenant acima
            flash(f'Entrada registrada com sucesso! Novo estoque: {produto.estoque_atual} {produto.unidade_medida}', 'success')
            return redirect(url_for('estoque.index'))
            
        except ValueError as e:
            flash(f'Erro ao registrar entrada: {str(e)}', 'danger')
            produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
            return render_template('estoque/entrada.html', produtos=produtos)
    
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
    return render_template('estoque/entrada.html', produtos=produtos)

@bp.route('/saida', methods=['GET', 'POST'])
def saida():
    """Registra saída manual de estoque"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        produto_id = request.form.get('produto_id', type=int)
        quantidade = request.form.get('quantidade', type=float)
        referencia = request.form.get('referencia')
        observacao = request.form.get('observacao')
        
        if not produto_id or not quantidade or quantidade <= 0:
            flash('Produto e quantidade válida são obrigatórios!', 'danger')
            produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
            return render_template('estoque/saida.html', produtos=produtos)
        
        # Verificar se produto pertence ao tenant
        produto_check = Produto.query.filter_by(id=produto_id, restaurant_id=restaurant_id).first()
        if not produto_check:
             flash('Produto inválido.', 'danger')
             return redirect(url_for('estoque.index'))

        # Registrar movimento de saída
        try:
            movimento = EstoqueMovimentacao.registrar_saida(
                produto_id=produto_id,
                quantidade=quantidade,
                referencia=referencia or 'Saída Manual',
                observacao=observacao
            )
            
            produto = Produto.query.get(produto_id)
            flash(f'Saída registrada com sucesso! Novo estoque: {produto.estoque_atual} {produto.unidade_medida}', 'success')
            return redirect(url_for('estoque.index'))
            
        except ValueError as e:
            flash(f'Erro ao registrar saída: {str(e)}', 'danger')
            produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
            return render_template('estoque/saida.html', produtos=produtos)
    
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
    return render_template('estoque/saida.html', produtos=produtos)

@bp.route('/detalhe_produto/<int:id>')
def detalhe_produto(id):
    """Mostra detalhes do estoque de um produto"""
    restaurant_id = get_current_restaurant_id()
    produto = Produto.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Buscar movimentações deste produto (garantindo tenant através do produto, mas filtro explicito também é bom)
    page = request.args.get('page', 1, type=int)
    # Movimentações devem ter restaurant_id igual ao do produto
    movimentacoes = EstoqueMovimentacao.query.filter_by(
        produto_id=id, 
        restaurant_id=restaurant_id
    ).order_by(
        EstoqueMovimentacao.data_movimentacao.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('estoque/detalhe_produto.html', 
                          produto=produto, 
                          movimentacoes=movimentacoes)

@bp.route('/relatorio')
def relatorio():
    """Relatório de estoque atual"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
        
    # Obter todos os produtos com seu valor em estoque
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.categoria, Produto.nome).all()
    
    # Calcular totais
    total_valor_estoque = sum(p.calcular_valor_em_estoque() for p in produtos)
    total_itens = len(produtos)
    itens_em_falta = sum(1 for p in produtos if p.esta_em_falta())
    
    # Agrupar por categoria
    categorias = {}
    for produto in produtos:
        categoria = produto.categoria or 'Sem Categoria'
        if categoria not in categorias:
            categorias[categoria] = {
                'produtos': [],
                'total_valor': 0
            }
        
        valor_estoque = produto.calcular_valor_em_estoque()
        categorias[categoria]['produtos'].append(produto)
        categorias[categoria]['total_valor'] += valor_estoque
    
    return render_template('estoque/relatorio.html',
                          produtos=produtos,
                          categorias=categorias,
                          total_valor_estoque=total_valor_estoque,
                          total_itens=total_itens,
                          itens_em_falta=itens_em_falta)

@bp.route('/exportar_relatorio')
def exportar_relatorio():
    """Exporta relatório de estoque para CSV"""
    from flask import Response
    
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
    
    # Obter todos os produtos
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.categoria, Produto.nome).all()
    
    # Criar DataFrame
    data = [
        {
            'ID': p.id,
            'Código': p.codigo,
            'Nome': p.nome,
            'Categoria': p.categoria,
            'Unidade': p.unidade_medida if hasattr(p, 'unidade_medida') else p.unidade, # Verificar nome do campo
            'Estoque Atual': p.estoque_atual,
            'Estoque Mínimo': p.estoque_minimo,
            'Preço Unitário': float(p.preco_unitario),
            'Valor em Estoque': p.calcular_valor_em_estoque(),
            'Fornecedor': p.fornecedor.razao_social if p.fornecedor else 'N/A',
            'Status': 'Em Falta' if p.esta_em_falta() else 'Normal'
        } for p in produtos
    ]
    
    df = pd.DataFrame(data)
    
    # Gerar CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    
    # Retornar como download
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename=relatorio_estoque_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# API Endpoints
@bp.route('/api/movimentacoes/<int:produto_id>')
def api_movimentacoes(produto_id):
    """API para obter movimentações de um produto (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    # Verificar se produto pertence ao tenant
    produto_check = Produto.query.filter_by(id=produto_id, restaurant_id=restaurant_id).first()
    if not produto_check:
        return jsonify([])

    # Limite opcional
    limite = request.args.get('limite', type=int, default=100)
    
    movimentacoes = EstoqueMovimentacao.query.filter_by(
        produto_id=produto_id,
        restaurant_id=restaurant_id
    ).order_by(
        EstoqueMovimentacao.data_movimentacao.desc()
    ).limit(limite).all()
    
    return jsonify([
        {
            'id': m.id,
            'tipo': m.tipo,
            'quantidade': m.quantidade,
            'data': m.data_movimentacao.strftime('%d/%m/%Y %H:%M'),
            'referencia': m.referencia,
            'valor_unitario': float(m.valor_unitario) if m.valor_unitario else None,
            'observacao': m.observacao
        } for m in movimentacoes
    ])

@bp.route('/api/em_falta')
def api_em_falta():
    """API para listar produtos com estoque abaixo do mínimo (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    produtos = Produto.query.filter(
        Produto.restaurant_id == restaurant_id,
        Produto.estoque_atual < Produto.estoque_minimo
    ).all()
    
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'estoque_atual': p.estoque_atual,
            'estoque_minimo': p.estoque_minimo,
            'unidade': p.unidade_medida if hasattr(p, 'unidade_medida') else p.unidade,
            'percentual': (p.estoque_atual / p.estoque_minimo * 100) if p.estoque_minimo > 0 else 0
        } for p in produtos
    ])

@bp.route('/novo_produto', methods=['GET', 'POST'])
def novo_produto():
    """Cria um novo produto no estoque"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
        
    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        unidade = request.form.get('unidade')
        preco_unitario = request.form.get('preco_unitario', type=float, default=0)
        estoque_minimo = request.form.get('estoque_minimo', type=float, default=0)
        estoque_atual = request.form.get('estoque_atual', type=float, default=0)
        categoria = request.form.get('categoria')
        marca = request.form.get('marca')
        fornecedor_id = request.form.get('fornecedor_id', type=int)
        
        # Validações básicas
        if not nome or not unidade:
            flash('Nome e Unidade são obrigatórios!', 'danger')
            return redirect(url_for('estoque.novo_produto'))
        
        # Verificar se código já existe (se informado) e pertence ao tenant
        if codigo and Produto.query.filter_by(codigo=codigo, restaurant_id=restaurant_id).first():
            flash('Código de produto já cadastrado!', 'danger')
            return redirect(url_for('estoque.novo_produto'))
        
        # Criar novo produto
        produto = Produto(
            nome=nome,
            codigo=codigo,
            descricao=descricao,
            unidade_medida=unidade, # Ajustado nome do campo
            preco_unitario=preco_unitario,
            estoque_minimo=estoque_minimo,
            estoque_atual=estoque_atual,
            categoria=categoria,
            marca=marca,
            fornecedor_id=fornecedor_id,
            restaurant_id=restaurant_id
        )
        
        db.session.add(produto)
        db.session.commit()
        
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('estoque.index'))
    
    # Obter lista de fornecedores para o formulário
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    return render_template('estoque/novo_produto.html', fornecedores=fornecedores)
