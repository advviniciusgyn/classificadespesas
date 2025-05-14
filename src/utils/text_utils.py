"""
Funções utilitárias para manipulação e normalização de texto.
"""
import re
from typing import Optional
from unidecode import unidecode


def normalize_text(text: Optional[str]) -> str:
    """
    Normaliza um texto removendo acentos, convertendo para minúsculas
    e removendo caracteres especiais.
    
    Args:
        text: Texto a ser normalizado
        
    Returns:
        Texto normalizado
    """
    if text is None:
        return ""
    
    # Converte para string caso não seja
    text = str(text)
    
    # Remove espaços extras
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Converte para minúsculas
    text = text.lower()
    
    # Remove acentos
    text = unidecode(text)
    
    return text


def extract_numbers(text: Optional[str]) -> str:
    """
    Extrai apenas os números de um texto.
    
    Args:
        text: Texto de onde extrair os números
        
    Returns:
        String contendo apenas os números do texto
    """
    if text is None:
        return ""
    
    return re.sub(r'[^\d]', '', str(text))


def is_similar(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """
    Verifica se dois textos são similares usando uma medida simples de similaridade.
    
    Args:
        text1: Primeiro texto
        text2: Segundo texto
        threshold: Limiar de similaridade (0 a 1)
        
    Returns:
        True se os textos forem similares, False caso contrário
    """
    # Normaliza os textos
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    # Se um dos textos estiver contido no outro, são similares
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Calcula a similaridade de Jaccard usando n-gramas
    def get_ngrams(text, n=3):
        return [text[i:i+n] for i in range(len(text) - n + 1)]
    
    if len(norm1) < 3 or len(norm2) < 3:
        # Para textos muito curtos, usa comparação direta
        return norm1 == norm2
    
    # Obtém os n-gramas
    ngrams1 = set(get_ngrams(norm1))
    ngrams2 = set(get_ngrams(norm2))
    
    # Calcula a similaridade de Jaccard
    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))
    
    if union == 0:
        return False
    
    similarity = intersection / union
    
    return similarity >= threshold


def clean_description(description: str) -> str:
    """
    Limpa e padroniza a descrição de uma transação.
    
    Args:
        description: Descrição original da transação
        
    Returns:
        Descrição limpa e padronizada
    """
    if not description:
        return ""
    
    # Converte para string
    desc = str(description)
    
    # Remove caracteres especiais e espaços extras
    desc = re.sub(r'[^\w\s]', ' ', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    # Remove palavras comuns que não ajudam na categorização
    common_words = ['ltda', 'me', 'sa', 's/a', 'eireli', 'com', 'de', 'do', 'da']
    for word in common_words:
        desc = re.sub(r'\b' + word + r'\b', '', desc, flags=re.IGNORECASE)
    
    # Remove espaços extras novamente
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    return desc.lower()
