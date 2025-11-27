import streamlit as st
import pandas as pd
import requests
from io import StringIO, BytesIO
from datetime import datetime
import numpy as np

# --- CONFIGURAÇÕES E FUNÇÕES ---

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Investimentos ES",
    page_icon="📊",
    layout="wide"
)

# Título do app
st.title("📊 Dashboard de Investimentos ES")
st.markdown("---")

@st.cache_data(ttl=3600) # Cache por 1 hora
def carregar_dados_google_sheets():
    """
    Carrega dados do Google Sheets usando o file ID
    """
    try:
        # File ID do Google Sheets
        file_id = "10fL3n_XrPPGgSQ4DiIQm0MEvi0CLGbd_" 
        
        # URL para download como CSV
        url = f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv'
        
        # Fazer download do arquivo
        response = requests.get(url)
        response.raise_for_status()
        
        # Tentar diferentes encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                # Ler os dados com encoding específico
                # Usando BytesIO para melhor manipulação de encoding
                dados = pd.read_csv(BytesIO(response.content), encoding=encoding)
                return dados
            except UnicodeDecodeError:
                continue
        
        # Se nenhum encoding funcionar
        dados = pd.read_csv(BytesIO(response.content), encoding='utf-8', errors='replace')
        return dados
        
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return None

def corrigir_caracteres_ptbr(texto):
    """
    Corrige caracteres portugueses que foram mal decodificados
    """
    if pd.isna(texto):
        return texto
    
    texto_str = str(texto)
    
    # Mapeamento de caracteres problemáticos
    correcoes = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
        'Ã£': 'ã', 'Ãµ': 'õ', 'Ã§': 'ç',
        'Ã€': 'À', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú',
        'Ãƒ': 'Ã', 'Ã•': 'Õ', 'Ã‡': 'Ç',
        'Ã¢': 'â', 'Ãª': 'ê', 'Ã®': 'î', 'Ã´': 'ô', 'Ã»': 'û',
        'Ã¤': 'ä', 'Ã«': 'ë', 'Ã¯': 'ï', 'Ã¶': 'ö', 'Ã¼': 'ü',
        'Ã±': 'ñ', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú',
        'Ã§': 'ç', 'Ã£': 'ã', 'Ãµ': 'õ'
    }
    
    for erro, correcao in correcoes.items():
        texto_str = texto_str.replace(erro, correcao)
    
    return texto_str

def converter_coluna_numerica(coluna):
    """
    Converte uma coluna para numérico, tratando strings com formato de moeda
    """
    # Se já for numérico, retornar como está
    if pd.api.types.is_numeric_dtype(coluna):
        return coluna
    
    coluna_limpa = coluna.astype(str)
    
    # Remover caracteres não numéricos exceto pontos, vírgulas e hífen
    coluna_limpa = coluna_limpa.str.replace('R\$', '', regex=False)
    coluna_limpa = coluna_limpa.str.replace('USD', '', regex=False)
    coluna_limpa = coluna_limpa.str.replace('€', '', regex=False)
    coluna_limpa = coluna_limpa.str.replace(' ', '', regex=False)
    coluna_limpa = coluna_limpa.str.replace('"', '', regex=False)
    coluna_limpa = coluna_limpa.str.replace("'", "", regex=False)
    
    # Verificar se o formato é brasileiro (vírgula como decimal)
    tem_virgula = coluna_limpa.str.contains(',').any()
    tem_ponto_milhar = coluna_limpa.str.contains(r'\.\d{3},').any()
    
    if tem_virgula and tem_ponto_milhar:
        # Formato brasileiro: 1.000,00 -> remover pontos e converter vírgula para ponto
        coluna_limpa = coluna_limpa.str.replace('.', '', regex=False)
        coluna_limpa = coluna_limpa.str.replace(',', '.', regex=False)
    elif tem_virgula and not tem_ponto_milhar:
        # Formato europeu: 1000,00 -> converter vírgula para ponto
        coluna_limpa = coluna_limpa.str.replace(',', '.', regex=False)
    
    # Converter para numérico
    return pd.to_numeric(coluna_limpa, errors='coerce')

def to_excel(df):
    """Converte DataFrame para Excel"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    processed_data = output.getvalue()
    return processed_data

# --- CARREGAMENTO E PRÉ-PROCESSAMENTO ---

# Carregar dados
with st.spinner("Carregando dados do Google Sheets..."):
    dados = carregar_dados_google_sheets()

if dados is None or dados.empty:
    st.error("Não foi possível carregar os dados. Verifique o link do Google Sheets.")
    st.stop()

# Aplicar correção de caracteres em todas as colunas de texto
for coluna in dados.columns:
    if dados[coluna].dtype == 'object':
        dados[coluna] = dados[coluna].apply(corrigir_caracteres_ptbr)

# Detectar coluna de investimento
colunas_investimento = [col for col in dados.columns if 'invest' in col.lower()]
if colunas_investimento:
    coluna_investimento = colunas_investimento[0]
    # Converter a coluna
    dados[coluna_investimento] = converter_coluna_numerica(dados[coluna_investimento])
else:
    coluna_investimento = None

# Identificar coluna de data automaticamente
colunas_data = [col for col in dados.columns if 'data' in col.lower() or 'date' in col.lower()]
if colunas_data:
    coluna_data = colunas_data[0]
    # Converter para datetime se possível
    if not pd.api.types.is_datetime64_any_dtype(dados[coluna_data]):
        dados[coluna_data] = pd.to_datetime(dados[coluna_data], errors='coerce')
    dados = dados.dropna(subset=[coluna_data]) # Remover linhas sem data válida
else:
    coluna_data = dados.columns[0]
    st.error(f"Coluna de data não encontrada. Usando a coluna '{coluna_data}' para datas, mas o filtro de data pode não funcionar.")


# --- GESTÃO DE ESTADO DO FILTRO E CALLBACK ---

DATE_START_KEY = 'date_inicio_state'
DATE_END_KEY = 'date_fim_state'
SPECIFIC_FILTERS_KEYS = 'specific_filters_keys'

# Filtros específicos (usados para Selectbox)
filtros_select_names = ['source', 'região', 'cidade', 'regiao', 'region', 'city']

# Encontrar os valores min e max de data após o pré-processamento
data_min = dados[coluna_data].min().date() if dados[coluna_data].notna().any() else datetime.now().date()
data_max = dados[coluna_data].max().date() if dados[coluna_data].notna().any() else datetime.now().date()

# 1. Função de callback para resetar o estado dos filtros
def reset_filtros():
    """Reseta todos os valores dos filtros no st.session_state."""
    
    # Resetar filtros de data (usamos o valor padrão min/max)
    st.session_state[DATE_START_KEY] = data_min
    st.session_state[DATE_END_KEY] = data_max
    
    # Resetar filtros específicos (Selectboxes)
    if SPECIFIC_FILTERS_KEYS in st.session_state:
        for key in st.session_state[SPECIFIC_FILTERS_KEYS].values():
            st.session_state[key] = 'Todos'
    
# 2. Inicialização dos estados

# Inicialização dos Filtros Específicos (para Selectboxes)
if SPECIFIC_FILTERS_KEYS not in st.session_state:
    st.session_state[SPECIFIC_FILTERS_KEYS] = {}

if DATE_START_KEY not in st.session_state:
    st.session_state[DATE_START_KEY] = data_min

if DATE_END_KEY not in st.session_state:
    st.session_state[DATE_END_KEY] = data_max
    
# --- SIDEBAR PARA FILTROS ---

st.sidebar.title("⚙️ Filtros")

# 3. Widgets de Filtro

# Filtro de data
if dados[coluna_data].notna().any():
    
    st.sidebar.date_input(
        "Data inicial:",
        min_value=data_min,
        max_value=data_max,
        key=DATE_START_KEY # Vincula o widget à chave no session state
    )

    st.sidebar.date_input(
        "Data final:",
        min_value=data_min,
        max_value=data_max,
        key=DATE_END_KEY # Vincula o widget à chave no session state
    )
    
    # O filtro usará os valores atualizados do session_state
    data_inicio = st.session_state[DATE_START_KEY]
    data_fim = st.session_state[DATE_END_KEY]
    
else:
    st.sidebar.error("Não foi possível processar as datas")
    data_inicio = datetime.now().date()
    data_fim = datetime.now().date()


# Filtros específicos: source, região e cidade
filtros_aplicados = {}

for filtro_name in filtros_select_names:
    # Verificar se a coluna existe no dataset (case insensitive)
    colunas_existentes = [col for col in dados.columns if filtro_name in col.lower()]
    
    if colunas_existentes:
        coluna_filtro = colunas_existentes[0]
        valores_unicos = ['Todos'] + sorted([str(x) for x in dados[coluna_filtro].dropna().unique()])
        
        filter_key = f"filter_{coluna_filtro}_key"
        
        # 3.1 Inicializa o estado para a Selectbox (se necessário)
        if filter_key not in st.session_state:
            st.session_state[filter_key] = 'Todos'
            
        # 3.2 Armazena a chave para que a função reset_filtros possa acessá-la
        st.session_state[SPECIFIC_FILTERS_KEYS][coluna_filtro] = filter_key

        # 3.3 Encontra o índice do valor salvo no state
        # Certifica-se de que o valor do state está na lista de opções (pode ser "Todos")
        try:
            indice_padrao = valores_unicos.index(st.session_state[filter_key])
        except ValueError:
            # Caso o valor salvo não exista mais, volta para 'Todos'
            indice_padrao = 0
            st.session_state[filter_key] = 'Todos'
        
        # Selectbox: O valor é lido do session_state
        st.sidebar.selectbox(
            f"{coluna_filtro.title()}:",
            options=valores_unicos,
            index=indice_padrao,
            key=filter_key # Vincula o widget à chave no session state
        )
        
        # O valor selecionado para aplicar o filtro é o valor atual do session_state
        filtros_aplicados[coluna_filtro] = st.session_state[filter_key]

# Botão Limpar Filtros
st.sidebar.markdown("---")
# O botão chama a função reset_filtros, que atualiza o session state e força um rerun.
st.sidebar.button(
    "🔄 Limpar Filtros", 
    use_container_width=True, 
    key="btn_limpar_filtros", 
    on_click=reset_filtros
)
st.sidebar.markdown("---")


# --- APLICAR FILTROS ---

dados_filtrados = dados.copy()

# Filtrar por data
if dados[coluna_data].notna().any():
    dados_filtrados = dados_filtrados[
        (dados_filtrados[coluna_data].dt.date >= data_inicio) & 
        (dados_filtrados[coluna_data].dt.date <= data_fim)
    ]

# Aplicar outros filtros específicos
for coluna_filtro, valor_selecionado in filtros_aplicados.items():
    if valor_selecionado != 'Todos':
        dados_filtrados = dados_filtrados[
            dados_filtrados[coluna_filtro].astype(str) == valor_selecionado
        ]

# --- LAYOUT PRINCIPAL E VISUALIZAÇÃO ---

st.subheader("📈 Visão Geral")

# Métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_registros = len(dados_filtrados)
    st.metric("Total de Registros", total_registros)

with col2:
    if coluna_investimento and coluna_investimento in dados_filtrados.columns:
        total_investimento = dados_filtrados[coluna_investimento].sum()
        if pd.notna(total_investimento) and total_investimento != 0:
            st.metric("Total Investido", f"R$ {total_investimento:,.2f}")
        else:
            st.metric("Total Investido", "R$ 0,00")
    else:
        st.metric("Total Investido", "N/A")

with col3:
    if coluna_investimento and coluna_investimento in dados_filtrados.columns and len(dados_filtrados) > 0:
        media_investimentos = dados_filtrados[coluna_investimento].mean()
        if pd.notna(media_investimentos) and media_investimentos != 0:
            st.metric("Média de Investimentos", f"R$ {media_investimentos:,.2f}")
        else:
            st.metric("Média de Investimentos", "R$ 0,00")
    else:
        st.metric("Média de Investimentos", "N/A")

with col4:
    if len(dados_filtrados) > 0:
        st.metric("Período", f"{data_inicio} a {data_fim}")
    else:
        st.metric("Período", "N/A")

st.markdown("---")

# Tabela de dados
st.subheader("📊 Dados Filtrados")

if len(dados_filtrados) > 0:
    # Mostrar dados em uma tabela
    st.dataframe(
        dados_filtrados,
        use_container_width=True,
        height=400
    )
    
    # Download dos dados filtrados
    st.markdown("---")
    st.subheader("💾 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download como CSV
        csv = dados_filtrados.to_csv(index=False, date_format='%Y-%m-%d', encoding='utf-8')
        st.download_button(
            label="📥 Download como CSV",
            data=csv,
            file_name=f"dados_filtrados_{data_inicio}_{data_fim}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Download como Excel
        excel_data = to_excel(dados_filtrados)
        st.download_button(
            label="📥 Download como Excel",
            data=excel_data,
            file_name=f"dados_filtrados_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.ms-excel"
        )

else:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
    st.info("Tente ajustar os filtros para visualizar os dados.")

# Rodapé
st.markdown("---")
st.markdown(
    "Vent Digital  •  "
    f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)