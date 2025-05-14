"""
Categorizador baseado em IA para transações financeiras.
"""
import pandas as pd
import google.generativeai as genai
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
import streamlit as st

from .base_categorizer import BaseCategorizer
from ..utils.text_utils import normalize_text, clean_description
from ..config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Configura a API do Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class AICategorizer(BaseCategorizer):
    """
    Categorizador que usa IA (Google Gemini) para categorizar transações
    que não foram categorizadas por outros métodos.
    """
    
    def __init__(self, categories_data: Optional[pd.DataFrame] = None, api_key: Optional[str] = None):
        """
        Inicializa o categorizador baseado em IA.
        
        Args:
            categories_data: DataFrame com os dados de categorias pré-definidas
                             (padrão, descrição, categoria)
            api_key: Chave de API do Google Gemini (opcional, pode usar a do config)
        """
        super().__init__(categories_data)
        
        # Configura a API se fornecida uma chave
        if api_key:
            genai.configure(api_key=api_key)
        
        # Verifica se a API está configurada
        if not GEMINI_API_KEY and not api_key:
            logger.warning("API do Google Gemini não configurada. O categorizador de IA não funcionará.")
        
        # Armazena exemplos para few-shot learning
        self.examples = []
        
        if categories_data is not None:
            self._prepare_examples()
    
    def _prepare_examples(self) -> None:
        """
        Prepara exemplos para few-shot learning.
        """
        if self.categories_data is None or self.categories_data.empty:
            return
        
        # Limpa os exemplos
        self.examples = []
        
        # Obtém categorias únicas
        categories = self.categories_data['category'].unique()
        
        # Para cada categoria, seleciona alguns exemplos
        for category in categories:
            # Filtra padrões desta categoria
            category_patterns = self.categories_data[self.categories_data['category'] == category]
            
            # Seleciona até 3 exemplos por categoria
            for _, row in category_patterns.head(3).iterrows():
                self.examples.append({
                    'pattern': row['pattern'],
                    'category': category
                })
    
    def categorize(self, transactions: pd.DataFrame) -> pd.DataFrame:
        """
        Categoriza as transações usando IA (Google Gemini).
        
        Args:
            transactions: DataFrame com as transações a serem categorizadas
                         (deve conter pelo menos a coluna 'description')
        
        Returns:
            DataFrame com as transações categorizadas (adiciona a coluna 'category')
        """
        # Verifica se a API está configurada
        api_key = GEMINI_API_KEY
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
        
        if not api_key:
            # Se a API não está configurada, retorna o DataFrame sem alterações
            logger.error("API do Google Gemini não configurada. Impossível categorizar com IA.")
            return transactions
        
        # Cria uma cópia do DataFrame para não modificar o original
        result = transactions.copy()
        
        # Adiciona a coluna 'category' se não existir
        if 'category' not in result.columns:
            result['category'] = ''
        
        # Prepara os exemplos se ainda não foram preparados
        if not self.examples and self.categories_data is not None:
            self._prepare_examples()
        
        # Obtém categorias disponíveis
        available_categories = self.get_categories()
        
        # Aplica categorização por IA apenas para transações sem categoria
        for idx, row in result.iterrows():
            if row['category']:  # Pula se já tem categoria
                continue
            
            try:
                # Categoriza usando IA
                category = self._categorize_with_ai(row['description'], available_categories)
                
                if category:
                    result.loc[idx, 'category'] = category
                    result.loc[idx, 'categorized_by'] = 'ai'
            except Exception as e:
                logger.error(f"Erro ao categorizar com IA: {e}")
        
        return result
    
    def _categorize_with_ai(self, description: str, available_categories: List[str]) -> Optional[str]:
        """
        Categoriza uma transação usando a API do Google Gemini.
        
        Args:
            description: Descrição da transação
            available_categories: Lista de categorias disponíveis
            
        Returns:
            Categoria atribuída ou None se não for possível categorizar
        """
        if not description or not available_categories:
            return None
        
        # Constrói o prompt para a IA
        prompt = self._build_prompt(description, available_categories)
        
        try:
            # Configura o modelo
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Faz a requisição para a API
            response = model.generate_content(prompt)
            
            # Processa a resposta
            if response and response.text:
                # Extrai a categoria da resposta
                category = self._extract_category_from_response(response.text, available_categories)
                return category
            
            return None
        except Exception as e:
            logger.error(f"Erro na API do Google Gemini: {e}")
            return None
    
    def _build_prompt(self, description: str, available_categories: List[str]) -> str:
        """
        Constrói o prompt para a API do Google Gemini.
        
        Args:
            description: Descrição da transação
            available_categories: Lista de categorias disponíveis
            
        Returns:
            Prompt formatado para a API
        """
        # Cabeçalho do prompt
        prompt = "Categorize a seguinte transação financeira em uma das categorias disponíveis.\n\n"
        
        # Adiciona exemplos para few-shot learning
        if self.examples:
            prompt += "Exemplos:\n"
            for example in self.examples:
                prompt += f'"{example["pattern"]}" → {example["category"]}\n'
            prompt += "\n"
        
        # Adiciona a descrição a ser categorizada
        prompt += f'Agora, classifique só a categoria desta transação:\n"{description}"\n\n'
        
        # Adiciona as categorias disponíveis
        prompt += "Categorias disponíveis:\n"
        for category in available_categories:
            prompt += f"- {category}\n"
        
        # Instruções finais
        prompt += "\nResponda apenas com o nome da categoria, sem explicações adicionais."
        
        return prompt
    
    def _extract_category_from_response(self, response_text: str, available_categories: List[str]) -> Optional[str]:
        """
        Extrai a categoria da resposta da API.
        
        Args:
            response_text: Texto da resposta da API
            available_categories: Lista de categorias disponíveis
            
        Returns:
            Categoria extraída ou None se não for possível extrair
        """
        # Limpa a resposta
        clean_response = response_text.strip().lower()
        
        # Verifica se a resposta é exatamente uma das categorias disponíveis
        for category in available_categories:
            if clean_response == category.lower():
                return category
        
        # Se não for exata, procura a categoria na resposta
        for category in available_categories:
            if category.lower() in clean_response:
                return category
        
        return None
    
    def load_categories(self, categories_path: str) -> None:
        """
        Carrega as categorias de um arquivo CSV ou Excel e prepara os exemplos.
        
        Args:
            categories_path: Caminho para o arquivo de categorias
        """
        super().load_categories(categories_path)
        self._prepare_examples()
    
    def add_category(self, pattern: str, category: str) -> None:
        """
        Adiciona uma nova categoria ao categorizador e atualiza os exemplos.
        
        Args:
            pattern: Padrão de descrição para correspondência
            category: Categoria a ser atribuída
        """
        super().add_category(pattern, category)
        self._prepare_examples()
    
    def set_api_key(self, api_key: str) -> None:
        """
        Define a chave de API do Google Gemini.
        
        Args:
            api_key: Chave de API
        """
        genai.configure(api_key=api_key)
