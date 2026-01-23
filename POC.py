import streamlit as st
import pandas as pd
import plotly.express as px

# ================= CONFIGURAÇÃO =================
st.set_page_config(
    page_title="Dashboard de Investimentos ES",
    layout="wide",
)

# ================== CARREGAMENTO ==================
@st.cache_data
def carregar_dados_excel(caminho):
    try:
        df = pd.read_excel(caminho)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo: {e}")
        st.stop()

# 👉 NOVA BASE
CAMINHO_EXCEL = "NOTICIAS_VALORES_MONETARIOS v2.xlsx"
dados = carregar_dados_excel(CAMINHO_EXCEL)

# ================== DETECÇÃO DE COLUNAS ==================
# Procura coluna de data
col_data = None
for c in dados.columns:
    if "data" in c.lower() or "publicacao" in c.lower():
        col_data = c
        break

if col_data is None:
    st.error("❌ Nenhuma coluna de data encontrada.")
    st.stop()

# Procura coluna de fonte
col_fonte = None
for c in dados.columns:
    if "fonte" in c.lower():
        col_fonte = c
        break

# Procura coluna de região
col_regiao = None
for c in dados.columns:
    if "região" in c.lower() or "regiao" in c.lower():
        col_regiao = c
        break

# Procura coluna de cidade
col_cidade = None
for c in dados.columns:
    if "cidade" in c.lower() or "município" in c.lower() or "municipio" in c.lower():
        col_cidade = c
        break

# Procura coluna de valor
colunas_possiveis_valor = ["Valores_Monetarios", "Valores", "Valor"]
coluna_valor = None

for col in colunas_possiveis_valor:
    if col in dados.columns:
        coluna_valor = col
        break

if coluna_valor is None:
    st.error("❌ Nenhuma coluna de valores encontrada na planilha.")
    st.stop()

# ================== TRATAMENTO DE DADOS ==================
# TRATAMENTO DE DATAS
dados[col_data] = pd.to_datetime(dados[col_data], errors='coerce', dayfirst=True)

# TRATAMENTO DE VALORES MONETÁRIOS
def limpar_valor_monetario(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    if valor_str == '':
        return None

    valor_str = valor_str.replace('R$', '').replace('$', '').strip()

    try:
        return float(valor_str)
    except:
        pass

    if '.' in valor_str and ',' in valor_str:
        partes = valor_str.split(',')
        inteiro = partes[0].replace('.', '')
        decimal = partes[1]
        try:
            return float(f"{inteiro}.{decimal}")
        except:
            return None

    if ',' in valor_str and '.' not in valor_str:
        try:
            return float(valor_str.replace(',', '.'))
        except:
            return None

    try:
        return float(valor_str.replace('.', ''))
    except:
        return None

# Aplica limpeza
dados["Valor_Tratado"] = dados[coluna_valor].apply(limpar_valor_monetario)

# Remove linhas inválidas
dados_limpos = dados.dropna(subset=["Valor_Tratado", col_data]).copy()

if dados_limpos.empty:
    st.error("❌ Nenhum dado válido encontrado após limpeza dos dados.")
    st.stop()

# Colunas auxiliares
dados_limpos["Ano"] = dados_limpos[col_data].dt.year
dados_limpos["Mês"] = dados_limpos[col_data].dt.month
dados_limpos["Data"] = dados_limpos[col_data].dt.date

data_min = dados_limpos["Data"].min()
data_max = dados_limpos["Data"].max()

# ================== SIDEBAR ==================
st.sidebar.header("Filtros")

# Session state
if 'filtro_data_inicio' not in st.session_state:
    st.session_state.filtro_data_inicio = data_min
if 'filtro_data_fim' not in st.session_state:
    st.session_state.filtro_data_fim = data_max
if 'filtro_fonte' not in st.session_state:
    st.session_state.filtro_fonte = "Todas"

# Limpar filtros
def limpar_filtros():
    st.session_state.filtro_data_inicio = data_min
    st.session_state.filtro_data_fim = data_max
    st.session_state.filtro_fonte = "Todas"

if st.sidebar.button("🧹 Limpar todos os filtros", type="secondary"):
    limpar_filtros()
    st.rerun()

st.sidebar.divider()

# Período
st.sidebar.subheader("📅 Período")
col1, col2 = st.sidebar.columns(2)

with col1:
    data_inicio = st.date_input(
        "Data inicial",
        st.session_state.filtro_data_inicio,
        min_value=data_min,
        max_value=data_max
    )

with col2:
    data_fim = st.date_input(
        "Data final",
        st.session_state.filtro_data_fim,
        min_value=data_min,
        max_value=data_max
    )

st.session_state.filtro_data_inicio = data_inicio
st.session_state.filtro_data_fim = data_fim

# Fonte
if col_fonte:
    st.sidebar.subheader("📰 Fonte")
    fontes = sorted(dados_limpos[col_fonte].dropna().unique())
    opcoes_fonte = ["Todas"] + fontes

    fonte_selecionada = st.sidebar.selectbox(
        "Selecione uma fonte",
        opcoes_fonte,
        index=opcoes_fonte.index(st.session_state.filtro_fonte)
        if st.session_state.filtro_fonte in opcoes_fonte else 0
    )

    st.session_state.filtro_fonte = fonte_selecionada

# Região
if col_regiao:
    st.sidebar.subheader("🗺️ Região")
    regioes = sorted(dados_limpos[col_regiao].dropna().unique())
    regioes_sel = st.sidebar.multiselect("Selecione a região", regioes, default=regioes)

# Cidade
if col_cidade:
    st.sidebar.subheader("🏙️ Cidade")
    df_cidades = dados_limpos
    if col_regiao:
        df_cidades = df_cidades[df_cidades[col_regiao].isin(regioes_sel)]

    cidades = sorted(df_cidades[col_cidade].dropna().unique())
    cidades_sel = st.sidebar.multiselect("Selecione a cidade", cidades, default=cidades)

# ================== APLICA FILTROS ==================
df = dados_limpos.copy()

df = df[(df["Data"] >= data_inicio) & (df["Data"] <= data_fim)]

if col_fonte and fonte_selecionada != "Todas":
    df = df[df[col_fonte] == fonte_selecionada]

if col_regiao:
    df = df[df[col_regiao].isin(regioes_sel)]

if col_cidade:
    df = df[df[col_cidade].isin(cidades_sel)]

# ================== KPIs ==================
total_registros = df.shape[0]
total_investido = df["Valor_Tratado"].sum() if total_registros > 0 else 0
valor_medio = df["Valor_Tratado"].mean() if total_registros > 0 else 0

# Função para formatar valores em reais
def formatar_reais(valor):
    if valor >= 1_000_000_000:  # Bilhões
        return f"R$ {valor/1_000_000_000:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
    elif valor >= 1_000_000:  # Milhões
        return f"R$ {valor/1_000_000:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    else:  # Milhares ou menos
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ================== VISÃO GERAL ==================
st.title("📊 Dashboard de Investimentos - Espírito Santo")

# Mostra período filtrado
periodo_str = ""
if data_inicio != data_min or data_fim != data_max:
    periodo_str = f" ({data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})"

st.subheader(f"📈 Visão Geral{periodo_str}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total de Registros",
        f"{total_registros:,}".replace(",", "."),
        help="Número de notícias com valores monetários válidos"
    )

with col2:
    st.metric(
        "Total Investido",
        formatar_reais(total_investido),
        help="Soma de todos os valores monetários no período"
    )

with col3:
    st.metric(
        "Valor Médio por Registro",
        formatar_reais(valor_medio),
        help="Média dos valores monetários"
    )

st.divider()

# ================== ANÁLISES VISUAIS ==================
if total_registros > 0:
    st.subheader("📊 Análises Visuais")
    
    # TABS para diferentes visualizações
    tab1, tab2, tab3 = st.tabs(["📈 Evolução Temporal", "📰 Por Fonte", "🏆 Top Investimentos"])
    
    with tab1:
        # Evolução temporal
        if len(df["Data"].unique()) > 1:
            # Agrupa por mês/ano
            evolucao = df.copy()
            evolucao["Mês-Ano"] = evolucao[col_data].dt.strftime('%m/%Y')
            evolucao["Data_Ord"] = evolucao[col_data].dt.to_period('M')
            
            evolucao_agrupada = (
                evolucao.groupby(["Data_Ord", "Mês-Ano"], as_index=False)["Valor_Tratado"]
                .sum()
                .sort_values("Data_Ord")
            )
            
            fig_evolucao = px.line(
                evolucao_agrupada,
                x="Mês-Ano",
                y="Valor_Tratado",
                markers=True,
                title=f"Evolução dos Investimentos{periodo_str}"
            )
            fig_evolucao.update_layout(
                yaxis_title="Valor Total (R$)",
                xaxis_title="Mês-Ano",
                xaxis=dict(tickangle=45)
            )
            st.plotly_chart(fig_evolucao, width="stretch")
        else:
            st.info("📅 Selecione um período mais amplo para ver a evolução temporal.")
    
    with tab2:
        # Por fonte
        if col_fonte and len(df[col_fonte].unique()) > 1:
            por_fonte = (
                df.groupby(col_fonte, as_index=False)["Valor_Tratado"]
                .sum()
                .sort_values("Valor_Tratado", ascending=False)
            )
            
            fig_fonte = px.bar(
                por_fonte,
                x=col_fonte,
                y="Valor_Tratado",
                title=f"Investimentos por Fonte{periodo_str}"
            )
            fig_fonte.update_layout(
                yaxis_title="Valor Total (R$)",
                xaxis_title="Fonte",
                xaxis=dict(tickangle=45)
            )
            st.plotly_chart(fig_fonte, width="stretch")
        else:
            st.info("📰 Selecione 'Todas' nas fontes para ver a distribuição completa.")
    
    with tab3:
        # Top 10 maiores investimentos
        top_10 = df.nlargest(10, "Valor_Tratado")[["Título", col_data, col_fonte, "Valor_Tratado"]].copy()
        top_10 = top_10.sort_values("Valor_Tratado", ascending=True)
        
        # Cria título abreviado para o gráfico
        top_10["Título_Curto"] = top_10["Título"].apply(
            lambda x: (x[:50] + "...") if len(x) > 50 else x
        )
        
        fig_top10 = px.bar(
            top_10,
            y="Título_Curto",
            x="Valor_Tratado",
            orientation='h',
            title="Top 10 Maiores Investimentos",
            hover_data=[col_fonte, col_data, "Título"]
        )
        fig_top10.update_layout(
            xaxis_title="Valor (R$)",
            yaxis_title="",
            height=500
        )
        st.plotly_chart(fig_top10, width="stretch")
    
    st.divider()
    
    # ================== TABELA DE REGISTROS ==================
    st.subheader(f"📋 Registros Encontrados ({total_registros})")
    
    # Colunas para mostrar
    colunas_mostrar = ["Título", "Link", col_data, col_fonte, "Valor_Tratado"]
    colunas_mostrar = [c for c in colunas_mostrar if c in df.columns]
    
    # Prepara dataframe para exibição
    df_display = df[colunas_mostrar].copy()
    df_display = df_display.sort_values(col_data, ascending=False)
    df_display[col_data] = df_display[col_data].dt.strftime('%d/%m/%Y')
    df_display["Valor (R$)"] = df_display["Valor_Tratado"].apply(formatar_reais)
    
    # Remove coluna original
    if "Valor_Tratado" in df_display.columns:
        df_display = df_display.drop(columns=["Valor_Tratado"])
    
    # Configuração das colunas
    column_config = {
        "Link": st.column_config.LinkColumn("Link", display_text="🔗"),
        "Título": st.column_config.TextColumn("Título", width="large"),
        col_data: st.column_config.TextColumn("Data"),
    }
    
    if col_fonte:
        column_config[col_fonte] = st.column_config.TextColumn("Fonte")
    
    column_config["Valor (R$)"] = st.column_config.TextColumn("Valor")
    
    st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        column_config=column_config
    )
    
    # ================== DOWNLOAD ==================
    st.divider()
    st.subheader("📥 Download dos Dados")
    
    # Prepara dados para download
    df_download = df.copy()
    df_download[col_data] = df_download[col_data].dt.strftime('%d/%m/%Y')
    df_download["Valor (R$)"] = df_download["Valor_Tratado"].apply(formatar_reais)
    
    if "Valor_Tratado" in df_download.columns:
        df_download = df_download.drop(columns=["Valor_Tratado"])
    
    csv = df_download.to_csv(index=False, sep=';', encoding='utf-8-sig')
    
    st.download_button(
        label="📥 Baixar dados em CSV",
        data=csv,
        file_name=f"investimentos_es_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width="stretch"
    )

else:
    st.warning("⚠️ Nenhum registro encontrado com os filtros aplicados. Tente ajustar os filtros.")

# ================== INFORMAÇÕES ==================
st.divider()
with st.expander("ℹ️ Sobre este dashboard"):
    st.write("""
    **Dashboard de Investimentos - Espírito Santo**
    
    Este dashboard apresenta informações sobre investimentos públicos
    no estado do Espírito Santo, extraídos de notícias oficiais.
    
    **Funcionalidades:**
    - Filtragem por período de datas
    - Filtragem por fonte/origem da notícia
    - Visualização da evolução temporal dos investimentos
    - Análise por fonte de informação
    - Lista dos maiores investimentos
    - Download dos dados filtrados
    
    **Fonte dos dados:** Notícias oficiais do governo do ES
    
    **Como usar:**
    1. Use os seletores de data para definir o período desejado
    2. Selecione uma fonte específica ou "Todas" para ver todas
    3. Clique em "Limpar todos os filtros" para voltar à visualização completa
    4. Use as abas para alternar entre diferentes visualizações
    5. Baixe os dados filtrados em formato CSV
    """)