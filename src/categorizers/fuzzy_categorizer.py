"""
Categorizador baseado em fuzzy matching para transações financeiras.
"""
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from rapidfuzz import process, fuzz

from .base_categorizer import BaseCategorizer
from ..utils.text_utils import normalize_text, clean_description
from ..config import FUZZY_MATCH_THRESHOLD


class FuzzyCategorizer(BaseCategorizer):
    """
    Categorizador que usa fuzzy matching (correspondência aproximada)
    para categorizar transações.
    """
    
    def __init__(self, categories_data: Optional[pd.DataFrame] = None, threshold: int = FUZZY_MATCH_THRESHOLD):
        """
        Inicializa o categorizador baseado em fuzzy matching.
        
        Args:
            categories_data: DataFrame com os dados de categorias pré-definidas
                             (padrão, descrição, categoria)
            threshold: Limiar de pontuação para considerar uma correspondência válida (0-100)
        """
        super().__init__(categories_data)
        self.threshold = threshold
        self.patterns_dict = {}
        
        if categories_data is not None:
            self._prepare_patterns()
    
    def _prepare_patterns(self) -> None:
        """
        Prepara o dicionário de padrões para fuzzy matching.
        """
        if self.categories_data is None or self.categories_data.empty:
            return
        
        # Limpa o dicionário
        self.patterns_dict = {}
        
        # Processa cada padrão
        for _, row in self.categories_data.iterrows():
            pattern = str(row['pattern']).strip()
            category = str(row['category']).strip()
            
            # Normaliza o padrão
            normalized_pattern = normalize_text(pattern)
            
            # Adiciona ao dicionário
            self.patterns_dict[normalized_pattern] = category
    
    def categorize(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categoriza as transações usando fuzzy matching.
        
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
        if not self.patterns_dict:
            self._prepare_patterns()
        
        # Cria uma cópia do DataFrame para não modificar o original
        result = transactions.copy()
        
        # Adiciona a coluna 'category' se não existir
        if 'category' not in result.columns:
            result['category'] = ''
        
        # Lista de padrões para o fuzzy matching
        patterns = list(self.patterns_dict.keys())
        
        # Aplica fuzzy matching apenas para transações sem categoria
        for idx, row in result.iterrows():
            if row['category']:  # Pula se já tem categoria
                continue
            
            # Normaliza a descrição
            desc = normalize_text(row['description'])
            
            # Aplica fuzzy matching
            match, score = self._find_best_match(desc, patterns)
            
            if match and score >= self.threshold:
                result.loc[idx, 'category'] = self.patterns_dict[match]
                result.loc[idx, 'match_score'] = score
        
        return result
    
    def _find_best_match(self, description: str, patterns: List[str]) -> Tuple[Optional[str], int]:
        """
        Encontra o melhor match para uma descrição usando fuzzy matching.
        
        Args:
            description: Descrição normalizada da transação
            patterns: Lista de padrões para comparação
            
        Returns:
            Tupla com o melhor padrão encontrado e sua pontuação,
            ou (None, 0) se nenhum padrão atingir o limiar
        """
        if not patterns:
            return None, 0
        
        # Usa o algoritmo de Levenshtein para encontrar o melhor match
        match_result = process.extractOne(
            description,
            patterns,
            scorer=fuzz.token_sort_ratio,  # Usa token sort para ignorar ordem das palavras
            score_cutoff=self.threshold
        )
        
        if match_result:
            return match_result[0], match_result[1]
        
        return None, 0
    
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
    
    def set_threshold(self, threshold: int) -> None:
        """
        Define o limiar de pontuação para considerar uma correspondência válida.
        
        Args:
            threshold: Limiar de pontuação (0-100)
        """
        if threshold < 0 or threshold > 100:
            raise ValueError("O limiar deve estar entre 0 e 100")
        
        self.threshold = threshold
