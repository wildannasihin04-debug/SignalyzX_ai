import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Trading Signal & Chart Analyzer",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS Dark Mode
st.markdown("""
    <style>
    .stApp { background-color: #0e0e10; color: #ffffff; }
    div[data-baseweb="tab-list"] { background-color: #16161a; border-radius: 8px; padding: 5px; }
    div[data-baseweb="tab"] { color: #888888; }
    div[aria-selected="true"] { color: #f3ba2f !important; font-weight: bold; }
    .stButton>button { background-color: #f3ba2f; color: #000000; font-weight: bold; font-size: 16px; border-radius: 8px; width: 100%; border: none; padding: 12px; }
    .stButton>button:hover { background-color: #d9a320; color: #000000; }
    .card-signal { background-color: #16161a; border: 1px solid #2a2a30; border-radius: 10px; padding: 20px; margin-top: 15px; }
    .price-badge { background-color: #1f222d; padding: 10px; border-radius: 6px; border-left: 4px solid #f3ba2f; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# 1. FUNGSI AMBIL HARGA DENGAN FALLBACK AMAN
def get_live_price_safe(symbol):
    if not symbol:
        return None
    sym = symbol.upper().replace("/", "").replace(" ", "").strip()
    
    # Crypto via Binance API
    try:
        clean_sym = sym if "USDT" in sym else sym + "USDT"
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={clean_sym}", timeout=2)
        if res.status_code == 200:
            return float(res.json()["price"])
    except Exception:
        pass
        
    # Forex & Commodity via Public API
    yf_map = {"XAUUSD": "GC=F", "GOLD": "GC=F", "XAGUSD": "SI=F"}
    yf_code = yf_map.get(sym, f"{sym}=X" if len(sym) == 6 else None)
    
    if yf_code:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_code}?interval=1m&range=1d"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=2)
            if res.status_code == 200:
                data = res.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return float(price)
        except Exception:
            pass
            
    return None

# 2. FUNGSI EKSEKUSI AI SANGAT STABIL
def generate_ai_response(api_key, prompt, image=None):
    if not api_key or len(api_key.strip()) < 5:
        raise ValueError("Silakan masukkan Gemini API Key di menu Sidebar sebelah kiri.")
        
    genai.configure(api_key=api_key.strip())
    
    # Model-model Gemini yang didukung
    candidate_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    
    last_err = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            if image:
                res = model.generate_content([prompt, image])
            else:
                res = model.generate_content(prompt)
            if res and res.text:
                return res.text
        except Exception as e:
            last_err = e
            continue

    raise Exception(f"Gagal menghubungi AI ({last_err}). Pastikan API Key Gemini Anda valid.")

# SIDEBAR: KUNCI API
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
st.sidebar.caption("Dapatkan API Key gratis di: [Google AI Studio](https://aistudio.google.com/)")

st.title("⚡ AI Trading Assistant")
st.caption("Aplikasi analisis teknikal & pembaca chart presisi tinggi.")

tab1, tab2, tab3 = st.tabs(["01. Buat Signal", "02. Signal Hari Ini", "03. Analisa Chart"])

# TAB 1: BUAT SIGNAL
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

    # Ambil harga acuan awal
    auto_p = get_live_price_safe(pair) if pair else None
    
    st.subheader("03. HARGA RUNNING MT5 SAYA")
    st.caption("Harga terdeteksi otomatis. Anda dapat menyesuaikan angka ini jika broker MT5 Anda sedikit berbeda.")
    current_price = st.number_input(
        "Masukkan/Sesuaikan Harga MT5 Saat Ini:",
        value=float(auto_p) if auto_p else 0.0,
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
                with st.spinner("🤖 Menyusun signal presisi..."):
                    price_acuan = current_price if current_price > 0 else (auto_p if auto_p else "Harga Market Saat Ini")
                    
                    prompt = f"""
                    Bertindaklah sebagai Senior Trader Profesional.
                    Analisis instrumen {pair} untuk gaya trading {gaya}.

                    SYARAT UTAMA PRESISI:
                    HARGA RUNNING MT5 SEKARANG ADALAH: {price_acuan}.
                    SANGAT PENTING: Semua harga Entry, Stop Loss (SL), dan Take Profit (TP1, TP2, TP3) HARUS DIBUAT DENGAN PATOKAN HARGA {price_acuan} INI! Jangan gunakan harga lain.

                    Format Output:
                    - PAIR: {pair}
                    - HARGA MT5 PATOKAN: {price_acuan}
                    - DIRECTION: [BUY / SELL]
                    - ENTRY: [Harga Entry dekat {price_acuan}]
                    - STOP LOSS: [Harga SL]
                    - TAKE PROFIT 1: [Harga TP1]
                    - TAKE PROFIT 2: [Harga TP2]
                    - TAKE PROFIT 3: [Harga TP3]
                    - RISK / REWARD: 1:2
                    - TINGKAT KEYAKINAN: [%]
                    - ANALISIS TEKNIKAL: [Penjelasan singkat Trend, RSI, EMA]
                    - INVALIDASI SIGNAL: [Kondisi Batal]
                    """
                    result_text = generate_ai_response(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    st.subheader("📊 Signal Harian Terpopuler")
    if st.button("Tampilkan Signal Harian AI", key="btn_daily"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        else:
            try:
                with st.spinner("Memuat signal harian..."):
                    gold_p = get_live_price_safe("XAUUSD")
                    btc_p = get_live_price_safe("BTCUSDT")
                    prompt = f"""
                    Berikan 2 signal harian terbaik hari ini:
                    1. XAUUSD (Harga Live Acuan: {gold_p if gold_p else 'Pasar Terkini'})
                    2. BTCUSDT (Harga Live Acuan: {btc_p if btc_p else 'Pasar Terkini'})
                    
                    Sertakan Entry, Stop Loss, Take Profit, dan Alasan Teknikal berdasarkan harga tersebut.
                    """
                    result_text = generate_ai_response(api_key, prompt)
                    st.markdown(result_text)
            except Exception as e:
                st.error(f"{e}")

# TAB 3: ANALISA CHART
with tab3:
    st.subheader("01. UPLOAD SCREENSHOT CHART")
    uploaded_file = st.file_uploader("Unggah screenshot chart MT5 / TradingView:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Chart berhasil diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN & HARGA RUNNING")
    chart_pair = st.text_input("Tulis pair pada chart:", "XAUUSD")
    chart_price = st.number_input("Masukkan harga running yang tertera di MT5 kamu (Opsional):", value=0.0, format="%.4f")

    st.subheader("03. TIMEFRAME")
    tf = st.select_slider("Pilih Timeframe:", options=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"], value="M15")

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key di menu Sidebar terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Unggah foto/screenshot chart Anda terlebih dahulu.")
        else:
            try:
                with st.spinner("🤖 AI Vision sedang membaca sumbu harga & chart..."):
                    price_note = f"Harga running di MT5 user adalah {chart_price}" if chart_price > 0 else "Gunakan skala harga yang terbaca di sumbu kanan gambar screenshot"
                    prompt = f"""
                    Analisis gambar screenshot chart {chart_pair} timeframe {tf} ini.

                    PETUNJUK ANALISIS:
                    1. {price_note}.
                    2. Tentukan arah pergerakan (BUY/SELL/WAIT).
                    3. Berikan rekomendasi Entry, SL, dan TP yang 100% presisi mengikuti skala harga di screenshot ini.

                    Format Respon:
                    - INSTRUMEN: {chart_pair}
                    - HARGA TERBACA/ACUAN: [Harga]
                    - STRUKTUR TREN & PATTERN: [Analisis]
                    - SUPPORT & RESISTANCE: [Level Harga]
                    - RECOMMENDATION: [BUY / SELL / WAIT]
                    - ENTRY: [Harga]
                    - STOP LOSS: [Harga]
                    - TAKE PROFIT: [Harga]
                    - RINGKASAN ANALISIS: [Penjelasan]
                    """
                    result_text = generate_ai_response(api_key, prompt, image)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{e}")
