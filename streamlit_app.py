"""
Arquivo principal para deploy no Streamlit Cloud.
Este arquivo contém o código da aplicação principal.
"""
import streamlit as st

# Configurações do Streamlit
ST_PAGE_TITLE = "Categorizador de Despesas"
ST_PAGE_ICON = "💰"

# IMPORTANTE: st.set_page_config deve ser a primeira chamada do Streamlit
st.set_page_config(
    page_title=ST_PAGE_TITLE,
    page_icon=ST_PAGE_ICON,
    layout="wide"
)

# Importações restantes
import os
import sys
import pandas as pd
import numpy as np
import logging
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import io
import pdfplumber
from datetime import datetime
import re
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from rapidfuzz import fuzz, process
import unidecode
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# As configurações da API do Google Gemini estão no arquivo config.py
# A chave da API deve ser configurada nos segredos do Streamlit Cloud

# Configurações de categorização
FUZZY_MATCH_THRESHOLD = 80  # pontuação mínima para correspondência fuzzy (0-100)

# Importa o código completo da aplicação
from src.utils.text_utils import *
from src.extractors.base_extractor import BaseExtractor
from src.extractors.generic_extractor import GenericExtractor
from src.categorizers.base_categorizer import BaseCategorizer
from src.categorizers.rule_based_categorizer import RuleBasedCategorizer
from src.categorizers.fuzzy_categorizer import FuzzyCategorizer
from src.categorizers.ai_categorizer import AICategorizer
from src.categorizers.chain_categorizer import ChainCategorizer

# Importa o código da função main do arquivo main.py
from src.main import main

# Executa a aplicação
if __name__ == "__main__":
    main()
