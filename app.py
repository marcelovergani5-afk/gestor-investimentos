import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface
st.set_page_config(page_title="Strategic Wealth Command Center", layout="wide")

# 2. Função de Busca de Dados de Alta Disponibilidade
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        # Limpeza de lista e adição do Dólar
        tickers_limpos = list(set([str(t).strip().upper() for t in tickers if t]))
        all_tickers = tickers_limpos + ['USDBRL=X']
        
        # Download com tratamento de erro
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty:
            return pd.Series()

        # Seleção inteligente de colunas de preço
        if 'Adj Close' in df_raw.columns:
            df_precos = df_raw['Adj Close']
        elif 'Close' in df_raw.columns:
            df_precos = df_raw['Close']
        else:
            return pd.Series()
            
        # Retorna o último preço válido de cada ativo
        return df_precos.ffill().iloc[-1]
        
    except Exception as e:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")

# 3. Sua Carteira Real (Dados do contexto)
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

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Gerenciar Carteira")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker (Ex: PETR4.SA, BTC-USD)").upper()
        q_in = st.number_input("Quantidade", min_value=0.0)
        a_in = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        if st.form_submit_button("Adicionar Ativo"):
            if t_in:
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- LÓGICA DE CÁLCULO ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())

# Busca cotação do dólar (Segurança extra)
try:
    cotacao_dolar = precos_atuais['USDBRL=X']
except:
    cotacao_dolar = 5.20 # Valor reserva caso a API falhe temporariamente

if not precos_atuais.empty:
    df_p['Preço Unit.'] = df_p['Ativo'].map(precos_atuais)
    
    # LIMPEZA CRÍTICA: Remove ativos que falharam na busca de preço
    df_p = df_p.dropna(subset=['Preço Unit.'])

    # Cálculo em Reais
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
        c1, c2, c3 = st.columns(3)
        c1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
        c2.metric("Dólar Hoje", f"R$ {cotacao_dolar:.2f}")
        c3.metric("Ativos Ativos", len(df_p))

        # Gráfico
        fig = px.pie(df_p, values='Total R$', names='Ativo', hole=0.5, title="Distribuição de Patrimônio")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela de Decisão (Rebalanceamento)
        st.write("### ⚖️ Estratégia de Rebalanceamento")
        
        def cor_status(val):
            if val < -2.0: return 'background-color: #004d00; color: white' # Comprar
            if val > 2.0: return 'background-color: #4d0000; color: white'  # Aguardar
            return ''
        
        # Garantindo que os dados são numéricos antes de formatar
        df_final = df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].copy()
        df_final[['Atual %', 'Alvo', 'Desvio %']] = df_final[['Atual %', 'Alvo', 'Desvio %']].apply(pd.to_numeric)

        st.dataframe(
            df_final.style.applymap(cor_status, subset=['Desvio %'])
            .format("{:.2f}%", subset=['Atual %', 'Alvo', 'Desvio %']),
            use_container_width=True
        )
    else:
        st.info("Adicione quantidades para ver os cálculos.")
else:
    st.error("Erro ao conectar com o mercado. Verifique sua conexão.")
