#!/usr/bin/env python3
"""
Script para adicionar mais vendas em Novembro e Dezembro/2025
para melhorar a demonstração do sistema
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_prato import Prato
from app.models.modelo_previsao import HistoricoVendas
from datetime import datetime, timedelta
import random

app = create_app('default')

def adicionar_vendas_novembro_dezembro():
    """Adiciona vendas extras para Novembro e Dezembro/2025"""
    
    with app.app_context():
        print("🚀 Adicionando vendas para Novembro e Dezembro/2025...\n")
        
        # Buscar restaurante demo
        restaurante = Restaurante.query.filter_by(nome="Demo Bistrô").first()
        if not restaurante:
            print("❌ Restaurante Demo não encontrado!")
            return
        
        # Buscar pratos
        pratos = Prato.query.filter_by(restaurant_id=restaurante.id).all()
        if not pratos:
            print("❌ Nenhum prato encontrado!")
            return
        
        # Criar lista de pratos com popularidade
        pratos_info = []
        for prato in pratos:
            popularidade = 0.25 if 'Arroz' in prato.nome or 'Feijão' in prato.nome else \
                          0.20 if 'Suco' in prato.nome else \
                          0.15 if 'Frango' in prato.nome else \
                          0.10 if 'Refrigerante' in prato.nome else \
                          0.08 if 'Filé' in prato.nome else \
                          0.05
            pratos_info.append({
                'obj': prato,
                'popularidade': popularidade
            })
        
        # Normalizar popularidades
        total_pop = sum(p['popularidade'] for p in pratos_info)
        for p in pratos_info:
            p['popularidade'] = p['popularidade'] / total_pop
        
        # Períodos para adicionar vendas
        periodos = [
            {
                'nome': 'Novembro/2025',
                'inicio': datetime(2025, 11, 1),
                'fim': datetime(2025, 11, 30),
                'vendas_por_dia': (80, 150)  # Min e Max vendas por dia
            },
            {
                'nome': 'Dezembro/2025',
                'inicio': datetime(2025, 12, 1),
                'fim': datetime(2025, 12, 31),
                'vendas_por_dia': (100, 180)  # Dezembro tem mais movimento (festas)
            }
        ]
        
        total_vendas_criadas = 0
        
        for periodo in periodos:
            print(f"\n📅 Processando {periodo['nome']}...")
            vendas_periodo = 0
            
            # Limpar vendas existentes do período
            HistoricoVendas.query.filter(
                HistoricoVendas.data >= periodo['inicio'].date(),
                HistoricoVendas.data <= periodo['fim'].date(),
                HistoricoVendas.restaurant_id == restaurante.id
            ).delete()
            db.session.commit()
            
            data_atual = periodo['inicio']
            while data_atual <= periodo['fim']:
                dia_semana = data_atual.weekday()  # 0=Segunda, 6=Domingo
                
                # Fator de sazonalidade
                if dia_semana >= 5:  # Fim de semana
                    fator_dia = random.uniform(1.4, 1.8)
                elif dia_semana == 4:  # Sexta
                    fator_dia = random.uniform(1.2, 1.4)
                else:  # Segunda a Quinta
                    fator_dia = random.uniform(0.9, 1.1)
                
                # Dezembro tem fator extra (festas de fim de ano)
                if data_atual.month == 12:
                    if data_atual.day >= 20:  # Semana do Natal
                        fator_dia *= 1.5
                    elif data_atual.day >= 15:
                        fator_dia *= 1.2
                
                # Calcular vendas do dia
                min_vendas, max_vendas = periodo['vendas_por_dia']
                vendas_dia = int(random.uniform(min_vendas, max_vendas) * fator_dia)
                
                for _ in range(vendas_dia):
                    # Escolher prato baseado na popularidade
                    prato_escolhido = random.choices(
                        pratos_info,
                        weights=[p['popularidade'] for p in pratos_info],
                        k=1
                    )[0]
                    
                    prato_obj = prato_escolhido['obj']
                    
                    # Determinar período do dia
                    if random.random() < 0.85:  # 85% em almoço/jantar
                        periodo_dia = 'almoço' if random.random() < 0.53 else 'jantar'
                    else:
                        periodo_dia = 'outros'
                    
                    # Quantidade
                    quantidade = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1], k=1)[0]
                    
                    # Preço com pequena variação
                    preco_base = float(prato_obj.preco_venda)
                    variacao = random.uniform(0.95, 1.0)
                    valor_unitario = round(preco_base * variacao, 2)
                    
                    # Criar venda
                    venda = HistoricoVendas(
                        data=data_atual.date(),
                        prato_id=prato_obj.id,
                        quantidade=quantidade,
                        valor_unitario=valor_unitario,
                        valor_total=quantidade * valor_unitario,
                        periodo_dia=periodo_dia,
                        dia_semana=dia_semana,
                        semana_mes=(data_atual.day - 1) // 7 + 1,
                        mes=data_atual.month,
                        restaurant_id=restaurante.id
                    )
                    db.session.add(venda)
                    vendas_periodo += 1
                
                # Commit a cada 5 dias
                if data_atual.day % 5 == 0:
                    db.session.commit()
                    print(f"  ✓ Dia {data_atual.day:02d}: {vendas_periodo} vendas criadas")
                
                data_atual += timedelta(days=1)
            
            db.session.commit()
            total_vendas_criadas += vendas_periodo
            print(f"✅ {periodo['nome']}: {vendas_periodo} vendas criadas")
        
        print(f"\n🎉 Total de vendas adicionadas: {total_vendas_criadas}")
        print(f"\n📊 Agora você pode testar os relatórios:")
        print(f"   • Novembro/2025: http://127.0.0.1:5000/relatorio/pratos?data_inicio=2025-11-01&data_fim=2025-11-30")
        print(f"   • Dezembro/2025: http://127.0.0.1:5000/relatorio/pratos?data_inicio=2025-12-01&data_fim=2025-12-31")
        print(f"   • Nov+Dez/2025: http://127.0.0.1:5000/relatorio/pratos?data_inicio=2025-11-01&data_fim=2025-12-31\n")

if __name__ == '__main__':
    adicionar_vendas_novembro_dezembro()
