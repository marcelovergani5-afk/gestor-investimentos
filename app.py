import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface (Otimizado para computador)
st.set_page_config(page_title="Wealth Command Center Pro", layout="wide")

# 2. Função de Busca de Dados de Alta Precisão
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        tickers_limpos = list(set([str(t).strip().upper() for t in tickers if t and t != "CDB"]))
        all_tickers = tickers_limpos + ['USDBRL=X']
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty:
            return pd.Series()

        coluna_preco = 'Adj Close' if 'Adj Close' in df_raw.columns else 'Close'
        df_precos = df_raw[coluna_preco]
            
        if isinstance(df_precos, pd.Series):
            return pd.Series({tickers_limpos[0]: df_precos.ffill().iloc[-1]})

        return df_precos.ffill().iloc[-1]
    except Exception:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")

# 3. Inicialização da Carteira com Rendimento (Custo Total e Unidades)
if 'portfolio' not in st.session_state:
    # Incluindo os seus ativos com os valores de investimento conhecidos
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 920.0, "Alvo": 10.0, "Custo": 28000.0},
        {"Ativo": "GOAU4.SA", "Qtd": 800.0, "Alvo": 10.0, "Custo": 35000.0},
        {"Ativo": "CDB", "Qtd": 1.0, "Alvo": 50.0, "Custo": 600000.0},
        {"Ativo": "IAUM", "Qtd": 260.0, "Alvo": 5.0, "Custo": 26000.0},
        {"Ativo": "SCHD", "Qtd": 60.0, "Alvo": 5.0, "Custo": 25000.0},
        {"Ativo": "STAG", "Qtd": 80.0, "Alvo": 5.0, "Custo": 18000.0},
        {"Ativo": "BTC-USD", "Qtd": 0.05, "Alvo": 5.0, "Custo": 15000.0},
        {"Ativo": "SCHV", "Qtd": 40.0, "Alvo": 4.0, "Custo": 14000.0},
        {"Ativo": "DUHP", "Qtd": 30.0, "Alvo": 2.0, "Custo": 6000.0},
        {"Ativo": "JEPQ", "Qtd": 15.0, "Alvo": 2.0, "Custo": 4500.0},
        {"Ativo": "AOK", "Qtd": 10.0, "Alvo": 2.0, "Custo": 2100.0}
    ])

# --- BARRA LATERAL: ADICIONAR COM CUSTO ---
with st.sidebar:
    st.header("⚙️ Gestão de Ativos")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker (Ex: PETR4.SA, BTC-USD)").upper().strip()
        q_in = st.number_input("Quantidade (Unidades)", min_value=0.0, format="%.8f", step=0.000001)
        c_in = st.number_input("Valor Total Investido (R$)", min_value=0.0, step=100.0)
        a_in = st.number_input("Alvo % da Carteira", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Guardar Ativo"):
            if t_in:
                if len(t_in) >= 5 and t_in[-1].isdigit() and ".SA" not in t_in:
                    t_in += ".SA"
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in, "Custo": c_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- CÁLCULOS DE PERFORMANCE ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())
cotacao_dolar = precos_atuais.get('USDBRL=X', 5.20)

# Mapeia preços (CDB é fixo pelo custo)
df_p['Preço Unit.'] = df_p.apply(lambda r: r['Custo'] if r['Ativo'] == "CDB" else precos_atuais.get(r['Ativo'], 0), axis=1)

def calcular_valor_atual(row):
    if row['Ativo'] == "CDB": return row['Custo']
    p = float(row['Preço Unit.'])
    q = float(row['Qtd'])
    return p * q if ".SA" in str(row['Ativo']) else p * q * float(cotacao_dolar)

df_p['Valor Atual (R$)'] = df_p.apply(calcular_valor_atual, axis=1)
patrimonio_total = df_p['Valor Atual (R$)'].sum()

# Métricas de Rentabilidade
df_p['Rentab. R$'] = df_p['Valor Atual (R$)'] - df_p['Custo']
df_p['Rentab. %'] = (df_p['Rentab. R$'] / df_p['Custo'].replace(0, 1)) * 100
df_p['Atual %'] = (df_p['Valor Atual (R$)'] / patrimonio_total) * 100
df_p['Desvio %'] = df_p['Atual %'] - df_p['Alvo']

# --- INTERFACE VISUAL ---
st.metric("Património Total Estimado", f"R$ {patrimonio_total:,.2f}")

tab1, tab2 = st.tabs(["📊 Dashboard de Alocação", "📈 Performance e Rendimento"])

with tab1:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        fig = px.pie(df_p, values='Valor Atual (R$)', names='Ativo', hole=0.5, title="Onde está o seu dinheiro")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.write("### Rebalanceamento")
        st.dataframe(df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].style.format("{:.2f}%"), use_container_width=True)

with tab2:
    st.write("### Análise de Rendimento por Ativo")
    # Tabela com as unidades e rentabilidade solicitadas
    df_renda = df_p[['Ativo', 'Qtd', 'Custo', 'Valor Atual (R$)', 'Rentab. R$', 'Rentab. %']].copy()
    
    def color_rentab(val):
        color = 'green' if val > 0 else 'red'
        return f'color: {color}'

    st.dataframe(
        df_renda.style.applymap(color_rentab, subset=['Rentab. R$', 'Rentab. %'])
        .format({
            'Qtd': '{:.4f}',
            'Custo': 'R$ {:,.2f}',
            'Valor Atual (R$)': 'R$ {:,.2f}',
            'Rentab. R$': 'R$ {:,.2f}',
            'Rentab. %': '{:.2f}%'
        }),
        use_container_width=True
    )
