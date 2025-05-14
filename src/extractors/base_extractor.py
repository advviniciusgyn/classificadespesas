"""
Classe base para todos os extratores de PDF.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
import os


class BaseExtractor(ABC):
    """
    Classe abstrata base para todos os extratores de PDF.
    
    Implementa o padrão Strategy para permitir diferentes estratégias
    de extração para diferentes formatos de extratos bancários.
    """
    
    def __init__(self, pdf_path: str):
        """
        Inicializa o extrator com o caminho para o arquivo PDF.
        
        Args:
            pdf_path: Caminho absoluto para o arquivo PDF a ser processado
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")
        
        self.pdf_path = pdf_path
        self.extracted_data = None
    
    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """
        Extrai os dados do PDF e retorna um DataFrame com as transações.
        
        Returns:
            DataFrame com as colunas padronizadas:
                - date: Data da transação
                - description: Descrição da transação
                - amount: Valor da transação (positivo para créditos, negativo para débitos)
                - type: Tipo da transação (opcional)
                - reference: Referência ou número da transação (opcional)
        """
        pass
    
    @abstractmethod
    def can_process(self) -> bool:
        """
        Verifica se este extrator é capaz de processar o PDF fornecido.
        
        Returns:
            True se o extrator pode processar o PDF, False caso contrário
        """
        pass
    
    def get_data(self) -> pd.DataFrame:
        """
        Retorna os dados extraídos, executando a extração se necessário.
        
        Returns:
            DataFrame com as transações extraídas
        """
        if self.extracted_data is None:
            self.extracted_data = self.extract()
        return self.extracted_data
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Retorna metadados sobre o extrato (banco, período, etc).
        
        Returns:
            Dicionário com metadados do extrato
        """
        return {
            "source_file": os.path.basename(self.pdf_path),
            "extractor": self.__class__.__name__
        }
