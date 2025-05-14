"""
Categorizador em cadeia que combina múltiplos categorizadores.
"""
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple

from .base_categorizer import BaseCategorizer
from .rule_based_categorizer import RuleBasedCategorizer
from .fuzzy_categorizer import FuzzyCategorizer
from .ai_categorizer import AICategorizer
from ..config import ENABLE_AI_FALLBACK

logger = logging.getLogger(__name__)


class ChainCategorizer(BaseCategorizer):
    """
    Categorizador que implementa o padrão Chain of Responsibility,
    tentando categorizar transações com diferentes estratégias em sequência.
    """
    
    def __init__(self, categories_data: Optional[pd.DataFrame] = None, enable_ai: bool = ENABLE_AI_FALLBACK):
        """
        Inicializa o categorizador em cadeia.
        
        Args:
            categories_data: DataFrame com os dados de categorias pré-definidas
                             (padrão, descrição, categoria)
            enable_ai: Se True, usa IA como último recurso para categorização
        """
        super().__init__(categories_data)
        self.enable_ai = enable_ai
        
        # Inicializa os categorizadores da cadeia
        self.rule_categorizer = RuleBasedCategorizer(categories_data)
        self.fuzzy_categorizer = FuzzyCategorizer(categories_data)
        self.ai_categorizer = AICategorizer(categories_data) if enable_ai else None
        
        # Estatísticas de categorização
        self.stats = {
            'total': 0,
            'rule_based': 0,
            'fuzzy': 0,
            'ai': 0,
            'uncategorized': 0
        }
    
    def categorize(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categoriza as transações usando a cadeia de categorizadores.
        
        Args:
            transactions: DataFrame com as transações a serem categorizadas
                         (deve conter pelo menos a coluna 'description')
        
        Returns:
            DataFrame com as transações categorizadas (adiciona a coluna 'category')
        """
        # Reseta as estatísticas
        self._reset_stats()
        self.stats['total'] = len(transactions)
        
        # Cria uma cópia do DataFrame para não modificar o original
        result = transactions.copy()
        
        # Adiciona a coluna 'category' e 'categorized_by' se não existirem
        if 'category' not in result.columns:
            result['category'] = ''
        if 'categorized_by' not in result.columns:
            result['categorized_by'] = ''
        
        # 1. Tenta categorizar com regras (correspondência exata e substring)
        logger.info("Aplicando categorizador baseado em regras...")
        result = self.rule_categorizer.categorize(result)
        
        # Conta quantas foram categorizadas por regras
        categorized_mask = (result['category'] != '') & (result['categorized_by'] == '')
        result.loc[categorized_mask, 'categorized_by'] = 'rule_based'
        self.stats['rule_based'] = categorized_mask.sum()
        
        # 2. Para as não categorizadas, tenta fuzzy matching
        uncategorized = result[result['category'] == '']
        if not uncategorized.empty:
            logger.info(f"Aplicando fuzzy matching para {len(uncategorized)} transações não categorizadas...")
            fuzzy_result = self.fuzzy_categorizer.categorize(uncategorized)
            
            # Atualiza apenas as linhas que foram categorizadas
            categorized_by_fuzzy = fuzzy_result['category'] != ''
            result.loc[fuzzy_result.index[categorized_by_fuzzy], 'category'] = fuzzy_result.loc[categorized_by_fuzzy, 'category']
            result.loc[fuzzy_result.index[categorized_by_fuzzy], 'categorized_by'] = 'fuzzy'
            
            # Atualiza estatísticas
            self.stats['fuzzy'] = categorized_by_fuzzy.sum()
        
        # 3. Para as ainda não categorizadas, tenta IA (se habilitada)
        if self.enable_ai and self.ai_categorizer:
            uncategorized = result[result['category'] == '']
            if not uncategorized.empty:
                logger.info(f"Aplicando IA para {len(uncategorized)} transações não categorizadas...")
                ai_result = self.ai_categorizer.categorize(uncategorized)
                
                # Atualiza apenas as linhas que foram categorizadas
                categorized_by_ai = ai_result['category'] != ''
                result.loc[ai_result.index[categorized_by_ai], 'category'] = ai_result.loc[categorized_by_ai, 'category']
                result.loc[ai_result.index[categorized_by_ai], 'categorized_by'] = 'ai'
                
                # Atualiza estatísticas
                self.stats['ai'] = categorized_by_ai.sum()
        
        # Atualiza estatística de não categorizadas
        self.stats['uncategorized'] = (result['category'] == '').sum()
        
        return result
    
    def _reset_stats(self) -> None:
        """
        Reseta as estatísticas de categorização.
        """
        self.stats = {
            'total': 0,
            'rule_based': 0,
            'fuzzy': 0,
            'ai': 0,
            'uncategorized': 0
        }
    
    def get_stats(self) -> Dict[str, int]:
        """
        Retorna as estatísticas de categorização.
        
        Returns:
            Dicionário com estatísticas de categorização
        """
        return self.stats
    
    def load_categories(self, categories_path: str) -> None:
        """
        Carrega as categorias de um arquivo CSV ou Excel e atualiza todos os categorizadores.
        
        Args:
            categories_path: Caminho para o arquivo de categorias
        """
        super().load_categories(categories_path)
        
        # Atualiza os categorizadores da cadeia
        self.rule_categorizer.load_categories(categories_path)
        self.fuzzy_categorizer.load_categories(categories_path)
        
        if self.enable_ai and self.ai_categorizer:
            self.ai_categorizer.load_categories(categories_path)
    
    def add_category(self, pattern: str, category: str) -> None:
        """
        Adiciona uma nova categoria a todos os categorizadores.
        
        Args:
            pattern: Padrão de descrição para correspondência
            category: Categoria a ser atribuída
        """
        super().add_category(pattern, category)
        
        # Atualiza os categorizadores da cadeia
        self.rule_categorizer.add_category(pattern, category)
        self.fuzzy_categorizer.add_category(pattern, category)
        
        if self.enable_ai and self.ai_categorizer:
            self.ai_categorizer.add_category(pattern, category)
    
    def set_fuzzy_threshold(self, threshold: int) -> None:
        """
        Define o limiar de pontuação para o fuzzy matching.
        
        Args:
            threshold: Limiar de pontuação (0-100)
        """
        self.fuzzy_categorizer.set_threshold(threshold)
    
    def set_ai_enabled(self, enabled: bool) -> None:
        """
        Habilita ou desabilita o uso de IA como fallback.
        
        Args:
            enabled: Se True, habilita o uso de IA
        """
        self.enable_ai = enabled
        
        # Inicializa o categorizador de IA se necessário
        if enabled and self.ai_categorizer is None:
            self.ai_categorizer = AICategorizer(self.categories_data)
        
    def set_ai_api_key(self, api_key: str) -> None:
        """
        Define a chave de API para o categorizador de IA.
        
        Args:
            api_key: Chave de API do Google Gemini
        """
        if self.ai_categorizer:
            self.ai_categorizer.set_api_key(api_key)
        elif self.enable_ai:
            self.ai_categorizer = AICategorizer(self.categories_data, api_key=api_key)
