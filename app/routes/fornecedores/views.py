from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from app.extensions import db
from app.models.modelo_fornecedor import Fornecedor
from app.routes.fornecedores import bp
from app.utils.tenant import get_current_restaurant_id

@bp.route('/')
@bp.route('/index')
def index():
    """Lista todos os fornecedores"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    page = request.args.get('page', 1, type=int)
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('fornecedores/index.html', fornecedores=fornecedores)

@bp.route('/criar', methods=['GET', 'POST'])
def criar():
    """Cria um novo fornecedor"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        # Obter dados do formulário
        cnpj = request.form.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
        razao_social = request.form.get('razao_social')
        nome_fantasia = request.form.get('nome_fantasia')
        endereco = request.form.get('endereco')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep', '').replace('-', '')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        inscricao_estadual = request.form.get('inscricao_estadual')
        
        # Validações básicas
        if not cnpj or not razao_social:
            flash('CNPJ e Razão Social são obrigatórios!', 'danger')
            return render_template('fornecedores/criar.html')
        
        # Verificar se CNPJ já existe e pertence ao tenant
        if Fornecedor.query.filter_by(cnpj=cnpj, restaurant_id=restaurant_id).first():
            flash('CNPJ já cadastrado!', 'danger')
            return render_template('fornecedores/criar.html')
        
        # Criar novo fornecedor
        fornecedor = Fornecedor(
            cnpj=cnpj,
            razao_social=razao_social,
            nome_fantasia=nome_fantasia,
            endereco=endereco,
            cidade=cidade,
            estado=estado,
            cep=cep,
            telefone=telefone,
            email=email,
            inscricao_estadual=inscricao_estadual,
            restaurant_id=restaurant_id
        )
        
        db.session.add(fornecedor)
        db.session.commit()
        
        flash('Fornecedor cadastrado com sucesso!', 'success')
        return redirect(url_for('fornecedores.index'))
    
    return render_template('fornecedores/criar.html')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Edita um fornecedor existente"""
    restaurant_id = get_current_restaurant_id()
    fornecedor = Fornecedor.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    if request.method == 'POST':
        # Obter dados do formulário
        cnpj = request.form.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
        razao_social = request.form.get('razao_social')
        
        # Validações básicas
        if not cnpj or not razao_social:
            flash('CNPJ e Razão Social são obrigatórios!', 'danger')
            return render_template('fornecedores/editar.html', fornecedor=fornecedor)
        
        # Verificar se CNPJ já existe (se for diferente do atual) e pertence ao tenant
        if cnpj != fornecedor.cnpj and Fornecedor.query.filter_by(cnpj=cnpj, restaurant_id=restaurant_id).first():
            flash('CNPJ já cadastrado em outro fornecedor!', 'danger')
            return render_template('fornecedores/editar.html', fornecedor=fornecedor)
        
        # Atualizar dados
        fornecedor.cnpj = cnpj
        fornecedor.razao_social = razao_social
        fornecedor.nome_fantasia = request.form.get('nome_fantasia')
        fornecedor.endereco = request.form.get('endereco')
        fornecedor.cidade = request.form.get('cidade')
        fornecedor.estado = request.form.get('estado')
        fornecedor.cep = request.form.get('cep', '').replace('-', '')
        fornecedor.telefone = request.form.get('telefone')
        fornecedor.email = request.form.get('email')
        fornecedor.inscricao_estadual = request.form.get('inscricao_estadual')
        
        db.session.commit()
        
        flash('Fornecedor atualizado com sucesso!', 'success')
        return redirect(url_for('fornecedores.index'))
    
    return render_template('fornecedores/editar.html', fornecedor=fornecedor)

@bp.route('/visualizar/<int:id>')
def visualizar(id):
    """Visualiza detalhes de um fornecedor"""
    restaurant_id = get_current_restaurant_id()
    fornecedor = Fornecedor.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    return render_template('fornecedores/visualizar.html', fornecedor=fornecedor)

@bp.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    """Remove um fornecedor do sistema"""
    restaurant_id = get_current_restaurant_id()
    fornecedor = Fornecedor.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    
    # Verificar se possui produtos ou notas fiscais vinculadas
    if fornecedor.produtos.count() > 0 or fornecedor.notas_fiscais.count() > 0:
        # Ao invés de excluir, apenas marcar como inativo
        fornecedor.ativo = False
        db.session.commit()
        flash('Fornecedor marcado como inativo pois possui produtos ou notas fiscais vinculadas!', 'warning')
    else:
        db.session.delete(fornecedor)
        db.session.commit()
        flash('Fornecedor removido com sucesso!', 'success')
    
    return redirect(url_for('fornecedores.index'))

# API Endpoints
@bp.route('/api/listar')
def api_listar():
    """API para listar fornecedores (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])
        
    fornecedores = Fornecedor.query.filter_by(restaurant_id=restaurant_id).order_by(Fornecedor.razao_social).all()
    return jsonify([
        {
            'id': f.id,
            'cnpj': f.cnpj,
            'cnpj_formatado': f.cnpj_formatado,
            'razao_social': f.razao_social,
            'nome_fantasia': f.nome_fantasia,
            'cidade': f.cidade,
            'estado': f.estado,
            'ativo': f.ativo
        } for f in fornecedores
    ])

@bp.route('/api/buscar/<string:termo>')
def api_buscar(termo):
    """API para buscar fornecedores por termo (JSON)"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        return jsonify([])

    termo = f'%{termo}%'
    fornecedores = Fornecedor.query.filter(
        Fornecedor.restaurant_id == restaurant_id,
        (Fornecedor.razao_social.ilike(termo)) | 
        (Fornecedor.nome_fantasia.ilike(termo)) | 
        (Fornecedor.cnpj.ilike(termo))
    ).all()
    
    return jsonify([
        {
            'id': f.id,
            'cnpj': f.cnpj,
            'razao_social': f.razao_social,
            'nome_fantasia': f.nome_fantasia
        } for f in fornecedores
    ])
