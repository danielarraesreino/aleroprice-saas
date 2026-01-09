from flask import Blueprint, render_template, request, jsonify

from . import bp

@bp.route('/calculadora-roi', methods=['GET', 'POST'])
def calculadora_roi():
    """Calculadora de ROI pública (Lead Magnet)"""
    resultado = None
    faturamento = None
    
    if request.method == 'POST':
        try:
            faturamento_str = request.form.get('faturamento_estimado', '0')
            # Limpar formatação de moeda se houver (R$, pontos, virgulas)
            faturamento_str = faturamento_str.replace('R$', '').replace('.', '').replace(',', '.')
            faturamento = float(faturamento_str)
            
            # Estimativa de desperdício (10% - Dado de mercado Abrasel)
            desperdicio = faturamento * 0.10
            
            resultado = {
                'faturamento': faturamento,
                'desperdicio': desperdicio,
                'mensagem': f"Você pode estar perdendo R$ {desperdicio:,.2f} por mês em desperdício invisível."
            }
        except ValueError:
            resultado = {'erro': 'Por favor, insira um valor válido.'}
            
    return render_template('public/roi.html', resultado=resultado, faturamento=faturamento)
