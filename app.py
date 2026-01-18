import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import warnings
import json
import os
import requests
from io import BytesIO

# Uyarıları kapat
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Portföy Analiz Botu V13", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu (4 Katmanlı)")
st.markdown("Bu uygulama, **V18.0 Stratejisi** ile Portföy, BIST 100, **Popüler Yan Tahtalar** ve Tüm Pazarı analiz eder.")

# --- DOSYA YÖNETİMİ ---
PORTFOY_DOSYASI = "portfoy.json"

def portfoy_yukle():
    if os.path.exists(PORTFOY_DOSYASI):
        with open(PORTFOY_DOSYASI, "r") as f:
            return json.load(f)
    return ["TUPRS.IS", "ASTOR.IS", "DOAS.IS", "MGROS.IS", "BIMAS.IS", "SOKM.IS", "AKBNK.IS", "YKBNK.IS", "EDATA.IS", "RUBNS.IS", "VESBE.IS", "TEHOL.IS"]

def portfoy_kaydet(liste):
    with open(PORTFOY_DOSYASI, "w") as f:
        json.dump(liste, f)

# Session State
if 'portfoy_listesi' not in st.session_state: st.session_state['portfoy_listesi'] = portfoy_yukle()
if 'sonuc_portfoy' not in st.session_state: st.session_state['sonuc_portfoy'] = None
if 'sonuc_bist100' not in st.session_state: st.session_state['sonuc_bist100'] = None
if 'sonuc_yan' not in st.session_state: st.session_state['sonuc_yan'] = None # YENİ
if 'sonuc_tum' not in st.session_state: st.session_state['sonuc_tum'] = None
if 'tum_hisseler_listesi' not in st.session_state: st.session_state['tum_hisseler_listesi'] = []
if 'yan_hisseler_listesi' not in st.session_state: st.session_state['yan_hisseler_listesi'] = [] # YENİ

# --- STATİK LİSTELER ---
# BIST 100 Listesi (Filtreleme ve 2. Sekme İçin)
BIST_100_LISTESI = [
"AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALTNY.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BALSU.IS", "BIMAS.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", "DAPGM.IS", "DOAS.IS", "DOHOL.IS", "DSTKF.IS", "ECILC.IS", "EFOR.IS", "EGEEN.IS", "EKGYO.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLRMK.IS", "GRSEL.IS", "GRTHO.IS", "GSRAY.IS", "GUBRF.IS", "HALKB.IS", "HEKTS.IS", "ISCTR.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KCHOL.IS", "KLRHO.IS", "KONTR.IS", "KRDMD.IS", "KTLEV.IS", "KUYAS.IS", "MAGEN.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "MPARK.IS", "OBAMS.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PASEU.IS", "PATEK.IS", "PETKM.IS", "PGSUS.IS", "QUAGR.IS", "RALYH.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "SKBNK.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TRALT.IS", "TRENJ.IS", "TRMET.IS", "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS", "TUREX.IS", "TURSG.IS", "ULKER.IS", "VAKBN.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "ZOREN.IS"
]
# Karşılaştırma için .IS uzantısız set
BIST_100_SET = set([h.replace(".IS", "") for h in BIST_100_LISTESI])

# --- CANLI HİSSE LİSTESİ ÇEKME (TRADINGVIEW) ---
@st.cache_data(ttl=3600)
def hisse_taramasi_yap(mod="tum"):
    # Mod: 'tum' (Tüm Pazar) veya 'hacim' (Popüler Yan Tahtalar)
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        
        # Sıralama Kriteri: Popülerler için Hacim, Tümü için Piyasa Değeri
        sort_criteria = "volume" if mod == "hacim" else "market_cap_basic"
        range_limit = 250 if mod == "hacim" else 600 # Hacimde ilk 250'ye bakıp eleyeceğiz
        
        payload = {
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "options": {"lang": "tr"},
            "symbols": {"query": {"types": []}},
            "columns": ["name", "close", "volume", "market_cap_basic"],
            "sort": {"sortBy": sort_criteria, "sortOrder": "desc"},
            "range": [0, range_limit]
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            tum_liste = [item['d'][0] for item in data['data']] # .IS eklemeden al
            
            if mod == "hacim":
                # FİLTRELEME MANTIĞI: Listede olup BIST 100'de OLMAYANLARI al
                yan_tahtalar = []
                for h in tum_liste:
                    if h not in BIST_100_SET:
                        yan_tahtalar.append(f"{h}.IS")
                return yan_tahtalar[:50] # En hacimli 50 yan tahta
            else:
                return [f"{h}.IS" for h in tum_liste] # Hepsini döndür
        else:
            return []
    except Exception as e:
        return []

# --- SİDEBAR ---
with st.sidebar:
    st.header("💼 Portföy Yönetimi")
    st.write("📋 **Mevcut Hisselerin:**")
    st.code(", ".join([h.replace(".IS","") for h in st.session_state['portfoy_listesi']]))
    
    yeni_hisse = st.text_input("Hisse Kodu Gir (Örn: GARAN):").upper()
    if st.button("➕ Ekle"):
        if yeni_hisse:
            sembol = f"{yeni_hisse}.IS" if not yeni_hisse.endswith(".IS") else yeni_hisse
            if sembol not in st.session_state['portfoy_listesi']:
                st.session_state['portfoy_listesi'].append(sembol)
                portfoy_kaydet(st.session_state['portfoy_listesi'])
                st.success(f"{yeni_hisse} eklendi!")
                st.rerun()
            else:
                st.warning("Bu hisse zaten listenizde.")

    silinecek_hisse = st.selectbox("Çıkarılacak Hisse Seç:", options=["Seçiniz"] + [h.replace(".IS","") for h in st.session_state['portfoy_listesi']])
    if st.button("➖ Çıkar"):
        if silinecek_hisse != "Seçiniz":
            sembol = f"{silinecek_hisse}.IS"
            if sembol in st.session_state['portfoy_listesi']:
                st.session_state['portfoy_listesi'].remove(sembol)
                portfoy_kaydet(st.session_state['portfoy_listesi'])
                st.success(f"{silinecek_hisse} silindi!")
                st.rerun()

# --- ANALİZ FONKSİYONLARI ---
def veri_cek_ve_hazirla(sembol):
    try:
        df_d = yf.download(sembol, period="2y", interval="1d", progress=False)
        if df_d.empty: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        df_w = yf.download(sembol, period="5y", interval="1wk", progress=False)
        if df_w.empty: return None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        df_w['LRC_MID_W'] = ta.linreg(df_w['Close'], length=50)
        if df_w['LRC_MID_W'] is not None:
            stdev_w = df_w['Close'].rolling(window=50).std()
            df_w['LRC_UPPER_W'] = df_w['LRC_MID_W'] + (2 * stdev_w)
        else:
            df_w['LRC_UPPER_W'] = 0
             
        haftalik_sinyaller = df_w[['LRC_UPPER_W']].shift(1)
        
        df_d.index = df_d.index.tz_localize(None)
        haftalik_sinyaller.index = haftalik_sinyaller.index.tz_localize(None)
        df_d = df_d.join(haftalik_sinyaller.reindex(df_d.index, method='ffill'))
        
        return df_d
    except Exception as e:
        return None

def indikatorleri_hesapla(df, sembol):
    try:
        df['EMA_50_D'] = ta.ema(df['Close'], length=50)
        df['EMA_100_D'] = ta.ema(df['Close'], length=100)
        df['EMA_200_D'] = ta.ema(df['Close'], length=200)
        
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        st = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if st is not None:
            df['ST_DEGER_D'] = st.iloc[:, 0]
            df['ST_YON_D'] = st.iloc[:, 1]
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            col_mid = [c for c in bb.columns if c.startswith('BBM')][0]
            df['BB_MID'] = bb[col_mid]
        
        df['LRC_MID_D'] = ta.linreg(df['Close'], length=50)
        stdev = df['Close'].rolling(window=50).std()
        df['LRC_UPPER_D'] = df['LRC_MID_D'] + (2 * stdev)

        df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_SMA20']

        df['Perf_1W'] = df['Close'].pct_change(periods=5) * 100
        df['Perf_1M'] = df['Close'].pct_change(periods=21) * 100
        
        return df
    except Exception as e:
        return None

def strateji_analizi(df, sembol):
    try:
        bugun = df.iloc[-1]
        fiyat = bugun['Close']
        if pd.isna(bugun.get('EMA_200_D')): return None

        ema_50 = bugun['EMA_50_D']
        ema_100 = bugun['EMA_100_D']
        ema_200 = bugun['EMA_200_D']
        st_deger_d = bugun['ST_DEGER_D']
        st_yon_d = bugun['ST_YON_D'] 
        rsi = bugun['RSI']
        
        perf_1w = bugun.get('Perf_1W', 0)
        perf_1m = bugun.get('Perf_1M', 0)
        macd_val = bugun.get('MACD_12_26_9')
        macd_sig = bugun.get('MACDs_12_26_9')
        macd_al = macd_val > macd_sig
        
        hedef_gunluk = bugun['LRC_UPPER_D']
        bb_mid = bugun['BB_MID']
        rvol = bugun['RVOL'] if not pd.isna(bugun['RVOL']) else 1.0
        hacim_ikon = "🔋" if rvol > 1.2 else ("🪫" if rvol < 0.8 else "▪️")
        
        fiyat_ema200_ustunde = fiyat > ema_200
        bb_uzaklik = (fiyat - bb_mid) / fiyat
        tavan_uzaklik_d = (hedef_gunluk - fiyat) / fiyat
        st_uzaklik_d = abs((fiyat - st_deger_d) / fiyat)

        etiket_st_d = "🟢" if st_yon_d == 1 else "🔴"
        macd_etiket = "🟢 AL" if macd_al else "🔴 SAT"

        veri = {
            "Hisse": sembol.replace(".IS", ""),
            "Fiyat": fiyat,
            "1H Değ.": perf_1w,
            "1A Değ.": perf_1m,
            "EMA(50)": ema_50,
            "EMA(100)": ema_100,
            "EMA(200)": ema_200, 
            "MACD": macd_etiket,
            "RSI": rsi,
            "Hacim": f"{hacim_ikon} %{int(rvol*100)}",
            "S.Trend(G)": etiket_st_d, 
            "STOP (G)": st_deger_d,
            "HEDEF (G)": hedef_gunluk, 
            "STRATEJİK YORUM": ""
        }

        if not fiyat_ema200_ustunde:
            if rsi < 30: veri["STRATEJİK YORUM"] = "⚡ TEPKİ: EMA200 altı ama aşırı ucuz (RSI<30)."
            elif macd_al and st_yon_d == 1: veri["STRATEJİK YORUM"] = "🚀 DİP DÖNÜŞÜ?: Riskli ama göstergeler düzeliyor."
            else: veri["STRATEJİK YORUM"] = "⛔ UZAK DUR: Trend Negatif (EMA200 Altı)."
        else:
            if rsi > 70: veri["STRATEJİK YORUM"] = f"⚠️ KAR AL: RSI şişti ({int(rsi)})."
            elif tavan_uzaklik_d < 0.02: veri["STRATEJİK YORUM"] = f"🧱 DİRENÇTE: Hedefe ({round(hedef_gunluk,2)}) değdi."
            elif st_yon_d == 1: 
                ek_mesaj = " (Hacim Zayıf!)" if rvol < 0.8 else " (Hacim Güçlü🚀)" if rvol > 1.3 else ""
                if macd_al:
                    if 0 < bb_uzaklik < 0.03: veri["STRATEJİK YORUM"] = f"✅ EKLEME: Ortalamalara yakın.{ek_mesaj}"
                    else: veri["STRATEJİK YORUM"] = f"⚖️ GİRİŞ/TUT: Trend güçlü.{ek_mesaj}"
                else: veri["STRATEJİK YORUM"] = f"⚠️ YORGUNLUK: Trend iyi ama MACD negatife döndü."
            else: 
                if macd_al: veri["STRATEJİK YORUM"] = f"👀 TAKİP: Düzeltme bitiyor olabilir (MACD Al)."
                else: veri["STRATEJİK YORUM"] = f"⏳ DÜZELTME: Kısa vade satıcılı."

        return veri
    except Exception as e:
        return None

def analiz_motoru(hisse_listesi, progress_bar, status_text):
    sonuclar = []
    total = len(hisse_listesi)
    for i, hisse in enumerate(hisse_listesi):
        status_text.text(f"Analiz ediliyor: {hisse} ({i+1}/{total})")
        ham_veri = veri_cek_ve_hazirla(hisse)
        if ham_veri is not None:
            islenmis_veri = indikatorleri_hesapla(ham_veri, hisse)
            if islenmis_veri is not None:
                analiz = strateji_analizi(islenmis_veri, hisse)
                if analiz: sonuclar.append(analiz)
        progress_bar.progress((i + 1) / total)
    return pd.DataFrame(sonuclar)

# --- FORMATLAYICILAR ---
def format_yuzde(val):
    if pd.isna(val): return "-"
    renk = "🟢" if val >= 0 else "🔴"
    prefix = "+" if val >= 0 else ""
    return f"{renk} %{prefix}{val:.2f}"

column_settings = {
    "Fiyat": st.column_config.NumberColumn(format="%.2f"),
    "EMA(50)": st.column_config.NumberColumn(format="%.2f"),
    "EMA(100)": st.column_config.NumberColumn(format="%.2f"),
    "EMA(200)": st.column_config.NumberColumn(format="%.2f"),
    "STOP (G)": st.column_config.NumberColumn(format="%.2f"),
    "HEDEF (G)": st.column_config.NumberColumn(format="%.2f"),
    "RSI": st.column_config.NumberColumn(format="%.0f"),
}

# --- ARAYÜZ (4 SEKME) ---
tab1, tab2, tab3, tab4 = st.tabs(["💼 Portföyüm", "🏢 BIST 100", "🔥 Popüler Yan Tahtalar", "🌍 BIST Tüm Pazar"])

# 1. PORTFÖY
with tab1:
    st.subheader(f"Portföy Analizi ({len(st.session_state['portfoy_listesi'])} Hisse)")
    if st.button("🚀 Portföyümü Analiz Et", key="btn_portfoy"):
        prog = st.progress(0)
        stat = st.empty()
        df = analiz_motoru(st.session_state['portfoy_listesi'], prog, stat)
        if not df.empty:
            df = df.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
            st.session_state['sonuc_portfoy'] = df
        stat.text("Tamamlandı.")
        prog.progress(1.0)
    
    if st.session_state['sonuc_portfoy'] is not None:
        st.dataframe(st.session_state['sonuc_portfoy'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")

# 2. BIST 100
with tab2:
    st.subheader(f"BIST 100 Analizi ({len(BIST_100_LISTESI)} Hisse)")
    if st.button("🚀 BIST 100'ü Tara", key="btn_bist100"):
        prog = st.progress(0)
        stat = st.empty()
        df = analiz_motoru(BIST_100_LISTESI, prog, stat)
        if not df.empty:
            df = df.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
            st.session_state['sonuc_bist100'] = df
        stat.text("Tamamlandı.")
        prog.progress(1.0)
    
    if st.session_state['sonuc_bist100'] is not None:
        st.dataframe(st.session_state['sonuc_bist100'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")

# 3. POPÜLER YAN TAHTALAR (YENİ)
with tab3:
    st.subheader("🔥 Popüler Yan Tahtalar (BIST 100 Hariç - En Hacimli 50)")
    st.markdown("*Kriter: BIST 100'de olmayan ve şu an en yüksek hacme sahip 50 hisse.*")
    
    if st.button("Listeyi Çek ve Analiz Et", key="btn_yan"):
        with st.spinner("Piyasa taranıyor ve BIST 100 ayıklanıyor..."):
            # Hacme göre sıralı, BIST 100 olmayan ilk 50 hisseyi çek
            yan_liste = hisse_taramasi_yap(mod="hacim")
            st.session_state['yan_hisseler_listesi'] = yan_liste
        
        if yan_liste:
            st.info(f"Bulunan Popüler Hisseler: {', '.join([h.replace('.IS','') for h in yan_liste[:10]])} ... ve diğerleri.")
            prog = st.progress(0)
            stat = st.empty()
            df = analiz_motoru(yan_liste, prog, stat)
            if not df.empty:
                df = df.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
                st.session_state['sonuc_yan'] = df
            stat.text("Tamamlandı.")
            prog.progress(1.0)
    
    if st.session_state['sonuc_yan'] is not None:
        st.dataframe(st.session_state['sonuc_yan'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")

# 4. TÜM PAZAR
with tab4:
    st.subheader("🌍 BIST Tüm Pazar Analizi")
    st.warning("⚠️ 500+ Hisse taranır. Süre: 10-15 Dakika.")
    
    if st.button("1. Adım: Listeyi Çek", key="btn_tum_cek"):
        with st.spinner("Liste çekiliyor..."):
            liste = hisse_taramasi_yap(mod="tum")
            st.session_state['tum_hisseler_listesi'] = liste
            st.success(f"{len(liste)} hisse bulundu.")
            
    if st.session_state['tum_hisseler_listesi']:
        if st.button("2. Adım: Analizi Başlat", key="btn_tum_analiz"):
            prog = st.progress(0)
            stat = st.empty()
            df = analiz_motoru(st.session_state['tum_hisseler_listesi'], prog, stat)
            if not df.empty:
                df = df.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
                st.session_state['sonuc_tum'] = df
            stat.text("Bitti.")
            prog.progress(1.0)
            
        if st.session_state['sonuc_tum'] is not None:
            st.dataframe(st.session_state['sonuc_tum'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")
            
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                st.session_state['sonuc_tum'].to_excel(writer, index=False, sheet_name="Tum_BIST")
            st.download_button(label="📥 Tüm Raporu İndir", data=buffer, file_name="BIST_Full_Analiz.xlsx", mime="application/vnd.ms-excel")

