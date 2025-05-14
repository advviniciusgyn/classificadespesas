"""
Configurações globais para o aplicativo de categorização de despesas.
"""
import os
from pathlib import Path
import streamlit as st

# Configurações do Streamlit
STREAMLIT_PAGE_TITLE = "Categorizador de Despesas"
STREAMLIT_PAGE_ICON = "💰"

# Configurações de categorização
FUZZY_MATCH_THRESHOLD = 80  # pontuação mínima para correspondência fuzzy (0-100)
ENABLE_AI_FALLBACK = True  # usar IA como fallback para categorias não identificadas

# Configurações da API do Google Gemini
# No Streamlit Cloud, use st.secrets["GEMINI_API_KEY"] para acessar a chave da API
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else os.environ.get("GEMINI_API_KEY", "")
