import streamlit as st
import requests
import base64
from datetime import datetime

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Ultra Pro Trading Analyst + Fundamental News",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS TradingView / Pro Dark Theme
st.markdown("""
    <style>
    .stApp { background-color: #131722; color: #d1d4dc; font-family: 'Trebuchet MS', sans-serif; }
    div[data-baseweb="tab-list"] { background-color: #1e222d; border-radius: 6px; padding: 4px; }
    div[data-baseweb="tab"] { color: #787b86; font-size: 14px; font-weight: 600; }
    div[aria-selected="true"] { background-color: #2962ff !important; color: #ffffff !important; border-radius: 4px; }
    .stButton>button { background: linear-gradient(90deg, #2962ff 0%, #1e53e5 100%); color: #ffffff; border-radius: 6px; border: none; font-weight: bold; padding: 12px; box-shadow: 0 4px 12px rgba(41,98,255,0.3); }
    .stButton>button:hover { background: #1e53e5; transform: translateY(-1px); }
    .card-signal { background-color: #1e222d; border: 1px solid #2a2e39; border-radius: 8px; padding: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); margin-top: 15px; }
    .metric-card { background-color: #1e222d; padding: 12px; border-radius: 6px; border-left: 4px solid #2962ff; margin-bottom: 15px; font-size: 14px; color: #d1d4dc; }
    .news-card { background-color: #2a2e39; padding: 10px; border-radius: 6px; border-left: 4px solid #ff4444; margin-bottom: 10px; }
    .stSelectbox>div>div, .stNumberInput>div>div>input, .stTextInput>div>div>input { background-color: #1e222d !important; color: #ffffff !important; border: 1px solid #363a45 !important; border-radius: 6px !important; }
    label, .stMarkdown, h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. PENGAMBILAN DATA PASAR SPOT & NEWS
# ==========================================
def get_spot_price_mt5(pair_str):
    if not pair_str: return None
    p = pair_str.upper().replace("/", "").replace(" ", "").strip()
    if "XAU" in p or "GOLD" in p:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=3)
            if r.status_code == 200: return float(r.json()["price"])
        except Exception: pass
    if "USDT" in p or p in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"]:
        symbol = p if "USDT" in p else f"{p}USDT"
        try:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3)
            if r.status_code == 200: return float(r.json()["price"])
        except Exception: pass
    if len(p) == 6 and not p.startswith("XAU") and not p.startswith("XAG"):
        try:
            r = requests.get(f"https://api.frankfurter.app/latest?from={p[:3]}&to={p[3:]}", timeout=3)
            if r.status_code == 200: return float(r.json()["rates"][p[3:]])
        except Exception: pass
    return None

def fetch_economic_news():
    """Mengambil berita ekonomi terkini secara gratis"""
    try:
        url = "https://nifty-news.vercel.app/api/news"
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def calc_ema(prices, period):
    if not prices or len(prices) < period: return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]: ema = (p * k) + (ema * (1 - k))
    return ema

def calc_rsi(prices, period=14):
    if not prices or len(prices) < period + 1: return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0: return 100.0
    return 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))

def fetch_klines(pair, timeframe="M15"):
    s = pair.upper().replace("/", "").replace(" ", "").strip()
    if "USDT" in s or s in ["BTC", "ETH", "SOL", "XRP", "BNB"]:
        clean_s = s if "USDT" in s else f"{s}USDT"
        tf_map = {"M5":"5m","M15":"15m","M30":"30m","H1":"1h","H4":"4h","D1":"1d"}
        url = f"https://api.binance.com/api/v3/klines?symbol={clean_s}&interval={tf_map.get(timeframe, '15m')}&limit=100"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                return [float(x[4]) for x in data], [float(x[2]) for x in data], [float(x[3]) for x in data]
        except Exception: pass
    return None, None, None

# ==========================================
# 2. PEMANGGIL AI GEMINI ENGINE
# ==========================================
def get_available_gemini_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            valid_models = [m.get("name") for m in res.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
            if valid_models: return valid_models
    except Exception: pass
    return ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]

def call_gemini_api(api_key, prompt, image_bytes=None, mime_type="image/jpeg"):
    if not api_key or len(api_key.strip()) < 10: raise ValueError("API Key Gemini belum diisi!")
    clean_key = api_key.strip()
    if mime_type == "image/jpg": mime_type = "image/jpeg"
    models = get_available_gemini_models(clean_key)
    models.sort(key=lambda x: 0 if 'flash' in x else 1)
    parts = [{"text": prompt}]
    if image_bytes: parts.append({"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode('utf-8')}})
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json"}
    last_err = ""
    for model_path in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={clean_key}"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200: return res.json()['candidates'][0]['content']['parts'][0]['text']
            else: last_err = res.text
        except Exception as e:
            last_err = str(e)
            continue
    raise Exception(f"Gagal memanggil AI: {last_err}")

# UI STREAMLIT
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")

st.title("⚡ AI Ultra Pro Analyst + News")
st.caption("SMC, Multi-Timeframe Confluence & Fundamental News Analysis")

tab1, tab2, tab3, tab4 = st.tabs(["01. Buat Signal Pro", "02. Signal Hari Ini", "03. Analisa Chart", "04. Kalender & News AI"])

# TAB 1: BUAT SIGNAL PRO
with tab1:
    col1, col2 = st.columns(2)
    with col1: market = st.radio("Market:", ["Emas", "Crypto", "Forex"], label_visibility="collapsed")
    with col2:
        options = ["XAUUSD", "XAGUSD"] if market == "Emas" else (["BTCUSDT", "ETHUSDT", "SOLUSDT"] if market == "Crypto" else ["EURUSD", "GBPUSD", "USDJPY"])
        options.append("Tulis Sendiri...")
        pair_select = st.selectbox("Pair:", options, label_visibility="collapsed")
        pair = st.text_input("Pair Kustom:").upper() if pair_select == "Tulis Sendiri..." else pair_select

    spot_price = get_spot_price_mt5(pair) if pair else None
    current_price = st.number_input("Harga Spot MT5 Running:", value=float(spot_price) if spot_price else 0.0, format="%.4f")
    tf = st.select_slider("Timeframe Analisis Utama:", options=["M5", "M15", "M30", "H1", "H4", "D1"], value="M15")
    gaya = st.radio("Gaya Trading:", ["Scalping (Presisi M5/M15)", "Day Trade (Multi-Timeframe M15/H1)", "Swing (Struktur H4/D1)"], horizontal=True)

    if st.button("Buat Signal Ultra Pro", key="btn_signal"):
        if not api_key: st.error("⚠️ Masukkan API Key di Sidebar!")
        else:
            try:
                with st.spinner("📊 Menganalisis Multi-Timeframe, Indikator & Dampak News..."):
                    closes, highs, lows = fetch_klines(pair, timeframe=tf)
                    price_ref = current_price if current_price > 0 else (spot_price if spot_price else "Harga Pasar Terkini")
                    tech_data = f"Harga Spot MT5: {price_ref}\n"
                    if closes and len(closes) >= 50:
                        tech_data += f"- RSI (14): {calc_rsi(closes, 14):.1f}\n- EMA 20: {calc_ema(closes, 20):.4f}\n- EMA 50: {calc_ema(closes, 50):.4f}\n- High 50-Candle: {max(highs[-50:]):.4f}\n- Low 50-Candle: {min(lows[-50:]):.4f}\n"

                    prompt = f"""
                    Bertindaklah sebagai Senior Institutional Trader & Fundamental Analyst.
                    Analisis instrumen {pair} ({gaya}, TF {tf}).
                    
                    DATA PASAR REAL-TIME:
                    {tech_data}
                    
                    PERINTAH ANALISIS ULTRA PRO:
                    1. HINDARI RISK NEWS VOLATILITY: Peringatkan jika ada potensi dampaknya terhadap instrumen ini.
                    2. KONFIRMASI MULTI-TIMEFRAME (MTF): Pastikan tren M15 searah dengan H1/H4.
                    3. KEPUTUSAN PRESI: (BUY / SELL / WAIT).
                    4. PATOKAN HARGA: {price_ref}. Tentukan Entry, SL, TP1, TP2, TP3.
                    5. MANAJEMEN RISIKO: Tentukan titik pemicu pindahkan SL ke Breakeven (BE).
                    6. ALASAN LENGKAP: Jelaskan mengapa BUY/SELL berdasarkan SMC, Indikator, dan Fundamental.
                    """
                    result = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    if st.button("Tampilkan Signal Harian", key="btn_daily"):
        if not api_key: st.error("⚠️ Masukkan API Key!")
        else:
            try:
                gold_p = get_spot_price_mt5("XAUUSD")
                btc_p = get_spot_price_mt5("BTCUSDT")
                prompt = f"""
                Berikan 2 signal harian terbaik hari ini berdasarkan SMC & Fundamental News:
                1. XAUUSD (Harga Spot: {gold_p if gold_p else 'Pasar Terkini'})
                2. BTCUSDT (Harga Spot: {btc_p if btc_p else 'Pasar Terkini'})
                
                Sertakan Direction, Entry, Stop Loss, Take Profit, dan Alasan Analisis Lengkap (Kenapa BUY / Kenapa SELL).
                """
                result = call_gemini_api(api_key, prompt)
                st.markdown(result)
            except Exception as e: st.error(f"Error: {e}")

# TAB 3: ANALISA CHART
with tab3:
    uploaded_file = st.file_uploader("Upload Chart:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file: st.image(uploaded_file, caption="Chart diunggah")
    chart_pair = st.text_input("Pair Chart:", "XAUUSD")
    chart_tf = st.selectbox("Timeframe Chart:", ["M5", "M15", "M30", "H1", "H4", "D1"], index=1)

    if st.button("Analisa Chart Vision", key="btn_chart"):
        if not api_key or not uploaded_file: st.error("⚠️ Masukkan API Key dan unggah gambar!")
        else:
            try:
                prompt = f"Analisis screenshot chart {chart_pair} TF {chart_tf}. Tentukan Trend, SR, Order Block, Entry, SL, TP, dan Alasan Kenapa BUY/SELL."
                result = call_gemini_api(api_key, prompt, uploaded_file.getvalue(), uploaded_file.type)
                st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                st.markdown(result)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 4: KALENDER & ANALISA NEWS
with tab4:
    st.subheader("📰 Fundamental News & Impact Analyst")
    st.caption("Prediksi dampak berita ekonomi besar (NFP, CPI, FOMC, Suku Bunga) terhadap market.")
    
    news_input = st.text_area("Tulis/Tempel teks Berita / Isu Ekonomi yang ingin dianalisis (Contoh: Rilis data CPI US naik 3.5% atau Keputusan Suku Bunga Fed):", height=100)
    
    if st.button("Analisis Dampak Berita Ke Market", key="btn_news"):
        if not api_key: st.error("⚠️ Masukkan API Key di Sidebar!")
        else:
            try:
                with st.spinner("🤖 AI sedang menganalisis sentimen fundamental & dampaknya ke XAUUSD/Forex..."):
                    query = news_input if news_input else "Analisis peristiwa berita ekonomi utama minggu ini (NFP, CPI, FOMC) dan dampaknya terhadap pergerakan Emas (XAUUSD), Dolar (USD), dan Bitcoin."
                    prompt = f"""
                    Bertindaklah sebagai Chief Economist & Fundamental Forex/Gold Analyst.
                    Analisis berita / kondisi ekonomi berikut:
                    "{query}"
                    
                    BERIKAN ANALISIS LENGKAP:
                    1. 📢 HUBUNGAN SENTIMEN: Apakah ini BULLISH atau BEARISH untuk Dolar US (USD), Emas (XAUUSD), dan Crypto?
                    2. 💥 ESTIMASI VOLATILITAS: Berapa besar estimasi lonjakan pergerakan harga (High / Medium / Low Volatility)?
                    3. 📈 SKENARIO PERGERAKAN HARGA: Jika rilis data di atas ekspektasi vs di bawah ekspektasi pasar.
                    4. ⚠️ REKOMENDASI TRADING: Jam berapa trading harus dihentikan sementara (News Filter Zone) untuk menghindari SL tersapu.
                    """
                    result = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error Analisis News: {e}")
