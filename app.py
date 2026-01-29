import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Configurações de Interface (Otimizado para Desktop)
st.set_page_config(page_title="Wealth Management Command Center", layout="wide")

# 2. Função de Busca de Dados Global
@st.cache_data(ttl=600)
def buscar_mercado(tickers):
    try:
        # Limpa e filtra tickers vazios
        lista = list(set([str(t).strip().upper() for t in tickers if t]))
        if not lista: return pd.Series()
        
        # Adiciona o dólar para conversão automática
        all_tickers = lista + ['USDBRL=X']
        df_raw = yf.download(all_tickers, period="5d", progress=False)
        
        if df_raw.empty: return pd.Series()
        
        # Prioriza 'Adj Close' para precisão (dividendos inclusos)
        precos = df_raw['Adj Close'] if 'Adj Close' in df_raw.columns else df_raw['Close']
        return precos.ffill().iloc[-1]
    except Exception:
        return pd.Series()

# --- TELA PRINCIPAL ---
st.title("🚀 Wealth Management Command Center")
st.markdown("---")

# 3. Gerenciamento de Dados (Inicia vazio como solicitado)
if 'meus_ativos' not in st.session_state:
    st.session_state.meus_ativos = pd.DataFrame(columns=['Ativo', 'Qtd', 'Custo Inicial', 'Alvo %'])

# --- BARRA LATERAL: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📥 Adicionar Novo Ativo")
    st.info("BR: .SA (ex: ITUB3.SA)\nEUA: Ticker (ex: AAPL)\nCripto: -USD (ex: BTC-USD)")
    
    with st.form("cadastro_ativo"):
        ticker = st.text_input("Código do Ativo").upper().strip()
        qtd = st.number_input("Quantidade (Unidades)", min_value=0.0, format="%.8f", step=0.000001)
        custo = st.number_input("Valor Inicial Investido (R$ Total)", min_value=0.0, step=100.0)
        alvo = st.number_input("Alvo desejado (%) na carteira", min_value=0.0, max_value=100.0)
        
        if st.form_submit_button("Adicionar Ativo"):
            if ticker:
                novo_item = pd.DataFrame([{"Ativo": ticker, "Qtd": qtd, "Custo Inicial": custo, "Alvo %": alvo}])
                st.session_state.meus_ativos = pd.concat([st.session_state.meus_ativos, novo_item], ignore_index=True)
                st.rerun()
    
    if st.button("🗑️ Limpar Carteira"):
        st.session_state.meus_ativos = pd.DataFrame(columns=['Ativo', 'Qtd', 'Custo Inicial', 'Alvo %'])
        st.rerun()

# --- PROCESSAMENTO E EXIBIÇÃO ---
df = st.session_state.meus_ativos.copy()

if not df.empty:
    precos_vivos = buscar_mercado(df['Ativo'].tolist())
    dolar = precos_vivos.get('USDBRL=X', 5.00) # Valor de segurança

    # Mapeamento de preços e cálculos
    df['Preço Mercado'] = df['Ativo'].map(precos_vivos)
    
    def calc_valor_atual(row):
        p = float(row['Preço Mercado']) if pd.notnull(row['Preço Mercado']) else 0
        q = float(row['Qtd'])
        # Conversão BRL/USD
        return p * q if ".SA" in str(row['Ativo']) else p * q * float(dolar)

    df['Valor Atual (R$)'] = df.apply(calc_valor_atual, axis=1)
    
    # Métricas de Performance
    patrimonio_total = df['Valor Atual (R$)'].sum()
    investimento_total = df['Custo Inicial'].sum()
    lucro_total = patrimonio_total - investimento_total
    
    # KPIs no topo
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Patrimônio Atual", f"R$ {patrimonio_total:,.2f}")
    kpi2.metric("Investimento Total", f"R$ {investimento_total:,.2f}")
    kpi3.metric("Lucro/Prejuízo Total", f"R$ {lucro_total:,.2f}", f"{(lucro_total/investimento_total*100):.2f}%" if investimento_total > 0 else "0%")

    st.markdown("---")

    # Abas de visualização
    aba_graf, aba_perf = st.tabs(["📊 Distribuição", "📈 Performance Detalhada"])

    with aba_graf:
        col_pie, col_reb = st.columns([1, 1.2])
        with col_pie:
            fig = px.pie(df, values='Valor Atual (R$)', names='Ativo', hole=0.5, title="Alocação por Ativo")
            st.plotly_chart(fig, use_container_width=True)
        with col_reb:
            df['Atual %'] = (df['Valor Atual (R$)'] / patrimonio_total) * 100
            df['Desvio %'] = df['Atual %'] - df['Alvo %']
            st.write("### Sugestão de Rebalanceamento")
            st.dataframe(df[['Ativo', 'Atual %', 'Alvo %', 'Desvio %']].style.format("{:.2f}%"))

    with aba_perf:
        st.write("### Análise de Rendimento Individual")
        df['Rend. R$'] = df['Valor Atual (R$)'] - df['Custo Inicial']
        df['Rend. %'] = (df['Rend. R$'] / df['Custo Inicial'].replace(0, 1)) * 100
        
        # Tabela completa
        df_show = df[['Ativo', 'Qtd', 'Custo Inicial', 'Valor Atual (R$)', 'Rend. R$', 'Rend. %']]
        st.dataframe(df_show.style.format({
            'Qtd': '{:.6f}',
            'Custo Inicial': 'R$ {:,.2f}',
            'Valor Atual (R$)': 'R$ {:,.2f}',
            'Rend. R$': 'R$ {:,.2f}',
            'Rend. %': '{:.2f}%'
        }), use_container_width=True)

else:
    st.info("Sua carteira está vazia. Adicione seu primeiro ativo na barra lateral esquerda!")
