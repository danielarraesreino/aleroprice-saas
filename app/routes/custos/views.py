from flask import render_template, redirect, url_for, flash, request, abort
from app.extensions import db
from app.models.modelo_custo import CustoIndireto
from app.routes.custos import bp
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models.modelo_prato import Prato
from app.models.modelo_estoque import EstoqueMovimentacao # Para estimar vendas se precisar
from app.utils.tenant import get_current_restaurant_id

@bp.route('/')
@bp.route('/index')
def index():
    """Lista custos indiretos"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        flash('Erro: Restaurante não identificado.', 'danger')
        return redirect(url_for('auth.login'))

    mes = request.args.get('mes', date.today().month, type=int)
    ano = request.args.get('ano', date.today().year, type=int)
    tipo = request.args.get('tipo', '')
    
    data_inicio = date(ano, mes, 1)
    if mes == 12:
        data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        data_fim = date(ano, mes + 1, 1) - timedelta(days=1)
    
    query = CustoIndireto.query.filter(
        CustoIndireto.data_referencia >= data_inicio,
        CustoIndireto.data_referencia <= data_fim,
        CustoIndireto.restaurant_id == restaurant_id
    )
    
    if tipo:
        query = query.filter_by(tipo=tipo)
        
    custos = query.all()
    total = sum(float(c.valor) for c in custos)
    
    return render_template('custos/index.html', 
                          custos=custos, 
                          total=total,
                          mes=mes,
                          ano=ano,
                          tipo=tipo)

@bp.route('/criar', methods=['GET', 'POST'])
def criar():
    """Cria novo custo"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        descricao = request.form.get('descricao')
        valor = request.form.get('valor', type=float)
        data_ref_str = request.form.get('data_referencia')
        tipo = request.form.get('tipo')
        recorrente = 'recorrente' in request.form
        parcelas = request.form.get('parcelas', type=int, default=1)
        
        if not descricao or not valor or not data_ref_str:
            flash('Campos obrigatórios faltando!', 'danger')
            return redirect(url_for('custos.criar'))
            
        try:
            data_ref = datetime.strptime(data_ref_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Data inválida.', 'danger')
            return redirect(url_for('custos.criar'))
        
        # Se for investimento parcelado
        if parcelas > 1:
            valor_parcela = valor / parcelas
            for i in range(parcelas):
                data_p = data_ref + relativedelta(months=i)
                novo = CustoIndireto(
                    descricao=f"{descricao} ({i+1}/{parcelas})",
                    valor=valor_parcela,
                    data_referencia=data_p,
                    tipo=tipo,
                    recorrente=False,
                    observacao=f"Parcela de investimento. Total: {valor}",
                    restaurant_id=restaurant_id
                )
                db.session.add(novo)
        else:
            custo = CustoIndireto(
                descricao=descricao,
                valor=valor,
                data_referencia=data_ref,
                tipo=tipo,
                recorrente=recorrente,
                restaurant_id=restaurant_id
            )
            db.session.add(custo)
            
        db.session.commit()
        flash('Custo adicionado com sucesso!', 'success')
        return redirect(url_for('custos.index'))
        
    return render_template('custos/criar.html', hoje=date.today())

@bp.route('/excluir/<int:id>')
def excluir(id):
    restaurant_id = get_current_restaurant_id()
    custo = CustoIndireto.query.filter_by(id=id, restaurant_id=restaurant_id).first_or_404()
    db.session.delete(custo)
    db.session.commit()
    flash('Custo removido.', 'success')
    return redirect(url_for('custos.index'))

@bp.route('/rateio', methods=['GET', 'POST'])
def rateio():
    """Calcula e aplica rateio aos pratos"""
    restaurant_id = get_current_restaurant_id()
    if not restaurant_id:
        abort(403)

    if request.method == 'POST':
        mes = request.form.get('mes', type=int)
        ano = request.form.get('ano', type=int)
        vendas_estimadas = request.form.get('vendas_estimadas', type=int)
        
        if not vendas_estimadas or vendas_estimadas <= 0:
            flash('Vendas estimadas inválidas.', 'danger')
            return redirect(url_for('custos.rateio'))
            
        data_base = date(ano, mes, 1)
        # Passar restaurant_id para o método atualizado
        qtd, valor_por_prato = CustoIndireto.atualizar_rateio_pratos(data_base, vendas_estimadas, restaurant_id)
        
        flash(f'Rateio aplicado! Valor adicionado por prato: R$ {valor_por_prato:.2f}', 'success')
        return redirect(url_for('pratos.index'))
        
    return render_template('custos/rateio.html', hoje=date.today())
