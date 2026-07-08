"""
Módulo de importação inteligente de vendas
Fornece funcionalidades para importar vendas em massa com fuzzy matching e agregação
"""

from thefuzz import fuzz, process
from typing import List, Tuple, Optional, Dict, Any
import pandas as pd
from datetime import date
from app.models.modelo_prato import Prato, PratoInsumo
from app.models.modelo_produto import Produto
from app.models.modelo_estoque import MovimentacaoEstoque
from app.extensions import db


class ImportadorVendas:
    """Classe para processar importação de vendas em massa"""
    
    # Threshold mínimo para considerar um match válido
    FUZZY_THRESHOLD = 80
    
    # Mapeamentos de nomes de colunas possíveis
    COLUNAS_DATA = ['data', 'date', 'dia', 'fecha']
    COLUNAS_PRODUTO = ['produto', 'item', 'prato', 'nome', 'product', 'dish', 'nome_item']
    COLUNAS_QUANTIDADE = ['quantidade', 'qtd', 'qty', 'quantity', 'unidades']
    COLUNAS_VALOR = ['valor', 'preco', 'price', 'valor_unitario', 'preco_unitario', 'unit_price']
    
    def __init__(self, restaurant_id: int):
        """
        Inicializa o importador para um restaurante específico
        
        Args:
            restaurant_id: ID do restaurante (multi-tenancy)
        """
        self.restaurant_id = restaurant_id
        self.pratos_cache = None
        self.matches_cache = {}
    
    def _carregar_pratos(self) -> List[Prato]:
        """Carrega e cacheia os pratos do restaurante"""
        if self.pratos_cache is None:
            self.pratos_cache = Prato.query.filter_by(
                restaurant_id=self.restaurant_id,
                ativo=True
            ).all()
        return self.pratos_cache
    
    def encontrar_prato_por_nome(self, nome: str, threshold: int = None) -> Tuple[Optional[int], int]:
        """
        Encontra um prato usando fuzzy matching
        
        Args:
            nome: Nome do prato a buscar
            threshold: Score mínimo para considerar match (padrão: FUZZY_THRESHOLD)
        
        Returns:
            Tupla (prato_id, score) ou (None, 0) se não encontrar
        """
        if threshold is None:
            threshold = self.FUZZY_THRESHOLD
        
        # Verificar cache
        cache_key = nome.lower().strip()
        if cache_key in self.matches_cache:
            return self.matches_cache[cache_key]
        
        pratos = self._carregar_pratos()
        if not pratos:
            return None, 0
        
        # Criar dicionário de nomes para IDs
        nomes_pratos = {prato.nome: prato.id for prato in pratos}
        
        # Usar fuzzy matching
        resultado = process.extractOne(
            nome,
            nomes_pratos.keys(),
            scorer=fuzz.token_sort_ratio
        )
        
        if resultado and resultado[1] >= threshold:
            prato_nome, score = resultado[0], resultado[1]
            prato_id = nomes_pratos[prato_nome]
            
            # Cachear resultado
            self.matches_cache[cache_key] = (prato_id, score)
            
            return prato_id, score
        
        return None, 0
    
    def detectar_colunas(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detecta automaticamente as colunas do DataFrame
        
        Args:
            df: DataFrame com os dados importados
        
        Returns:
            Dicionário mapeando tipo de coluna para nome real
        """
        colunas = df.columns.str.lower().str.strip()
        mapeamento = {}
        
        # Detectar coluna de data
        for col_original, col_lower in zip(df.columns, colunas):
            if any(nome in col_lower for nome in self.COLUNAS_DATA):
                mapeamento['data'] = col_original
                break
        
        # Detectar coluna de produto
        for col_original, col_lower in zip(df.columns, colunas):
            if any(nome in col_lower for nome in self.COLUNAS_PRODUTO):
                mapeamento['produto'] = col_original
                break
        
        # Detectar coluna de quantidade
        for col_original, col_lower in zip(df.columns, colunas):
            if any(nome in col_lower for nome in self.COLUNAS_QUANTIDADE):
                mapeamento['quantidade'] = col_original
                break
        
        # Detectar coluna de valor
        for col_original, col_lower in zip(df.columns, colunas):
            if any(nome in col_lower for nome in self.COLUNAS_VALOR):
                mapeamento['valor'] = col_original
                break
        
        return mapeamento
    
    def agregar_vendas(self, df: pd.DataFrame, mapeamento: Dict[str, str]) -> pd.DataFrame:
        """
        Agrega vendas por data e produto
        
        Args:
            df: DataFrame com os dados
            mapeamento: Mapeamento de colunas
        
        Returns:
            DataFrame agregado
        """
        # Renomear colunas para padrão
        df_renamed = df.rename(columns={
            mapeamento['data']: 'data',
            mapeamento['produto']: 'produto',
            mapeamento['quantidade']: 'quantidade',
            mapeamento['valor']: 'valor_unitario'
        })
        
        # Converter data para formato correto
        df_renamed['data'] = pd.to_datetime(df_renamed['data']).dt.date
        
        # Converter quantidade e valor para numérico
        df_renamed['quantidade'] = pd.to_numeric(df_renamed['quantidade'], errors='coerce')
        df_renamed['valor_unitario'] = pd.to_numeric(
            df_renamed['valor_unitario'].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
        
        # Remover linhas com valores inválidos
        df_renamed = df_renamed.dropna(subset=['data', 'produto', 'quantidade', 'valor_unitario'])
        
        # Agregar por data e produto
        df_agregado = df_renamed.groupby(['data', 'produto']).agg({
            'quantidade': 'sum',
            'valor_unitario': 'mean'  # Média dos valores unitários
        }).reset_index()
        
        return df_agregado
    
    def processar_baixa_estoque(self, prato_id: int, quantidade_vendida: int) -> bool:
        """
        Processa a baixa de estoque baseada na ficha técnica do prato
        
        Args:
            prato_id: ID do prato vendido
            quantidade_vendida: Quantidade de porções vendidas
        
        Returns:
            True se processou com sucesso, False caso contrário
        """
        try:
            prato = Prato.query.get(prato_id)
            if not prato:
                return False
            
            # Obter insumos do prato
            insumos = PratoInsumo.query.filter_by(prato_id=prato_id).all()
            
            for insumo in insumos:
                # Calcular quantidade consumida por porção
                qtd_por_porcao = insumo.quantidade / prato.porcoes_rendimento
                
                # Quantidade total consumida
                qtd_consumida = qtd_por_porcao * quantidade_vendida
                
                # Criar movimentação de estoque (saída)
                movimentacao = MovimentacaoEstoque(
                    produto_id=insumo.produto_id,
                    tipo='saida',
                    quantidade=qtd_consumida,
                    motivo=f'Venda de {quantidade_vendida}x {prato.nome}',
                    restaurant_id=self.restaurant_id
                )
                
                db.session.add(movimentacao)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao processar baixa de estoque: {str(e)}")
            return False


def encontrar_prato_por_nome(nome: str, pratos: List[Prato], threshold: int = 80) -> Tuple[Optional[int], int]:
    """
    Função helper para encontrar prato por nome (para uso em testes)
    
    Args:
        nome: Nome do prato a buscar
        pratos: Lista de objetos Prato
        threshold: Score mínimo para considerar match
    
    Returns:
        Tupla (prato_id, score) ou (None, 0) se não encontrar
    """
    if not pratos:
        return None, 0
    
    # Criar dicionário de nomes para IDs
    nomes_pratos = {prato.nome: prato.id for prato in pratos}
    
    # Usar fuzzy matching
    resultado = process.extractOne(
        nome,
        nomes_pratos.keys(),
        scorer=fuzz.token_sort_ratio
    )
    
    if resultado and resultado[1] >= threshold:
        prato_nome, score = resultado[0], resultado[1]
        prato_id = nomes_pratos[prato_nome]
        return prato_id, score
    
    return None, 0
