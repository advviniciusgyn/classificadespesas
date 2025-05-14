"""
Classe base para todos os categorizadores de transações.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd


class BaseCategorizer(ABC):
    """
    Classe abstrata base para todos os categorizadores de transações.
    
    Define a interface comum para todos os categorizadores, permitindo
    que sejam usados de forma intercambiável.
    """
    
    def __init__(self, categories_data: Optional[pd.DataFrame] = None):
        """
        Inicializa o categorizador com os dados de categorias.
        
        Args:
            categories_data: DataFrame com os dados de categorias pré-definidas
                             (padrão, descrição, categoria)
        """
        self.categories_data = categories_data
    
    @abstractmethod
    def categorize(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categoriza as transações fornecidas.
        
        Args:
            transactions: DataFrame com as transações a serem categorizadas
                         (deve conter pelo menos a coluna 'description')
        
        Returns:
            DataFrame com as transações categorizadas (adiciona a coluna 'category')
        """
        pass
    
    def load_categories(self, categories_path: str) -> None:
        """
        Carrega as categorias de um arquivo CSV ou Excel.
        
        Args:
            categories_path: Caminho para o arquivo de categorias
        """
        if categories_path.endswith('.csv'):
            self.categories_data = pd.read_csv(categories_path)
        elif categories_path.endswith(('.xlsx', '.xls')):
            self.categories_data = pd.read_excel(categories_path)
        else:
            raise ValueError(f"Formato de arquivo não suportado: {categories_path}")
        
        # Verifica se o DataFrame tem as colunas necessárias
        required_columns = ['pattern', 'category']
        missing_columns = [col for col in required_columns if col not in self.categories_data.columns]
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias ausentes no arquivo de categorias: {missing_columns}")
    
    def save_categories(self, categories_path: str) -> None:
        """
        Salva as categorias em um arquivo CSV ou Excel.
        
        Args:
            categories_path: Caminho para o arquivo de categorias
        """
        if self.categories_data is None:
            raise ValueError("Não há categorias para salvar")
        
        if categories_path.endswith('.csv'):
            self.categories_data.to_csv(categories_path, index=False)
        elif categories_path.endswith(('.xlsx', '.xls')):
            self.categories_data.to_excel(categories_path, index=False)
        else:
            raise ValueError(f"Formato de arquivo não suportado: {categories_path}")
    
    def add_category(self, pattern: str, category: str) -> None:
        """
        Adiciona uma nova categoria ao categorizador.
        
        Args:
            pattern: Padrão de descrição para correspondência
            category: Categoria a ser atribuída
        """
        if self.categories_data is None:
            self.categories_data = pd.DataFrame(columns=['pattern', 'category'])
        
        # Verifica se o padrão já existe
        if pattern in self.categories_data['pattern'].values:
            # Atualiza a categoria
            self.categories_data.loc[self.categories_data['pattern'] == pattern, 'category'] = category
        else:
            # Adiciona nova linha
            new_row = pd.DataFrame({'pattern': [pattern], 'category': [category]})
            self.categories_data = pd.concat([self.categories_data, new_row], ignore_index=True)
    
    def get_categories(self) -> List[str]:
        """
        Retorna a lista de categorias únicas.
        
        Returns:
            Lista de categorias únicas
        """
        if self.categories_data is None or self.categories_data.empty:
            return []
        
        return self.categories_data['category'].unique().tolist()
    
    def get_patterns_by_category(self, category: str) -> List[str]:
        """
        Retorna a lista de padrões para uma categoria específica.
        
        Args:
            category: Categoria para a qual buscar os padrões
            
        Returns:
            Lista de padrões para a categoria
        """
        if self.categories_data is None or self.categories_data.empty:
            return []
        
        return self.categories_data.loc[self.categories_data['category'] == category, 'pattern'].tolist()
    
    def get_category_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas sobre as categorias (contagem por categoria).
        
        Returns:
            Dicionário com contagem de padrões por categoria
        """
        if self.categories_data is None or self.categories_data.empty:
            return {}
        
        return self.categories_data['category'].value_counts().to_dict()
