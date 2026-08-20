import streamlit as st
import requests
import base64
from datetime import datetime, timezone, timedelta

# Konfigurasi Tampilan Website
st.set_page_config(
    page_title="AI Ultra Session SMC Analyst",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS TradingView Pro / Dashboard Theme
st.markdown("""
    <style>
    .stApp { background-color: #131722; color: #d1d4dc; font-family: 'Trebuchet MS', sans-serif; }
    div[data-baseweb="tab-list"] { background-color: #1e222d; border-radius: 6px; padding: 4px; }
    div[data-baseweb="tab"] { color: #787b86; font-size: 14px; font-weight: 600; }
    div[aria-selected="true"] { background-color: #2962ff !important; color: #ffffff !important; border-radius: 4px; }
    .stButton>button { background: linear-gradient(90deg, #2962ff 0%, #1e53e5 100%); color: #ffffff; border-radius: 6px; border: none; font-weight: bold; padding: 12px; box-shadow: 0 4px 12px rgba(41,98,255,0.3); }
    .stButton>button:hover { background: #1e53e5; transform: translateY(-1px); }
    .card-signal { background-color: #1e222d; border: 1px solid #2a2e39; border-radius: 8px; padding: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); margin-top: 15px; }
    .price-badge-green { background-color: #1e222d; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #00e676; margin-bottom: 10px; font-size: 14px; color: #ffffff; }
    .session-badge { background-color: #1e222d; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #2962ff; margin-bottom: 15px; font-size: 13px; color: #ffffff; }
    .stSelectbox>div>div, .stTextInput>div>div>input { background-color: #1e222d !important; color: #ffffff !important; border: 1px solid #363a45 !important; border-radius: 6px !important; }
    label, .stMarkdown, h1, h2, h3 { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# INISIALISASI MEMORI SESSION STATE (AUTO-SAVE SIGNAL)
if "last_signal" not in st.session_state:
    st.session_state["last_signal"] = None
if "signal_history" not in st.session_state:
    st.session_state["signal_history"] = []

# LOGIKA PEMBACAAN API KEY OTOMATIS (SECRETS)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis):", type="password")
    st.sidebar.caption("Dapatkan API Key di: [Google AI Studio](https://aistudio.google.com/)")

# FUNGSI DETEKSI SESI PASAR & KILLZONE REAL-TIME (WIB)
def get_market_session_info():
    now_utc = datetime.now(timezone.utc)
    now_wib = now_utc + timedelta(hours=7)
    time_str = now_wib.strftime("%H:%M WIB")
    hour = now_wib.hour
    
    sessions = []
    if 7 <= hour < 16:
        sessions.append("🌏 Sesi Asia (Tokyo)")
    if 14 <= hour < 23:
        sessions.append("🇬🇧 Sesi London (Eropa)")
    if 19 <= hour or hour < 4:
        sessions.append("🇺🇸 Sesi New York (AS)")
        
    killzone = "💤 Sesi Konsolidasi / Biasa"
    if 14 <= hour <= 17:
        killzone = "⚡ LONDON OPEN KILLZONE (Volatilitas Tinggi)"
    elif 19 <= hour <= 23:
        killzone = "🔥 NEW YORK & OVERLAP KILLZONE (PUNCAK VOLATILITAS TEKSTUR SMC)"
    elif 7 <= hour <= 10:
        killzone = "🌏 ASIA OPEN KILLZONE (Pembentukan Range)"
        
    return time_str, ", ".join(sessions) if sessions else "Pasar Tutup / Transisi", killzone

# PENGAMBILAN HARGA SPOT REAL-TIME DARI PROVIDER BEBAS BLOKIR
def get_spot_price_mt5(pair_str):
    if not pair_str: return None
    p = pair_str.upper().replace("/", "").replace(" ", "").strip()
    
    # A. EMAS / GOLD SPOT (XAUUSD)
    if "XAU" in p or "GOLD" in p:
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=3)
            if r.status_code == 200: return float(r.json()["price"])
        except Exception: pass

    # B. CRYPTO (Coinbase / CoinCap API)
    crypto_symbols = {
        "BTCUSDT": "BTC", "BTC": "BTC",
        "ETHUSDT": "ETH", "ETH": "ETH",
        "SOLUSDT": "SOL", "SOL": "SOL",
        "XRPUSDT": "XRP", "XRP": "XRP",
        "BNBUSDT": "BNB", "BNB": "BNB"
    }
    coin_code = crypto_symbols.get(p, p.replace("USDT", "") if "USDT" in p else None)
    if coin_code:
        try:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{coin_code}-USD/spot", timeout=3)
            if r.status_code == 200: return float(r.json()["data"]["amount"])
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

def calc_atr(highs, lows, closes, period=14):
    if not closes or len(closes) < period + 1: return None
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)
    if len(tr_list) < period: return None
    atr = sum(tr_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
    return atr

def fetch_klines(pair, timeframe="M15"):
    s = pair.upper().replace("/", "").replace(" ", "").strip()
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
st.title("⚡ AI Ultra Session SMC Analyst")
st.caption("SMC + RSI Divergence Filter • ATR Dynamic SL Buffer • Visual Cards UI")

# INFORMASI SESI REAL-TIME
wib_time, active_sessions, current_killzone = get_market_session_info()
st.markdown(f"""
<div class='session-badge'>
🕒 <b>Waktu Saat Ini:</b> {wib_time}<br>
🏛️ <b>Sesi Aktif:</b> {active_sessions}<br>
🎯 <b>Status Killzone:</b> <b>{current_killzone}</b>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["01. Buat Signal Pro", "02. Signal Hari Ini", "03. Analisa Chart", "04. 📜 Riwayat Signal"])

# INSTRUKSI LAYOUT HASIL ANALISIS (KARTU PENJELASAN CONFLUENCE + KARTU ENTRY VISUAL)
COMBINED_LAYOUT_INSTRUCTION = """
LAKUKAN PENYUSUNAN RESPON DALAM 2 BAGIAN UTAMA MENGGUNAKAN HTML CARD BERIKUT:

<!-- BAGIAN 1: KARTU VISUAL PENJELASAN ANALISIS (NEWS, CONFLUENCE INDICATORS & SMC) -->
<div style="background-color: #1a1e29; border: 1px solid #2e3548; border-radius: 10px; padding: 16px; margin-bottom: 15px;">
  
  <div style="background-color: #12151e; border-left: 4px solid #ff9800; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
    <div style="color: #ff9800; font-weight: bold; font-size: 14px; margin-bottom: 6px;">📊 ANALISIS NEWS & SENTIMEN FUNDAMENTAL</div>
    <div style="color: #d1d4dc; font-size: 13px; line-height: 1.6;">
      • <b>Status / Peringatan News:</b> [Detail Jam WIB News & Peringatan]<br>
      • <b>Proyeksi Bias Sentimen:</b> [BUY (Bullish) / SELL (Bearish) / Neutral]<br>
      • <b>Penjelasan Ringkas:</b> [Alasan sentimen pasar secara singkat]
    </div>
  </div>

  <div style="background-color: #12151e; border-left: 4px solid #00e676; padding: 12px; border-radius: 6px;">
    <div style="color: #00e676; font-weight: bold; font-size: 14px; margin-bottom: 6px;">🛡️ CONFLUENCE FILTER (SMC + RSI DIVERGENCE + ATR BUFFER)</div>
    <div style="color: #d1d4dc; font-size: 13px; line-height: 1.6;">
      • <b>Trend Utama & EMA:</b> [Bullish / Bearish berdasarkan EMA 20/50]<br>
      • <b>Status RSI Divergence:</b> [Normal / Bearish Divergence (Hati-hati Fakeout Buy) / Bullish Divergence]<br>
      • <b>Validasi Body Close (Anti-Fakeout):</b> [Status BOS/CHoCH Body Close vs Wick Sweep Trap]<br>
      • <b>ATR Buffer SL:</b> [Toleransi jarak penyangga pips aman yang ditambahkan pada SL]
    </div>
  </div>

</div>

<!-- BAGIAN 2: KARTU VISUAL ENTRY / EKSEKUSI (KARTU VISUAL UTAMA) -->
<div style="background-color: #1a1e29; border: 1px solid #2e3548; border-radius: 10px; padding: 18px; margin-bottom: 15px;">
  <div style="background-color: #2962ff; color: #ffffff; padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 16px; margin-bottom: 12px; display: inline-block;">
    🎯 REKOMENDASI: [BUY LIMIT / SELL LIMIT / BUY / SELL / WAIT]
  </div>
  
  <div style="background-color: #12151e; border-left: 4px solid #2962ff; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
    <div style="color: #787b86; font-size: 12px; font-weight: bold;">🎯 ENTRY ZONE (DISCOUNT / FVG)</div>
    <div style="color: #2962ff; font-size: 18px; font-weight: bold;">[Harga Entry Presisi]</div>
    <div style="color: #a0a5b5; font-size: 12px;">[Catatan Ringkas Skenario Entry]</div>
  </div>

  <div style="background-color: #12151e; border-left: 4px solid #ff4444; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
    <div style="color: #787b86; font-size: 12px; font-weight: bold;">🛑 STOP LOSS (SL KETAT + ATR BUFFER)</div>
    <div style="color: #ff4444; font-size: 18px; font-weight: bold;">[Harga SL Aman dengan Tambahan Buffer ATR]</div>
    <div style="color: #a0a5b5; font-size: 12px;">[Detail pips SL & penyangga ATR]</div>
  </div>

  <div style="background-color: #12151e; border-left: 4px solid #00e676; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
    <div style="color: #787b86; font-size: 12px; font-weight: bold;">🏆 TARGET PROFIT (RR MINIMAL 1:2+)</div>
    <div style="color: #00e676; font-size: 14px; font-weight: bold;">• TP 1 (RR 1:2): <span style="font-size: 16px;">[Harga TP1]</span></div>
    <div style="color: #00e676; font-size: 14px; font-weight: bold;">• TP 2 (RR 1:3): <span style="font-size: 16px;">[Harga TP2]</span></div>
    <div style="color: #00e676; font-size: 14px; font-weight: bold;">• TP 3 (RR 1:4): <span style="font-size: 16px;">[Harga TP3]</span></div>
  </div>

  <div style="background-color: #12151e; border-left: 4px solid #ffd600; padding: 12px; border-radius: 6px;">
    <div style="color: #ffd600; font-size: 13px; font-weight: bold;">💡 SARAN LOT & PENGAMANAN PROFIT</div>
    <div style="color: #d1d4dc; font-size: 13px;"><b>Ukuran Lot Aman:</b> [Saran Lot, misal 0.01 Micro Lot]</div>
    <div style="color: #d1d4dc; font-size: 13px;"><b>Rule Breakeven (BE):</b> [Harga pemicu geser SL ke Entry]</div>
  </div>
</div>
"""

# TAB 1: BUAT SIGNAL PRO
with tab1:
    if st.session_state["last_signal"] is not None:
        last = st.session_state["last_signal"]
        with st.expander(f"📌 SIGNAL TERAKHIR DISIMPAN: {last['pair']} ({last['time']})", expanded=False):
            st.markdown(last["result"], unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1: market = st.radio("Market:", ["Emas", "Crypto", "Forex"], label_visibility="collapsed")
    with col2:
        options = ["XAUUSD", "XAGUSD"] if market == "Emas" else (["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"] if market == "Crypto" else ["EURUSD", "GBPUSD", "USDJPY"])
        options.append("Tulis Sendiri...")
        pair_select = st.selectbox("Pilih Pair:", options, label_visibility="collapsed")
        pair = st.text_input("Pair Kustom:").upper() if pair_select == "Tulis Sendiri..." else pair_select

    auto_price = get_spot_price_mt5(pair) if pair else None
    if auto_price:
        st.markdown(f"<div class='price-badge-green'>🟢 <b>Harga Real-Time Live:</b> {auto_price:,.4f}</div>", unsafe_allow_html=True)

    tf = st.select_slider("Timeframe Analisis Utama:", options=["M5", "M15", "M30", "H1", "H4", "D1"], value="M15")
    gaya = st.radio("Gaya Trading:", ["Scalping (Presisi M5/M15)", "Day Trade (Multi-Timeframe M15/H1)", "Swing (Struktur H4/D1)"], horizontal=True)

    if st.button("Buat Signal Ultra Pro (Auto)", key="btn_signal"):
        if not api_key: st.error("⚠️ API Key belum dikonfigurasi!")
        elif not pair: st.warning("⚠️ Pilih pair terlebih dasar!")
        else:
            try:
                with st.spinner(f"📊 Menarik data Sesi, Indikator & Harga Real-Time {pair}..."):
                    live_p = get_spot_price_mt5(pair)
                    closes, highs, lows = fetch_klines(pair, timeframe=tf)
                    
                    price_ref = f"{live_p:,.4f}" if live_p else (f"{closes[-1]:,.4f}" if closes else "Harga Pasar Terkini")
                    tech_data = f"Harga Spot Real-Time: {price_ref}\n"
                    if closes and len(closes) >= 50:
                        rsi_v = calc_rsi(closes, 14)
                        ema20_v = calc_ema(closes, 20)
                        ema50_v = calc_ema(closes, 50)
                        atr_v = calc_atr(highs, lows, closes, 14)
                        
                        tech_data += f"- RSI (14 Momentum): {rsi_v:.1f if rsi_v else 'N/A'}\n"
                        tech_data += f"- EMA 20: {ema20_v:.4f if ema20_v else 'N/A'}\n"
                        tech_data += f"- EMA 50: {ema50_v:.4f if ema50_v else 'N/A'}\n"
                        tech_data += f"- ATR 14 (Nilai Volatilitas Buffer SL): {atr_v:.4f if atr_v else 'N/A'}\n"
                        tech_data += f"- High 50-Candle: {max(highs[-50:]):.4f}\n- Low 50-Candle: {min(lows[-50:]):.4f}\n"

                    prompt = f"""
                    Bertindaklah sebagai Senior Institutional Smart Money Concepts (SMC) Trader & Confluence Analyst.
                    Analisis {pair} (Gaya: {gaya}, Timeframe Utama: {tf}).
                    
                    KONDISI WAKTU & SESI PASAR REAL-TIME:
                    - Waktu WIB: {wib_time}
                    - Sesi Aktif: {active_sessions}
                    - Status Killzone: {current_killzone}
                    
                    DATA PASAR & STRUKTUR HARGA INDIKATOR:
                    {tech_data}

                    ATURAN CONFLUENCE & ANTI-FAKEOUT KETAT:
                    1. RSI DIVERGENCE CHECK: Evaluasi apakah ada perbedaan arah antara pergerakan harga dan RSI (Bearish Divergence / Bullish Divergence). Jika ada Divergence berlawanan, BATALKAN ENTRY atau berikan peringatan FAKEOUT!
                    2. SL BUFFER DINAMIS BERBASIS ATR: Jangan memasang Stop Loss pas di ujung Order Block/FVG. Tambahkan jarak buffer sebesar 0.5x s.d. 1x nilai ATR (penyangga pips aman) di luar ekor terluar untuk mencegah SL tersapu spread/wick hunting.
                    3. VALIDASI BODY CLOSE: CHoCH & BOS HANYA VALID jika CANDLE BODY CLOSE di luar level kunci (Wick sweep = Trap/Candle Palsu).
                    4. REWARD MINIMAL 1:2 (TP1 minimal 2x jarak SL).

                    FORMAT JAWABAN WAJIB MENGGUNAKAN LAYOUT DUA KARTU VISUAL BERIKUT:
                    {COMBINED_LAYOUT_INSTRUCTION}
                    """
                    result = call_gemini_api(api_key, prompt)
                    
                    # SIMPAN HASIL KE MEMORI SESSION STATE
                    st.session_state["last_signal"] = {
                        "pair": pair,
                        "time": wib_time,
                        "price_ref": price_ref,
                        "result": result
                    }
                    st.session_state["signal_history"].insert(0, st.session_state["last_signal"])

                    st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                    st.markdown(result, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 2: SIGNAL HARI INI
with tab2:
    if st.button("Tampilkan Signal Harian Sesi Ini", key="btn_daily"):
        if not api_key: st.error("⚠️ API Key belum dikonfigurasi!")
        else:
            try:
                gold_p = get_spot_price_mt5("XAUUSD")
                btc_p = get_spot_price_mt5("BTCUSDT")
                prompt = f"""
                Berikan 2 signal harian terbaik saat ini berdasarkan Sesi Pasar ({active_sessions}), Deteksi RSI Divergence, ATR SL Buffer, Anti-Fakeout SMC & RR Minimal 1:2:
                1. XAUUSD (Harga Live Spot: {gold_p if gold_p else 'Pasar Terkini'})
                2. BTCUSDT (Harga Live Spot: {btc_p if btc_p else 'Pasar Terkini'})
                
                Gunakan format Kartu Visual lengkap berikut untuk masing-masing signal:
                {COMBINED_LAYOUT_INSTRUCTION}
                """
                result = call_gemini_api(api_key, prompt)
                st.markdown(result, unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 3: ANALISA CHART
with tab3:
    uploaded_file = st.file_uploader("Upload Chart:", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_file: st.image(uploaded_file, caption="Chart diunggah")
    chart_pair = st.text_input("Pair Chart:", "XAUUSD")
    chart_tf = st.selectbox("Timeframe Chart:", ["M5", "M15", "M30", "H1", "H4", "D1"], index=1)

    if st.button("Analisa Chart Vision Sesi Ini", key="btn_chart"):
        if not api_key or not uploaded_file: st.error("⚠️ API Key belum dikonfigurasi atau gambar belum diunggah!")
        else:
            try:
                prompt = f"""
                Analisis screenshot chart {chart_pair} TF {chart_tf} ini layaknya Session SMC Analyst (Sesi {active_sessions}).
                Evaluasi RSI Divergence visual, ATR Buffer pada SL, CHoCH, BOS, FVG, Order Block, serta bedakan penembusan asli (Body Close) vs Candle Palsu (Wick Sweep).
                
                Susun hasil analisis menggunakan format Kartu Visual lengkap berikut:
                {COMBINED_LAYOUT_INSTRUCTION}
                """
                result = call_gemini_api(api_key, prompt, uploaded_file.getvalue(), uploaded_file.type)
                st.markdown("<div class='card-signal'>", unsafe_allow_html=True)
                st.markdown(result, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e: st.error(f"Error: {e}")

# TAB 4: RIWAYAT SIGNAL TERSIMPAN
with tab4:
    st.subheader("📜 Riwayat Signal Sesi Ini")
    st.caption("Daftar sinyal yang sudah pernah Anda buat sebelumnya agar tidak terhapus saat keluar ke MT5.")
    
    if not st.session_state["signal_history"]:
        st.info("Belum ada riwayat sinyal tersimpan. Buat sinyal baru di menu '01. Buat Signal Pro'.")
    else:
        for idx, item in enumerate(st.session_state["signal_history"]):
            with st.expander(f"📌 {idx+1}. {item['pair']} - {item['time']} (@ {item['price_ref']})", expanded=(idx==0)):
                st.markdown(item["result"], unsafe_allow_html=True)
