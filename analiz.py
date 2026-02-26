import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime

# --- 1. AYARLAR VE GÜVENLİK ---
st.set_page_config(page_title="PRO ANALİZ V2", layout="wide")

def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Sistem Şifresi", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state.password == "1234"}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.warning("🔒 Giriş Yapınız.")
    st.stop()

# --- 2. API AYARLARI ---
API_KEY = "7ab9862a233578646432c282ae1fa676"
BASE_URL = "https://v3.football.api-sports.io/"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}

# --- 3. VERİ ÇEKME MOTORU ---
def get_data(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=12).json()
        if res.get('errors'): st.error(f"API Hatası: {res['errors']}"); return []
        return res.get('response', [])
    except: return []

def get_live_stats(fixture_id):
    """ Canlı Korner, Kart ve Şut verilerini çeker """
    stats_data = get_data(f"fixtures/statistics?fixture={fixture_id}")
    result = {"korner": 0, "kart": 0, "sut": 0}
    if stats_data:
        for team in stats_data:
            for s in team['statistics']:
                val = s['value'] if s['value'] else 0
                if s['type'] == 'Corner Kicks': result['korner'] += val
                if s['type'] == 'Yellow Cards': result['kart'] += val
                if s['type'] == 'Total Shots': result['sut'] += val
    return result

# --- 4. ANA PANEL ---
st.title("⚽ PRO-İDDAA KOMUTA MERKEZİ V2")
tabs = st.tabs(["📡 CANLI ANALİZ", "📅 PROGRAM", "📺 YAYIN"])

# --- CANLI ANALİZ SEKMESİ ---
with tabs[0]:
    if st.button("🔄 Verileri Tazele"): st.rerun()
    
    live_matches = get_data("fixtures?live=all")
    
    if not live_matches:
        st.info("Şu an canlı maç verisi yok veya API kotası doldu.")
    else:
        for m in live_matches:
            m_id = m['fixture']['id']
            # Derin İstatistik Çekimi
            l_stats = get_live_stats(m_id)
            
            with st.expander(f"🏟️ {m['fixture']['status']['elapsed']}' | {m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']}", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                
                # METRİKLER
                c1.metric("SKOR", f"{m['goals']['home']}-{m['goals']['away']}")
                c2.metric("KORNER", l_stats['korner'])
                c3.metric("KART", l_stats['kart'])
                
                # KORNER ANALİZ ALGORİTMASI
                dk = m['fixture']['status']['elapsed']
                if dk > 5:
                    # Dakika başına korner ortalamasından maç sonu tahmini
                    projeksiyon = (l_stats['korner'] / dk) * 95 
                    tahmin = "9.5 ÜST" if projeksiyon > 9.3 else "8.5 / 9.5 ALT"
                    c4.subheader(f"🔮 {tahmin}")
                    st.caption(f"Yapay Zeka Maç Sonu Korner Beklentisi: {round(projeksiyon, 1)}")
                else:
                    c4.write("Analiz Başlıyor...")

# --- PROGRAM SEKMESİ ---
with tabs[1]:
    lig = st.selectbox("Lig Seç", [3, 848, 203, 39], format_func=lambda x: {3:"Avrupa Ligi", 848:"Konferans Ligi", 203:"Süper Lig", 39:"Premier Lig"}[x])
    if st.button("Analiz Et"):
        fix = get_data(f"fixtures?league={lig}&season=2025&next=10")
        if fix:
            res = [{"Maç": f"{f['teams']['home']['name']}-{f['teams']['away']['name']}", "Saat": f['fixture']['date'][11:16], "Tahmin": "GOL VAR / 2.5 ÜST"} for f in fix]
            st.table(pd.DataFrame(res))

# --- YAYIN SEKMESİ ---
with tabs[2]:
    ara = st.text_input("Maç Yaz (Örn: Fenerbahçe):")
    if ara:
        st.markdown(f"### [🔗 {ara} CANLI İZLE (HD)](https://www.google.com/search?q={ara.replace(' ', '+')}+canli+izle+selcuksports+taraftarium24)")

