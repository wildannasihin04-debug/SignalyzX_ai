import streamlit as st
import google.generativeai as genai
from PIL import Image

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Trading Signal & Chart Analyzer",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk tampilan Dark Mode & Accent Gold khas aplikasi Trading di Video
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

# --- SIDEBAR: KUNCI API GRATIS ---
st.sidebar.title("🔑 Pengaturan AI")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
st.sidebar.caption("Dapatkan API Key gratis di: [Google AI Studio](https://aistudio.google.com/)")

st.title("⚡ AI Trading Assistant")
st.caption("Aplikasi analisis teknikal, signal generator & pembaca chart otomatis.")

# --- TABS UTAMA (Sesuai Fitur Video) ---
tab1, tab2, tab3 = st.tabs(["01. Buat Signal", "02. Signal Hari Ini", "03. Analisa Chart"])

# ==========================================
# TAB 1: BUAT SIGNAL (Crypto, Forex, Emas)
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
    
    if pair_select == "Tulis Sendiri...":
        pair = st.text_input("Tulis Pair kustom (Contoh: MANTAUSDT):").upper()
    else:
        pair = pair_select

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
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Bertindaklah sebagai Senior Financial & Crypto/Forex Trader.
                Analisis kondisi teknikal pasar saat ini untuk pair {pair} dengan strategi {gaya}.
                
                Berikan respon dengan struktur teks rapi sebagai berikut:
                - DIRECTION: [BUY / SELL]
                - ENTRY: [Harga Entry Spesisifik]
                - STOP LOSS: [Harga Stop Loss]
                - TAKE PROFIT 1 (RR 1:2): [Harga]
                - TAKE PROFIT 2 (RR 1:3): [Harga]
                - TAKE PROFIT 3 (RR 1:4): [Harga]
                - RISK / REWARD: 1:2
                - TINGKAT KEYAKINAN: [Persentase %]
                - RINGKASAN TEKNIKAL: [Penjelasan singkat aksi harga, EMA 20/50/100, RSI, dan struktur candle M15/H1/H4]
                - SIGNAL BATAL KALAU: [Kondisi harga mendiskualifikasi signal ini]
                """
                
                with st.spinner("🤖 AI sedang menghitung indikator & menyusun signal..."):
                    response = model.generate_content(prompt)
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(response.text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

# ==========================================
# TAB 2: SIGNAL HARI INI (Rekap Harian)
# ==========================================
with tab2:
    st.subheader("📊 Signal Harian Terpopuler")
    st.info("Fitur ini menampilkan rekomendasi signal harian dengan akurasi & Risk/Reward terbaik.")
    
    if st.button("Tampilkan Signal Harian AI", key="btn_daily"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Berikan 2 signal trading harian terbaik hari ini untuk XAUUSD dan BTCUSDT lengkap dengan Entry, Stop Loss, Take Profit, dan Ringkasan Analisis Analisis Teknikal."
                
                with st.spinner("Memuat signal harian..."):
                    res = model.generate_content(prompt)
                    st.markdown(res.text)
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# TAB 3: ANALISA CHART (Upload Gambar Chart)
# ==========================================
with tab3:
    st.subheader("01. CHART KAMU")
    uploaded_file = st.file_uploader("Unggah screenshot chart trading kamu (PNG, JPG, WEBP):", type=["png", "jpg", "jpeg", "webp"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Chart yang diunggah", use_column_width=True)

    st.subheader("02. INSTRUMEN")
    chart_pair = st.text_input("Tulis pair pada chart (contoh: BTCUSDT, XAUUSD):", "BTCUSDT")

    st.subheader("03. TIMEFRAME CHART")
    tf = st.select_slider("Pilih Timeframe:", options=["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"], value="M15")

    if st.button("Analisa chart", key="btn_chart"):
        if not api_key:
            st.error("⚠️ Masukkan Gemini API Key terlebih dahulu!")
        elif uploaded_file is None:
            st.warning("⚠️ Silakan unggah foto/screenshot chart terlebih dahulu!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Kamu adalah pakar pembaca Chart Patterns & Price Action Trading.
                Analisis gambar chart {chart_pair} pada timeframe {tf} ini.
                
                Tentukan:
                1. Arah Tren & Pola Candle/Pattern yang terlihat.
                2. Level Support & Resistance kunci.
                3. Rekomendasi Signal (BUY/SELL), Entry, Stop Loss, dan Target Take Profit (TP1, TP2, TP3).
                4. Ringkasan Teknikal & Alasan Validasi.
                """
                
                with st.spinner("🤖 AI Vision sedang membaca pola & garis pada chart kamu..."):
                    response = model.generate_content([prompt, image])
                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(response.text)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Gagal menganalisis gambar: {e}")
