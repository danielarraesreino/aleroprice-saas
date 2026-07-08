from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from app.extensions import db
from app.models.modelo_cardapio import Cardapio, CardapioSecao, CardapioItem
from app.models.modelo_prato import Prato
from app.routes.cardapios import bp
from datetime import datetime, date
from app.utils.tenant import get_current_restaurant_id
import pandas as pd
import io

@bp.route('/')
@bp.route('/index')
def index():
    """Lista todos os cardápios"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    
    # Filtros opcionais
    tipo = request.args.get('tipo')
    temporada = request.args.get('temporada')
    ativos = request.args.get('ativos', default=True, type=lambda v: str(v).lower() == 'true')
    
    # Construir query base
    query = Cardapio.query.filter_by(restaurant_id=restaurant_id)
    
    # Aplicar filtros
    if tipo:
        query = query.filter_by(tipo=tipo)
    if temporada:
        query = query.filter_by(temporada=temporada)
    if ativos is not None:
        query = query.filter_by(ativo=ativos)
    
    # Ordenar e paginar
    cardapios = query.order_by(Cardapio.data_inicio.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # Obter lista de tipos e temporadas para filtros (do tenant)
    tipos = db.session.query(Cardapio.tipo).filter_by(restaurant_id=restaurant_id).distinct().all()
    tipos = [t[0] for t in tipos if t[0]]
    
    temporadas = db.session.query(Cardapio.temporada).filter_by(restaurant_id=restaurant_id).distinct().all()
    temporadas = [t[0] for t in temporadas if t[0]]
    
    return render_template('cardapios/index.html', 
                          cardapios=cardapios,
                          tipos=tipos,
                          temporadas=temporadas)

@bp.route('/criar', methods=['GET', 'POST'])
def criar():
    """Cria um novo cardápio"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        temporada = request.form.get('temporada')
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        
        # Validações básicas
        if not nome or not data_inicio:
            flash('Nome e Data de Início são obrigatórios!', 'danger')
            return redirect(url_for('cardapios.criar'))
        
        # Converter datas
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            if data_fim:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                if data_fim < data_inicio:
                    flash('Data final deve ser posterior à data inicial!', 'danger')
                    return redirect(url_for('cardapios.criar'))
        except ValueError:
            flash('Formato de data inválido!', 'danger')
            return redirect(url_for('cardapios.criar'))
        
        # Criar o cardápio
        cardapio = Cardapio(
            nome=nome,
            descricao=descricao,
            tipo=tipo,
            temporada=temporada,
            data_inicio=data_inicio,
            data_fim=data_fim,
            ativo=True,
            restaurant_id=restaurant_id
        )
        
        db.session.add(cardapio)
        db.session.commit()
        
        flash('Cardápio criado com sucesso! Agora adicione seções e pratos.', 'success')
        return redirect(url_for('cardapios.adicionar_secao', id=cardapio.id))
    
    return render_template('cardapios/criar.html')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Edita um cardápio existente"""
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        # Obter dados do formulário
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        tipo = request.form.get('tipo')
        temporada = request.form.get('temporada')
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        ativo = 'ativo' in request.form
        
        # Validações básicas
        if not nome or not data_inicio:
            flash('Nome e Data de Início são obrigatórios!', 'danger')
            return render_template('cardapios/editar.html', cardapio=cardapio)
        
        # Converter datas
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            if data_fim:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                if data_fim < data_inicio:
                    flash('Data final deve ser posterior à data inicial!', 'danger')
                    return render_template('cardapios/editar.html', cardapio=cardapio)
        except ValueError:
            flash('Formato de data inválido!', 'danger')
            return render_template('cardapios/editar.html', cardapio=cardapio)
        
        # Atualizar o cardápio
        cardapio.nome = nome
        cardapio.descricao = descricao
        cardapio.tipo = tipo
        cardapio.temporada = temporada
        cardapio.data_inicio = data_inicio
        cardapio.data_fim = data_fim
        cardapio.ativo = ativo
        
        db.session.commit()
        
        flash('Cardápio atualizado com sucesso!', 'success')
        return redirect(url_for('cardapios.visualizar', id=id))
    
    return render_template('cardapios/editar.html', cardapio=cardapio)

@bp.route('/visualizar/<int:id>')
def visualizar(id):
    """Visualiza detalhes de um cardápio"""
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Ordenar seções pela ordem
    secoes = sorted(cardapio.secoes, key=lambda s: s.ordem)
    
    return render_template('cardapios/visualizar.html', 
                          cardapio=cardapio,
                          secoes=secoes)

@bp.route('/adicionar_secao/<int:id>', methods=['GET', 'POST'])
def adicionar_secao(id):
    """Adiciona uma seção ao cardápio"""
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        ordem = request.form.get('ordem', type=int, default=1)
        
        if not nome:
            flash('Nome da seção é obrigatório!', 'danger')
            return redirect(url_for('cardapios.adicionar_secao', id=id))
        
        # Criar a seção
        secao = CardapioSecao(
            cardapio_id=cardapio.id,
            nome=nome,
            descricao=descricao,
            ordem=ordem
        )
        
        db.session.add(secao)
        db.session.commit()
        
        flash('Seção adicionada com sucesso!', 'success')
        
        # Verificar se o usuário quer adicionar mais seções ou ir para adicionar itens
        if 'adicionar_itens' in request.form:
            return redirect(url_for('cardapios.adicionar_item', secao_id=secao.id))
        else:
            return redirect(url_for('cardapios.adicionar_secao', id=id))
    
    return render_template('cardapios/adicionar_secao.html', cardapio=cardapio)

@bp.route('/editar_secao/<int:id>', methods=['GET', 'POST'])
def editar_secao(id):
    """Edita uma seção do cardápio"""
    restaurant_id = get_current_restaurant_id()
    
    # Join manual para garantir tenant
    secao = CardapioSecao.query.join(Cardapio).filter(
        CardapioSecao.id == id, 
        Cardapio.restaurant_id == restaurant_id
    ).first_or_404()
    
    cardapio = secao.cardapio
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        ordem = request.form.get('ordem', type=int, default=1)
        
        if not nome:
            flash('Nome da seção é obrigatório!', 'danger')
            return render_template('cardapios/editar_secao.html', secao=secao)
        
        # Atualizar dados
        secao.nome = nome
        secao.descricao = descricao
        secao.ordem = ordem
        
        db.session.commit()
        
        flash('Seção atualizada com sucesso!', 'success')
        return redirect(url_for('cardapios.visualizar', id=cardapio.id))
    
    return render_template('cardapios/editar_secao.html', secao=secao)

@bp.route('/remover_secao/<int:id>', methods=['POST'])
def remover_secao(id):
    """Remove uma seção do cardápio"""
    restaurant_id = get_current_restaurant_id()
    secao = CardapioSecao.query.join(Cardapio).filter(
        CardapioSecao.id == id, 
        Cardapio.restaurant_id == restaurant_id
    ).first_or_404()
    cardapio_id = secao.cardapio_id
    
    db.session.delete(secao)
    db.session.commit()
    
    flash('Seção removida com sucesso!', 'success')
    return redirect(url_for('cardapios.visualizar', id=cardapio_id))

@bp.route('/adicionar_item/<int:secao_id>', methods=['GET', 'POST'])
def adicionar_item(secao_id):
    """Adiciona um item/prato a uma seção do cardápio"""
    restaurant_id = get_current_restaurant_id()
    # Verificar tenant via secao -> cardapio
    secao = CardapioSecao.query.join(Cardapio).filter(
        CardapioSecao.id == secao_id, 
        Cardapio.restaurant_id == restaurant_id
    ).first_or_404()
    cardapio = secao.cardapio
    
    if request.method == 'POST':
        prato_id = request.form.get('prato_id', type=int)
        preco_venda = request.form.get('preco_venda', type=float)
        ordem = request.form.get('ordem', type=int, default=1)
        destaque = 'destaque' in request.form
        disponivel = 'disponivel' in request.form
        observacao = request.form.get('observacao')
        
        if not prato_id:
            flash('Selecione um prato!', 'danger')
            pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).order_by(Prato.nome).all()
            return render_template('cardapios/adicionar_item.html', 
                                secao=secao, 
                                cardapio=cardapio,
                                pratos=pratos)
        
        # Validar prato tenant
        prato = Prato.query.filter_by(id=prato_id, restaurant_id=restaurant_id).first()
        if not prato:
            flash('Prato inválido.', 'danger')
            return redirect(url_for('cardapios.visualizar', id=cardapio.id))

        # Verificar se o prato já existe nesta seção
        item_existente = CardapioItem.query.filter_by(
            secao_id=secao_id, prato_id=prato_id
        ).first()
        
        if item_existente:
            flash('Este prato já está cadastrado nesta seção do cardápio!', 'warning')
            pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).order_by(Prato.nome).all()
            return render_template('cardapios/adicionar_item.html', 
                                secao=secao, 
                                cardapio=cardapio,
                                pratos=pratos)
        
        # Criar o item
        item = CardapioItem(
            secao_id=secao_id,
            prato_id=prato_id,
            preco_venda=preco_venda,
            ordem=ordem,
            destaque=destaque,
            disponivel=disponivel,
            observacao=observacao
        )
        
        db.session.add(item)
        db.session.commit()
        
        flash('Item adicionado com sucesso!', 'success')
        
        # Verificar se o usuário quer adicionar mais itens
        if 'continuar' in request.form:
            return redirect(url_for('cardapios.adicionar_item', secao_id=secao_id))
        else:
            return redirect(url_for('cardapios.visualizar', id=cardapio.id))
    
    # Obter lista de pratos disponíveis (do tenant)
    pratos = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).order_by(Prato.nome).all()
    
    return render_template('cardapios/adicionar_item.html', 
                          secao=secao, 
                          cardapio=cardapio,
                          pratos=pratos)

@bp.route('/editar_item/<int:id>', methods=['GET', 'POST'])
def editar_item(id):
    """Edita um item do cardápio"""
    restaurant_id = get_current_restaurant_id()
    # Complex join check
    item = CardapioItem.query.join(CardapioSecao).join(Cardapio).filter(
        CardapioItem.id == id,
        Cardapio.restaurant_id == restaurant_id
    ).first_or_404()
    
    secao = item.secao
    cardapio = secao.cardapio
    
    if request.method == 'POST':
        preco_venda = request.form.get('preco_venda', type=float)
        ordem = request.form.get('ordem', type=int, default=1)
        destaque = 'destaque' in request.form
        disponivel = 'disponivel' in request.form
        observacao = request.form.get('observacao')
        
        # Atualizar o item
        item.preco_venda = preco_venda
        item.ordem = ordem
        item.destaque = destaque
        item.disponivel = disponivel
        item.observacao = observacao
        
        db.session.commit()
        
        flash('Item atualizado com sucesso!', 'success')
        return redirect(url_for('cardapios.visualizar', id=cardapio.id))
    
    return render_template('cardapios/editar_item.html', 
                          item=item, 
                          secao=secao, 
                          cardapio=cardapio)

@bp.route('/remover_item/<int:id>', methods=['POST'])
def remover_item(id):
    """Remove um item do cardápio"""
    restaurant_id = get_current_restaurant_id()
    item = CardapioItem.query.join(CardapioSecao).join(Cardapio).filter(
        CardapioItem.id == id,
        Cardapio.restaurant_id == restaurant_id
    ).first_or_404()
    secao = item.secao
    cardapio_id = secao.cardapio_id
    
    db.session.delete(item)
    db.session.commit()
    
    flash('Item removido com sucesso!', 'success')
    return redirect(url_for('cardapios.visualizar', id=cardapio_id))

@bp.route('/exportar/<int:id>')
def exportar(id):
    """Exporta o cardápio para um arquivo CSV"""
    from flask import Response
    
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Dados do cardápio
    dados_cardapio = {
        'Nome': cardapio.nome,
        'Descrição': cardapio.descricao or '',
        'Tipo': cardapio.tipo or '',
        'Temporada': cardapio.temporada or '',
        'Data de Início': cardapio.data_inicio.strftime('%d/%m/%Y'),
        'Data de Fim': cardapio.data_fim.strftime('%d/%m/%Y') if cardapio.data_fim else 'Não definido',
        'Status': 'Ativo' if cardapio.ativo else 'Inativo',
        'Total de Pratos': cardapio.total_pratos,
        'Ticket Médio Estimado': f'R$ {cardapio.ticket_medio_estimado:.2f}'
    }
    
    df_cardapio = pd.DataFrame([dados_cardapio])
    
    # Lista de itens do cardápio
    itens_data = []
    
    for secao in sorted(cardapio.secoes, key=lambda s: s.ordem):
        for item in sorted(secao.itens, key=lambda i: i.ordem):
            itens_data.append({
                'Seção': secao.nome,
                'Ordem Seção': secao.ordem,
                'Prato': item.prato.nome,
                'Ordem Item': item.ordem,
                'Preço': float(item.get_preco_venda) if item.get_preco_venda else None,
                'Custo Total': item.prato.custo_total_por_porcao,
                'Margem (%)': float(item.prato.margem),
                'Destaque': 'Sim' if item.destaque else 'Não',
                'Disponível': 'Sim' if item.disponivel else 'Não',
                'Observação': item.observacao or ''
            })
    
    df_itens = pd.DataFrame(itens_data)
    
    # Exportar para CSV
    output = io.StringIO()
    output.write("DADOS DO CARDÁPIO\n")
    df_cardapio.T.to_csv(output, header=False)
    output.write("\nITENS DO CARDÁPIO\n")
    df_itens.to_csv(output, index=False)
    
    # Retornar como download
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename=cardapio_{cardapio.nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@bp.route('/imprimir/<int:id>')
def imprimir(id):
    """Exibe versão para impressão do cardápio"""
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Ordenar seções e itens
    secoes = sorted(cardapio.secoes, key=lambda s: s.ordem)
    
    for secao in secoes:
        secao.itens_ordenados = sorted(secao.itens, key=lambda i: i.ordem)
    
    return render_template('cardapios/imprimir.html', 
                          cardapio=cardapio,
                          secoes=secoes)

@bp.route('/sugestao')
def sugestao():
    """Sugere um cardápio com base em rentabilidade"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)
        
    # Obter pratos ativos ordenados por margem de lucro (do tenant)
    pratos_alta_margem = Prato.query.filter_by(ativo=True, restaurant_id=restaurant_id).all()
    
    # Ordenar por margem de lucro (em valor, não percentual)
    pratos_alta_margem.sort(
        key=lambda p: (float(p.preco_venda or 0) - p.custo_total_por_porcao) if p.preco_venda else 0, 
        reverse=True
    )
    
    # Agrupar por categoria
    pratos_por_categoria = {}
    for prato in pratos_alta_margem:
        categoria = prato.categoria or 'Sem Categoria'
        if categoria not in pratos_por_categoria:
            pratos_por_categoria[categoria] = []
        pratos_por_categoria[categoria].append(prato)
    
    # Calcular estatísticas gerais para o cardápio sugerido
    pratos_com_precos = [p for p in pratos_alta_margem if p.preco_venda and p.preco_venda > 0]
    if pratos_com_precos:
        preco_medio = sum(float(p.preco_venda) for p in pratos_com_precos) / len(pratos_com_precos)
        margem_media_percentual = sum(
            ((float(p.preco_venda) - p.custo_total_por_porcao) / float(p.preco_venda)) * 100 
            for p in pratos_com_precos if float(p.preco_venda) > 0
        ) / len(pratos_com_precos)
        custo_medio = sum(p.custo_total_por_porcao for p in pratos_com_precos) / len(pratos_com_precos)
    else:
        preco_medio = 0
        margem_media_percentual = 0
        custo_medio = 0
    
    # Estrutura de estatísticas para o template
    estatisticas = {
        'preco_medio': preco_medio,
        'margem_media': margem_media_percentual,
        'custo_medio': custo_medio,
        'total_pratos': len(pratos_alta_margem),
        'total_categorias': len(pratos_por_categoria),
        'popularidade_media': 7.5  # Valor estimado na escala 0-10 (pode ser calculado a partir de dados reais de vendas)
    }
    
    return render_template('cardapios/sugestao.html', 
                          pratos_por_categoria=pratos_por_categoria,
                          pratos_alta_margem=pratos_alta_margem[:10],  # Top 10 mais rentáveis
                          estatisticas=estatisticas)

# API Endpoints
@bp.route('/api/listar')
def api_listar():
    """API para listar cardápios (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])

    cardapios = Cardapio.query.filter_by(ativo=True, restaurant_id=restaurant_id).all()
    return jsonify([
        {
            'id': c.id,
            'nome': c.nome,
            'tipo': c.tipo,
            'temporada': c.temporada,
            'data_inicio': c.data_inicio.strftime('%d/%m/%Y'),
            'data_fim': c.data_fim.strftime('%d/%m/%Y') if c.data_fim else None,
            'total_pratos': c.total_pratos,
            'ticket_medio': round(c.ticket_medio_estimado, 2)
        } for c in cardapios
    ])

@bp.route('/api/cardapio/<int:id>')
def api_cardapio(id):
    """API para obter detalhes de um cardápio (JSON)"""
    restaurant_id = get_current_restaurant_id()
    cardapio = Cardapio.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Organizar por seções
    secoes_data = []
    for secao in sorted(cardapio.secoes, key=lambda s: s.ordem):
        itens_data = [
            {
                'id': item.id,
                'prato': {
                    'id': item.prato.id,
                    'nome': item.prato.nome,
                    'descricao': item.prato.descricao
                },
                'preco': float(item.get_preco_venda) if item.get_preco_venda else None,
                'ordem': item.ordem,
                'destaque': item.destaque,
                'disponivel': item.disponivel,
                'observacao': item.observacao
            } for item in sorted(secao.itens, key=lambda i: i.ordem) if item.disponivel
        ]
        
        secoes_data.append({
            'id': secao.id,
            'nome': secao.nome,
            'descricao': secao.descricao,
            'ordem': secao.ordem,
            'itens': itens_data
        })
    
    return jsonify({
        'id': cardapio.id,
        'nome': cardapio.nome,
        'descricao': cardapio.descricao,
        'tipo': cardapio.tipo,
        'temporada': cardapio.temporada,
        'data_inicio': cardapio.data_inicio.strftime('%d/%m/%Y'),
        'data_fim': cardapio.data_fim.strftime('%d/%m/%Y') if cardapio.data_fim else None,
        'ativo': cardapio.ativo,
        'secoes': secoes_data
    })
