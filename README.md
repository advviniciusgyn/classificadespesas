# Categorizador de Despesas

Aplicativo para extrair informações de extratos bancários e cartões de crédito em PDF, e categorizar automaticamente as despesas com base em uma lista de pré-categorizações fornecida pelo usuário.

## Funcionalidades

- Extração de dados de transações de múltiplos arquivos PDF (extratos bancários e cartões de crédito)
- Normalização dos dados extraídos (datas, valores, descrições)
- Categorização de transações usando:
  - Correspondência exata com lista pré-categorizada
  - Correspondência aproximada (fuzzy matching) para casos sem correspondência exata
  - IA como fallback para transações não categorizadas pelos métodos anteriores
- Geração de relatórios com as transações categorizadas
- Interface simples para upload de PDFs e visualização de resultados

## Uso Local

### Requisitos

- Python 3.9+
- Dependências listadas em `requirements.txt`

### Instalação

1. Clone este repositório
2. Crie um ambiente virtual Python:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

### Execução

1. Ative o ambiente virtual
2. Execute o aplicativo:
   ```
   streamlit run src/main.py
   ```
3. Acesse a interface web no navegador (geralmente em http://localhost:8501)
4. Faça upload dos PDFs de extratos e do arquivo de categorias
5. Visualize e exporte os resultados

## Deploy no Streamlit Cloud

Para fazer o deploy deste aplicativo no Streamlit Cloud, siga estas etapas:

1. Crie uma conta no [Streamlit Cloud](https://streamlit.io/cloud)
2. Conecte sua conta do GitHub
3. Faça fork deste repositório para sua conta do GitHub
4. No Streamlit Cloud, clique em "New app" e selecione o repositório
5. Configure o app:
   - Main file path: `src/main.py`
   - Python version: 3.9 ou superior
   - Requirements: `requirements.txt` (já incluído no repositório)

### Configuração de Segredos

Para usar a funcionalidade de IA (Google Gemini), você precisa configurar uma chave de API:

1. Obtenha uma chave de API do [Google AI Studio](https://ai.google.dev/)
2. No Streamlit Cloud, vá para as configurações do seu app
3. Na seção "Secrets", adicione:
   ```
   GEMINI_API_KEY = "sua-chave-api-aqui"
   ```

**Importante:** Por motivos de segurança, nunca inclua sua chave de API diretamente no código ou em arquivos que serão enviados para repositórios públicos. Sempre use variáveis de ambiente ou o sistema de segredos do Streamlit Cloud.

## Formato do Arquivo de Categorias

O arquivo de categorias deve ser um CSV ou Excel com duas colunas:

- **pattern**: Padrão de descrição para correspondência
- **category**: Categoria a ser atribuída

Exemplo:

| pattern | category |
|---------|----------|
| supermercado | Alimentação |
| farmacia | Saúde |
| *uber* | Transporte |

Observações:

- Use asteriscos (*) ao redor de um padrão para indicar correspondência por substring
- Sem asteriscos, o padrão será usado para correspondência exata

## Estrutura do Projeto

- `src/`: Código-fonte
  - `extractors/`: Módulos para extração de PDFs
  - `categorizers/`: Módulos para categorização
  - `utils/`: Funções utilitárias
  - `main.py`: Aplicativo principal
  - `config.py`: Configurações
- `requirements.txt`: Dependências do projeto

## Licença

Este projeto está licenciado sob a licença MIT.
