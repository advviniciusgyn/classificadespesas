"""
Extrator genérico para PDFs de extratos bancários e cartões de crédito.
"""
import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from .base_extractor import BaseExtractor
from ..utils.text_utils import normalize_text

logger = logging.getLogger(__name__)


class GenericExtractor(BaseExtractor):
    """
    Extrator genérico que tenta identificar e extrair tabelas de transações
    de qualquer PDF de extrato bancário ou cartão de crédito.
    """
    
    def __init__(self, pdf_path: str):
        """
        Inicializa o extrator genérico.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
        """
        super().__init__(pdf_path)
        self.date_patterns = [
            r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY
            r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'\d{2}/\d{2}/\d{2}',   # DD/MM/YY
        ]
        self.amount_patterns = [
            r'-?\d+[.,]\d{2}',  # 123,45 ou -123,45
            r'-?\d+\.\d{3}[.,]\d{2}',  # 1.234,56 ou -1.234,56
        ]
    
    def can_process(self) -> bool:
        """
        Verifica se este extrator pode processar o PDF.
        O extrator genérico tenta processar qualquer PDF.
        
        Returns:
            True se conseguir encontrar pelo menos uma tabela no PDF
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables and len(tables) > 0:
                        return True
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar se pode processar o PDF: {e}")
            return False
    
    def extract(self) -> pd.DataFrame:
        """
        Extrai transações do PDF usando pdfplumber.
        
        Returns:
            DataFrame com as transações extraídas
        """
        all_rows = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processando página {page_num+1} de {len(pdf.pages)}")
                    
                    # Tenta extrair tabelas
                    tables = page.extract_tables()
                    
                    if not tables:
                        logger.warning(f"Nenhuma tabela encontrada na página {page_num+1}")
                        continue
                    
                    for table_num, table in enumerate(tables):
                        if not table:
                            continue
                        
                        # Identifica colunas de data, descrição e valor
                        header_row = table[0] if table else []
                        col_indices = self._identify_columns(header_row)
                        
                        if not col_indices:
                            # Se não conseguir identificar pelo cabeçalho, tenta pela estrutura
                            col_indices = self._guess_columns_by_content(table)
                        
                        if not col_indices:
                            logger.warning(f"Não foi possível identificar colunas na tabela {table_num+1}")
                            continue
                        
                        # Extrai as linhas de transação
                        for row in table[1:]:  # Pula o cabeçalho
                            transaction = self._extract_transaction(row, col_indices)
                            if transaction:
                                all_rows.append(transaction)
        
        except Exception as e:
            logger.error(f"Erro ao extrair dados do PDF: {e}")
        
        # Cria o DataFrame com as transações
        if not all_rows:
            logger.warning("Nenhuma transação extraída do PDF")
            return pd.DataFrame(columns=['date', 'description', 'amount'])
        
        df = pd.DataFrame(all_rows)
        
        # Normaliza os dados
        df = self._normalize_dataframe(df)
        
        return df
    
    def _identify_columns(self, header_row: List[str]) -> Dict[str, int]:
        """
        Identifica os índices das colunas relevantes pelo cabeçalho.
        
        Args:
            header_row: Lista com os textos do cabeçalho da tabela
            
        Returns:
            Dicionário com os índices das colunas de data, descrição e valor
        """
        if not header_row or all(cell is None for cell in header_row):
            return {}
        
        col_indices = {}
        
        # Normaliza o cabeçalho para facilitar a identificação
        normalized_header = [normalize_text(str(cell)) if cell else "" for cell in header_row]
        
        # Palavras-chave para identificar cada tipo de coluna
        date_keywords = ['data', 'dt', 'date', 'dia']
        desc_keywords = ['descricao', 'historico', 'lancamento', 'description', 'transacao']
        amount_keywords = ['valor', 'montante', 'amount', 'r$', 'debito', 'credito']
        
        # Busca as colunas pelo cabeçalho
        for idx, header in enumerate(normalized_header):
            if any(keyword in header for keyword in date_keywords):
                col_indices['date'] = idx
            elif any(keyword in header for keyword in desc_keywords):
                col_indices['description'] = idx
            elif any(keyword in header for keyword in amount_keywords):
                col_indices['amount'] = idx
        
        return col_indices
    
    def _guess_columns_by_content(self, table: List[List[str]]) -> Dict[str, int]:
        """
        Tenta adivinhar as colunas pela estrutura e conteúdo da tabela.
        
        Args:
            table: Tabela extraída do PDF
            
        Returns:
            Dicionário com os índices das colunas de data, descrição e valor
        """
        if not table or len(table) < 2:
            return {}
        
        # Pega algumas linhas de amostra (pula o possível cabeçalho)
        sample_rows = table[1:min(6, len(table))]
        
        col_indices = {}
        num_cols = len(table[0])
        
        # Contadores para cada tipo de coluna
        date_counts = [0] * num_cols
        amount_counts = [0] * num_cols
        
        # Analisa o conteúdo de cada coluna
        for row in sample_rows:
            if len(row) != num_cols:
                continue
                
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                    
                cell_text = str(cell).strip()
                
                # Verifica se parece uma data
                if any(re.search(pattern, cell_text) for pattern in self.date_patterns):
                    date_counts[idx] += 1
                
                # Verifica se parece um valor monetário
                if any(re.search(pattern, cell_text) for pattern in self.amount_patterns):
                    amount_counts[idx] += 1
        
        # Identifica a coluna de data (a que tiver mais matches)
        if max(date_counts) > 0:
            col_indices['date'] = date_counts.index(max(date_counts))
        
        # Identifica a coluna de valor (a que tiver mais matches)
        if max(amount_counts) > 0:
            col_indices['amount'] = amount_counts.index(max(amount_counts))
        
        # A coluna de descrição geralmente é a mais longa e está entre a data e o valor
        if 'date' in col_indices and 'amount' in col_indices:
            # Se a data vem antes do valor
            if col_indices['date'] < col_indices['amount']:
                # Pega a coluna mais à direita entre a data e o valor
                for i in range(col_indices['date'] + 1, col_indices['amount']):
                    col_indices['description'] = i
                    break
            else:
                # Se o valor vem antes da data, a descrição pode estar entre eles
                for i in range(col_indices['amount'] + 1, col_indices['date']):
                    col_indices['description'] = i
                    break
        
        # Se ainda não encontrou a descrição, assume que é a coluna mais longa
        if 'description' not in col_indices:
            # Calcula o tamanho médio de cada coluna
            col_lengths = [0] * num_cols
            for row in sample_rows:
                for idx, cell in enumerate(row):
                    if cell:
                        col_lengths[idx] += len(str(cell))
            
            # Exclui as colunas já identificadas
            for col_type in ['date', 'amount']:
                if col_type in col_indices:
                    col_lengths[col_indices[col_type]] = 0
            
            # A coluna mais longa é provavelmente a descrição
            if max(col_lengths) > 0:
                col_indices['description'] = col_lengths.index(max(col_lengths))
        
        return col_indices
    
    def _extract_transaction(self, row: List[str], col_indices: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """
        Extrai uma transação de uma linha da tabela.
        
        Args:
            row: Linha da tabela
            col_indices: Índices das colunas relevantes
            
        Returns:
            Dicionário com os dados da transação ou None se não for uma transação válida
        """
        if not row or len(row) == 0:
            return None
        
        # Verifica se tem as colunas mínimas necessárias
        required_cols = ['date', 'description', 'amount']
        if not all(col in col_indices for col in required_cols):
            return None
        
        # Extrai os valores das colunas
        date_val = row[col_indices['date']] if col_indices['date'] < len(row) else None
        desc_val = row[col_indices['description']] if col_indices['description'] < len(row) else None
        amount_val = row[col_indices['amount']] if col_indices['amount'] < len(row) else None
        
        # Verifica se tem os valores mínimos
        if not date_val or not desc_val or not amount_val:
            return None
        
        # Converte para string
        date_str = str(date_val).strip()
        desc_str = str(desc_val).strip()
        amount_str = str(amount_val).strip()
        
        # Verifica se a data parece válida
        if not any(re.search(pattern, date_str) for pattern in self.date_patterns):
            return None
        
        # Verifica se o valor parece válido
        if not any(re.search(pattern, amount_str) for pattern in self.amount_patterns):
            return None
        
        # Retorna a transação
        return {
            'date': date_str,
            'description': desc_str,
            'amount': amount_str
        }
    
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza o DataFrame de transações.
        
        Args:
            df: DataFrame com as transações extraídas
            
        Returns:
            DataFrame normalizado
        """
        if df.empty:
            return df
        
        # Cria uma cópia para não modificar o original
        result = df.copy()
        
        # Normaliza as datas
        result['date'] = result['date'].apply(self._normalize_date)
        
        # Normaliza os valores
        result['amount'] = result['amount'].apply(self._normalize_amount)
        
        # Normaliza as descrições
        result['description'] = result['description'].apply(normalize_text)
        
        # Remove linhas com valores inválidos
        result = result.dropna(subset=['date', 'amount'])
        
        return result
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normaliza uma string de data para o formato YYYY-MM-DD.
        
        Args:
            date_str: String com a data
            
        Returns:
            Data normalizada ou None se não for possível normalizar
        """
        if not date_str:
            return None
        
        # Remove caracteres não numéricos e separadores
        clean_str = re.sub(r'[^\d/.-]', '', date_str)
        
        # Tenta diferentes formatos
        formats = [
            '%d/%m/%Y', '%d/%m/%y', '%d.%m.%Y', '%d.%m.%y',
            '%d-%m-%Y', '%d-%m-%y', '%Y/%m/%d', '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(clean_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def _normalize_amount(self, amount_str: str) -> Optional[float]:
        """
        Normaliza uma string de valor monetário para um float.
        
        Args:
            amount_str: String com o valor
            
        Returns:
            Valor normalizado ou None se não for possível normalizar
        """
        if not amount_str:
            return None
        
        # Remove caracteres não numéricos, exceto ponto, vírgula e sinal
        clean_str = re.sub(r'[^\d,.+-]', '', amount_str)
        
        # Trata valores negativos indicados por parênteses
        if '(' in amount_str and ')' in amount_str:
            clean_str = '-' + clean_str
        
        # Substitui vírgula por ponto para conversão para float
        clean_str = clean_str.replace('.', '').replace(',', '.')
        
        try:
            return float(clean_str)
        except ValueError:
            return None
