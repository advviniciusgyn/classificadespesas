"""
Categorizador baseado em regras para transações financeiras.
"""
import pandas as pd
from typing import Dict, List, Optional, Any

from .base_categorizer import BaseCategorizer
from ..utils.text_utils import normalize_text, clean_description


class RuleBasedCategorizer(BaseCategorizer):
    """
    Categorizador que usa regras baseadas em correspondência exata e substring
    para categorizar transações.
    """
    
    def __init__(self, categories_data: Optional[pd.DataFrame] = None):
        """
        Inicializa o categorizador baseado em regras.
        
        Args:
            categories_data: DataFrame com os dados de categorias pré-definidas
                             (padrão, descrição, categoria)
        """
        super().__init__(categories_data)
        self.exact_match_patterns = {}
        self.substring_patterns = {}
        
        if categories_data is not None:
            self._prepare_patterns()
    
    def _prepare_patterns(self) -> None:
        """
        Prepara os dicionários de padrões para correspondência exata e substring.
        """
        if self.categories_data is None or self.categories_data.empty:
            return
        
        # Limpa os dicionários
        self.exact_match_patterns = {}
        self.substring_patterns = {}
        
        # Processa cada padrão
        for _, row in self.categories_data.iterrows():
            pattern = str(row['pattern']).strip()
            category = str(row['category']).strip()
            
            # Normaliza o padrão
            normalized_pattern = normalize_text(pattern)
            
            # Decide se é correspondência exata ou substring
            if normalized_pattern.startswith('*') and normalized_pattern.endswith('*'):
                # Substring (contém)
                clean_pattern = normalized_pattern.strip('*')
                self.substring_patterns[clean_pattern] = category
            else:
                # Correspondência exata
                self.exact_match_patterns[normalized_pattern] = category
    
    def categorize(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categoriza as transações usando regras baseadas em correspondência exata e substring.
        
        Args:
            transactions: DataFrame com as transações a serem categorizadas
                         (deve conter pelo menos a coluna 'description')
        
        Returns:
            DataFrame com as transações categorizadas (adiciona a coluna 'category')
        """
        if self.categories_data is None or self.categories_data.empty:
            # Se não há categorias definidas, retorna o DataFrame original com categoria vazia
            result = transactions.copy()
            result['category'] = ''
            return result
        
        # Prepara os padrões se ainda não foram preparados
        if not self.exact_match_patterns and not self.substring_patterns:
            self._prepare_patterns()
        
        # Cria uma cópia do DataFrame para não modificar o original
        result = transactions.copy()
        
        # Adiciona a coluna 'category' se não existir
        if 'category' not in result.columns:
            result['category'] = ''
        
        # Normaliza as descrições para facilitar a correspondência
        normalized_descriptions = result['description'].apply(normalize_text)
        
        # Aplica correspondência exata
        for idx, desc in enumerate(normalized_descriptions):
            if result.loc[idx, 'category']:  # Pula se já tem categoria
                continue
                
            # Tenta correspondência exata
            if desc in self.exact_match_patterns:
                result.loc[idx, 'category'] = self.exact_match_patterns[desc]
                continue
            
            # Tenta correspondência por substring
            for pattern, category in self.substring_patterns.items():
                if pattern in desc:
                    result.loc[idx, 'category'] = category
                    break
        
        return result
    
    def load_categories(self, categories_path: str) -> None:
        """
        Carrega as categorias de um arquivo CSV ou Excel e prepara os padrões.
        
        Args:
            categories_path: Caminho para o arquivo de categorias
        """
        super().load_categories(categories_path)
        self._prepare_patterns()
    
    def add_category(self, pattern: str, category: str) -> None:
        """
        Adiciona uma nova categoria ao categorizador e atualiza os padrões.
        
        Args:
            pattern: Padrão de descrição para correspondência
            category: Categoria a ser atribuída
        """
        super().add_category(pattern, category)
        self._prepare_patterns()
    
    def get_match_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas sobre os tipos de correspondência.
        
        Returns:
            Dicionário com contagem de padrões por tipo de correspondência
        """
        return {
            'exact_match': len(self.exact_match_patterns),
            'substring': len(self.substring_patterns),
            'total': len(self.exact_match_patterns) + len(self.substring_patterns)
        }
