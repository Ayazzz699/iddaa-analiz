import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
from datetime import datetime

# --- 1. GÜVENLİK VE SAYFA AYARLARI ---
st.set_page_config(page_title="PRO İDDAA ANALİZ", layout="wide")

# Sadece senin kullanman için şifre koruması
def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.text_input("Sistem Şifresi", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state.password == "1234"}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.warning("🔒 Lütfen yetkili giriş şifresini giriniz.")
    st.stop()

# --- 2. API KONFİGÜRASYONU ---
# Kendi API anahtarını aşağıya yapıştırdığından emin ol
API_KEY = "be89a4fda1mshbe9a84ef6434b94p1ff5e4jsnfc2d87499454" 
BASE_URL = "https://v3.football.api-sports.io/"
HEADERS = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY
}

# --- 3. VERİ ÇEKME FONKSİYONU (Gelişmiş Hata Ayıklama) ---
def get_api_data(endpoint):
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, headers=HEADERS, timeout=12)
        data = response.json()
        
        # Eğer API hata döndürürse ekrana basar
        if data.get('errors'):
            st.error(f"❌ API Hatası: {data['errors']}")
            return []
            
        return data.get('response', [])
    except Exception as e:
        st.error(f"🚀 Bağlantı Hatası: {e}")
        return []

def hesapla_poisson(ev_gol, dep_gol):
    ev_beklenen = ev_gol if ev_gol > 0 else 0.5
    dep_beklenen = dep_gol if dep_gol > 0 else 0.5
    toplam_lambda = ev_beklenen + dep_beklenen
    olasilik_alt = sum([poisson.pmf(i, toplam_lambda) for i in range(3)])
    return round((1 - olasilik_alt) * 100, 1)

# --- 4. ANA ARAYÜZ ---
st.title("🛡️ Pro-İddaa Analiz Komuta Merkezi")
st.sidebar.success("Sistem Aktif")

sekme1, sekme2, sekme3 = st.tabs(["📡 CANLI MAÇLAR & ANALİZ", "📅 GÜNLÜK PROGRAM", "📺 YAYIN ARA"])

# --- TAB 1: CANLI SKORLAR (UEFA DAHİL) ---
with sekme1:
    col1, col2 = st.columns([1, 4])
    if col1.button("🔄 Skorları Güncelle"):
        st.rerun()
    
    # Tüm canlı maçları çek
    live_matches = get_api_data("fixtures?live=all")
    
    if not live_matches:
        st.info("⚠️ Şu an aktif canlı maç (veya UEFA verisi) gelmiyor. API aboneliğini veya maç saatini kontrol et.")
        # Acil durum: Bugünün tüm maçlarını listeleme butonu
        if st.button("Bugünün Tüm Maçlarını Listele"):
            today = datetime.now().strftime('%Y-%m-%d')
            today_matches = get_api_data(f"fixtures?date={today}")
            for m in today_matches:
                st.write(f"⏰ {m['fixture']['date'][11:16]} | {m['teams']['home']['name']} vs {m['teams']['away']['name']}")
    else:
        for m in live_matches:
            # Önemli ligler veya UEFA maçlarını vurgula
            is_uefa = "UEFA" in m['league']['name']
            header_text = f"{'🏆' if is_uefa else '⚽'} {m['fixture']['status']['elapsed']}' | {m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']}"
            
            with st.expander(header_text, expanded=is_uefa):
                c1, c2, c3, c4 = st.columns(4)
                
                # İstatistikleri bul (Korner/Kart)
                corners, cards = "N/A", "N/A"
                if m.get('statistics'):
                    for s in m['statistics']:
                        if s['type'] == 'Corner Kicks': corners = s['value']
                        if s['type'] == 'Yellow Cards': cards = s['value']
                
                c1.metric("Skor", f"{m['goals']['home']} - {m['goals']['away']}")
                c2.metric("Korner", corners)
                c3.metric("Kart", cards)
                
                # Yapay Zeka Tahmini
                toplam_gol = (m['goals']['home'] or 0) + (m['goals']['away'] or 0)
                if m['fixture']['status']['elapsed'] > 30:
                    tahmin = "GOL BEKLENİYOR" if toplam_gol < 2 else "MAÇ DENGELİ"
                    c4.warning(f"Analiz: {tahmin}")

# --- TAB 2: GÜNLÜK PROGRAM ---
with sekme2:
    st.subheader("📊 Maç Önü Poisson Analizi")
    lig_secimi = st.selectbox("Lig / Kupa Seç", 
                             [3, 848, 203, 39, 140, 135, 78], 
                             format_func=lambda x: {3:"UEFA Avrupa Ligi", 848:"UEFA Konferans Ligi", 203:"Süper Lig", 39:"Premier Lig", 140:"La Liga", 135:"Serie A", 78:"Bundesliga"}[x])
    
    if st.button("Analizleri Listele"):
        fixtures = get_api_data(f"fixtures?league={lig_secimi}&season=2025&next=15")
        if fixtures:
            df_list = []
            for f in fixtures:
                df_list.append({
                    "Maç": f"{f['teams']['home']['name']} - {f['teams']['away']['name']}",
                    "Saat": f['fixture']['date'][11:16],
                    "2.5 Üst %": f"%{hesapla_poisson(1.6, 1.3)}",
                    "Tahmin": "KG VAR" if hesapla_poisson(1.6, 1.3) > 60 else "ALT / DENGELİ"
                })
            st.table(pd.DataFrame(df_list))

# --- TAB 3: YAYIN ARA ---
with sekme3:
    st.subheader("📺 Canlı Maç Yayını Arama")
    search_query = st.text_input("Maç Adı (Örn: Nottingham Forest Fenerbahçe):")
    if search_query:
        st.markdown(f"### [🔗 {search_query} Maçını Canlı İzle (Google)](https://www.google.com/search?q={search_query.replace(' ', '+')}+canli+izle+taraftarium24+selcuksports)")
        st.info("İpucu: Çıkan sonuçlarda 'Taraftarium24' veya 'SelçukSports' içeren linklere bakabilirsin.")
