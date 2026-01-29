import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# Configurações de Especialista
st.set_page_config(page_title="Strategic Wealth Manager", layout="wide")

# Estilização
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def get_data(tickers):
    # Busca ativos + Dólar
    data = yf.download(tickers + ['USDBRL=X'], period="1d")['Adj Close'].iloc[-1]
    return data

# --- TELA INICIAL ---
st.title("🚀 Strategic Wealth Command Center")
st.subheader("Gestão Global: B3, Exterior e Cripto")

# Simulando conexão com sua planilha (para teste imediato)
# Na versão final, conectamos ao seu Google Sheets
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 100, "Alvo": 20.0},
        {"Ativo": "AAPL", "Qtd": 10, "Alvo": 30.0},
        {"Ativo": "BTC-USD", "Qtd": 0.02, "Alvo": 25.0},
        {"Ativo": "WRLD11.SA", "Qtd": 50, "Alvo": 25.0}
    ])

# --- BARRA LATERAL (GESTÃO) ---
with st.sidebar:
    st.header("⚙️ Gerenciar Carteira")
    with st.form("add_asset"):
        new_ticker = st.text_input("Ticker (Ex: PETR4.SA, TSLA, ETH-USD)").upper()
        new_qtd = st.number_input("Quantidade", min_value=0.0)
        new_target = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        if st.form_submit_button("Adicionar Ativo"):
            new_row = pd.DataFrame([{"Ativo": new_ticker, "Qtd": new_qtd, "Alvo": new_target}])
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
            st.rerun()

# --- PROCESSAMENTO ---
tickers = st.session_state.portfolio['Ativo'].tolist()
prices = get_data(tickers)
usd_brl = prices['USDBRL=X']

# Cálculo de Valores
df = st.session_state.portfolio.copy()
df['Preço'] = df['Ativo'].map(prices)

def calc_brl(row):
    # Se não tem .SA e não é par de moeda BRL, assume USD
    if ".SA" in row['Ativo']:
        return row['Preço'] * row['Qtd']
    else:
        return row['Preço'] * row['Qtd'] * usd_brl

df['Valor Total (R$)'] = df.apply(calc_brl, axis=1)
total_patrimonio = df['Valor Total (R$)'].sum()
df['Atual %'] = (df['Valor Total (R$)'] / total_patrimonio) * 100
df['Desvio %'] = df['Atual %'] - df['Alvo']

# --- DASHBOARD VISUAL ---
m1, m2, m3 = st.columns(3)
m1.metric("Patrimônio Total", f"R$ {total_patrimonio:,.2f}")
m2.metric("Câmbio USD/BRL", f"R$ {usd_brl:.2f}")
m3.metric("Ativos Monitorados", len(df))

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 🍰 Alocação por Ativo")
    fig = px.pie(df, values='Valor Total (R$)', names='Ativo', hole=0.5, 
                 color_discrete_sequence=px.colors.qualitative.Dark24)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("### ⚖️ Analisador de Decisão")
    
    def highlight_decision(val):
        if val < -3: return 'background-color: #006400; color: white' # Verde escuro (Compra)
        if val > 3: return 'background-color: #8b0000; color: white'  # Vermelho (Venda/Aguardar)
        return ''

    df_view = df[['Ativo', 'Atual %', 'Alvo', 'Desvio %']]
    st.dataframe(df_view.style.applymap(highlight_decision, subset=['Desvio %']).format("{:.2f}%", subset=['Atual %', 'Alvo', 'Desvio %']), use_container_width=True)

# --- CALCULADORA DE APORTE ---
st.divider()
st.write("### 💰 Calculadora de Próximo Aporte")
val_aporte = st.number_input("Quanto você quer investir hoje? (R$)", min_value=0.0)

if val_aporte > 0:
    # Lógica de rebalanceamento: foca nos ativos que estão abaixo do alvo
    df_buy = df[df['Desvio %'] < 0].copy()
    total_desvio = abs(df_buy['Desvio %'].sum())
    df_buy['Sugestão (R$)'] = (abs(df_buy['Desvio %']) / total_desvio) * val_aporte
    
    st.success("Para equilibrar sua carteira, distribua seu aporte assim:")
    st.table(df_buy[['Ativo', 'Sugestão (R$)']].sort_values('Sugestão (R$)', ascending=False))
