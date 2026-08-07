import streamlit as st
import google.generativeai as genai
from PIL import Image

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Trading Signal & Chart Analyzer",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS Tampilan Dark Mode
st.markdown("""
    <style>
    .stApp {
        background-color: #0e0e10;
        color: #ffffff;
    }
    div[data-baseweb="tab-list"] {
        background-color: #16161a;
        border-radius: 8px;
        padding: 5px;
    }
    div[data-baseweb="tab"] {
        color: #888888;
    }
    div[aria-selected="true"] {
        color: #f3ba2f !important;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #f3ba2f;
        color: #000000;
        font-weight: bold;
        font-size: 16px;
        border-radius: 8px;
        width: 100%;
        border: none;
        padding: 12px;
    }
    .stButton>button:hover {
        background-color: #d9a320;
        color: #000000;
    }
    .card-signal {
        background-color: #16161a;
        border: 1px solid #2a2a30;
        border-radius: 10px;
        padding: 20px;
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Function Otomatis Pilih Model Gemini yang Aktif
def get_active_model(api_key):
    genai.configure(api_key=api_key)
    # Mencari model yang tersedia di API key pengguna
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Prioritaskan model flash
    for m in available_models:
        if 'flash' in m:
            return genai.GenerativeModel(m)
            
    # Jika flash tidak ada, pakai model pertama yang mendukung
    if available_models:
        return genai.GenerativeModel(available_models[0])
    
    # Fallback default jika tidak terdeteksi
    return genai.GenerativeModel('gemini-1.5-flash')

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

    st.subheader("03. GAYA TRADING")
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
                with st.spinner("🤖 AI sedang menghubungkan server & menyusun signal..."):
                    model = get_active_model(api_key)
                    prompt = f"""
                    Bertindaklah sebagai Senior Trader. Analisis pair {pair} dengan strategi {gaya}.
                    Format respon:
                    - DIRECTION: [BUY / SELL]
                    - ENTRY: [Harga Entry]
                    - STOP LOSS: [Harga SL]
                    - TAKE PROFIT 1 (RR 1:2): [Harga TP1]
                    - TAKE PROFIT 2 (RR 1:3): [Harga TP2]
                    - TAKE PROFIT 3 (RR 1:4): [Harga TP3]
                    - RISK / REWARD: 1:2
                    - TINGKAT KEYAKINAN: [%]
                    - RINGKASAN TEKNIKAL: [Penjelasan singkat EMA, RSI, Candle]
                    - SIGNAL BATAL KALAU: [Kondisi batal]
                    """
                    response = model.generate_content(prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(response.text)
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
                with st.spinner("Memuat signal harian..."):
                    model = get_active_model(api_key)
                    prompt = "Berikan 2 signal trading harian terbaik hari ini untuk XAUUSD dan BTCUSDT lengkap dengan Entry, Stop Loss, Take Profit, dan Alasan Analisis."
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
            except Exception as e:
                st.error(f"Error: {e}")

# TAB 3: ANALISA CHART
with tab3:
    st.subheader("01. CHART KAMU")
    uploaded_file = st.file_uploader("Unggah screenshot chart:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Chart diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN")
    chart_pair = st.text_input("Tulis pair pada chart:", "BTCUSDT")

    st.subheader("03. TIMEFRAME CHART")
    tf = st.select_slider("Pilih Timeframe:", options=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"], value="M15")

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Unggah gambar chart terlebih dahulu!")
        else:
            try:
                with st.spinner("🤖 AI Vision sedang menganalisis pola chart..."):
                    model = get_active_model(api_key)
                    prompt = f"Analisis chart {chart_pair} timeframe {tf} ini. Tentukan Tren, Pattern, Support/Resistance, dan Signal (BUY/SELL) beserta SL/TP."
                    response = model.generate_content([prompt, image])
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(response.text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")
