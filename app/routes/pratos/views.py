from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from app.extensions import db
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_produto import Produto
from app.models.modelo_custo import CustoIndireto
from app.routes.pratos import bp
from datetime import datetime, date
from app.utils.tenant import get_current_restaurant_id
import pandas as pd
import io
from sqlalchemy import func
from sqlalchemy.orm import joinedload

@bp.route('/')
@bp.route('/index')
def index():
    """Lista todos os pratos"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    categoria = request.args.get('categoria')
    ordenar_por = request.args.get('ordenar_por', 'nome')
    
    # Construir query base com filtro de tenant
    query = Prato.query.filter_by(restaurant_id=restaurant_id).options(
        joinedload(Prato.insumos).joinedload(PratoInsumo.produto)
    )
    
    # Aplicar filtros
    if categoria:
        query = query.filter_by(categoria=categoria)
    
    # Aplicar ordenação
    if ordenar_por == 'custo':
        # Aqui estamos ordenando pelos pratos mais caros primeiro
        # Não é possível fazer isso diretamente via SQL pois é uma propriedade calculada
        # Seria necessário usar raw SQL ou obter todos e ordenar na memória
        pratos = query.all()
        pratos.sort(key=lambda p: p.custo_total_por_porcao, reverse=True)
        
        # Paginacao manual
        per_page = 20
        total = len(pratos)
        start = (page - 1) * per_page
        end = start + per_page
        pratos_page = pratos[start:end]
        
        # Simular um objeto de paginação
        from collections import namedtuple
        Pagination = namedtuple('Pagination', ['items', 'page', 'per_page', 'total', 'pages'])
        pages = (total + per_page - 1) // per_page  # Arredonda para cima
        paginacao = Pagination(pratos_page, page, per_page, total, pages)
        
    else:  # ordenar por nome ou outro campo direto
        if ordenar_por == 'nome':
            query = query.order_by(Prato.nome)
        elif ordenar_por == 'categoria':
            query = query.order_by(Prato.categoria, Prato.nome)
        elif ordenar_por == 'preco':
            query = query.order_by(Prato.preco_venda.desc())
        
        # Paginacao via SQLAlchemy
        paginacao = query.paginate(page=page, per_page=20, error_out=False)
    
    # Obter lista de categorias para filtro
    # Usa query separada limpa (sem joins desnecessários) para categorias
    categorias = db.session.query(Prato.categoria).filter_by(restaurant_id=restaurant_id).distinct().all()
    categorias = [c[0] for c in categorias if c[0]]
    
    return render_template('pratos/index.html', 
                          pratos=paginacao, 
                          categorias=categorias,
                          ordenar_por=ordenar_por)

@bp.route('/criar', methods=['GET', 'POST'])
def criar():
    """Cria um novo prato"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        categoria = request.form.get('categoria')
        rendimento = request.form.get('rendimento', type=float)
        unidade_rendimento = request.form.get('unidade_rendimento')
        porcoes_rendimento = request.form.get('porcoes_rendimento', type=int)
        tempo_preparo = request.form.get('tempo_preparo', type=int)
        margem = request.form.get('margem', type=float, default=30.0)
        
        # Validações básicas
        if not nome or not rendimento or not unidade_rendimento or not porcoes_rendimento:
            flash('Nome, rendimento, unidade de rendimento e porções são obrigatórios!', 'danger')
            return redirect(url_for('pratos.criar'))
        
        # Verificar se nome já existe (dentro do tenant)
        if Prato.query.filter_by(nome=nome, restaurant_id=restaurant_id).first():
            flash('Já existe um prato com este nome!', 'danger')
            return redirect(url_for('pratos.criar'))
        
        # Criar o prato
        prato = Prato(
            nome=nome,
            descricao=descricao,
            categoria=categoria,
            rendimento=rendimento,
            unidade_rendimento=unidade_rendimento,
            porcoes_rendimento=porcoes_rendimento,
            tempo_preparo=tempo_preparo,
            margem=margem,
            restaurant_id=restaurant_id
        )
        
        # Obter o valor de rateio dos custos indiretos (média) do tenant
        primeiro_dia_mes = date.today().replace(day=1)
        valor_rateio = CustoIndireto.query.filter(
            CustoIndireto.restaurant_id == restaurant_id,
            CustoIndireto.data_referencia >= primeiro_dia_mes
        ).with_entities(func.avg(CustoIndireto.valor)).scalar() or 0
        
        prato.custo_indireto = valor_rateio
        
        db.session.add(prato)
        db.session.commit()
        
        # Processar ingredientes
        ingredientes = request.form.getlist('ingredientes[]')
        for ingrediente in ingredientes:
            quantidade = request.form.get(f'quantidade_{ingrediente}', type=float)
            produto = None
            # Se for número, buscar por ID
            if ingrediente.isdigit():
                produto = Produto.query.filter_by(id=int(ingrediente), restaurant_id=restaurant_id).first()
            else:
                # Buscar por nome no tenant
                produto = Produto.query.filter_by(nome=ingrediente, restaurant_id=restaurant_id).first()
                if not produto:
                    # Criar novo produto com unidade padrão 'un' e preço 0
                    produto = Produto(
                        nome=ingrediente, 
                        unidade='un', 
                        preco_unitario=0, 
                        restaurant_id=restaurant_id
                    )
                    db.session.add(produto)
                    db.session.flush()  # Para obter o ID
            if produto and quantidade and quantidade > 0:
                insumo = PratoInsumo(
                    prato_id=prato.id,
                    produto_id=produto.id,
                    quantidade=quantidade,
                    ordem=len(prato.insumos) + 1,
                    obrigatorio=True
                )
                db.session.add(insumo)
        db.session.commit()
        
        flash('Prato criado com sucesso!', 'success')
        return redirect(url_for('pratos.visualizar', id=prato.id))
    
    return render_template('pratos/criar.html')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Edita um prato existente"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        
        # Verificar se nome já existe (se for diferente do atual) no tenant
        if nome != prato.nome and Prato.query.filter_by(nome=nome, restaurant_id=restaurant_id).first():
            flash('Já existe um prato com este nome!', 'danger')
            return render_template('pratos/editar.html', prato=prato)
        
        # Atualizar dados
        prato.nome = nome
        prato.descricao = request.form.get('descricao')
        prato.categoria = request.form.get('categoria')
        prato.rendimento = request.form.get('rendimento', type=float)
        prato.unidade_rendimento = request.form.get('unidade_rendimento')
        prato.tempo_preparo = request.form.get('tempo_preparo', type=int)
        prato.margem = request.form.get('margem', type=float, default=30.0)
        
        # Atualizar preço sugerido
        if 'atualizar_preco' in request.form:
            prato.atualizar_preco_sugerido()
        
        db.session.commit()
        
        flash('Prato atualizado com sucesso!', 'success')
        return redirect(url_for('pratos.visualizar', id=id))
    
    return render_template('pratos/editar.html', prato=prato)

@bp.route('/visualizar/<int:id>')
def visualizar(id):
    """Visualiza detalhes de um prato"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Calcular informações adicionais
    custo_direto_total = prato.custo_direto_total
    custo_direto_por_porcao = prato.custo_direto_por_porcao
    custo_total_por_porcao = prato.custo_total_por_porcao
    preco_sugerido = prato.calcular_preco_sugerido()
    
    # Calcular margens
    margem_atual = 0
    if custo_total_por_porcao > 0 and prato.preco_venda:
        margem_atual = (float(prato.preco_venda) - custo_total_por_porcao) / custo_total_por_porcao * 100
    
    return render_template('pratos/visualizar.html', 
                          prato=prato,
                          custo_direto_total=custo_direto_total,
                          custo_direto_por_porcao=custo_direto_por_porcao,
                          custo_total_por_porcao=custo_total_por_porcao,
                          preco_sugerido=preco_sugerido,
                          margem_atual=margem_atual)

@bp.route('/adicionar_insumo/<int:id>', methods=['GET', 'POST'])
def adicionar_insumo(id):
    """Adiciona insumos a um prato"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        produto_id = request.form.get('produto_id', type=int)
        quantidade = request.form.get('quantidade', type=float)
        observacao = request.form.get('observacao')
        ordem = request.form.get('ordem', type=int, default=1)
        obrigatorio = 'obrigatorio' in request.form
        
        if not produto_id or not quantidade or quantidade <= 0:
            flash('Produto e quantidade válida são obrigatórios!', 'danger')
            produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
            return render_template('pratos/adicionar_insumo.html', prato=prato, produtos=produtos)
        
        # Validar se produto pertence ao tenant
        produto = Produto.query.filter_by(id=produto_id, restaurant_id=restaurant_id).first()
        if not produto:
            flash('Produto inválido.', 'danger')
            return redirect(url_for('pratos.visualizar', id=id))

        # Verificar se o insumo já existe neste prato
        insumo_existente = PratoInsumo.query.filter_by(
            prato_id=prato.id, produto_id=produto_id
        ).first()
        
        if insumo_existente:
            flash('Este insumo já está cadastrado neste prato! Edite-o em vez de adicionar novamente.', 'warning')
            return redirect(url_for('pratos.visualizar', id=id))
        
        # Criar o insumo
        insumo = PratoInsumo(
            prato_id=prato.id,
            produto_id=produto_id,
            quantidade=quantidade,
            observacao=observacao,
            ordem=ordem,
            obrigatorio=obrigatorio
        )
        
        db.session.add(insumo)
        db.session.commit()
        
        # Atualizar o preço sugerido do prato
        prato.atualizar_preco_sugerido()
        db.session.commit()
        
        flash('Insumo adicionado com sucesso!', 'success')
        
        # Verificar se o usuário quer adicionar mais insumos
        if 'continuar' in request.form:
            return redirect(url_for('pratos.adicionar_insumo', id=id))
        else:
            return redirect(url_for('pratos.visualizar', id=id))
    
    produtos = Produto.query.filter_by(restaurant_id=restaurant_id).order_by(Produto.nome).all()
    return render_template('pratos/adicionar_insumo.html', prato=prato, produtos=produtos)

@bp.route('/editar_insumo/<int:id>', methods=['GET', 'POST'])
def editar_insumo(id):
    """Edita um insumo de um prato"""
    restaurant_id = get_current_restaurant_id()
    # Garantir que o insumo pertence a um prato do tenant
    insumo = PratoInsumo.query.join(Prato).filter(PratoInsumo.id == id, Prato.restaurant_id == restaurant_id).first_or_404()
    prato = insumo.prato
    
    if request.method == 'POST':
        quantidade = request.form.get('quantidade', type=float)
        observacao = request.form.get('observacao')
        ordem = request.form.get('ordem', type=int, default=1)
        obrigatorio = 'obrigatorio' in request.form
        
        if not quantidade or quantidade <= 0:
            flash('Quantidade válida é obrigatória!', 'danger')
            return render_template('pratos/editar_insumo.html', insumo=insumo)
        
        # Atualizar o insumo
        insumo.quantidade = quantidade
        insumo.observacao = observacao
        insumo.ordem = ordem
        insumo.obrigatorio = obrigatorio
        
        db.session.commit()
        
        # Atualizar o preço sugerido do prato
        prato.atualizar_preco_sugerido()
        db.session.commit()
        
        flash('Insumo atualizado com sucesso!', 'success')
        return redirect(url_for('pratos.visualizar', id=prato.id))
    
    return render_template('pratos/editar_insumo.html', insumo=insumo)

@bp.route('/remover_insumo/<int:id>', methods=['POST'])
def remover_insumo(id):
    """Remove um insumo de um prato"""
    restaurant_id = get_current_restaurant_id()
    insumo = PratoInsumo.query.join(Prato).filter(PratoInsumo.id == id, Prato.restaurant_id == restaurant_id).first_or_404()
    prato_id = insumo.prato_id
    
    db.session.delete(insumo)
    db.session.commit()
    
    # Atualizar o preço sugerido do prato
    prato = Prato.query.get(prato_id)
    prato.atualizar_preco_sugerido()
    db.session.commit()
    
    flash('Insumo removido com sucesso!', 'success')
    return redirect(url_for('pratos.visualizar', id=prato_id))

@bp.route('/atualizar_preco/<int:id>', methods=['POST'])
def atualizar_preco(id):
    """Atualiza o preço de venda de um prato com base no preço sugerido"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Atualizar o preço sugerido
    preco_sugerido = prato.atualizar_preco_sugerido()
    
    flash(f'Preço de venda atualizado para R$ {float(prato.preco_venda):.2f}', 'success')
    return redirect(url_for('pratos.visualizar', id=id))

@bp.route('/definir_preco/<int:id>', methods=['POST'])
def definir_preco(id):
    """Define manualmente o preço de venda"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    preco_manual = request.form.get('preco_manual', type=float)
    if not preco_manual or preco_manual < 0:
        flash('Preço inválido!', 'danger')
        return redirect(url_for('pratos.visualizar', id=id))
    
    prato.preco_venda = preco_manual
    db.session.commit()
    
    flash(f'Preço de venda definido manualmente para R$ {preco_manual:.2f}', 'success')
    return redirect(url_for('pratos.visualizar', id=id))

@bp.route('/ficha_tecnica/<int:id>')
def ficha_tecnica(id):
    """Exibe a ficha técnica completa de um prato"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Ordenar insumos por ordem
    insumos = sorted(prato.insumos, key=lambda i: i.ordem)
    
    return render_template('pratos/ficha_tecnica.html', prato=prato, insumos=insumos)

@bp.route('/exportar_ficha/<int:id>')
def exportar_ficha(id):
    """Exporta a ficha técnica para CSV"""
    from flask import Response
    
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Ordenar insumos por ordem
    insumos = sorted(prato.insumos, key=lambda i: i.ordem)
    
    # Criar DataFrame de insumos
    data_insumos = [
        {
            'Ordem': i.ordem,
            'Produto': i.produto.nome,
            'Quantidade': i.quantidade,
            'Unidade': i.produto.unidade_medida,
            'Custo Unitário': float(i.produto.preco_unitario),
            'Custo Total': i.custo_total,
            'Custo por Porção': i.custo_por_porcao,
            'Obrigatório': 'Sim' if i.obrigatorio else 'Não',
            'Observação': i.observacao or ''
        } for i in insumos
    ]
    
    df_insumos = pd.DataFrame(data_insumos)
    
    # Criar DataFrame com informações do prato
    data_prato = [
        {
            'Nome': prato.nome,
            'Categoria': prato.categoria or '',
            'Rendimento': f"{prato.rendimento} {prato.unidade_rendimento}",
            'Tempo de Preparo': f"{prato.tempo_preparo} min" if prato.tempo_preparo else '',
            'Custo Direto Total': prato.custo_direto_total,
            'Custo Direto por Porção': prato.custo_direto_por_porcao,
            'Custo Indireto por Porção': float(prato.custo_indireto),
            'Custo Total por Porção': prato.custo_total_por_porcao,
            'Margem (%)': float(prato.margem),
            'Preço Sugerido': prato.calcular_preco_sugerido(),
            'Preço de Venda': float(prato.preco_venda) if prato.preco_venda else 0,
            'Descrição': prato.descricao or ''
        }
    ]
    
    df_prato = pd.DataFrame(data_prato)
    
    # Exportar para CSV
    output = io.StringIO()
    output.write("FICHA TÉCNICA DE PREPARO\n")
    df_prato.T.to_csv(output, header=False)
    output.write("\nINSUMOS\n")
    df_insumos.to_csv(output, index=False)
    
    # Retornar como download
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename=ficha_tecnica_{prato.nome}_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@bp.route('/relatorio_custos')
def relatorio_custos():
    """Relatório de custos de todos os pratos"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
        
    # Obter todos os pratos do tenant
    pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).all()
    
    # Ordenar por custo total (do mais caro para o mais barato)
    pratos.sort(key=lambda p: p.custo_total_por_porcao, reverse=True)
    
    # Calcular estatísticas
    custo_total = sum(p.custo_total_por_porcao for p in pratos)
    custo_medio = custo_total / len(pratos) if pratos else 0
    
    # Agrupar por categoria
    categorias = {}
    for prato in pratos:
        categoria = prato.categoria or 'Sem Categoria'
        if categoria not in categorias:
            categorias[categoria] = {
                'pratos': [],
                'custo_medio': 0
            }
        
        categorias[categoria]['pratos'].append(prato)
    
    # Calcular custo médio por categoria
    for categoria, dados in categorias.items():
        total = sum(p.custo_total_por_porcao for p in dados['pratos'])
        dados['custo_medio'] = total / len(dados['pratos'])
    
    return render_template('pratos/relatorio_custos.html',
                          pratos=pratos,
                          categorias=categorias,
                          custo_medio=custo_medio)

# API Endpoints
@bp.route('/api/listar')
def api_listar():
    """API para listar pratos (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).order_by(Prato.nome).all()
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'categoria': p.categoria,
            'rendimento': p.rendimento,
            'unidade_rendimento': p.unidade_rendimento,
            'preco_venda': float(p.preco_venda) if p.preco_venda else None,
            'custo_total': p.custo_total_por_porcao
        } for p in pratos
    ])

@bp.route('/api/ficha_tecnica/<int:id>')
def api_ficha_tecnica(id):
    """API para obter ficha técnica de um prato (JSON)"""
    restaurant_id = get_current_restaurant_id()
    prato = Prato.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    return jsonify({
        'id': prato.id,
        'nome': prato.nome,
        'descricao': prato.descricao,
        'categoria': prato.categoria,
        'rendimento': prato.rendimento,
        'unidade_rendimento': prato.unidade_rendimento,
        'tempo_preparo': prato.tempo_preparo,
        'custo_direto_total': prato.custo_direto_total,
        'custo_direto_por_porcao': prato.custo_direto_por_porcao,
        'custo_indireto': float(prato.custo_indireto),
        'custo_total_por_porcao': prato.custo_total_por_porcao,
        'margem': float(prato.margem),
        'preco_sugerido': prato.calcular_preco_sugerido(),
        'preco_venda': float(prato.preco_venda) if prato.preco_venda else None,
        'insumos': [
            {
                'id': i.id,
                'produto': {
                    'id': i.produto.id,
                    'nome': i.produto.nome,
                    'unidade_medida': i.produto.unidade_medida
                },
                'quantidade': i.quantidade,
                'custo_unitario': float(i.produto.preco_unitario),
                'custo_total': i.custo_total,
                'ordem': i.ordem,
                'obrigatorio': i.obrigatorio,
                'observacao': i.observacao
            } for i in sorted(prato.insumos, key=lambda x: x.ordem)
        ]
    })

@bp.route('/api/sugerir_ingredientes')
def sugerir_ingredientes():
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    termo = request.args.get('termo', '')
    ingredientes = Produto.query.filter(
        Produto.restaurant_id == restaurant_id,
        Produto.nome.ilike(f'%{termo}%')
    ).all()
    sugestoes = [{'id': i.id, 'nome': i.nome} for i in ingredientes]
    if not sugestoes and termo:
        sugestoes.append({'id': termo, 'nome': f'Adicionar novo ingrediente: {termo}'})
    return jsonify(sugestoes)

@bp.route('/api/verificar_estoque', methods=['GET'])
def verificar_estoque():
    """Verifica se há estoque suficiente para os ingredientes"""
    restaurant_id = get_current_restaurant_id()
    
    ingredientes = request.args.getlist('ingredientes[]')
    quantidades = request.args.getlist('quantidades[]')
    
    if not ingredientes or not quantidades or not restaurant_id:
        return jsonify([])
    
    resultado = []
    for i, ingrediente_id in enumerate(ingredientes):
        try:
            quantidade = float(quantidades[i])
            # Validar e buscar produto do tenant
            produto = Produto.query.filter_by(id=ingrediente_id, restaurant_id=restaurant_id).first()
            
            if produto:
                estoque_atual = produto.estoque_atual or 0
                estoque_suficiente = estoque_atual >= quantidade
                
                resultado.append({
                    'id': produto.id,
                    'nome': produto.nome,
                    'quantidade_necessaria': quantidade,
                    'estoque_atual': estoque_atual,
                    'unidade': produto.unidade,
                    'estoque_suficiente': estoque_suficiente
                })
        except (ValueError, TypeError):
            continue
    
    return jsonify(resultado)
