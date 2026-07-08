#!/usr/bin/env python3
"""
Script para popular dados de demonstração de Desperdício e Doações
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_desperdicio import CategoriaDesperdicio, RegistroDesperdicio, MetaDesperdicio
from app.models.modelo_produto import Produto
from app.models.modelo_prato import Prato
from datetime import datetime, timedelta, date
import random

app = create_app('default')

def criar_categorias_desperdicio(restaurante):
    """Cria categorias de desperdício"""
    print("📂 Criando categorias de desperdício...")
    
    categorias_data = [
        {
            'nome': 'Sobras de Preparo',
            'descricao': 'Aparas, cascas, partes não utilizadas durante o preparo',
            'cor': '#FFA726'  # Laranja
        },
        {
            'nome': 'Estragado',
            'descricao': 'Produtos vencidos ou deteriorados',
            'cor': '#EF5350'  # Vermelho
        },
        {
            'nome': 'Sobras de Clientes',
            'descricao': 'Comida não consumida pelos clientes',
            'cor': '#FFCA28'  # Amarelo
        },
        {
            'nome': 'Erro de Preparo',
            'descricao': 'Pratos preparados incorretamente',
            'cor': '#FF7043'  # Laranja escuro
        },
        {
            'nome': 'Doação',
            'descricao': 'Alimentos doados para instituições (não é desperdício)',
            'cor': '#66BB6A'  # Verde
        }
    ]
    
    categorias = []
    for cat_data in categorias_data:
        # Verificar se já existe
        cat = CategoriaDesperdicio.query.filter_by(
            nome=cat_data['nome'],
            restaurant_id=restaurante.id
        ).first()
        
        if not cat:
            cat = CategoriaDesperdicio(
                nome=cat_data['nome'],
                descricao=cat_data['descricao'],
                cor=cat_data['cor'],
                ativo=True,
                restaurant_id=restaurante.id
            )
            db.session.add(cat)
            categorias.append(cat)
        else:
            categorias.append(cat)
    
    db.session.commit()
    print(f"✅ {len(categorias)} categorias criadas/encontradas")
    return categorias

def criar_registros_desperdicio(restaurante, categorias, produtos, pratos, dias=180):
    """Cria registros de desperdício e doações para os últimos N dias"""
    print(f"\n🗑️ Criando registros de desperdício e doações para {dias} dias...")
    
    # Limpar registros anteriores
    RegistroDesperdicio.query.filter_by(restaurant_id=restaurante.id).delete()
    db.session.commit()
    
    # Mapear categorias
    cat_sobras_preparo = next(c for c in categorias if c.nome == 'Sobras de Preparo')
    cat_estragado = next(c for c in categorias if c.nome == 'Estragado')
    cat_sobras_clientes = next(c for c in categorias if c.nome == 'Sobras de Clientes')
    cat_erro_preparo = next(c for c in categorias if c.nome == 'Erro de Preparo')
    cat_doacao = next(c for c in categorias if c.nome == 'Doação')
    
    data_inicial = datetime.now() - timedelta(days=dias)
    total_registros = 0
    
    # Instituições para doações
    instituicoes = [
        'Lar dos Idosos São Vicente',
        'Casa de Apoio Esperança',
        'Banco de Alimentos Municipal',
        'Projeto Prato Cheio',
        'Abrigo Novo Horizonte'
    ]
    
    for dia in range(dias):
        data_atual = data_inicial + timedelta(days=dia)
        dia_semana = data_atual.weekday()
        
        # Fator de desperdício (fins de semana têm mais)
        if dia_semana >= 5:  # Sábado ou Domingo
            fator_dia = random.uniform(1.3, 1.6)
        else:
            fator_dia = random.uniform(0.8, 1.1)
        
        # 1. Sobras de Preparo (diário)
        qtd_sobras_preparo = random.uniform(5, 10) * fator_dia
        produto_preparo = random.choice(produtos)
        registro = RegistroDesperdicio(
            data_registro=data_atual,
            categoria_id=cat_sobras_preparo.id,
            produto_id=produto_preparo['obj'].id,
            quantidade=round(qtd_sobras_preparo, 2),
            unidade='kg',
            valor_estimado=round(qtd_sobras_preparo * float(produto_preparo['obj'].preco_unitario) * 0.3, 2),
            motivo='Aparas e sobras do preparo diário',
            responsavel='Equipe de Cozinha',
            local='Cozinha',
            restaurant_id=restaurante.id
        )
        db.session.add(registro)
        total_registros += 1
        
        # 2. Sobras de Clientes (diário)
        qtd_sobras_clientes = random.uniform(8, 12) * fator_dia
        prato_sobra = random.choice(pratos)
        registro = RegistroDesperdicio(
            data_registro=data_atual,
            categoria_id=cat_sobras_clientes.id,
            prato_id=prato_sobra['obj'].id,
            quantidade=round(qtd_sobras_clientes, 2),
            unidade='kg',
            valor_estimado=round(qtd_sobras_clientes * float(prato_sobra['obj'].preco_venda) * 0.5, 2),
            motivo='Sobras deixadas pelos clientes',
            responsavel='Equipe de Salão',
            local='Salão',
            restaurant_id=restaurante.id
        )
        db.session.add(registro)
        total_registros += 1
        
        # 3. Erro de Preparo (ocasional)
        if random.random() < 0.4:  # 40% de chance por dia
            qtd_erro = random.uniform(1, 2)
            prato_erro = random.choice(pratos)
            registro = RegistroDesperdicio(
                data_registro=data_atual,
                categoria_id=cat_erro_preparo.id,
                prato_id=prato_erro['obj'].id,
                quantidade=round(qtd_erro, 2),
                unidade='un',
                valor_estimado=round(qtd_erro * float(prato_erro['obj'].preco_venda), 2),
                motivo=random.choice(['Pedido cancelado', 'Erro na preparação', 'Ponto incorreto']),
                responsavel='Cozinha',
                local='Cozinha',
                acoes_corretivas='Reforçar treinamento da equipe',
                restaurant_id=restaurante.id
            )
            db.session.add(registro)
            total_registros += 1
        
        # 4. Estragado (semanal)
        if dia % 7 == 0:  # Uma vez por semana
            qtd_estragado = random.uniform(2, 3)
            produto_estragado = random.choice(produtos)
            registro = RegistroDesperdicio(
                data_registro=data_atual,
                categoria_id=cat_estragado.id,
                produto_id=produto_estragado['obj'].id,
                quantidade=round(qtd_estragado, 2),
                unidade='kg',
                valor_estimado=round(qtd_estragado * float(produto_estragado['obj'].preco_unitario), 2),
                motivo='Produto vencido',
                responsavel='Estoque',
                local='Estoque',
                acoes_corretivas='Melhorar controle FIFO',
                restaurant_id=restaurante.id
            )
            db.session.add(registro)
            total_registros += 1
        
        # 5. Doações (2-3x por semana)
        if random.random() < 0.35:  # ~35% de chance = ~2.5x por semana
            qtd_doacao = random.randint(20, 30)  # Porções
            prato_doacao = random.choice(pratos)
            instituicao = random.choice(instituicoes)
            
            registro = RegistroDesperdicio(
                data_registro=data_atual,
                categoria_id=cat_doacao.id,
                prato_id=prato_doacao['obj'].id,
                quantidade=qtd_doacao,
                unidade='porções',
                valor_estimado=0,  # Doação não tem custo de desperdício
                motivo=f'Doação para {instituicao}',
                responsavel='Gerência',
                local='Salão',
                descricao=f'{qtd_doacao} porções de {prato_doacao["obj"].nome} doadas',
                restaurant_id=restaurante.id
            )
            db.session.add(registro)
            total_registros += 1
        
        # Commit a cada 10 dias
        if dia % 10 == 0:
            db.session.commit()
            print(f"  ✓ Dia {dia}/{dias}: {total_registros} registros criados")
    
    db.session.commit()
    print(f"✅ {total_registros} registros de desperdício e doações criados!")
    return total_registros

def criar_metas_desperdicio(restaurante, categorias):
    """Cria metas de redução de desperdício"""
    print("\n🎯 Criando metas de redução de desperdício...")
    
    # Limpar metas anteriores
    MetaDesperdicio.query.filter_by(restaurant_id=restaurante.id).delete()
    db.session.commit()
    
    # Mapear categorias
    cat_sobras_clientes = next(c for c in categorias if c.nome == 'Sobras de Clientes')
    cat_sobras_preparo = next(c for c in categorias if c.nome == 'Sobras de Preparo')
    cat_doacao = next(c for c in categorias if c.nome == 'Doação')
    
    metas_data = [
        {
            'descricao': 'Reduzir sobras de clientes em 20%',
            'data_inicio': date(2025, 11, 1),
            'data_fim': date(2026, 1, 31),
            'categoria_id': cat_sobras_clientes.id,
            'valor_inicial': 300.0,  # kg/mês
            'meta_reducao_percentual': 20.0,
            'acoes_propostas': '- Implementar opções de meia porção\n- Orientar clientes sobre tamanhos\n- Oferecer embalagens para levar',
            'responsavel': 'Gerente de Salão'
        },
        {
            'descricao': 'Reduzir desperdício de preparo em 15%',
            'data_inicio': date(2025, 12, 1),
            'data_fim': date(2026, 2, 28),
            'categoria_id': cat_sobras_preparo.id,
            'valor_inicial': 200.0,  # kg/mês
            'meta_reducao_percentual': 15.0,
            'acoes_propostas': '- Treinamento em técnicas de aproveitamento integral\n- Revisar fichas técnicas\n- Criar receitas com sobras',
            'responsavel': 'Chef de Cozinha'
        },
        {
            'descricao': 'Aumentar doações em 30%',
            'data_inicio': date(2025, 11, 1),
            'data_fim': date(2026, 1, 31),
            'categoria_id': cat_doacao.id,
            'valor_inicial': 80.0,  # porções/mês
            'meta_reducao_percentual': -30.0,  # Negativo = aumento
            'acoes_propostas': '- Firmar parceria com mais 2 instituições\n- Estabelecer rotina de doações\n- Divulgar ações sociais',
            'responsavel': 'Gerência'
        }
    ]
    
    metas = []
    for meta_data in metas_data:
        valor_meta = meta_data['valor_inicial'] * (1 - meta_data['meta_reducao_percentual'] / 100)
        
        meta = MetaDesperdicio(
            descricao=meta_data['descricao'],
            data_inicio=meta_data['data_inicio'],
            data_fim=meta_data['data_fim'],
            categoria_id=meta_data['categoria_id'],
            valor_inicial=meta_data['valor_inicial'],
            valor_meta=valor_meta,
            meta_reducao_percentual=meta_data['meta_reducao_percentual'],
            ativo=True,
            acoes_propostas=meta_data['acoes_propostas'],
            responsavel=meta_data['responsavel'],
            restaurant_id=restaurante.id
        )
        db.session.add(meta)
        metas.append(meta)
    
    db.session.commit()
    print(f"✅ {len(metas)} metas criadas!")
    return metas

def main():
    with app.app_context():
        print("🚀 Iniciando Seeding de Desperdício e Doações...\n")
        
        # Buscar restaurante demo
        restaurante = Restaurante.query.filter_by(nome="Demo Bistrô").first()
        if not restaurante:
            print("❌ Restaurante Demo não encontrado!")
            return
        
        # Buscar produtos e pratos
        produtos_objs = Produto.query.filter_by(restaurant_id=restaurante.id).all()
        pratos_objs = Prato.query.filter_by(restaurant_id=restaurante.id).all()
        
        if not produtos_objs or not pratos_objs:
            print("❌ Produtos ou pratos não encontrados! Execute seed_demo_full.py primeiro.")
            return
        
        # Preparar listas
        produtos = [{'obj': p} for p in produtos_objs]
        pratos = [{'obj': p} for p in pratos_objs]
        
        # 1. Criar categorias
        categorias = criar_categorias_desperdicio(restaurante)
        
        # 2. Criar registros de desperdício e doações
        total_registros = criar_registros_desperdicio(restaurante, categorias, produtos, pratos, dias=180)
        
        # 3. Criar metas
        metas = criar_metas_desperdicio(restaurante, categorias)
        
        print("\n" + "="*60)
        print("🎉 SEEDING DE DESPERDÍCIO COMPLETO!")
        print("="*60)
        print(f"\n📊 Resumo:")
        print(f"   • Categorias: {len(categorias)}")
        print(f"   • Registros: {total_registros}")
        print(f"   • Metas: {len(metas)}")
        print(f"\n🌐 Acesse: http://127.0.0.1:5000/desperdicio/index\n")

if __name__ == '__main__':
    main()
