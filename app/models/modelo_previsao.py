from app.extensions import db
from sqlalchemy import func
from datetime import datetime, date, timedelta
import json

class HistoricoVendas(db.Model):
    __tablename__ = 'historico_vendas'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, index=True)
    
    # Item vendido - pode ser prato ou item de cardápio
    cardapio_item_id = db.Column(db.Integer, db.ForeignKey('cardapio_item.id'))
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'))
    
    # Informações sobre a venda
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    valor_unitario = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    # Metadados para análise
    periodo_dia = db.Column(db.String(20))  # manhã, tarde, noite
    dia_semana = db.Column(db.Integer)  # 0-6 (segunda a domingo)
    semana_mes = db.Column(db.Integer)  # 1-5
    mes = db.Column(db.Integer)  # 1-12
    feriado = db.Column(db.Boolean, default=False)
    evento_especial = db.Column(db.String(100))  # ex: "Dia dos Namorados"
    clima = db.Column(db.String(50))  # ex: "chuvoso", "ensolarado"
    temperatura = db.Column(db.Float)  # temperatura média do dia
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relacionamentos
    cardapio_item = db.relationship('CardapioItem', backref='historico_vendas')
    prato = db.relationship('Prato', backref='historico_vendas')
    
    # Método para facilitar a criação de registros
    @classmethod
    def registrar_venda(cls, data, item_id, tipo_item, quantidade, valor_unitario, 
                      periodo_dia=None, evento_especial=None, clima=None, temperatura=None, restaurant_id=None):
        """Registra uma venda no histórico"""
        # Calcula informações derivadas da data
        if isinstance(data, str):
            data = datetime.strptime(data, '%Y-%m-%d').date()
        
        dia_semana = data.weekday()  # 0 = Segunda-feira, 6 = Domingo
        semana_mes = (data.day - 1) // 7 + 1
        mes = data.month
        
        # Verifica se é um item de cardápio ou prato
        cardapio_item_id = item_id if tipo_item == 'cardapio_item' else None
        prato_id = item_id if tipo_item == 'prato' else None
        
        # Cria o registro
        venda = cls(
            data=data,
            cardapio_item_id=cardapio_item_id,
            prato_id=prato_id,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=quantidade * valor_unitario,
            periodo_dia=periodo_dia,
            dia_semana=dia_semana,
            semana_mes=semana_mes,
            mes=mes,
            evento_especial=evento_especial,
            clima=clima,
            temperatura=temperatura,
            restaurant_id=restaurant_id
        )
        
        db.session.add(venda)
        db.session.commit()
        
        return venda
    
    def __repr__(self):
        item_nome = self.cardapio_item.prato.nome if self.cardapio_item else \
                    self.prato.nome if self.prato else "Item desconhecido"
        return f"<Venda: {item_nome} - {self.quantidade} unidades em {self.data}>"
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'data': self.data.isoformat(),
            'cardapio_item_id': self.cardapio_item_id,
            'prato_id': self.prato_id,
            'quantidade': self.quantidade,
            'valor_unitario': float(self.valor_unitario),
            'valor_total': float(self.valor_total),
            'periodo_dia': self.periodo_dia,
            'dia_semana': self.dia_semana,
            'semana_mes': self.semana_mes,
            'mes': self.mes,
            'feriado': self.feriado,
            'evento_especial': self.evento_especial,
            'clima': self.clima,
            'temperatura': self.temperatura,
            'cardapio_item': self.cardapio_item.to_dict() if self.cardapio_item else None,
            'prato': self.prato.to_dict() if self.prato else None
        }


class PrevisaoDemanda(db.Model):
    __tablename__ = 'previsao_demanda'
    id = db.Column(db.Integer, primary_key=True)
    data_criacao = db.Column(db.DateTime, default=func.now(), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    
    # Item para previsão - pode ser prato ou item de cardápio
    cardapio_item_id = db.Column(db.Integer, db.ForeignKey('cardapio_item.id'))
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'))
    
    # Método usado para a previsão
    metodo = db.Column(db.String(50), nullable=False)  # ex: media_movel, regressao_linear
    parametros = db.Column(db.Text)  # Parâmetros do modelo em formato JSON
    
    # Resultado da previsão
    valores_previstos = db.Column(db.Text, nullable=False)  # JSON com as previsões para cada dia
    confiabilidade = db.Column(db.Float)  # 0-1, quanto maior, mais confiável
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relacionamentos
    cardapio_item = db.relationship('CardapioItem', backref='previsoes_demanda')
    prato = db.relationship('Prato', backref='previsoes_demanda')
    
    def get_valores_previstos(self):
        """Retorna os valores previstos como dicionário"""
        if self.valores_previstos:
            return json.loads(self.valores_previstos)
        return {}
    
    def set_valores_previstos(self, valores):
        """Define os valores previstos a partir de um dicionário"""
        self.valores_previstos = json.dumps(valores)
    
    def get_previsao_para_data(self, data):
        """Retorna a previsão para uma data específica"""
        if isinstance(data, str):
            data = datetime.strptime(data, '%Y-%m-%d').date()
            
        valores = self.get_valores_previstos()
        data_str = data.isoformat()
        return valores.get(data_str, None)
    
    def __repr__(self):
        item_nome = self.cardapio_item.prato.nome if self.cardapio_item else \
                    self.prato.nome if self.prato else "Item desconhecido"
        return f"<Previsão para {item_nome}: {self.data_inicio} a {self.data_fim}>"
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'data_criacao': self.data_criacao.isoformat(),
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat(),
            'cardapio_item_id': self.cardapio_item_id,
            'prato_id': self.prato_id,
            'metodo': self.metodo,
            'parametros': json.loads(self.parametros) if self.parametros else None,
            'valores_previstos': self.get_valores_previstos(),
            'confiabilidade': self.confiabilidade,
            'cardapio_item': self.cardapio_item.to_dict() if self.cardapio_item else None,
            'prato': self.prato.to_dict() if self.prato else None
        }


class FatorSazonalidade(db.Model):
    __tablename__ = 'fator_sazonalidade'
    id = db.Column(db.Integer, primary_key=True)
    
    # Período de aplicação
    mes = db.Column(db.Integer)  # 1-12 ou None se for para dia da semana
    dia_semana = db.Column(db.Integer)  # 0-6 ou None se for para mês
    periodo_dia = db.Column(db.String(20))  # manhã, tarde, noite ou None
    evento = db.Column(db.String(100))  # ex: "Natal", "Feriados" ou None
    
    # Item ou categoria afetado
    cardapio_item_id = db.Column(db.Integer, db.ForeignKey('cardapio_item.id'))
    prato_id = db.Column(db.Integer, db.ForeignKey('pratos.id'))
    categoria_id = db.Column(db.Integer)  # Para afetar uma categoria inteira de itens
    
    # Fator de multiplicação e descrição
    fator = db.Column(db.Float, nullable=False, default=1.0)  # Ex: 1.2 = aumento de 20%
    descricao = db.Column(db.String(200))
    
    # Multi-Tenancy
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    
    # Relacionamentos
    cardapio_item = db.relationship('CardapioItem', backref='fatores_sazonalidade')
    prato = db.relationship('Prato', backref='fatores_sazonalidade')
    
    def __repr__(self):
        tipo = ''
        if self.mes:
            tipo = f"Mês {self.mes}"
        elif self.dia_semana is not None:
            dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            tipo = dias[self.dia_semana]
        elif self.evento:
            tipo = self.evento
            
        item = self.cardapio_item.prato.nome if self.cardapio_item else \
               self.prato.nome if self.prato else \
               f"Categoria {self.categoria_id}" if self.categoria_id else "Geral"
               
        return f"<Fator {self.fator} para {item} em {tipo}>"
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'mes': self.mes,
            'dia_semana': self.dia_semana,
            'periodo_dia': self.periodo_dia,
            'evento': self.evento,
            'cardapio_item_id': self.cardapio_item_id,
            'prato_id': self.prato_id,
            'categoria_id': self.categoria_id,
            'fator': self.fator,
            'descricao': self.descricao,
            'cardapio_item': self.cardapio_item.to_dict() if self.cardapio_item else None,
            'prato': self.prato.to_dict() if self.prato else None
        }
