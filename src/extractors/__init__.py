"""
Módulo de extratores de PDFs para diferentes formatos de extratos bancários e cartões de crédito.
"""

from .base_extractor import BaseExtractor
from .generic_extractor import GenericExtractor

__all__ = ['BaseExtractor', 'GenericExtractor']
