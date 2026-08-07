import streamlit as st
import requests
import base64

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Pro Trading Analyst (SMC & Price Action)",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS Dark Mode Professional
st.markdown("""
    <style>
    .stApp { background-color: #0e0e10; color: #ffffff; }
    div[data-baseweb="tab-list"] { background-color: #16161a; border-radius: 8px; padding: 5px; }
    div[data-baseweb="tab"] { color: #888888; }
    div[aria-selected="true"] { color: #f3ba2f !important; font-weight: bold; }
    .stButton>button { background-color: #f3ba2f; color: #000000; font-weight: bold; font-size: 16px; border-radius: 8px; width: 100%; border: none; padding: 12px; }
    .stButton>button:hover { background-color: #d9a320; color: #000000; }
    .card-signal { background-color: #16161a; border: 1px solid #2a2a30; border-radius: 10px; padding: 20px; margin-top: 15px; }
    .metric-card { background-color: #1f222d; padding: 10px; border-radius: 6px; border-left: 4px solid #f3ba2f; margin-bottom: 10px; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. MESIN KALKULASI INDIKATOR RIIL (PYTHON)
# ==========================================
def calc_ema(prices, period):
    if not prices or len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p * k) + (ema * (1 - k))
    return ema

def calc_rsi(prices, period=14):
    if not prices or len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(abs(diff))
            losses.append(abs(diff))
            
    if len(gains) < period:
        return None
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def fetch_market_data(pair, timeframe="M15"):
    s = pair.upper().replace("/", "").replace(" ", "").strip()
    
    # A. Crypto via Binance API
    if "USDT" in s or s in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"]:
        clean_s = s if "USDT" in s else f"{s}USDT"
        tf_map = {"M1":"1m","M5":"5m","M15":"15m","M30":"30m","H1":"1h","H4":"4h","D1":"1d"}
        tf = tf_map.get(timeframe, "15m")
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_s}&interval={tf}&limit=100"
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                data = r.json()
                closes = [float(item[4]) for item in data]
                highs = [float(item[2]) for item in data]
                lows = [float(item[3]) for item in data]
                return closes, highs, lows
        except Exception:
            pass

    # B. Forex & Gold via Yahoo Finance API
    yf_map = {"XAUUSD": "GC=F", "GOLD": "GC=F", "XAGUSD": "SI=F"}
    yf_ticker = yf_map.get(s)
    if not yf_ticker and len(s) == 6:
        yf_ticker = f"{s}=X"
        
    if yf_ticker:
        tf_yf_map = {"M1":"1m","M5":"5m","M15":"15m","M30":"30m","H1":"1h","H4":"1h","D1":"1d"}
        tf_yf = tf_yf_map.get(timeframe, "15m")
        range_yf = "5d" if tf_yf in ["1m","5m","15m","30m"] else "1mo"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}?interval={tf_yf}&range={range_yf}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, headers=headers, timeout=4)
            if r.status_code == 200:
                result = r.json()['chart']['result'][0]
                quote = result['indicators']['quote'][0]
                closes = [c for c in quote['close'] if c is not None]
                highs = [h for h in quote['high'] if h is not None]
                lows = [l for l in quote['low'] if l is not None]
                return closes, highs, lows
        except Exception:
            pass
            
    return None, None, None

# ==========================================
# 2. MESIN AI PEMANGGIL GOOGLE GEMINI DENGAN DETEKSI
# ==========================================
def get_available_gemini_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            valid_models = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    valid_models.append(m.get("name"))
            if valid_models:
                return valid_models
    except Exception:
        pass
    return ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]

def call_gemini_api(api_key, prompt, image_bytes=None, mime_type="image/jpeg"):
    if not api_key or len(api_key.strip()) < 10:
        raise ValueError("API Key Gemini belum diisi atau salah! Masukkan API Key gratis Anda pada menu Sidebar sebelah kiri.")
    
    clean_key = api_key.strip()
    if mime_type == "image/jpg": mime_type = "image/jpeg"
        
    models = get_available_gemini_models(clean_key)
    models.sort(key=lambda x: 0 if 'flash' in x else 1)
    
    parts = [{"text": prompt}]
    if image_bytes:
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        parts.append({"inline_data": {"mime_type": mime_type, "data": base64_img}})
    
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json"}
    
    last_err = ""
    for model_path in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={clean_key}"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    continue
            else:
                try:
                    err_json = res.json()
                    last_err = err_json.get("error", {}).get("message", res.text)
                except Exception:
                    last_err = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_err = str(e)
            continue
            
    raise Exception(f"Gagal memanggil AI: {last_err}")

# ==========================================
# 3. TAMPILAN APLIKASI STREAMLIT
# ==========================================
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
st.sidebar.caption("Dapatkan API Key gratis di: [Google AI Studio](https://aistudio.google.com/)")

st.title("⚡ AI Pro Trading Analyst")
st.caption("Sistem analisis otomatis berbasis Smart Money Concepts (SMC), Price Action & Indikator Riil.")

tab1, tab2, tab3 = st.tabs(["01. Buat Signal Pro", "02. Signal Hari Ini", "03. Analisa Chart"])

# TAB 1: BUAT SIGNAL PRO
with tab1:
    st.subheader("01. MARKET & PAIR")
    col1, col2 = st.columns(2)
    with col1:
        market = st.radio("Pilih Market:", ["Crypto", "Forex", "Emas"], label_visibility="collapsed")
    with col2:
        if market == "Crypto":
            options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "Tulis Sendiri..."]
        elif market == "Forex":
            options = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY", "Tulis Sendiri..."]
        else:
            options = ["XAUUSD", "XAGUSD", "Tulis Sendiri..."]
        pair_select = st.selectbox("Pilih Pair:", options, label_visibility="collapsed")
        pair = st.text_input("Pair Kustom:").upper() if pair_select == "Tulis Sendiri..." else pair_select

    st.subheader("02. TIMEFRAME & GAYA TRADING")
    tf = st.select_slider("Timeframe Analisis:", options=["M5", "M15", "M30", "H1", "H4", "D1"], value="M15")
    gaya = st.radio("Gaya Trading:", ["Scalping (Presisi M5/M15)", "Day Trade (Multi-Timeframe M15/H1)", "Swing (Struktur H4/D1)"], horizontal=True)

    if st.button("Buat Signal Pro", key="btn_signal"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key di menu Sidebar terlebih dahulu!")
        elif not pair:
            st.warning("⚠️ Pilih atau masukkan nama pair terlebih dahulu.")
        else:
            try:
                with st.spinner(f"📊 Menghitung 100 Candle {pair} & Indikator Riil..."):
                    closes, highs, lows = fetch_market_data(pair, timeframe=tf)
                    
                    if closes and len(closes) >= 50:
                        cur_p = closes[-1]
                        rsi_val = calc_rsi(closes, 14)
                        ema20 = calc_ema(closes, 20)
                        ema50 = calc_ema(closes, 50)
                        ema200 = calc_ema(closes, 200)
                        high_50 = max(highs[-50:])
                        low_50 = min(lows[-50:])
                        
                        st.markdown(f"""
                        <div class='metric-card'>
                        📈 <b>DATA PASAR RIIL TERHITUNG ({tf}):</b><br>
                        • Harga Running: <b>{cur_p:,.4f}</b> | RSI(14): <b>{rsi_val:.1f}</b><br>
                        • EMA 20: <b>{ema20:,.4f}</b> | EMA 50: <b>{ema50:,.4f}</b> | EMA 200: <b>{ema200 if ema200 else 0:,.4f}</b><br>
                        • High 50-Candle: <b>{high_50:,.4f}</b> | Low 50-Candle: <b>{low_50:,.4f}</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        price_context = f"""
                        HASIL KALKULASI DATA TEKNIKAL PASAR RIIL:
                        - Pair: {pair} (Timeframe {tf})
                        - Harga Running Terkini: {cur_p}
                        - RSI (14): {rsi_val:.2f} (Overbought > 70, Oversold < 30)
                        - EMA 20: {ema20} (Posisi harga: {'Di Atas EMA 20' if cur_p > ema20 else 'Di Bawah EMA 20'})
                        - EMA 50: {ema50} (Posisi harga: {'Di Atas EMA 50' if cur_p > ema50 else 'Di Bawah EMA 50'})
                        - EMA 200: {ema200 if ema200 else 'Membutuhkan data lebih banyak'}
                        - Resisten / Liquidity High (50 Candle): {high_50}
                        - Support / Liquidity Low (50 Candle): {low_50}
                        """
                    else:
                        price_context = f"Pasar: {pair}, Timeframe: {tf}. Gunakan acuan harga running real-time pasar saat ini."

                    prompt = f"""
                    Bertindaklah sebagai Senior Institutional Quantitative & Smart Money Concepts (SMC) Trader.
                    
                    {price_context}
                    
                    Gaya Trading: {gaya}.
                    
                    Lakukan analisis mendalam ala Trader Profesional dengan struktur jawaban sebagai berikut:
                    
                    1. 🏛️ STRUKTUR PASAR & PRICE ACTION (SMC):
                       - Analisis Tren Utama (Bullish / Bearish / Ranging).
                       - Evaluasi penembusan struktur (BOS / CHoCH) dan area Liquidity Sweep (High/Low 50 candle).
                       - Deteksi potensi zona Order Block (OB), Supply/Demand, atau Fair Value Gap (FVG) terdekat.
                    
                    2. 📊 KONFIRMASI INDIKATOR TEKNIKAL:
                       - Analisis RSI (14): Apakah terjadi Momentum, Overbought/Oversold, atau potensi Divergence?
                       - Analisis Keselarasan EMA (EMA 20, 50, 200 Alignment): Apakah tren didukung oleh indikator pergerakan rata-rata?
                    
                    3. 🎯 KEPUTUSAN TRADING:
                       - REKOMENDASI POSISI: [BUY / SELL / WAIT]
                       - TINGKAT KEYAKINAN SET-UP: [%]
                    
                    4. 📋 RENCANA EKSEKUSI (SET-UP):
                       - ENTRY ZONE: [Harga Entry Presisi]
                       - STOP LOSS (SL): [Level SL Presisi di luar zona invalidasi]
                       - TAKE PROFIT 1 (TP1): [Target Conservatif / RR 1:1.5]
                       - TAKE PROFIT 2 (TP2): [Target Optimal / RR 1:2.5]
                       - TAKE PROFIT 3 (TP3): [Target Maksimal / Liquidity Zone]
                       - RISK TO REWARD RATIO: [Minimal 1:2]
                    
                    5. 💡 ALASAN LENGKAP ("KENAPA BUY / KENAPA SELL"):
                       - Alasan Struktur & Price Action: [Jelaskan secara logis]
                       - Alasan Konfirmasi Indikator: [Jelaskan kesesuaian RSI & EMA]
                       - Alasan Penempatan Stop Loss: [Jelaskan pertimbangan titik SL]
                       - Syarat Invalidasi Sinyal: [Kondisi harga yang membatalkan sinyal ini]
                    """
                    
                    result_text = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    st.subheader("📊 Signal Harian Terpopuler")
    if st.button("Tampilkan Signal Harian AI", key="btn_daily"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        else:
            try:
                with st.spinner("Memuat rekap signal harian..."):
                    prompt = """
                    Berikan 2 signal harian terbaik hari ini untuk XAUUSD dan BTCUSDT menggunakan prinsip Smart Money Concepts (SMC) dan Indikator Teknikal.
                    Sertakan Direction, Entry, Stop Loss, Take Profit, dan Alasan Analisis Lengkap (Kenapa BUY / Kenapa SELL).
                    """
                    result_text = call_gemini_api(api_key, prompt)
                    st.markdown(result_text)
            except Exception as e:
                st.error(f"{e}")

# TAB 3: ANALISA CHART (VISION API)
with tab3:
    st.subheader("01. UPLOAD SCREENSHOT CHART")
    uploaded_file = st.file_uploader("Unggah screenshot chart MT5 / TradingView:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Chart diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN & TIMEFRAME")
    chart_pair = st.text_input("Tulis pair pada chart:", "XAUUSD")
    chart_tf = st.selectbox("Timeframe Chart:", ["M5", "M15", "M30", "H1", "H4", "D1"], index=1)

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key di menu Sidebar terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Unggah foto/screenshot chart Anda terlebih dahulu.")
        else:
            try:
                with st.spinner("🤖 AI Vision sedang membaca struktur Price Action & Indikator pada chart..."):
                    img_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    prompt = f"""
                    Analisis gambar screenshot chart {chart_pair} timeframe {chart_tf} ini layaknya Senior Price Action Analyst.

                    LAKUKAN PENELITIAN VISUAL BERIKUT:
                    1. Identifikasi Tren Utama, Pola Candlestick, dan Pola Chart (misal: Head & Shoulders, Double Top/Bottom, Flag Pattern, dll).
                    2. Tentukan Level Support & Resistance Kunci serta area Order Block / FVG yang terlihat di gambar.
                    3. Perhatikan indikator yang ada pada screenshot (seperti EMA/MA, RSI, MACD jika ada).
                    4. Berikan Keputusan (BUY / SELL / WAIT) lengkap dengan Entry, SL, dan TP presisi berdasarkan skala harga di chart ini.
                    5. Berikan penjelasan transparan KENAPA merekomendasikan BUY / SELL tersebut.
                    """
                    result_text = call_gemini_api(api_key, prompt, image_bytes=img_bytes, mime_type=mime_type)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{e}")
