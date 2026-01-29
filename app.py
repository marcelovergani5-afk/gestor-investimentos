import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface
st.set_page_config(page_title="Strategic Wealth Command Center", layout="wide")

# 2. Função de Busca com Proteção contra Erros de Ticker
@st.cache_data(ttl=600)
def get_data(tickers):
    try:
        # Garante que todos os tickers são strings limpas
        tickers_limpos = [str(t).strip().upper() for t in tickers if t]
        all_tickers = list(set(tickers_limpos + ['USDBRL=X']))
        
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty:
            return pd.Series()

        # Seleção de preço (Ajustado ou Fechamento)
        df_precos = df_raw['Adj Close'] if 'Adj Close' in df_raw.columns else df_raw['Close']
            
        if isinstance(df_precos, pd.Series):
            return pd.Series({tickers_limpos[0]: df_precos.ffill().iloc[-1]})

        return df_precos.ffill().iloc[-1]
    except:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Strategic Wealth Command Center")

# 3. Inicialização da Carteira (Dados Reais do Usuário)
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

# --- BARRA LATERAL COM AJUDA ---
with st.sidebar:
    st.header("⚙️ Gerenciar Carteira")
    st.info("Dica: Use .SA para ações brasileiras (Ex: PETR4.SA)")
    with st.form("novo_ativo"):
        t_in = st.text_input("Ticker").upper().strip()
        q_in = st.number_input("Quantidade", min_value=0.0, format="%.2f")
        a_in = st.number_input("Alvo %", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Adicionar Ativo"):
            if t_in:
                # Tenta corrigir se for ação BR e faltar o .SA
                if len(t_in) >= 5 and t_in[-1].isdigit() and ".SA" not in t_in:
                    t_in += ".SA"
                
                nova_linha = pd.DataFrame([{"Ativo": t_in, "Qtd": q_in, "Alvo": a_in}])
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, nova_linha], ignore_index=True)
                st.rerun()

# --- CÁLCULOS SEGUROS ---
df_p = st.session_state.portfolio.copy()
precos_atuais = get_data(df_p['Ativo'].tolist())

# Busca cotação do dólar com segurança
cotacao_dolar = precos_atuais.get('USDBRL=X', 5.20)

if not precos_atuais.empty:
    # Mapeia preços e remove os que deram erro (NaN)
    df_p['Preço Unit.'] = df_p['Ativo'].map(precos_atuais)
    df_p = df_p.dropna(subset=['Preço Unit.'])

    # Função de conversão blindada
    def converter_brl(row):
        try:
            p = float(row['Preço Unit.'])
            q = float(row['Qtd'])
            if ".SA" in str(row['Ativo']):
                return p * q
            return p * q * float(cotacao_dolar)
        except:
            return 0.0

    df_p['Total R$'] = df_p.apply(converter_brl, axis=1)
    patrimonio_total = df_p['Total R$'].sum()
    
    if patrimonio_total > 0:
        df_p['Atual %'] = (df_p['Total R$'] / patrimonio_total) * 100
        df_p['Desvio %'] = df_p['Atual %'] - df_p['Alvo']

        # Gráficos e Tabelas (Sempre forçando números)
        c1, c2 = st.columns([1, 1])
        with c1:
            st.metric("Patrimônio Consolidado", f"R$ {patrimonio_total:,.2f}")
            fig = px.pie(df_p, values='Total R$', names='Ativo', hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.write("### ⚖️ Estratégia")
            df_final = df_p[['Ativo', 'Atual %', 'Alvo', 'Desvio %']].copy()
            st.dataframe(df_final.style.format("{:.2f}%"), use_container_width=True)
    else:
        st.warning("Adicione ativos com quantidades válidas.")
else:
    st.error("Erro de conexão com o mercado. Tente atualizar a página.")
