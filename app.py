import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface
st.set_page_config(page_title="Wealth Command Center", layout="wide")

# 2. Função de Busca de Dados Resiliente (Resolve KeyError: 'Adj Close')
@st.cache_data(ttl=600)
def buscar_mercado(tickers):
    try:
        lista = list(set([str(t).strip().upper() for t in tickers if t]))
        if not lista: return pd.Series()
        
        all_tickers = lista + ['USDBRL=X']
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty: return pd.Series()
        
        # Tenta pegar preço ajustado, se não tiver, pega o fechamento comum
        if 'Adj Close' in df_raw.columns:
            precos = df_raw['Adj Close']
        else:
            precos = df_raw['Close']
            
        return precos.ffill().iloc[-1]
    except Exception:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Wealth Management Command Center")

# 3. Gerenciamento de Dados (Inicia vazio para você adicionar)
if 'meus_ativos' not in st.session_state:
    st.session_state.meus_ativos = pd.DataFrame(columns=['Ativo', 'Qtd', 'Custo Inicial', 'Alvo %'])

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📥 Adicionar Novo Ativo")
    with st.form("cadastro_ativo"):
        ticker = st.text_input("Código (Ex: ITUB3.SA, AAPL, BTC-USD)").upper().strip()
        qtd = st.number_input("Quantidade", min_value=0.0, format="%.8f")
        custo = st.number_input("Valor Total Investido (R$)", min_value=0.0)
        alvo = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Adicionar"):
            if ticker:
                novo = pd.DataFrame([{"Ativo": ticker, "Qtd": qtd, "Custo Inicial": custo, "Alvo %": alvo}])
                st.session_state.meus_ativos = pd.concat([st.session_state.meus_ativos, novo], ignore_index=True)
                st.rerun()
    
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.meus_ativos = pd.DataFrame(columns=['Ativo', 'Qtd', 'Custo Inicial', 'Alvo %'])
        st.rerun()

# --- CÁLCULOS ---
df = st.session_state.meus_ativos.copy()

if not df.empty:
    precos_vivos = buscar_mercado(df['Ativo'].tolist())
    dolar = precos_vivos.get('USDBRL=X', 5.00)
