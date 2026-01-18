import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import warnings
from io import BytesIO

# Uyarıları kapat
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Portföy Analiz Botu V8", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu (Ayrıştırılmış & Formatlı)")
st.markdown("Bu uygulama, **V15.0 Stratejisi** (Portföy/Piyasa Ayrımı + 2 Basamak Hassasiyet) ile analiz yapar.")

# --- KULLANICI AYARLARI (HİSSELERİ BURADAN YÖNET) ---

# 1. SENİN PORTFÖYÜN (Elimde Var Dediklerin)
PORTFOY = [
    "TUPRS.IS", "ASTOR.IS", "DOAS.IS", 
    "MGROS.IS", "BIMAS.IS", "SOKM.IS", 
    "AKBNK.IS", "YKBNK.IS",
    "EDATA.IS", "RUBNS.IS", 
    "VESBE.IS", "TEHOL.IS",
]

# 2. GENEL TAKİP LİSTESİ (Piyasa / BIST 100 vb.)
GENEL_TAKIP = [
"AEFES.IS", "AGHOL.IS", "AGROT.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "BAGFS.IS", "BERA.IS", "BIENP.IS", "BIMAS.IS", "BIOEN.IS", "BOBET.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "EBEBK.IS", "ECILC.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "EUREN.IS", "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GSRAY.IS", "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KAYSE.IS", "KCAER.IS", "KCHOL.IS", "KLRHO.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PEKGY.IS", "PETKM.IS", "PGSUS.IS", "QUAGR.IS", "RALYH.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TARKM.IS", "TATEN.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TRALT.IS", "TRENJ.IS", "TRMET.IS", "TSKB.IS", "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUPRS.IS", "TURSG.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "YYLGD.IS", "ZOREN.IS"
]

# İki listeyi birleştirip tek seferde tarıyoruz (Mükerrerleri önlemek için set kullanıyoruz)
TUM_HISSELER = list(set(PORTFOY + GENEL_TAKIP))

# --- FONKSİYONLAR ---
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

        # --- TABLO VERİSİ ---
        # Sayısal değerleri olduğu gibi (float) bırakıyoruz, Streamlit config ile formatlayacağız.
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

        # --- YORUM MANTIĞI ---
        if not fiyat_ema200_ustunde:
            if rsi < 30:
                veri["STRATEJİK YORUM"] = "⚡ TEPKİ: EMA200 altı ama aşırı ucuz (RSI<30)."
            elif macd_al and st_yon_d == 1:
                 veri["STRATEJİK YORUM"] = "🚀 DİP DÖNÜŞÜ?: Riskli ama göstergeler düzeliyor."
            else:
                veri["STRATEJİK YORUM"] = "⛔ UZAK DUR: Trend Negatif (EMA200 Altı)."
        else:
            if rsi > 70:
                veri["STRATEJİK YORUM"] = f"⚠️ KAR AL: RSI şişti ({int(rsi)}). Düzeltme yakındır."
            elif tavan_uzaklik_d < 0.02:
                 veri["STRATEJİK YORUM"] = f"🧱 DİRENÇTE: Hedefe ({round(hedef_gunluk,2)}) değdi."
            elif st_yon_d == 1: 
                ek_mesaj = " (Hacim Zayıf!)" if rvol < 0.8 else " (Hacim Güçlü🚀)" if rvol > 1.3 else ""
                if macd_al:
                    if 0 < bb_uzaklik < 0.03:
                        veri["STRATEJİK YORUM"] = f"✅ EKLEME: Ortalamalara yakın, tam yol ileri.{ek_mesaj}"
                    else:
                        risk = round(st_uzaklik_d * 100, 1)
                        veri["STRATEJİK YORUM"] = f"⚖️ GİRİŞ/TUT: Stop Risk %{risk}. Trend güçlü.{ek_mesaj}"
                else:
                    veri["STRATEJİK YORUM"] = f"⚠️ YORGUNLUK: Trend iyi ama MACD negatife döndü."
            else: 
                if macd_al:
                    veri["STRATEJİK YORUM"] = f"👀 TAKİP: Düzeltme bitiyor olabilir (MACD Al)."
                else:
                    veri["STRATEJİK YORUM"] = f"⏳ DÜZELTME: Kısa vade satıcılı. EMA200'e çekilme beklenebilir."

        return veri
    except Exception as e:
        return None

# --- FORMATLAYICI (Görsel Ayarlar) ---
# Yüzdelik değişimleri renklendiren ve formatlayan fonksiyon
def format_yuzde(val):
    if pd.isna(val): return "-"
    renk = "🟢" if val >= 0 else "🔴"
    prefix = "+" if val >= 0 else ""
    return f"{renk} %{prefix}{val:.2f}"

# Streamlit Column Config ayarları (Sayıları 2 basamaklı göstermek için)
column_settings = {
    "Fiyat": st.column_config.NumberColumn(format="%.2f"),
    "EMA(50)": st.column_config.NumberColumn(format="%.2f"),
    "EMA(100)": st.column_config.NumberColumn(format="%.2f"),
    "EMA(200)": st.column_config.NumberColumn(format="%.2f"),
    "STOP (G)": st.column_config.NumberColumn(format="%.2f"),
    "HEDEF (G)": st.column_config.NumberColumn(format="%.2f"),
    "RSI": st.column_config.NumberColumn(format="%.0f"), # RSI tam sayı olsun
}

# --- ARAYÜZ MANTIĞI ---
if st.button("🚀 Portföyümü Analiz Et"):
    st.info("Portföy verileri çekiliyor... Lütfen bekleyiniz.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    sonuclar = []
    
    total = len(TUM_HISSELER)
    
    for i, hisse in enumerate(TUM_HISSELER):
        status_text.text(f"Analiz ediliyor: {hisse} ({i+1}/{total})")
        
        ham_veri = veri_cek_ve_hazirla(hisse)
        if ham_veri is not None:
            islenmis_veri = indikatorleri_hesapla(ham_veri, hisse)
            if islenmis_veri is not None:
                analiz = strateji_analizi(islenmis_veri, hisse)
                if analiz: sonuclar.append(analiz)
        
        progress_bar.progress((i + 1) / total)

    status_text.text("Analiz Tamamlandı!")
    progress_bar.progress(1.0)

    df_sonuc = pd.DataFrame(sonuclar)

    if not df_sonuc.empty:
        # 1. Genel Sıralama
        df_sonuc = df_sonuc.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
        
        # 2. Listeleri Ayrıştır
        # Portföydeki hisseleri bul
        # (Listenin sonundaki .IS ekini kaldırarak karşılaştırma yapıyoruz)
        portfoy_clean = [h.replace(".IS", "") for h in PORTFOY]
        
        df_portfoyum = df_sonuc[df_sonuc['Hisse'].isin(portfoy_clean)]
        df_genel = df_sonuc[~df_sonuc['Hisse'].isin(portfoy_clean)]
        
        st.success("✅ Rapor Hazır! (Sekmelerden portföyünü veya genel piyasayı seçebilirsin)")
        
        # --- SEKMELER (TABS) ---
        tab1, tab2 = st.tabs(["💼 Portföyüm", "🌍 Genel Takip Listesi"])
        
        with tab1:
            st.subheader(f"Senin Portföyün ({len(df_portfoyum)} Hisse)")
            if not df_portfoyum.empty:
                st.dataframe(
                    df_portfoyum.style.format({
                        "1H Değ.": format_yuzde,
                        "1A Değ.": format_yuzde
                    }),
                    column_config=column_settings, # Format ayarlarını burada uyguluyoruz
                    use_container_width=True, 
                    height=400
                )
            else:
                st.info("Portföy listendeki hisselerden veri gelmedi veya liste boş.")

        with tab2:
            st.subheader(f"Genel Piyasa Takibi ({len(df_genel)} Hisse)")
            if not df_genel.empty:
                st.dataframe(
                    df_genel.style.format({
                        "1H Değ.": format_yuzde,
                        "1A Değ.": format_yuzde
                    }),
                    column_config=column_settings, # Format ayarlarını burada uyguluyoruz
                    use_container_width=True, 
                    height=600
                )
            else:
                st.info("Genel takip listesi boş.")
        
        # EXCEL İNDİRME (Tümünü İndirir)
        df_excel = df_sonuc.copy()
        df_excel["1H Değ."] = df_excel["1H Değ."].apply(format_yuzde)
        df_excel["1A Değ."] = df_excel["1A Değ."].apply(format_yuzde)
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="Tum_Liste")
            if not df_portfoyum.empty:
                df_portfoyum.to_excel(writer, index=False, sheet_name="Portfoyum")
            
        st.download_button(
            label="📥 Excel Raporunu İndir (Tümü)",
            data=buffer,
            file_name="Portfoy_Analiz_Raporu_V15.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.error("❌ Veri çekilemedi. Lütfen daha sonra tekrar deneyiniz.")

