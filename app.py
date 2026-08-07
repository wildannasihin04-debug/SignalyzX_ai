import streamlit as st
import requests
import base64

# Konfigurasi Halaman & Tampilan
st.set_page_config(
    page_title="AI Trading Signal & Chart Analyzer",
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
    .price-box { background-color: #1f222d; padding: 12px; border-radius: 8px; border-left: 4px solid #f3ba2f; margin-bottom: 15px; font-size: 15px; }
    </style>
""", unsafe_allow_html=True)

# 1. FUNGSI AMBIL HARGA PASAR AKURAT & REAL-TIME
def get_live_price(pair_str):
    if not pair_str:
        return None
    p = pair_str.upper().replace("/", "").replace(" ", "").strip()
    
    # A. Crypto (Binance Public API)
    if "USDT" in p or p in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"]:
        symbol = p if "USDT" in p else f"{p}USDT"
        try:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3)
            if r.status_code == 200:
                return float(r.json()["price"])
        except Exception:
            pass

    # B. Forex (EURUSD, GBPUSD, dll via Frankfurter API)
    if len(p) == 6 and not p.startswith("XAU") and not p.startswith("XAG"):
        base_c = p[:3]
        target_c = p[3:]
        try:
            r = requests.get(f"https://api.frankfurter.app/latest?from={base_c}&to={target_c}", timeout=3)
            if r.status_code == 200:
                return float(r.json()["rates"][target_c])
        except Exception:
            pass

    # C. Emas / Gold (XAUUSD via Gold API)
    if "XAU" in p or "GOLD" in p:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=3)
            if r.status_code == 200:
                return float(r.json()["price"])
        except Exception:
            pass
            
    return None

# 2. FUNGSI UTAMA PANGGIL AI VIA REST API (ANTI-ERROR & TANPA SDK)
def call_gemini_api(api_key, prompt, image_bytes=None, mime_type="image/jpeg"):
    if not api_key or len(api_key.strip()) < 5:
        raise ValueError("API Key Gemini belum diisi! Masukkan API Key gratis Anda pada menu Sidebar sebelah kiri.")
    
    # Pilihan model terupdate
    models = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
    
    parts = [{"text": prompt}]
    if image_bytes:
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": base64_img
            }
        })
    
    payload = {"contents": [{"parts": parts}]}
    
    last_err = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200:
                data = res.json()
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except KeyError:
                    continue
            else:
                last_err = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_err = str(e)
            continue
            
    raise Exception(f"Gagal menghubungkan ke AI Google. Pastikan API Key Anda aktif. Detail: {last_err}")

# SIDEBAR: API KEY
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
st.sidebar.caption("Dapatkan API Key gratis di: [Google AI Studio](https://aistudio.google.com/)")

st.title("⚡ AI Trading Assistant")
st.caption("Aplikasi analisa teknikal & pembaca chart presisi berbasis AI Vision.")

tab1, tab2, tab3 = st.tabs(["01. Buat Signal", "02. Signal Hari Ini", "03. Analisa Chart"])

# ==========================================
# TAB 1: BUAT SIGNAL (OTOMATIS HARGA REAL-TIME)
# ==========================================
with tab1:
    st.subheader("01. MARKET")
    market = st.radio("Pilih Market:", ["Crypto", "Forex", "Emas"], horizontal=True, label_visibility="collapsed")

    st.subheader("02. INSTRUMEN")
    if market == "Crypto":
        options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "Tulis Sendiri..."]
    elif market == "Forex":
        options = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "EURJPY", "Tulis Sendiri..."]
    else:
        options = ["XAUUSD", "XAGUSD", "Tulis Sendiri..."]

    pair_select = st.selectbox("Pilih Pair:", options, label_visibility="collapsed")
    pair = st.text_input("Tulis Pair kustom:").upper() if pair_select == "Tulis Sendiri..." else pair_select

    # Ambil harga real-time otomatis
    auto_price = get_live_price(pair) if pair else None
    
    st.subheader("03. HARGA RUNNING MT5")
    current_price = st.number_input(
        "Harga Real-Time Terdeteksi (Dapat Anda sesuaikan dengan MT5 jika ada selisih broker):",
        value=float(auto_price) if auto_price else 0.0,
        format="%.4f"
    )

    st.subheader("04. GAYA TRADING")
    gaya = st.radio(
        "Pilih Gaya Trading:",
        ["Scalping (Tahan 15m - 3 jam)", "Day Trade (Tahan 2 - 12 jam)", "Swing (Tahan 1 - 5 hari)"],
        label_visibility="collapsed"
    )

    if st.button("Buat signal", key="btn_signal"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key di menu Sidebar terlebih dahulu!")
        elif not pair:
            st.warning("⚠️ Pilih atau masukkan nama pair terlebih dahulu.")
        else:
            try:
                with st.spinner("🤖 Mengambil data pasar real-time & menganalisis..."):
                    price_acuan = current_price if current_price > 0 else (auto_price if auto_price else "Harga Pasar Terkini")
                    
                    prompt = f"""
                    Bertindaklah sebagai Senior Trader Profesional & Analyst.
                    Analisis instrumen {pair} untuk gaya trading {gaya}.

                    ATURAN UTAMA PRESISI:
                    HARGA PASAR / MT5 RUNNING SAAT INI ADALAH: {price_acuan}.
                    SEMUA kalkulasi Entry, Stop Loss (SL), dan Take Profit (TP1, TP2, TP3) WAJIB menggunakan harga patokan {price_acuan} ini!

                    Format Output:
                    - INSTRUMEN: {pair}
                    - HARGA RUNNING PATOKAN: {price_acuan}
                    - DIRECTION: [BUY / SELL]
                    - ENTRY: [Harga Entry dekat {price_acuan}]
                    - STOP LOSS: [Harga SL]
                    - TAKE PROFIT 1: [Harga TP1]
                    - TAKE PROFIT 2: [Harga TP2]
                    - TAKE PROFIT 3: [Harga TP3]
                    - RISK / REWARD: 1:2
                    - TINGKAT KEYAKINAN: [%]
                    - ANALISIS TEKNIKAL: [Penjelasan singkat Trend, RSI, EMA, Price Action]
                    - INVALIDASI SIGNAL: [Kondisi Batal]
                    """
                    result_text = call_gemini_api(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{e}")

# ==========================================
# TAB 2: SIGNAL HARI INI
# ==========================================
with tab2:
    st.subheader("📊 Signal Harian Terpopuler")
    if st.button("Tampilkan Signal Harian AI", key="btn_daily"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        else:
            try:
                with st.spinner("Memuat rekap signal harian..."):
                    gold_p = get_live_price("XAUUSD")
                    btc_p = get_live_price("BTCUSDT")
                    prompt = f"""
                    Berikan 2 signal harian terbaik hari ini berdasarkan analisis teknikal real-time:
                    1. XAUUSD (Harga Live: {gold_p if gold_p else 'Pasar Terkini'})
                    2. BTCUSDT (Harga Live: {btc_p if btc_p else 'Pasar Terkini'})
                    
                    Sertakan Entry, Stop Loss, Take Profit, dan Alasan Teknikal berdasarkan harga pasar tersebut.
                    """
                    result_text = call_gemini_api(api_key, prompt)
                    st.markdown(result_text)
            except Exception as e:
                st.error(f"{e}")

# ==========================================
# TAB 3: ANALISA CHART (VISION API DIRECT)
# ==========================================
with tab3:
    st.subheader("01. UPLOAD SCREENSHOT CHART")
    uploaded_file = st.file_uploader("Unggah screenshot chart MT5 / TradingView:", type=["png", "jpg", "jpeg", "webp"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Chart diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN & HARGA RUNNING MT5")
    chart_pair = st.text_input("Tulis pair pada chart:", "XAUUSD")
    chart_price = st.number_input("Harga running tertera di MT5 (Opsional, untuk akurasi 100%):", value=0.0, format="%.4f")

    st.subheader("03. TIMEFRAME")
    tf = st.select_slider("Pilih Timeframe:", options=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"], value="M15")

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key di menu Sidebar terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Unggah foto/screenshot chart Anda terlebih dahulu.")
        else:
            try:
                with st.spinner("🤖 AI Vision sedang membaca sumbu harga & pola chart..."):
                    img_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    price_info = f"Harga running di MT5 saat ini adalah {chart_price}" if chart_price > 0 else "Gunakan skala harga di sumbu kanan gambar screenshot"
                    
                    prompt = f"""
                    Analisis gambar screenshot chart {chart_pair} timeframe {tf} ini.

                    PETUNJUK ANALISIS CHARTS:
                    1. {price_info}.
                    2. Perhatikan sumbu harga sebelah kanan dan pola candlestick/chart pattern.
                    3. Berikan rekomendasi Entry, SL, dan TP yang presisi sesuai skala harga pada screenshot ini.

                    Format Respon:
                    - INSTRUMEN: {chart_pair}
                    - HARGA TERBACA DI CHART: [Harga]
                    - STRUKTUR TREN & PATTERN: [Analisis]
                    - SUPPORT & RESISTANCE: [Level Harga]
                    - RECOMMENDATION: [BUY / SELL / WAIT]
                    - ENTRY: [Harga]
                    - STOP LOSS: [Harga]
                    - TAKE PROFIT: [Harga]
                    - CATATAN ANALISIS: [Penjelasan Ringkas]
                    """
                    result_text = call_gemini_api(api_key, prompt, image_bytes=img_bytes, mime_type=mime_type)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{e}")
