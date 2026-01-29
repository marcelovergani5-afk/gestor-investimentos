import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface
st.set_page_config(page_title="Wealth Command Center Pro", layout="wide")

# 2. Função de Busca de Dados com Proteção de Colunas
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        tickers_limpos = list(set([str(t).strip().upper() for t in tickers if t and t != "CDB"]))
        if not tickers_limpos: return pd.Series()
        
        all_tickers = tickers_limpos + ['USDBRL=X']
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty: return pd.Series()

        # Tenta Adj Close, senão Close, senão ignora (evita KeyError)
        if 'Adj Close' in df_raw.columns:
            df_precos = df_raw['Adj Close']
        elif 'Close' in df_raw.columns:
            df_precos = df_raw['Close']
        else:
            return pd.Series()
            
        return df_precos.ffill().iloc[-1]
    except Exception:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")

# 3. Inicialização da Carteira (Consolidando seus dados reais)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 920.0, "Alvo": 10.0, "Custo": 28000.0},
        {"Ativo": "GOAU4.SA", "Qtd": 800.0, "Alvo": 10.0, "Custo": 35000.0},
        {"Ativo": "CDB", "Qtd": 1.0, "Alvo": 50.0, "Custo": 600000.0},
        {"Ativo": "IAUM", "Qtd": 260.0, "Alvo": 5.0, "Custo": 26000.0},
        {"Ativo": "SCHD", "Qtd": 60.0, "Alvo": 5.0, "Custo": 25000.0},
        {"Ativo": "BTC-USD", "Qtd": 0.05, "Alvo": 5.0, "Custo": 15000.0}
    ])

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Gestão de Ativos")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker").upper().strip()
        q_in = st.number_input("Quantidade", min_value=0.0, format="%.8f", step=0.000001)
        c_in = st.number_input("Custo Total (R$)", min_value=0.0)
        a_in = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Guardar"):
            if t_in:
                if len(t_in) >= 5 and t_in[-1].isdigit() and ".SA" not in t_in: t_in += ".SA"
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in, "Custo": c_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- PROCESSAMENTO SEGURO ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())
cotacao_dolar = precos_atuais.get('USDBRL=X', 5.20)

# Mapeamento de preços sem falhas
df_p['Preço Unit.'] = df_p.apply(lambda r: r['Custo'] if r['Ativo'] == "CDB" else precos_atuais.get(r['Ativo'], 0), axis=1)

def converter_valor(row):
    if row['Ativo'] == "CDB": return row['Custo']
    p, q = float(row['Preço Unit.']), float(row['Qtd'])
    if p == 0: return row['Custo'] # Evita zerar se a API falhar
    return p * q if ".SA" in str(row['Ativo']) else p * q * float(cotacao_dolar)

df_p['Valor Atual (R$)'] = df_p.apply(converter_valor, axis=1)
patrimonio_total = df_p['Valor Atual (R$)'].sum()

# Cálculo de Rentabilidade com proteção contra divisão por zero
df_p['Rentab. R$'] = df_p['Valor Atual (R$)'] - df_p['Custo']
df_p['Rentab. %'] = (df_p['Rentab. R$'] / df_p['Custo'].replace(0, 1)) * 100
df_p['Atual %'] = (df_p['Valor Atual (R$)'] / patrimonio_total) * 100
df_p['Desvio %'] = df_p['Atual %'] - df_p['Alvo']

# --- INTERFACE ---
st.metric("Património Total", f"R$ {patrimonio_total:,.2f}")

aba1, aba2 = st.tabs(["📊 Alocação", "📈 Performance"])

with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.pie(df_p, values='Valor Atual (R$)', names='Ativo', hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        # fillna(0) impede o ValueError na exibição
        st.dataframe(df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].fillna(0).style.format("{:.2f}%"))

with aba2:
    st.write("### Desempenho dos Ativos")
    # Tabela de performance com proteção contra valores vazios
    df_perf = df_p[['Ativo', 'Qtd', 'Custo', 'Valor Atual (R$)', 'Rentab. %']].fillna(0)
    st.dataframe(df_perf.style.format({
        'Qtd': '{:.4f}', 
        'Custo': 'R$ {:,.2f}', 
        'Valor Atual (R$)': 'R$ {:,.2f}', 
        'Rentab. %': '{:.2f}%'
    }))
