"""
Aplicativo principal para categorização de despesas.
"""
import os
import streamlit as st
import pandas as pd
import logging
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import io

# Importações absolutas para evitar problemas com importações relativas
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.extractors.generic_extractor import GenericExtractor
from src.categorizers.chain_categorizer import ChainCategorizer
from src.utils.text_utils import normalize_text
from src.config import (
    STREAMLIT_PAGE_TITLE, 
    STREAMLIT_PAGE_ICON,
    GEMINI_API_KEY,
    ENABLE_AI_FALLBACK
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração da página Streamlit
st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    page_icon=STREAMLIT_PAGE_ICON,
    layout="wide"
)

def main():
    """Função principal do aplicativo."""
    
    # Título e descrição
    st.title("Categorizador de Despesas")
    st.markdown("""
    Este aplicativo extrai transações de extratos bancários e cartões de crédito em PDF, 
    e categoriza automaticamente as despesas com base em uma lista de pré-categorizações.
    """)
    
    # Sidebar para configurações
    with st.sidebar:
        st.header("Configurações")
        
        # Configuração da API do Google Gemini
        api_key = st.text_input(
            "Chave da API do Google Gemini (opcional)",
            value=GEMINI_API_KEY,
            type="password"
        )
        
        enable_ai = st.checkbox(
            "Usar IA para categorização",
            value=ENABLE_AI_FALLBACK
        )
        
        fuzzy_threshold = st.slider(
            "Limiar para fuzzy matching (0-100)",
            min_value=50,
            max_value=100,
            value=80,
            step=5
        )
        
        st.divider()
        
        # Sobre o aplicativo
        st.header("Sobre")
        st.markdown("""
        **Categorizador de Despesas** é um aplicativo que ajuda a organizar suas finanças
        extraindo e categorizando automaticamente transações de extratos bancários e cartões de crédito.
        
        Desenvolvido com Python, pandas e Streamlit.
        """)
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs(["Processar PDFs", "Gerenciar Categorias", "Visualizar Resultados"])
    
    # Aba 1: Processar PDFs
    with tab1:
        st.header("Processar PDFs")
        
        # Upload de PDFs
        uploaded_pdfs = st.file_uploader(
            "Faça upload dos PDFs de extratos bancários ou cartões de crédito",
            type=["pdf"],
            accept_multiple_files=True
        )
        
        # Upload do arquivo de categorias
        uploaded_categories = st.file_uploader(
            "Faça upload do arquivo de categorias (CSV ou Excel)",
            type=["csv", "xlsx", "xls"],
            help="O arquivo deve conter as colunas 'pattern' e 'category'. A coluna 'pattern' contém os padrões de descrição e a coluna 'category' contém as categorias correspondentes."
        )
        
        # Exibe informações sobre o formato do arquivo de categorias
        with st.expander("Informações sobre o arquivo de categorias"):
            st.markdown("""
            ### Formato do arquivo de categorias
            
            O arquivo de categorias deve conter duas colunas:
            
            - **pattern**: Padrão de descrição para correspondência
            - **category**: Categoria a ser atribuída
            
            #### Exemplos:
            
            | pattern | category |
            |---------|----------|
            | supermercado | Alimentação |
            | farmacia | Saúde |
            | *uber* | Transporte |
            
            #### Observações:
            
            - Use asteriscos (*) ao redor de um padrão para indicar correspondência por substring (ex: *uber* corresponderá a qualquer descrição que contenha "uber")
            - Sem asteriscos, o padrão será usado para correspondência exata
            - Para descrições não categorizadas pelos padrões, o aplicativo tentará fuzzy matching e, se habilitado, IA
            """)
            
            # Botão para baixar um modelo de arquivo de categorias
            if st.button("Baixar modelo de arquivo de categorias"):
                # Cria um DataFrame de exemplo
                example_df = pd.DataFrame({
                    'pattern': [
                        'supermercado', 'mercado', 'padaria', 
                        '*farmacia*', '*hospital*', '*clinica*',
                        'uber', 'taxi', '99',
                        '*netflix*', '*spotify*', '*cinema*'
                    ],
                    'category': [
                        'Alimentação', 'Alimentação', 'Alimentação',
                        'Saúde', 'Saúde', 'Saúde',
                        'Transporte', 'Transporte', 'Transporte',
                        'Entretenimento', 'Entretenimento', 'Entretenimento'
                    ]
                })
                
                # Converte para CSV
                csv = example_df.to_csv(index=False).encode('utf-8')
                
                # Botão para download
                st.download_button(
                    label="Baixar modelo CSV",
                    data=csv,
                    file_name="categorias_modelo.csv",
                    mime="text/csv"
                )
        
        # Botão para processar
        if st.button("Processar PDFs", type="primary", disabled=not (uploaded_pdfs and uploaded_categories)):
            if uploaded_pdfs and uploaded_categories:
                with st.spinner("Processando PDFs e categorizando transações..."):
                    # Processa os PDFs e categoriza as transações
                    results = process_pdfs(uploaded_pdfs, uploaded_categories, api_key, enable_ai, fuzzy_threshold)
                    
                    if results is not None:
                        # Exibe os resultados
                        st.success(f"Processamento concluído! {len(results)} transações extraídas e categorizadas.")
                        
                        # Salva os resultados na sessão para uso em outras abas
                        st.session_state.results = results
                        
                        # Exibe uma prévia dos resultados
                        st.subheader("Prévia dos resultados")
                        st.dataframe(results.head(10))
                        
                        # Opção para download dos resultados
                        csv = results.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Baixar resultados (CSV)",
                            data=csv,
                            file_name="transacoes_categorizadas.csv",
                            mime="text/csv"
                        )
                        
                        # Estatísticas de categorização
                        if 'categorized_by' in results.columns:
                            st.subheader("Estatísticas de categorização")
                            stats = results['categorized_by'].value_counts().to_dict()
                            stats['não categorizado'] = (results['category'] == '').sum()
                            
                            # Cria um gráfico de barras com as estatísticas
                            fig, ax = plt.subplots(figsize=(10, 5))
                            sns.barplot(x=list(stats.keys()), y=list(stats.values()), ax=ax)
                            ax.set_title("Métodos de categorização")
                            ax.set_xlabel("Método")
                            ax.set_ylabel("Quantidade de transações")
                            st.pyplot(fig)
            else:
                st.error("Por favor, faça upload dos PDFs e do arquivo de categorias.")
    
    # Aba 2: Gerenciar Categorias
    with tab2:
        st.header("Gerenciar Categorias")
        
        # Carrega as categorias se já foram processadas
        if uploaded_categories:
            categories_df = load_categories(uploaded_categories)
            
            if categories_df is not None:
                # Exibe as categorias existentes
                st.subheader("Categorias existentes")
                st.dataframe(categories_df)
                
                # Adicionar nova categoria
                st.subheader("Adicionar nova categoria")
                col1, col2 = st.columns(2)
                with col1:
                    new_pattern = st.text_input("Padrão de descrição")
                with col2:
                    new_category = st.text_input("Categoria")
                
                if st.button("Adicionar", disabled=not (new_pattern and new_category)):
                    if new_pattern and new_category:
                        # Adiciona a nova categoria ao DataFrame
                        new_row = pd.DataFrame({'pattern': [new_pattern], 'category': [new_category]})
                        categories_df = pd.concat([categories_df, new_row], ignore_index=True)
                        
                        # Salva o DataFrame atualizado
                        st.session_state.categories_df = categories_df
                        
                        # Exibe mensagem de sucesso
                        st.success(f"Categoria '{new_category}' adicionada com sucesso!")
                        
                        # Atualiza a exibição
                        st.experimental_rerun()
                
                # Opção para download do arquivo de categorias atualizado
                if st.button("Baixar arquivo de categorias atualizado"):
                    csv = categories_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Baixar categorias (CSV)",
                        data=csv,
                        file_name="categorias.csv",
                        mime="text/csv"
                    )
        else:
            st.info("Faça upload de um arquivo de categorias na aba 'Processar PDFs' para gerenciá-las aqui.")
    
    # Aba 3: Visualizar Resultados
    with tab3:
        st.header("Visualizar Resultados")
        
        # Verifica se há resultados para visualizar
        if 'results' in st.session_state and not st.session_state.results.empty:
            results = st.session_state.results
            
            # Filtros
            st.subheader("Filtros")
            col1, col2 = st.columns(2)
            
            with col1:
                # Filtro por categoria
                if 'category' in results.columns:
                    categories = ['Todas'] + sorted(results['category'].unique().tolist())
                    selected_category = st.selectbox("Categoria", categories)
            
            with col2:
                # Filtro por período
                if 'date' in results.columns:
                    min_date = pd.to_datetime(results['date']).min().date()
                    max_date = pd.to_datetime(results['date']).max().date()
                    date_range = st.date_input(
                        "Período",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )
            
            # Aplica os filtros
            filtered_results = results.copy()
            
            if 'category' in filtered_results.columns and selected_category != 'Todas':
                filtered_results = filtered_results[filtered_results['category'] == selected_category]
            
            if 'date' in filtered_results.columns and len(date_range) == 2:
                filtered_results['date'] = pd.to_datetime(filtered_results['date'])
                filtered_results = filtered_results[
                    (filtered_results['date'].dt.date >= date_range[0]) &
                    (filtered_results['date'].dt.date <= date_range[1])
                ]
            
            # Exibe os resultados filtrados
            st.subheader("Transações")
            st.dataframe(filtered_results)
            
            # Análises e gráficos
            st.subheader("Análises")
            
            # Gráfico de gastos por categoria
            if 'category' in filtered_results.columns and 'amount' in filtered_results.columns:
                # Agrupa por categoria e soma os valores
                category_totals = filtered_results.groupby('category')['amount'].sum().sort_values(ascending=False)
                
                # Cria o gráfico
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.barplot(x=category_totals.index, y=category_totals.values, ax=ax)
                ax.set_title("Gastos por categoria")
                ax.set_xlabel("Categoria")
                ax.set_ylabel("Valor total (R$)")
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
                
                # Gráfico de pizza com percentuais
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(
                    category_totals.values,
                    labels=category_totals.index,
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax.axis('equal')
                ax.set_title("Distribuição de gastos por categoria")
                st.pyplot(fig)
        else:
            st.info("Processe PDFs na aba 'Processar PDFs' para visualizar os resultados aqui.")


def process_pdfs(uploaded_pdfs, uploaded_categories, api_key, enable_ai, fuzzy_threshold):
    """
    Processa os PDFs e categoriza as transações.
    
    Args:
        uploaded_pdfs: Lista de arquivos PDF carregados
        uploaded_categories: Arquivo de categorias carregado
        api_key: Chave da API do Google Gemini
        enable_ai: Se True, usa IA para categorização
        fuzzy_threshold: Limiar para fuzzy matching
        
    Returns:
        DataFrame com as transações categorizadas
    """
    try:
        # Carrega as categorias
        categories_df = load_categories(uploaded_categories)
        if categories_df is None:
            st.error("Erro ao carregar o arquivo de categorias.")
            return None
        
        # Inicializa o categorizador
        categorizer = ChainCategorizer(categories_df, enable_ai=enable_ai)
        categorizer.set_fuzzy_threshold(fuzzy_threshold)
        
        if api_key:
            categorizer.set_ai_api_key(api_key)
        
        # Processa cada PDF
        all_transactions = []
        
        for pdf_file in uploaded_pdfs:
            # Salva o PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(pdf_file.read())
                pdf_path = tmp.name
            
            try:
                # Extrai as transações do PDF
                extractor = GenericExtractor(pdf_path)
                
                if extractor.can_process():
                    transactions = extractor.extract()
                    
                    if not transactions.empty:
                        # Adiciona o nome do arquivo como fonte
                        transactions['source'] = pdf_file.name
                        
                        # Adiciona as transações à lista
                        all_transactions.append(transactions)
                else:
                    st.warning(f"Não foi possível processar o arquivo {pdf_file.name}. Formato não suportado.")
            except Exception as e:
                st.error(f"Erro ao processar o arquivo {pdf_file.name}: {str(e)}")
            finally:
                # Remove o arquivo temporário
                os.unlink(pdf_path)
        
        if not all_transactions:
            st.warning("Nenhuma transação foi extraída dos PDFs.")
            return None
        
        # Combina todas as transações
        all_transactions_df = pd.concat(all_transactions, ignore_index=True)
        
        # Categoriza as transações
        categorized_df = categorizer.categorize(all_transactions_df)
        
        # Exibe estatísticas de categorização
        stats = categorizer.get_stats()
        logger.info(f"Estatísticas de categorização: {stats}")
        
        return categorized_df
    
    except Exception as e:
        st.error(f"Erro ao processar os PDFs: {str(e)}")
        logger.exception("Erro ao processar os PDFs")
        return None


def load_categories(uploaded_categories):
    """
    Carrega as categorias de um arquivo CSV ou Excel.
    
    Args:
        uploaded_categories: Arquivo de categorias carregado
        
    Returns:
        DataFrame com as categorias
    """
    try:
        # Salva o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_categories.name).suffix) as tmp:
            tmp.write(uploaded_categories.read())
            categories_path = tmp.name
        
        # Carrega o arquivo
        if categories_path.endswith('.csv'):
            categories_df = pd.read_csv(categories_path)
        elif categories_path.endswith(('.xlsx', '.xls')):
            categories_df = pd.read_excel(categories_path)
        else:
            st.error("Formato de arquivo de categorias não suportado.")
            return None
        
        # Verifica se o DataFrame tem as colunas necessárias
        required_columns = ['pattern', 'category']
        missing_columns = [col for col in required_columns if col not in categories_df.columns]
        
        if missing_columns:
            st.error(f"Colunas obrigatórias ausentes no arquivo de categorias: {missing_columns}")
            return None
        
        # Remove o arquivo temporário
        os.unlink(categories_path)
        
        # Reseta o arquivo para que possa ser lido novamente
        uploaded_categories.seek(0)
        
        return categories_df
    
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de categorias: {str(e)}")
        logger.exception("Erro ao carregar o arquivo de categorias")
        return None


if __name__ == "__main__":
    main()
