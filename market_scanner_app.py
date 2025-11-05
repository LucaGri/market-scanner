import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Configurazione pagina
st.set_page_config(
    page_title="Market Scanner - Spring Detector",
    page_icon="📈",
    layout="wide"
)

# Import yfinance solo quando necessario (lazy loading)
@st.cache_resource
def load_yfinance():
    """Carica yfinance solo quando serve"""
    import yfinance as yf
    return yf

# Titolo e descrizione
st.title("🔍 Market Scanner - Spring Detector")
st.markdown("**Sistema di screening per identificare titoli in compressione prima del movimento**")

# Sidebar con configurazioni
st.sidebar.header("⚙️ Configurazioni")

# Lista ticker predefiniti
FTSE_MIB = ['UCG.MI', 'ISP.MI', 'ENI.MI', 'ENEL.MI', 'TIT.MI', 'STM.MI', 'G.MI', 
            'RACE.MI', 'ATL.MI', 'STLAM.MI', 'BAMI.MI', 'CPR.MI', 'MB.MI', 
            'TEN.MI', 'CNHI.MI', 'AZM.MI', 'BMED.MI', 'SPM.MI', 'BGN.MI', 
            'MONC.MI', 'SRG.MI', 'PST.MI', 'PRY.MI', 'REC.MI', 'AMP.MI',
            'DIA.MI', 'FBK.MI', 'HER.MI', 'IP.MI', 'LDO.MI',
            'NEX.MI', 'IG.MI', 'TEL.MI', 'TRN.MI', 'UNI.MI', 'US.MI']

DAX_STOCKS = ['SIE.DE', 'SAP.DE', 'ALV.DE', 'DTE.DE', 'VOW3.DE', 'BAS.DE',
              'BMW.DE', 'ADS.DE', 'MUV2.DE', 'BAYN.DE', 'DAI.DE', 'DB1.DE',
              'DBK.DE', 'HEN3.DE', 'IFX.DE', 'MRK.DE', 'RWE.DE', 'HEI.DE',
              'VNA.DE', 'SHL.DE', 'BEI.DE', 'CON.DE', 'FRE.DE', 'PAH3.DE',
              'ZAL.DE', 'DHER.DE', 'EOAN.DE', '1COV.DE', 'PUM.DE', 'QIA.DE']

SP500_LARGE_CAPS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 
                    'BRK-B', 'V', 'UNH', 'JNJ', 'WMT', 'XOM', 'JPM', 'MA',
                    'PG', 'AVGO', 'HD', 'CVX', 'MRK', 'ABBV', 'KO', 'PEP',
                    'COST', 'BAC', 'ADBE', 'CRM', 'MCD', 'CSCO', 'ACN',
                    'TMO', 'LIN', 'NFLX', 'NKE', 'DIS', 'ABT', 'WFC', 'AMD',
                    'CMCSA', 'VZ', 'DHR', 'INTC', 'TXN', 'PM', 'NEE', 'RTX',
                    'UNP', 'UPS', 'AMGN', 'HON', 'QCOM', 'LOW', 'BMY', 'T',
                    'SPGI', 'SBUX', 'BA', 'IBM', 'GE', 'CAT', 'INTU', 'DE',
                    'AMAT', 'BKNG', 'MDT', 'BLK', 'ADP', 'CI', 'GILD', 'MMC',
                    'PLD', 'MDLZ', 'TJX', 'SYK', 'ADI', 'CVS', 'REGN', 'CB']

# Selezione mercati
markets = st.sidebar.multiselect(
    "Seleziona Mercati",
    ["FTSE MIB", "DAX", "S&P 500 Large Caps"],
    default=["FTSE MIB"]
)

# Costruzione lista ticker
tickers = []
if "FTSE MIB" in markets:
    tickers.extend(FTSE_MIB)
if "DAX" in markets:
    tickers.extend(DAX_STOCKS)
if "S&P 500 Large Caps" in markets:
    tickers.extend(SP500_LARGE_CAPS)

st.sidebar.info(f"📊 Totale titoli da analizzare: **{len(tickers)}**")

# Parametri di screening
st.sidebar.subheader("🎯 Soglie di Screening")
min_score = st.sidebar.slider("Score minimo", 0, 100, 60, 5)
max_results = st.sidebar.slider("Numero massimo risultati", 10, 100, 50, 10)

# Funzione per scaricare dati con timeout e retry
def download_stock_data(ticker, yf, period="60d", max_retries=2):
    """Scarica dati storici per un ticker con gestione errori"""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, timeout=10)
            if df.empty:
                return None
            return df
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(0.5)
    return None

# Funzione per calcolare ATR
def calculate_atr(df, period=14):
    """Calcola Average True Range"""
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    except:
        return pd.Series([0] * len(df))

# Funzione per calcolare lo score
def calculate_compression_score(df):
    """Calcola il punteggio di compressione per un titolo"""
    if df is None or len(df) < 60:
        return None
    
    try:
        score = 0
        metrics = {}
        
        # Ultimo prezzo
        current_price = df['Close'].iloc[-1]
        metrics['price'] = current_price
        
        # 1. VOLATILITÀ COMPRESSA (30 punti)
        atr_14 = calculate_atr(df, 14).iloc[-1]
        atr_60_mean = calculate_atr(df, 14).iloc[-60:].mean()
        
        if atr_60_mean > 0:
            atr_ratio = atr_14 / atr_60_mean
            metrics['atr_ratio'] = atr_ratio
            
            if atr_ratio < 0.7:
                score += 30
            elif atr_ratio < 0.85:
                score += 20
            elif atr_ratio < 1.0:
                score += 10
        else:
            metrics['atr_ratio'] = 0
        
        # 2. RANGE STRETTO (25 punti)
        last_10_days = df.iloc[-10:]
        range_pct = ((last_10_days['High'].max() - last_10_days['Low'].min()) / 
                     last_10_days['Close'].mean() * 100)
        metrics['range_10d'] = range_pct
        
        if range_pct < 5:
            score += 25
        elif range_pct < 8:
            score += 15
        elif range_pct < 12:
            score += 5
        
        # 3. VOLUME IN CALO (20 punti)
        vol_last_5 = df['Volume'].iloc[-5:].mean()
        vol_20 = df['Volume'].iloc[-20:].mean()
        
        if vol_20 > 0:
            vol_ratio = vol_last_5 / vol_20
            metrics['volume_ratio'] = vol_ratio
            
            if vol_ratio < 0.8:
                score += 20
            elif vol_ratio < 0.9:
                score += 12
            elif vol_ratio < 1.0:
                score += 5
        else:
            metrics['volume_ratio'] = 0
        
        # 4. PROSSIMITÀ A MA50 (15 punti)
        ma_50 = df['Close'].iloc[-50:].mean()
        distance_from_ma = abs(current_price - ma_50) / ma_50 * 100
        metrics['distance_ma50'] = distance_from_ma
        
        if distance_from_ma < 3:
            score += 15
        elif distance_from_ma < 5:
            score += 10
        elif distance_from_ma < 8:
            score += 5
        
        # 5. CONSOLIDAMENTO (10 punti)
        last_20_high = df['High'].iloc[-20:].max()
        last_20_low = df['Low'].iloc[-20:].min()
        consolidation_range = (last_20_high - last_20_low) / current_price * 100
        metrics['consolidation_range'] = consolidation_range
        
        if consolidation_range < 8:
            score += 10
        elif consolidation_range < 12:
            score += 5
        
        metrics['score'] = score
        
        # Aggiungi variazione giornaliera
        metrics['daily_change'] = ((current_price - df['Close'].iloc[-2]) / 
                                    df['Close'].iloc[-2] * 100)
        
        # Aggiungi volume corrente vs media
        current_volume = df['Volume'].iloc[-1]
        avg_volume_20 = df['Volume'].iloc[-20:].mean()
        metrics['volume_vs_avg'] = (current_volume / avg_volume_20 
                                     if avg_volume_20 > 0 else 0)
        
        return metrics
    except Exception as e:
        return None

# Bottone per avviare lo scan
if st.button("🚀 Avvia Scan", type="primary", use_container_width=True):
    
    if len(tickers) == 0:
        st.warning("⚠️ Seleziona almeno un mercato dalla sidebar!")
    else:
        # Carica yfinance solo quando serve
        with st.spinner("🔄 Inizializzazione sistema..."):
            yf = load_yfinance()
        
        st.markdown("---")
        st.subheader("📊 Scanning in corso...")
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        errors = []
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"Analizzando {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            # Scarica dati
            df = download_stock_data(ticker, yf)
            
            if df is not None:
                # Calcola score
                metrics = calculate_compression_score(df)
                
                if metrics and metrics['score'] >= min_score:
                    results.append({
                        'Ticker': ticker,
                        'Score': metrics['score'],
                        'Prezzo': round(metrics['price'], 2),
                        'Var %': round(metrics['daily_change'], 2),
                        'ATR Ratio': round(metrics.get('atr_ratio', 0), 2),
                        'Range 10g %': round(metrics['range_10d'], 2),
                        'Vol Ratio': round(metrics.get('volume_ratio', 0), 2),
                        'Dist MA50 %': round(metrics['distance_ma50'], 2),
                        'Vol vs Avg': round(metrics['volume_vs_avg'], 2)
                    })
            else:
                errors.append(ticker)
            
            # Pausa per rate limiting
            if (i + 1) % 10 == 0:
                time.sleep(0.5)
            else:
                time.sleep(0.1)
        
        progress_bar.empty()
        status_text.empty()
        
        # Mostra risultati
        if results:
            df_results = pd.DataFrame(results)
            df_results = df_results.sort_values('Score', ascending=False).head(max_results)
            
            st.success(f"✅ Trovati **{len(df_results)}** titoli in compressione!")
            
            # Metriche principali
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Titoli analizzati", total - len(errors))
            with col2:
                st.metric("Score medio", f"{df_results['Score'].mean():.1f}")
            with col3:
                st.metric("Score massimo", f"{df_results['Score'].max():.0f}")
            with col4:
                st.metric("Errori", len(errors))
            
            st.markdown("---")
            
            # Tabella risultati con formattazione
            st.dataframe(
                df_results.style.background_gradient(subset=['Score'], cmap='RdYlGn')
                                .format({
                                    'Prezzo': '{:.2f}',
                                    'Var %': '{:+.2f}%',
                                    'ATR Ratio': '{:.2f}',
                                    'Range 10g %': '{:.2f}%',
                                    'Vol Ratio': '{:.2f}',
                                    'Dist MA50 %': '{:.2f}%',
                                    'Vol vs Avg': '{:.2f}x'
                                }),
                use_container_width=True,
                height=600
            )
            
            # Download CSV
            st.markdown("---")
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f'market_scan_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                mime='text/csv',
                use_container_width=True
            )
            
            # Mostra errori se presenti
            if errors and len(errors) < 10:
                with st.expander(f"⚠️ Titoli non analizzati ({len(errors)})"):
                    st.write(", ".join(errors))
            
            # Interpretazione score
            st.markdown("---")
            st.subheader("📖 Legenda Score")
            st.markdown("""
            **Componenti del punteggio (max 100):**
            - 🔵 **Volatilità Compressa** (30 pt): ATR corrente vs ATR storico
            - 🟢 **Range Stretto** (25 pt): Movimento % ultimi 10 giorni
            - 🟡 **Volume in Calo** (20 pt): Volume recente vs media
            - 🟣 **Prossimità MA50** (15 pt): Distanza dalla media mobile 50 giorni
            - 🟠 **Consolidamento** (10 pt): Range di consolidamento 20 giorni
            
            **Score ≥ 80:** 🔥 Molla fortemente compressa - Alta priorità  
            **Score 60-79:** ⚠️ Compressione moderata - Monitorare  
            **Score < 60:** ℹ️ Compressione debole - Bassa priorità
            """)
            
        else:
            st.warning("⚠️ Nessun titolo trovato con score superiore alla soglia impostata.")
            st.info("💡 Prova ad abbassare il 'Score minimo' nella sidebar o seleziona più mercati.")
            
            if errors:
                st.error(f"⚠️ {len(errors)} titoli non sono stati analizzati per problemi di connessione.")

else:
    # Messaggio iniziale
    st.info("👆 Clicca su **'Avvia Scan'** per iniziare l'analisi dei mercati")
    
    st.markdown("---")
    st.subheader("🎯 Come funziona")
    st.markdown("""
    Questo scanner identifica titoli in **fase di compressione** ("molle cariche") 
    che potrebbero esplodere nei prossimi giorni.
    
    **Il sistema analizza:**
    1. Compressione della volatilità (ATR)
    2. Range di prezzo ristretto
    3. Volume in diminuzione (accumulazione silenziosa)
    4. Prossimità a livelli tecnici chiave
    5. Pattern di consolidamento
    
    **Output:** Una watchlist di 30-60 titoli pronti per il prossimo movimento.
    
    **Passo successivo:** Condividi la lista con Claude per analisi catalyst e setup operativi.
    
    **💡 Suggerimento:** Per la prima volta, inizia selezionando solo FTSE MIB (37 titoli) 
    per un test rapido. Poi espandi agli altri mercati.
    """)

# Footer
st.markdown("---")
st.caption("💡 Creato per individuare opportunità PRIMA del movimento | Aggiornamento dati: ultimi 60 giorni")
st.caption("⚡ Versione ottimizzata con lazy loading e gestione errori avanzata")
