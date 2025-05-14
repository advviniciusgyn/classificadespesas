"""
Arquivo principal para deploy no Streamlit Cloud.
Este arquivo importa e executa a aplicação principal do projeto.
"""
import os
import sys

# Adiciona o diretório src ao path do Python
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Importa a função main do arquivo main.py
from src.main import main

# Executa a aplicação
if __name__ == "__main__":
    main()
