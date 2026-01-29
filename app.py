import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface (Foco em Desktop)
st.set_page_config(page_title="Strategic Wealth Command Center", layout="wide")

# 2. Função de Busca de Dados Corrigida (Resolve o KeyError)
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        # Buscamos 5 dias para garantir dados em feriados e finais de semana
        df_precos = yf.download(tickers + ['USDBRL=X'], period="5d")['Adj Close']
        
        # Ajuste para caso o retorno seja apenas um ativo (Series vira DataFrame)
        if isinstance(df_precos, pd.Series):
            df_precos = df_precos.to_frame()
            
        # Preenche lacunas e pega o preço mais recente disponível
        return df_precos.ffill().iloc[-1]
    except Exception as e:
        st.error(f"Erro técnico na busca de cotações: {e}")
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")
st.subheader("Gestão Consolidada: B3, Exterior e Cripto")

# 3. Inicialização da sua Carteira Real
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 920.0, "Alvo": 15.0},
        {"Ativo": "GOAU4.SA", "Qtd": 800.0, "Alvo": 15.0},
        {"Ativo": "IAUM", "Qtd": 260.0, "Alvo": 10.0},
        {"Ativo": "SCHD", "Qtd": 60.0, "Alvo": 15.0},
        {"Ativo": "STAG", "Qtd": 80.0, "Alvo": 10.0},
        {"Ativo": "SCHV", "Qtd": 40.0, "Alvo": 10.0},
        {"Ativo": "DUHP", "Qtd": 30.0, "Alvo": 5.0},
        {"Ativo": "JEPQ", "Qtd": 15.0, "Alvo": 5.0},
        {"Ativo": "AOK", "Qtd": 10.0, "Alvo": 5.0},
        {"Ativo": "O", "Qtd": 10.0, "Alvo": 10.0}
    ])

# --- BARRA LATERAL PARA NOVOS ATIVOS ---
with st.sidebar:
    st.header("⚙️ Gerenciar Ativos")
    with st.form("novo_ativo"):
        ticker = st.text_input("Ticker (Ex: PETR4.SA, BTC-USD)").upper()
        qtd = st.number_input("Quantidade", min_value=0.0)
        alvo = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        if st.form_submit_button("Adicionar"):
            nova_linha = pd.DataFrame([{"Ativo": ticker, "Qtd": qtd, "Alvo": alvo}])
            st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
            st.rerun()

# --- CÁLCULOS E LÓGICA ---
lista_tickers = st.session_state.portfolio['Ativo'].tolist()
precos = get_data(lista_tickers)

if not precos.empty:
    usd_brl = precos['USDBRL=X']
    df = st.session_state.portfolio.copy()
    df['Preço Unit.'] = df['Ativo'].map(precos)

    # Conversão inteligente para BRL
    def converter_para_brl(row):
        if ".SA" in row['Ativo']: # Ativos Brasileiros
            return row['Preço Unit.'] * row['Qtd']
        else: # Ativos Exterior e Cripto (em USD)
            return row['Preço Unit.'] * row['Qtd'] * usd_brl

    df['Valor Total (R$)'] = df.apply(converter_para_brl, axis=1)
    total_patrimonio = df['Valor Total (R$)'].sum()
    df['Atual %'] = (df['Valor Total (R$)'] / total_patrimonio) * 100
    df['Desvio %'] = df['Atual %'] - df['Alvo']

    # --- EXIBIÇÃO ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Patrimônio Total", f"R$ {total_patrimonio:,.2f}")
    c2.metric("Dólar Hoje", f"R$ {usd_brl:.2f}")
    c3.metric("Ativos na Carteira", len(df))

    aba1, aba2 = st.tabs(["📊 Visão Geral", "⚖️ Rebalanceamento"])

    with aba1:
        fig = px.pie(df, values='Valor Total (R$)', names='Ativo', hole=0.5, title="Alocação por Ativo")
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        st.write("### Sugestões de Compra e Venda")
        def cor_status(val):
            if val < -2: return 'background-color: #004d00; color: white'
            if val > 2: return 'background-color: #4d0000; color: white'
            return ''
        
        st.dataframe(df[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].style.applymap(cor_status, subset=['Desvio %']).format("{:.2f}%"))

else:
    st.warning("Aguardando carregamento de dados do mercado...")
