import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface
st.set_page_config(page_title="Strategic Wealth Command Center", layout="wide")

# 2. Função de Busca de Dados ULTRA RESILIENTE (Resolve o erro da sua imagem)
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        # Limpeza: remove espaços e garante que estão em maiúsculas
        tickers_limpos = list(set([str(t).strip().upper() for t in tickers if t]))
        all_tickers = tickers_limpos + ['USDBRL=X']
        
        # Download robusto buscando 5 dias para evitar buracos em feriados
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty:
            return pd.Series()

        # Tenta pegar 'Adj Close', se falhar tenta 'Close'
        if 'Adj Close' in df_raw.columns:
            df_precos = df_raw['Adj Close']
        elif 'Close' in df_raw.columns:
            df_precos = df_raw['Close']
        else:
            return pd.Series()
            
        # Tratamento para múltiplos tickers ou apenas um
        if isinstance(df_precos, pd.Series):
            return pd.Series({tickers_limpos[0]: df_precos.ffill().iloc[-1]})

        return df_precos.ffill().iloc[-1]
        
    except Exception as e:
        st.sidebar.warning(f"Nota: Alguns dados podem estar instáveis. Erro: {e}")
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")
st.subheader("Gestão Consolidada: B3, Exterior e Cripto")

# 3. Inicialização da sua Carteira Real
if 'portfolio' not in st.session_state:
    # Dados baseados no seu perfil de investimento
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 920.0, "Alvo": 15.0}, # Itaú
        {"Ativo": "GOAU4.SA", "Qtd": 800.0, "Alvo": 15.0}, # Gerdau
        {"Ativo": "IAUM", "Qtd": 260.0, "Alvo": 10.0},      # Ouro
        {"Ativo": "SCHD", "Qtd": 60.0, "Alvo": 15.0},       # Dividendos EUA
        {"Ativo": "STAG", "Qtd": 80.0, "Alvo": 10.0},       # Industrial REIT
        {"Ativo": "SCHV", "Qtd": 40.0, "Alvo": 10.0},       # Value EUA
        {"Ativo": "DUHP", "Qtd": 30.0, "Alvo": 5.0},        # High Profitability
        {"Ativo": "JEPQ", "Qtd": 15.0, "Alvo": 5.0},        # Nasdaq Income
        {"Ativo": "AOK", "Qtd": 10.0, "Alvo": 5.0},         # Conservador
        {"Ativo": "O", "Qtd": 10.0, "Alvo": 10.0}           # Realty Income
    ])

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Gerenciar Ativos")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker (Ex: PETR4.SA, BTC-USD)").upper()
        q_in = st.number_input("Quantidade", min_value=0.0)
        a_in = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        if st.form_submit_button("Adicionar"):
            if t_in:
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- LÓGICA DE CÁLCULO ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())

# Busca o dólar separadamente se necessário para garantir
try:
    cotacao_dolar = precos_atuais['USDBRL=X']
except:
    cotacao_dolar = yf.download('USDBRL=X', period="5d")['Adj Close'].ffill().iloc[-1]

if not precos_atuais.empty:
    df_p['Preço Unit.'] = df_p['Ativo'].map(precos_atuais)
    
    # Remove ativos que não retornaram preço para não quebrar o gráfico
    df_p = df_p.dropna(subset=['Preço Unit.'])

    # Conversão para Real (BRL)
    def converter_brl(row):
        if ".SA" in row['Ativo']:
            return row['Preço Unit.'] * row['Qtd']
        return row['Preço Unit.'] * row['Qtd'] * cotacao_dolar

    df_p['Total R$'] = df_p.apply(converter_brl, axis=1)
    patrimonio_total = df_p['Total R$'].sum()
    
    if patrimonio_total > 0:
        df_p['Atual %'] = (df_p['Total R$'] / patrimonio_total) * 100
        df_p['Desvio %'] = df_p['Atual %'] - df_p['Alvo']

        # --- EXIBIÇÃO ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
        col2.metric("Dólar Hoje", f"R$ {cotacao_dolar:.2f}")
        col3.metric("Ativos Totais", len(df_p))

        tab1, tab2 = st.tabs(["📊 Gráficos", "⚖️ Estratégia"])
        with tab1:
            fig = px.pie(df_p, values='Total R$', names='Ativo', hole=0.5, title="Alocação de Patrimônio")
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.write("### Sugestão de Rebalanceamento")
            st.dataframe(df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].style.format("{:.2f}%"))
    else:
        st.info("Insira as quantidades dos seus ativos para gerar os cálculos.")
else:
    st.error("Conexão com o mercado financeiro instável. Tente atualizar a página em alguns instantes.")
