import streamlit as st
import requests
import base64

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Ultra Pro Trading Analyst (Auto + Real Price Fix)",
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
    .price-badge-green { background-color: #1e222d; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #00e676; margin-bottom: 15px; font-size: 14px; color: #ffffff; }
    .price-badge-red { background-color: #1e222d; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #ff4444; margin-bottom: 15px; font-size: 14px; color: #ffffff; }
    .stSelectbox>div>div, .stTextInput>div>div>input { background-color: #1e222d !important; color: #ffffff !important; border: 1px solid #363a45 !important; border-radius: 6px !important; }
    label, .stMarkdown, h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# LOGIKA PEMBACAAN API KEY OTOMATIS (SECRETS)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
    st.sidebar.caption("Dapatkan API Key di: [Google AI Studio](https://aistudio.google.com/)")

# PENGAMBILAN HARGA SPOT REAL-TIME DARI PROVIDER BEBAS BLOKIR (COINBASE / COINCAP / GOLD-API / FRANKFURTER)
def get_spot_price_mt5(pair_str):
    if not pair_str: return None
    p = pair_str.upper().replace("/", "").replace(" ", "").strip()
    
    # A. EMAS / GOLD SPOT (XAUUSD)
    if "XAU" in p or "GOLD" in p:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=3)
            if r.status_code == 200: return float(r.json()["price"])
        except Exception: pass

    # B. CRYPTO (Coinbase & CoinCap API - Bebas blokir IP US Streamlit Cloud)
    crypto_symbols = {
        "BTCUSDT": "BTC", "BTC": "BTC",
        "ETHUSDT": "ETH", "ETH": "ETH",
        "SOLUSDT": "SOL", "SOL": "SOL",
        "XRPUSDT": "XRP", "XRP": "XRP",
        "BNBUSDT": "BNB", "BNB": "BNB",
        "DOGEUSDT": "DOGE", "DOGE": "DOGE"
    }
    
    coin_code = crypto_symbols.get(p)
    if not coin_code and "USDT" in p:
        coin_code = p.replace("USDT", "")
        
    if coin_code:
        # Try Coinbase API
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin_code}-USD/spot", timeout=3)
            if r.status_code == 200:
                return float(r.json()["data"]["amount"])
        except Exception: pass
        
        # Try CoinCap API Backup
        try:
            coin_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp", "BNB": "binance-coin", "DOGE": "dogecoin"}
            slug = coin_map.get(coin_code, coin_code.lower())
            r = requests.get(f"https://api.coincap.io/v2/assets/{slug}", timeout=3)
            if r.status_code == 200:
                return float(r.json()["data"]["priceUsd"])
        except Exception: pass

    # C. FOREX SPOT (Frankfurter API)
    if len(p) == 6 and not p.startswith("XAU") and not p.startswith("XAG"):
        try:
            r = requests.get(f"https://api.frankfurter.app/latest?from={p[:3]}&to={p[3:]}", timeout=3)
            if r.status_code == 200: return float(r.json()["rates"][p[3:]])
        except Exception: pass
        
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
    # Fetch candles via KuCoin API (Unblocked on US AWS)
    crypto_symbols = {"BTCUSDT": "BTC-USDT", "ETHUSDT": "ETH-USDT", "SOLUSDT": "SOL-USDT", "XRPUSDT": "XRP-USDT", "BNBUSDT": "BNB-USDT"}
    kucoin_sym = crypto_symbols.get(s, f"{s.replace('USDT', '')}-USDT" if "USDT" in s else None)
    
    if kucoin_sym:
        tf_map = {"M5":"5min","M15":"15min","M30":"30min","H1":"1hour","H4":"4hour","D1":"1day"}
        url = f"https://api.kucoin.com/api/v1/market/candles?symbol={kucoin_sym}&type={tf_map.get(timeframe, '15min')}"
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    closes = [float(x[2]) for x in reversed(data[:100])]
                    highs = [float(x[3]) for x in reversed(data[:100])]
                    lows = [float(x[4]) for x in reversed(data[:100])]
                    return closes, highs, lows
        except Exception: pass
    return None, None, None

def get_available_gemini_models(api_key_str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key_str.strip()}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            valid_models = [m.get("name") for m in res.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
            if valid_models: return valid_models
    except Exception: pass
    return ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]

def call_gemini_api(api_key_str, prompt, image_bytes=None, mime_type="image/jpeg"):
    if not api_key_str or len(api_key_str.strip()) < 10: raise ValueError("API Key Gemini belum diisi!")
    clean_key = api_key_str.strip()
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
st.title("⚡ AI Ultra Pro Analyst")
st.caption("SMC, Unblocked Auto Price Stream & Strict Profit Protection Rules")

tab1, tab2, tab3, tab4 = st.tabs(["01. Buat Signal Pro", "02. Signal Hari Ini", "03. Analisa Chart", "04. Kalender & News AI"])

# TAB 1: BUAT SIGNAL PRO
with tab1:
    col1, col2 = st.columns(2)
    with col1: market = st.radio("Market:", ["Crypto", "Emas", "Forex"], label_visibility="collapsed")
    with col2:
        options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"] if market == "Crypto" else (["XAUUSD", "XAGUSD"] if market == "Emas" else ["EURUSD", "GBPUSD", "USDJPY"])
        options.append("Tulis Sendiri...")
        pair_select = st.selectbox("Pilih Pair:", options, label_visibility="collapsed")
        pair = st.text_input("Pair Kustom:").upper() if pair_select == "Tulis Sendiri..." else pair_select

    auto_price = get_spot_price_mt5(pair) if pair else None
    if auto_price:
        st.markdown(f"<div class='price-badge-green'>🟢 <b>Harga Real-Time Live (Coinbase/Spot):</b> ${auto_price:,.2f}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='price-badge-red'>⚠️ <b>Sistem Siap:</b> Menghubungkan ke API Pasar...</div>", unsafe_allow_html=True)

    tf = st.select_slider("Timeframe Analisis Utama:", options=["M5", "M15", "M30", "H1", "H4", "D1"], value="M15")
    gaya = st.radio("Gaya Trading:", ["Scalping (Presisi M5/M15)", "Day Trade (Multi-Timeframe M15/H1)", "Swing (Struktur H4/D1)"], horizontal=True)

    if st.button("Buat Signal Ultra Pro (Auto)", key="btn_signal"):
        if not api_key: st.error("⚠️ API Key belum dikonfigurasi!")
        elif not pair: st.warning("⚠️ Pilih pair terlebih dahulu!")
        else:
            try:
                with st.spinner(f"📊 Menarik harga real-time {pair} & menganalisis pasar..."):
                    live_p = get_spot_price_mt5(pair)
                    closes, highs, lows = fetch_klines(pair, timeframe=tf)
                    
                    if not live_p and not closes:
                        st.error("Gagal mengambil harga real-time. Periksa koneksi internet atau nama pair Anda.")
                    else:
                        price_ref = f"${live_p:,.2f}" if live_p else (f"${closes[-1]:,.2f}" if closes else "Harga Pasar Terkini")
                        tech_data = f"Harga Spot Real-Time Detik Ini: {price_ref}\n"
                        if closes and len(closes) >= 50:
                            tech_data += f"- RSI (14): {calc_rsi(closes, 14):.1f}\n- EMA 20: ${calc_ema(closes, 20):,.2f}\n- EMA 50: ${calc_ema(closes, 50):,.2f}\n- High 50-Candle: ${max(highs[-50:]):,.2f}\n- Low 50-Candle: ${min(lows[-50:]):,.2f}\n"

                        prompt = f"""
                        Bertindaklah sebagai Senior Institutional Trader & Risk Manager.
                        Analisis {pair} ({gaya}, TF {tf}).
                        
                        DATA PASAR REAL-TIME DETIK INI:
                        {tech_data}
                        
                        INSTRUKSI SANGAT KETAT:
                        1. GUNAKAN HARGA REAL-TIME SEKARANG {price_ref} SEBAGAI PATOKAN MUTLAK. JANGAN MENGARANG ANGKA HARGA DILUAR ANGKA {price_ref}!
                        2. Berikan rekomendasi: BUY LIMIT / SELL LIMIT / BUY / SELL / WAIT.
                        3. Tentukan Entry Zone, Stop Loss (SL), TP1, TP2, TP3.
                        4. 🛡️ ATURAN PENGAMANAN PROFIT KETAT (WAJIB ADA):
                           - Tuliskan HARGA TEPAT kapan user HARUS memindahkan SL ke titik Entry (Breakeven / BE).
                           - Tuliskan petunjuk kapan user HARUS melakukan Partial Close di MT5 agar tidak berbalik rugi.
                        5. Jelaskan Alasan Teknikal & SMC secara logis.
                        """
                        result = call_gemini_api(api_key, prompt)
                        st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                        st.markdown(result)
                        st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    if st.button("Tampilkan Signal Harian", key="btn_daily"):
        if not api_key: st.error("⚠️ API Key belum dikonfigurasi!")
        else:
            try:
                gold_p = get_spot_price_mt5("XAUUSD")
                btc_p = get_spot_price_mt5("BTCUSDT")
                prompt = f"""
                Berikan 2 signal harian terbaik hari ini berdasarkan SMC & Market Real-Time:
                1. XAUUSD (Harga Live Spot: ${gold_p:,.2f} jika ada)
                2. BTCUSDT (Harga Live Spot: ${btc_p:,.2f} jika ada)
                
                Sertakan Direction, Entry Zone, SL, TP, serta Aturan Pemicu Breakeven (BE) untuk mengamankan profit.
                JANGAN MENGARANG HARGA DILUAR ANGKA PASAR SAAT INI.
                """
                result = call_gemini_api(api_key, prompt)
                st.markdown(result)
            except Exception as e: st.error(f"Error: {e}")

# TAB 3: ANALISA CHART
with tab3:
    uploaded_file = st.file_uploader("Upload Chart:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file: st.image(uploaded_file, caption="Chart diunggah")
    chart_pair = st.text_input("Pair Chart:", "BTCUSDT")
    chart_tf = st.selectbox("Timeframe Chart:", ["M5", "M15", "M30", "H1", "H4", "D1"], index=1)

    if st.button("Analisa Chart Vision", key="btn_chart"):
        if not api_key or not uploaded_file: st.error("⚠️ API Key belum dikonfigurasi atau gambar belum diunggah!")
        else:
            try:
                prompt = f"Analisis screenshot chart {chart_pair} TF {chart_tf}. Tentukan Trend, SR, Order Block, Entry Zone, SL, TP, Aturan Breakeven, dan Alasan Kenapa BUY/SELL."
                result = call_gemini_api(api_key, prompt, uploaded_file.getvalue(), uploaded_file.type)
                st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                st.markdown(result)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 4: KALENDER & ANALISA NEWS
with tab4:
    st.subheader("📰 Fundamental News & Impact Analyst")
    st.caption("Prediksi dampak berita ekonomi besar terhadap market.")
    
    news_input = st.text_area("Tulis/Tempel berita ekonomi yang ingin dianalisis:", height=100)
    
    if st.button("Analisis Dampak Berita Ke Market", key="btn_news"):
        if not api_key: st.error("⚠️ API Key belum dikonfigurasi!")
        else:
            try:
                with st.spinner("🤖 Menganalisis sentimen berita..."):
                    query = news_input if news_input else "Analisis peristiwa berita ekonomi utama minggu ini (NFP, CPI, FOMC) dan dampaknya terhadap Emas (XAUUSD), Dolar (USD), dan Bitcoin."
                    prompt = f"""
                    Analisis berita / kondisi ekonomi berikut:
                    "{query}"
                    
                    BERIKAN ANALISIS:
                    1. Sentimen (Bullish / Bearish untuk USD, XAUUSD, BTC)
                    2. Estimasi Volatilitas (High / Medium / Low)
                    3. Rekomendasi Jam Filter News (Kapan tidak boleh trading).
                    """
                    result = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error Analisis News: {e}")
