import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import yfinance as yf

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
    </style>
""", unsafe_allow_html=True)

# 1. FUNGSI AMBIL HARGA REAL-TIME
def get_live_price(symbol):
    symbol = symbol.upper().replace("/", "").replace(" ", "")
    try:
        # Crypto via Binance API
        if "USDT" in symbol or "BTC" in symbol or "ETH" in symbol:
            clean_sym = symbol if "USDT" in symbol else symbol + "USDT"
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={clean_sym}", timeout=3)
            if res.status_code == 200:
                return float(res.json()["price"])
        
        # Gold (XAUUSD)
        if "XAU" in symbol or "GOLD" in symbol:
            ticker = yf.Ticker("GC=F")
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
        
        # Forex (EURUSD, GBPUSD, dll)
        if len(symbol) == 6:
            ticker = yf.Ticker(f"{symbol}=X")
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None

# 2. FUNGSI EKSEKUSI AI VISION & TEKS SANGAT AMAN
def generate_ai_response(api_key, prompt, image=None):
    genai.configure(api_key=api_key)
    
    # Memisahkan kandidat model untuk teks & vision agar tidak crash
    vision_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    text_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    candidates = vision_models if image else text_models
    
    last_error = None
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            if image:
                res = model.generate_content([prompt, image])
            else:
                res = model.generate_content(prompt)
            return res.text
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"Gagal memanggil AI: {last_error}")

# SIDEBAR: KUNCI API
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
st.sidebar.caption("Dapatkan API Key gratis di: [Google AI Studio](https://aistudio.google.com/)")

st.title("⚡ AI Trading Assistant")
st.caption("Aplikasi analisis teknikal, signal generator & pembaca chart otomatis.")

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

    # Mengambil harga live otomatis jika ada
    live_price = get_live_price(pair) if pair else None
    
    st.subheader("03. HARGA SAAT INI (MT5)")
    custom_price = st.number_input("Harga Running di MT5 Kamu (Bisa diisi manual agar 100% sama dengan MT5):", 
                                   value=float(live_price) if live_price else 0.0, 
                                   format="%.5f")

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
            st.warning("⚠️ Masukkan nama pair/instrumen terlebih dahulu.")
        else:
            try:
                with st.spinner("🤖 Mengambil harga real-time & menyusun signal..."):
                    harga_patokan = custom_price if custom_price > 0 else (live_price if live_price else "Sesuaikan dengan MT5 saat ini")
                    
                    prompt = f"""
                    Bertindaklah sebagai Senior Financial Trader.
                    Analisis pair {pair} dengan strategi {gaya}.
                    
                    PENTING: HARGA SAAT INI DI MARKET/MT5 ADALAH {harga_patokan}.
                    Gunakan angka harga {harga_patokan} ini sebagai acuan utama untuk menentukan Entry, Stop Loss, dan Take Profit. Jangan gunakan harga fiktif!

                    Format respon:
                    - INSTRUMEN: {pair}
                    - HARGA SEKARANG: {harga_patokan}
                    - DIRECTION: [BUY / SELL]
                    - ENTRY: [Harga Entry dekat {harga_patokan}]
                    - STOP LOSS: [Harga SL]
                    - TAKE PROFIT 1 (RR 1:2): [Harga TP1]
                    - TAKE PROFIT 2 (RR 1:3): [Harga TP2]
                    - TAKE PROFIT 3 (RR 1:4): [Harga TP3]
                    - RISK / REWARD: 1:2
                    - TINGKAT KEYAKINAN: [%]
                    - RINGKASAN TEKNIKAL: [Penjelasan singkat EMA, RSI, Candle]
                    - SIGNAL BATAL KALAU: [Kondisi batal]
                    """
                    result_text = generate_ai_response(api_key, prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    st.subheader("📊 Signal Harian Terpopuler")
    if st.button("Tampilkan Signal Harian AI", key="btn_daily"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        else:
            try:
                with st.spinner("Memuat signal harian real-time..."):
                    gold_price = get_live_price("XAUUSD")
                    btc_price = get_live_price("BTCUSDT")
                    prompt = f"""
                    Berikan 2 signal trading harian terbaik hari ini untuk XAUUSD (Harga Live saat ini: {gold_price}) dan BTCUSDT (Harga Live saat ini: {btc_price}).
                    Sertakan Entry, Stop Loss, Take Profit, dan Alasan Analisis berdasarkan harga real-time tersebut.
                    """
                    result_text = generate_ai_response(api_key, prompt)
                    st.markdown(result_text)
            except Exception as e:
                st.error(f"Error: {e}")

# TAB 3: ANALISA CHART
with tab3:
    st.subheader("01. CHART KAMU")
    uploaded_file = st.file_uploader("Unggah screenshot chart MT5 / TradingView:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Chart diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN")
    chart_pair = st.text_input("Tulis pair pada chart:", "XAUUSD")

    st.subheader("03. TIMEFRAME CHART")
    tf = st.select_slider("Pilih Timeframe:", options=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"], value="M15")

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Unggah gambar chart terlebih dahulu!")
        else:
            try:
                with st.spinner("🤖 AI Vision sedang membaca teks angka pada chart..."):
                    prompt = f"""
                    Kamu adalah pakar Vision Trading Analyst.
                    Analisis gambar screenshot chart {chart_pair} timeframe {tf} ini.

                    PETUNJUK SANGAT PENTING:
                    1. PERHATIKAN SUMBU HARGA (PRICE SCALE) DI SEBELAH KANAN GAMBAR CHART INI.
                    2. BACA TEKS ANGKA HARGA DENGAN TELITI DARI FOTO SCREENSHOT TERSEBUT.
                    3. JANGAN MENGARANG ATAU MENEBAK HARGA DILUAR ANGKA YANG TERTERA DI CHART INI.
                    4. Semua angka Entry, SL, dan TP HARUS SESUAI dengan skala harga yang terlihat di screenshot MT5/TradingView ini.

                    Format Respon:
                    - HARGA TERBACA DI CHART: [Tulis harga running yang tertera di chart]
                    - TREN & PATTERN: [Analisis struktur chart]
                    - SUPPORT & RESISTANCE: [Level harga dari chart]
                    - RECOMMENDATION: [BUY / SELL / WAIT]
                    - ENTRY: [Harga]
                    - STOP LOSS: [Harga]
                    - TAKE PROFIT: [Harga]
                    - ALASAN TEKNIKAL: [Penjelasan]
                    """
                    result_text = generate_ai_response(api_key, prompt, image)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result_text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error Analisa Chart: {e}")
