from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from app.extensions import db
from app.models.modelo_produto import Produto
from app.models.modelo_fornecedor import Fornecedor
from app.routes.produtos import bp
from app.utils.tenant import get_current_restaurant_id

@bp.route('/')
@bp.route('/index')
def index():
    """Lista todos os produtos/insumos"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login')) # Ajustar redirecionamento se necessário
        
    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    filtro_categoria = request.args.get('categoria')
    filtro_fornecedor = request.args.get('fornecedor_id', type=int)
    filtro_estoque_baixo = request.args.get('estoque_baixo', type=bool, default=False)
    
    # Construir a query base
    query = Produto.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros se existirem
    if filtro_categoria:
        query = query.filter_by(categoria=filtro_categoria)
    if filtro_fornecedor:
        query = query.filter_by(fornecedor_id=filtro_fornecedor)
    if filtro_estoque_baixo:
        query = query.filter(Produto.estoque_atual < Produto.estoque_minimo)
    
    # Ordenar e paginar os resultados
    produtos = query.order_by(Produto.nome).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter lista de categorias para filtro
    categorias = db.session.query(Produto.categoria).filter_by(restaurant_id=restaurant_id).distinct().all()
    categorias = [c[0] for c in categorias if c[0]]  # Remover categorias nulas
    
    # Obter lista de fornecedores para filtro
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    
    return render_template('produtos/index.html', 
                           produtos=produtos, 
                           categorias=categorias,
                           fornecedores=fornecedores)

@bp.route('/criar', methods=['GET', 'POST'])
def criar():
    """Cria um novo produto/insumo"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
        
    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        codigo = request.form.get('codigo')
        descricao = request.form.get('descricao')
        unidade_medida = request.form.get('unidade_medida')
        preco_unitario = request.form.get('preco_unitario', type=float, default=0)
        estoque_minimo = request.form.get('estoque_minimo', type=float, default=0)
        estoque_atual = request.form.get('estoque_atual', type=float, default=0)
        categoria = request.form.get('categoria')
        marca = request.form.get('marca')
        fornecedor_id = request.form.get('fornecedor_id', type=int)
        
        # Validações básicas
        if not nome or not unidade_medida:
            flash('Nome e Unidade de Medida são obrigatórios!', 'danger')
            return redirect(url_for('produtos.criar'))
        
        # Verificar se código já existe (se informado) e pertence ao mesmo restaurante
        if codigo and Produto.query.filter_by(codigo=codigo, restaurant_id=restaurant_id).first():
            flash('Código de produto já cadastrado!', 'danger')
            return redirect(url_for('produtos.criar'))
        
        # Criar novo produto
        produto = Produto(
            nome=nome,
            codigo=codigo,
            descricao=descricao,
            unidade_medida=unidade_medida,
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
        return redirect(url_for('produtos.index'))
    
    # Obter lista de fornecedores para o formulário
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    return render_template('produtos/criar.html', fornecedores=fornecedores)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Edita um produto existente"""
    restaurant_id = get_current_restaurant_id()
    produto = Produto.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        codigo = request.form.get('codigo')
        
        # Verificar se código já existe (se for diferente do atual)
        if codigo and codigo != produto.codigo and Produto.query.filter_by(codigo=codigo, restaurant_id=restaurant_id).first():
            flash('Código de produto já cadastrado em outro produto!', 'danger')
            fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
            return render_template('produtos/editar.html', produto=produto, fornecedores=fornecedores)
        
        # Atualizar dados
        produto.nome = nome
        produto.codigo = codigo
        produto.descricao = request.form.get('descricao')
        produto.unidade_medida = request.form.get('unidade_medida')
        produto.preco_unitario = request.form.get('preco_unitario', type=float, default=0)
        produto.estoque_minimo = request.form.get('estoque_minimo', type=float, default=0)
        produto.categoria = request.form.get('categoria')
        produto.marca = request.form.get('marca')
        produto.fornecedor_id = request.form.get('fornecedor_id', type=int)
        
        db.session.commit()
        
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('produtos.index'))
    
    # Obter lista de fornecedores para o formulário
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    return render_template('produtos/editar.html', produto=produto, fornecedores=fornecedores)

@bp.route('/visualizar/<int:id>')
def visualizar(id):
    """Visualiza detalhes de um produto"""
    restaurant_id = get_current_restaurant_id()
    produto = Produto.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    return render_template('produtos/visualizar.html', produto=produto)

@bp.route('/ajustar-estoque/<int:id>', methods=['GET', 'POST'])
def ajustar_estoque(id):
    """Ajusta manualmente o estoque de um produto"""
    from app.models.modelo_estoque import EstoqueMovimentacao
    
    restaurant_id = get_current_restaurant_id()
    produto = Produto.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')  # 'entrada' ou 'saida'
        quantidade = request.form.get('quantidade', type=float)
        observacao = request.form.get('observacao')
        
        if not tipo or not quantidade or quantidade <= 0:
            flash('Tipo e quantidade válida são obrigatórios!', 'danger')
            return redirect(url_for('produtos.ajustar_estoque', id=id))
        
        # Verificar se há estoque suficiente para saída
        if tipo == 'saida' and produto.estoque_atual < quantidade:
            flash(f'Estoque insuficiente! Atual: {produto.estoque_atual} {produto.unidade_medida}', 'danger')
            return redirect(url_for('produtos.ajustar_estoque', id=id))
        
        # Registrar movimentação
        try:
            if tipo == 'entrada':
                movimento = EstoqueMovimentacao.registrar_entrada(
                    produto_id=produto.id,
                    quantidade=quantidade,
                    referencia='Ajuste Manual',
                    observacao=observacao
                )
            else:  # saída
                movimento = EstoqueMovimentacao.registrar_saida(
                    produto_id=produto.id,
                    quantidade=quantidade,
                    referencia='Ajuste Manual',
                    observacao=observacao
                )
            
            flash(f'Estoque ajustado com sucesso! Novo estoque: {produto.estoque_atual} {produto.unidade_medida}', 'success')
            return redirect(url_for('produtos.visualizar', id=id))
        
        except ValueError as e:
            flash(f'Erro ao ajustar estoque: {str(e)}', 'danger')
            return redirect(url_for('produtos.ajustar_estoque', id=id))
    
    return render_template('produtos/ajustar_estoque.html', produto=produto)

@bp.route('/em-falta')
def em_falta():
    """Lista produtos com estoque abaixo do mínimo"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    produtos = Produto.query.filter(
        Produto.restaurant_id == restaurant_id,
        Produto.estoque_atual < Produto.estoque_minimo
    ).order_by(
        # Ordenar por percentual de falta (quanto menor, mais em falta)
        (Produto.estoque_atual / Produto.estoque_minimo)
    ).all()
    
    return render_template('produtos/em_falta.html', produtos=produtos)

# API Endpoints
@bp.route('/api/listar')
def api_listar():
    """API para listar produtos (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'codigo': p.codigo,
            'unidade_medida': p.unidade_medida,
            'preco_unitario': float(p.preco_unitario),
            'estoque_atual': p.estoque_atual,
            'categoria': p.categoria
        } for p in produtos
    ])

@bp.route('/api/buscar/<string:termo>')
def api_buscar(termo):
    """API para buscar produtos por termo (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])

    termo = f'%{termo}%'
    produtos = Produto.query.filter(
        Produto.restaurant_id == restaurant_id,
        (Produto.nome.ilike(termo)) | 
        (Produto.codigo.ilike(termo)) | 
        (Produto.categoria.ilike(termo))
    ).all()
    
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'codigo': p.codigo,
            'unidade_medida': p.unidade_medida,
            'preco_unitario': float(p.preco_unitario),
            'estoque_atual': p.estoque_atual
        } for p in produtos
    ])
