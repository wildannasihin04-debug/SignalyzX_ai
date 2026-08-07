import streamlit as st
import requests
import base64

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Pro Trading Analyst (Cyberpunk Neon)",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS Cyberpunk Neon
st.markdown("""
    <style>
    .stApp { background-color: #0d0e15; color: #e2e8f0; }
    div[data-baseweb="tab-list"] { background-color: #171923; border-radius: 12px; padding: 6px; border: 1px solid #2d3748; }
    div[data-baseweb="tab"] { color: #a0aec0; }
    div[aria-selected="true"] { background: linear-gradient(90deg, #805ad5 0%, #3182ce 100%) !important; color: #ffffff !important; border-radius: 8px; }
    .stButton>button { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: #000000; font-weight: 900; border-radius: 10px; border: none; padding: 14px; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button:hover { box-shadow: 0 0 20px rgba(79,172,254,0.6); }
    .card-signal { background-color: #171923; border: 1px solid #4a5568; border-radius: 16px; padding: 20px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); }
    .metric-card { background-color: #171923; padding: 12px; border-radius: 8px; border-left: 4px solid #00f2fe; margin-bottom: 15px; font-size: 14px; color: #e2e8f0; }
    .stSelectbox>div>div, .stNumberInput>div>div>input, .stTextInput>div>div>input { background-color: #2d3748 !important; color: #00f2fe !important; border-radius: 8px !important; }
    label, .stMarkdown, h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# 1. PENGAMBILAN HARGA SPOT MT5
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

# UI Streamlit
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key:", type="password")

st.title("⚡ Cyberpunk Trading AI")
st.caption("Neon Vision Style • Precision Technical Analysis")

tab1, tab2, tab3 = st.tabs(["01. Buat Signal Pro", "02. Signal Hari Ini", "03. Analisa Chart"])

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
    tf = st.select_slider("Timeframe:", options=["M5", "M15", "M30", "H1", "H4", "D1"], value="M15")
    gaya = st.radio("Gaya Trading:", ["Scalping (Presisi M5/M15)", "Day Trade (M15/H1)", "Swing (H4/D1)"], horizontal=True)

    if st.button("Buat Signal Pro", key="btn_signal"):
        if not api_key: st.error("⚠️ Masukkan API Key!")
        else:
            try:
                with st.spinner("📊 Menganalisis..."):
                    closes, highs, lows = fetch_klines(pair, timeframe=tf)
                    price_ref = current_price if current_price > 0 else (spot_price if spot_price else "Harga Pasar Terkini")
                    tech_data = f"Harga Spot MT5: {price_ref}\n"
                    if closes and len(closes) >= 50:
                        tech_data += f"- RSI (14): {calc_rsi(closes, 14):.1f}\n- EMA 20: {calc_ema(closes, 20):.4f}\n- EMA 50: {calc_ema(closes, 50):.4f}\n"

                    prompt = f"Bertindaklah sebagai Senior Analyst. Analisis {pair} ({gaya}, TF {tf}).\nDATA: {tech_data}\nPatokan harga {price_ref}.\nBerikan SMC Analysis, Decision (BUY/SELL), Entry, SL, TP (1-3), dan Alasan Lengkap."
                    result = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

with tab2:
    if st.button("Tampilkan Signal Harian", key="btn_daily"):
        if not api_key: st.error("⚠️ Masukkan API Key!")
        else:
            try:
                result = call_gemini_api(api_key, "Berikan 2 signal harian terbaik (XAUUSD & BTCUSDT) lengkap dengan SMC Analysis, Entry, SL, TP, dan Alasan.")
                st.markdown(result)
            except Exception as e: st.error(f"Error: {e}")

with tab3:
    uploaded_file = st.file_uploader("Upload Chart:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file: st.image(uploaded_file, caption="Chart diunggah")
    chart_pair = st.text_input("Pair Chart:", "XAUUSD")
    chart_tf = st.selectbox("Timeframe Chart:", ["M5", "M15", "M30", "H1", "H4", "D1"], index=1)

    if st.button("Analisa Chart", key="btn_chart"):
        if not api_key or not uploaded_file: st.error("⚠️ Masukkan API Key dan unggah gambar!")
        else:
            try:
                result = call_gemini_api(api_key, f"Analisis screenshot chart {chart_pair} TF {chart_tf}. Tentukan Trend, SR, Order Block, Entry, SL, TP, dan Alasan.", uploaded_file.getvalue(), uploaded_file.type)
                st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                st.markdown(result)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")
