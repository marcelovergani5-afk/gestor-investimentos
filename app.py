import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configuração de Interface
st.set_page_config(page_title="Strategic Wealth Command Center", layout="wide")

# 2. Função de Busca de Dados Resiliente
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        tickers_limpos = list(set([str(t).strip().upper() for t in tickers if t]))
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

# 3. Inicialização da Carteira (Mantendo seus dados atuais)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame([
        {"Ativo": "ITUB3.SA", "Qtd": 920.0, "Alvo": 15.0},
        {"Ativo": "GOAU4.SA", "Qtd": 800.0, "Alvo": 15.0},
        {"Ativo": "IAUM", "Qtd": 260.0, "Alvo": 15.0},
        {"Ativo": "SCHD", "Qtd": 60.0, "Alvo": 15.0},
        {"Ativo": "STAG", "Qtd": 80.0, "Alvo": 10.0},
        {"Ativo": "SCHV", "Qtd": 40.0, "Alvo": 10.0},
        {"Ativo": "DUHP", "Qtd": 30.0, "Alvo": 5.0},
        {"Ativo": "JEPQ", "Qtd": 15.0, "Alvo": 5.0},
        {"Ativo": "AOK", "Qtd": 10.0, "Alvo": 5.0},
        {"Ativo": "O", "Qtd": 10.0, "Alvo": 5.0}
    ])

# --- BARRA LATERAL (AJUSTADA PARA ALTA PRECISÃO) ---
with st.sidebar:
    st.header("⚙️ Gerenciar Carteira")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker (Ex: BTC-USD)").upper().strip()
        # MUDANÇA CRÍTICA: format="%.8f" permite 8 casas decimais e step menor permite precisão
        q_in = st.number_input("Quantidade", min_value=0.0, format="%.8f", step=0.00000001)
        a_in = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Adicionar Ativo"):
            if t_in:
                if len(t_in) >= 5 and t_in[-1].isdigit() and ".SA" not in t_in:
                    t_in += ".SA"
                
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- CÁLCULOS ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())
cotacao_dolar = precos_atuais.get('USDBRL=X', 5.20)

if not precos_atuais.empty:
    df_p['Preço Unit.'] = df_p['Ativo'].map(precos_atuais)
    df_p = df_p.dropna(subset=['Preço Unit.'])

    # Cálculo usando float64 para manter a precisão máxima
    def converter_brl(row):
        p = float(row['Preço Unit.'])
        q = float(row['Qtd']) # Aqui a precisão do BTC é mantida
        return p * q if ".SA" in str(row['Ativo']) else p * q * float(cotacao_dolar)

    df_p['Total R$'] = df_p.apply(converter_brl, axis=1)
    patrimonio_total = df_p['Total R$'].sum()
    
    if patrimonio_total > 0:
        df_p['Atual %'] = (df_p['Total R$'] / patrimonio_total) * 100
        df_p['Desvio %'] = df_p['Atual %'] - df_p['Alvo']

        # --- EXIBIÇÃO ---
        c1, c2, c3 = st.columns(3)
        # Exibindo seu patrimônio total que já ultrapassou os R$ 217 mil!
        c1.metric("Patrimônio Bolsa", f"R$ {patrimonio_total:,.2f}")
        c2.metric("Dólar", f"R$ {cotacao_dolar:.2f}")
        c3.metric("Ativos", len(df_p))

        col_graf, col_tab = st.columns([1, 1.2])
        
        with col_graf:
            fig = px.pie(df_p, values='Total R$', names='Ativo', hole=0.5, title="Alocação Atual")
            st.plotly_chart(fig, use_container_width=True)
        
        with col_tab:
            st.write("### ⚖️ Estratégia de Rebalanceamento")
            df_final = df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].fillna(0)
            
            def cor_status(val):
                if val < -2.0: return 'background-color: #004d00; color: white'
                if val > 2.0: return 'background-color: #4d0000; color: white'
                return ''

            st.dataframe(
                df_final.style.applymap(cor_status, subset=['Desvio %'])
                .format("{:.2f}%", subset=['Atual %', 'Alvo', 'Desvio %']),
                use_container_width=True
            )
else:
    st.warning("Carregando cotações...")
