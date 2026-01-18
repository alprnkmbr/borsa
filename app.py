import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import warnings
import json
import os
from io import BytesIO

# Uyarıları kapat
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Portföy Analiz Botu V11", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu (Yönetilebilir Mod)")
st.markdown("Bu uygulama, **V16.1 Stratejisi** ile portföyünü ve piyasayı **isteğe bağlı** olarak tarar.")

# --- DOSYA YÖNETİMİ (PORTFÖY KAYIT) ---
PORTFOY_DOSYASI = "portfoy.json"

def portfoy_yukle():
    if os.path.exists(PORTFOY_DOSYASI):
        with open(PORTFOY_DOSYASI, "r") as f:
            return json.load(f)
    return ["TUPRS.IS", "ASTOR.IS", "DOAS.IS", "MGROS.IS", "BIMAS.IS", "SOKM.IS", "AKBNK.IS", "YKBNK.IS", "EDATA.IS", "RUBNS.IS", "VESBE.IS", "TEHOL.IS"] # Varsayılan

def portfoy_kaydet(liste):
    with open(PORTFOY_DOSYASI, "w") as f:
        json.dump(liste, f)

# Session State Başlangıcı
if 'portfoy_listesi' not in st.session_state:
    st.session_state['portfoy_listesi'] = portfoy_yukle()

if 'sonuc_portfoy' not in st.session_state:
    st.session_state['sonuc_portfoy'] = None
if 'sonuc_bist100' not in st.session_state:
    st.session_state['sonuc_bist100'] = None
if 'sonuc_tum' not in st.session_state:
    st.session_state['sonuc_tum'] = None

# --- BIST LİSTELERİ ---
BIST_100_LISTESI = [
 "AEFES.IS", "AGHOL.IS", "AGROT.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS",
 "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "BAGFS.IS", "BERA.IS", "BIENP.IS", 
 "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS",
 "CWENE.IS", "DOAS.IS", "DOHOL.IS", "EBEBK.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", 
 "EREGL.IS", "EUPWR.IS", "EUREN.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GSRAY.IS", "GUBRF.IS", 
 "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KAYSE.IS", "KCAER.IS",
 "KCHOL.IS", "KLRHO.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "MAVI.IS",
 "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PEKGY.IS", "PETKM.IS", "PGSUS.IS", "QUAGR.IS", "RALYH.IS",
 "REEDR.IS", "SAHOL.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS",
 "TARKM.IS", "TATEN.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TRALT.IS", "TRENJ.IS", "TRMET.IS",
 "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUPRS.IS", "TURSG.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", 
 "YEOTK.IS", "YKBNK.IS", "YYLGD.IS", "ZOREN.IS"
]

BIST_DIGER_LISTESI = [
    "TERA.IS", "TEHOL.IS", "EDATA.IS", "RUBNS.IS", "KLRHO.IS", "TURSG.IS", "ANHYT.IS", "ANSGR.IS", 
    "TRGYO.IS", "HLGYO.IS", "OZKGY.IS", "GSDHO.IS", "IHLAS.IS", "NETAS.IS", "LOGO.IS", "KAREL.IS",
    "PARSN.IS", "TMSN.IS", "KATMR.IS", "PRKME.IS", "NATEN.IS", "ESEN.IS", "MAGEN.IS", "HUNER.IS",
    "KFEIN.IS", "LINK.IS", "ARDYZ.IS", "FONET.IS", "VBTYZ.IS", "ONCSM.IS", "SDTTR.IS", "TETMT.IS",
    "DOCO.IS", "CLEBI.IS", "AYGAZ.IS", "TRCAS.IS", "DEVA.IS", "SELEC.IS", "MPARK.IS", "LKMNH.IS"
]
BIST_DIGER_LISTESI = [h for h in BIST_DIGER_LISTESI if h not in BIST_100_LISTESI]


# --- SİDEBAR: PORTFÖY YÖNETİMİ ---
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

# --- ARAYÜZ ---
tab1, tab2, tab3 = st.tabs(["💼 Portföyüm", "🏢 BIST 100", "📈 BIST Tüm / Yan Tahtalar"])

# 1. SEKME: PORTFÖYÜM
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
        # GÜNCELLENEN KISIM: width="stretch"
        st.dataframe(st.session_state['sonuc_portfoy'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")

# 2. SEKME: BIST 100
with tab2:
    st.subheader(f"BIST 100 Analizi ({len(BIST_100_LISTESI)} Hisse)")
    st.info("⚠️ Tüm listeyi taramak 2-3 dakika sürebilir.")
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
        # GÜNCELLENEN KISIM: width="stretch"
        st.dataframe(st.session_state['sonuc_bist100'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")

# 3. SEKME: TÜM / YAN TAHTALAR
with tab3:
    st.subheader(f"Yan Tahtalar ve Diğerleri ({len(BIST_DIGER_LISTESI)} Hisse)")
    st.warning("⚠️ Bu liste geniştir, tarama süresi uzayabilir.")
    if st.button("🚀 Diğer Hisseleri Tara", key="btn_tum"):
        prog = st.progress(0)
        stat = st.empty()
        df = analiz_motoru(BIST_DIGER_LISTESI, prog, stat)
        if not df.empty:
            df = df.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
            st.session_state['sonuc_tum'] = df
        stat.text("Tamamlandı.")
        prog.progress(1.0)
    
    if st.session_state['sonuc_tum'] is not None:
        # GÜNCELLENEN KISIM: width="stretch"
        st.dataframe(st.session_state['sonuc_tum'].style.format({"1H Değ.": format_yuzde, "1A Değ.": format_yuzde}), column_config=column_settings, width="stretch")
