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
st.set_page_config(page_title="Portföy Analiz Botu", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu")
st.markdown("Bu uygulama, **V8.2 Stratejisi** (EMA + SuperTrend + RSI + Hacim) ile özel portföyünü tarar.")

# --- AYARLAR (Senin Dosyandan Birebir Alındı) ---
HISSELER = [
    "TUPRS.IS", "ASTOR.IS", "DOAS.IS", 
    "MGROS.IS", "BIMAS.IS", "SOKM.IS", 
    "AKBNK.IS", "YKBNK.IS",
    "EDATA.IS", "RUBNS.IS", 
    "VESBE.IS", "SASA.IS", "TEHOL.IS",
    "ASELS.IS", "ISCTR.IS", "SAHOL.IS", "KCHOL.IS", "TCELL.IS", "ULKER.IS", "THYAO.IS", 
    "KLRHO.IS", "TERA.IS"
]

# --- FONKSİYONLAR (Senin Kodundan Birebir Alındı) ---
def veri_cek_ve_hazirla(sembol):
    # Streamlit içinde print yerine arka planda işlem yapılır, loga yazmaz.
    try:
        # GÜNLÜK VERİ
        df_d = yf.download(sembol, period="2y", interval="1d", progress=False)
        if df_d.empty: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        # HAFTALIK VERİ
        df_w = yf.download(sembol, period="5y", interval="1wk", progress=False)
        if df_w.empty: return None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        # 1. Haftalık EMA
        df_w['EMA_100_W'] = ta.ema(df_w['Close'], length=100)
        
        # 2. Haftalık SuperTrend
        st_w = ta.supertrend(df_w['High'], df_w['Low'], df_w['Close'], length=10, multiplier=3)
        if st_w is not None:
             df_w['ST_DEGER_W'] = st_w.iloc[:, 0]
             df_w['ST_YON_W'] = st_w.iloc[:, 1]
        else:
             df_w['ST_DEGER_W'] = 0
             df_w['ST_YON_W'] = 0

        # 3. Haftalık LRC (Uzun Vade Hedef)
        df_w['LRC_MID_W'] = ta.linreg(df_w['Close'], length=50)
        # Haftalık standart sapma hesabı
        if df_w['LRC_MID_W'] is not None:
            stdev_w = df_w['Close'].rolling(window=50).std()
            df_w['LRC_UPPER_W'] = df_w['LRC_MID_W'] + (2 * stdev_w)
        else:
            df_w['LRC_UPPER_W'] = 0
             
        # Lookahead Bias Önlemi (Tüm haftalık verileri ötele)
        haftalik_sinyaller = df_w[['EMA_100_W', 'ST_YON_W', 'ST_DEGER_W', 'LRC_UPPER_W']].shift(1)
        
        # Birleştirme
        df_d.index = df_d.index.tz_localize(None)
        haftalik_sinyaller.index = haftalik_sinyaller.index.tz_localize(None)
        df_d = df_d.join(haftalik_sinyaller.reindex(df_d.index, method='ffill'))
        
        return df_d
    except Exception as e:
        return None

def indikatorleri_hesapla(df, sembol):
    try:
        # 1. EMA 200 (Günlük)
        df['EMA_200_D'] = ta.ema(df['Close'], length=200)
        
        # 2. SuperTrend GÜNLÜK
        st = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if st is not None:
            df['ST_DEGER_D'] = st.iloc[:, 0]
            df['ST_YON_D'] = st.iloc[:, 1]
        
        # 3. RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 4. Bollinger (Orta Bant)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            col_mid = [c for c in bb.columns if c.startswith('BBM')][0]
            df['BB_MID'] = bb[col_mid]
        
        # 5. LRC Kanalı GÜNLÜK (Kısa Vade Hedef)
        df['LRC_MID_D'] = ta.linreg(df['Close'], length=50)
        stdev = df['Close'].rolling(window=50).std()
        df['LRC_UPPER_D'] = df['LRC_MID_D'] + (2 * stdev)

        # --- YENİ EKLENEN: HACİM ANALİZİ ---
        # 20 Günlük Hacim Ortalaması
        df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
        # RVOL (Bugünkü Hacim / Ortalama Hacim)
        df['RVOL'] = df['Volume'] / df['Vol_SMA20']
        
        return df
    except Exception as e:
        return None

def strateji_analizi(df, sembol):
    try:
        bugun = df.iloc[-1]
        fiyat = bugun['Close']
        
        if pd.isna(bugun.get('EMA_100_W')) or pd.isna(bugun.get('EMA_200_D')): return None

        # --- DEĞİŞKENLER ---
        ema_gunluk = bugun['EMA_200_D']
        ema_haftalik = bugun['EMA_100_W']
        st_deger_d = bugun['ST_DEGER_D']
        st_deger_w = bugun['ST_DEGER_W']
        bb_mid = bugun['BB_MID']
        
        # HEDEFLER
        hedef_gunluk = bugun['LRC_UPPER_D']
        hedef_haftalik = bugun['LRC_UPPER_W']
        
        st_yon_d = bugun['ST_YON_D']
        st_yon_w = bugun['ST_YON_W']
        rsi = bugun['RSI']
        
        # --- YENİ HACİM DEĞİŞKENLERİ ---
        rvol = bugun['RVOL'] if not pd.isna(bugun['RVOL']) else 1.0
        hacim_ikon = "🔋" if rvol > 1.2 else ("🪫" if rvol < 0.8 else "▪️")
        
        gunluk_ema_pozitif = fiyat > ema_gunluk
        haftalik_ema_pozitif = fiyat > ema_haftalik
        
        # Mesafeler
        bb_uzaklik = (fiyat - bb_mid) / fiyat
        tavan_uzaklik_d = (hedef_gunluk - fiyat) / fiyat
        st_uzaklik_d = abs((fiyat - st_deger_d) / fiyat)

        # Etiketler
        etiket_st_d = "🟢" if st_yon_d == 1 else "🔴"
        etiket_st_w = "🟢" if st_yon_w == 1 else "🔴"
        
        # --- TABLO VERİSİ ---
        veri = {
            "Hisse": sembol.replace(".IS", "").replace("ALTIN", "ALTIN.S1"),
            "Fiyat": round(fiyat, 2),
            "EMA(G)": round(ema_gunluk, 2), 
            "EMA(H)": round(ema_haftalik, 2),
            "RSI": round(rsi, 0),
            "Hacim": f"{hacim_ikon} %{int(rvol*100)}",  # YENİ SÜTUN
            "S.Trend(G)": etiket_st_d, 
            "S.Trend(H)": etiket_st_w,
            "STOP (G)": round(st_deger_d, 2),
            "STOP (H)": round(st_deger_w, 2),
            "HEDEF (G)": round(hedef_gunluk, 2), 
            "HEDEF (H)": round(hedef_haftalik, 2),
            "STRATEJİK YORUM": ""
        }

        # --- YORUM MANTIĞI ---
        # SENARYO 1: TAM AYI
        if not gunluk_ema_pozitif and not haftalik_ema_pozitif:
            if rsi < 30:
                veri["STRATEJİK YORUM"] = "⚡ TEPKİ: Aşırı ucuz (RSI<30). Tepki gelebilir."
            else:
                fark = abs(round((fiyat - ema_gunluk)/fiyat*100, 1))
                if rvol > 1.5:
                    veri["STRATEJİK YORUM"] = f"⛔ CİDDİ SATIŞ: Hacimli düşüş var (%{int(rvol*100)}). Uzak dur."
                elif rvol < 0.6:
                    veri["STRATEJİK YORUM"] = f"👀 TAKİP: Düşüş hacimsizleşti, satıcılar yoruldu."
                else:
                    veri["STRATEJİK YORUM"] = f"⛔ UZAK DUR: EMA200 altındayız. Düşen bıçak."

        # SENARYO 2: TUZAK BÖLGESİ
        elif not gunluk_ema_pozitif and haftalik_ema_pozitif:
            if st_yon_w == 1:
                 veri["STRATEJİK YORUM"] = f"⚠️ KARAR ANI: Haftalık iyi ama Günlük kırık. Dönüş bekle."
            else:
                 veri["STRATEJİK YORUM"] = f"📉 ZAYIFLAMA: Momentum zayıf, trend negatife dönüyor."

        # SENARYO 3: TAM BOĞA
        elif gunluk_ema_pozitif and haftalik_ema_pozitif:
            # A. Aşırı Isınma
            if rsi > 70:
                veri["STRATEJİK YORUM"] = f"⚠️ KAR AL: RSI şişti ({rsi}) ve Hedefe yaklaştık."
            elif tavan_uzaklik_d < 0.02:
                 veri["STRATEJİK YORUM"] = f"🧱 DİRENÇTE: Günlük Tavan ({round(hedef_gunluk,2)}) görüldü."
            
            # C. Günlük ST YEŞİL
            elif st_yon_d == 1:
                if st_yon_w == 1:
                    # HACİM KONTROLÜ
                    ek_mesaj = " (Hacim Zayıf!)" if rvol < 0.8 else " (Hacim Güçlü🚀)" if rvol > 1.3 else ""
                    
                    if 0 < bb_uzaklik < 0.03:
                        veri["STRATEJİK YORUM"] = f"✅ EKLEME: Ortalamaya yakın, güvenli.{ek_mesaj}"
                    else:
                        risk = round(st_uzaklik_d * 100, 1)
                        veri["STRATEJİK YORUM"] = f"⚖️ GİRİŞ: Stop Risk %{risk}. Trend devam ediyor.{ek_mesaj}"
                else:
                    veri["STRATEJİK YORUM"] = f"🤔 DİKKAT: Fiyat iyi ama Haftalık ST Kırmızı."
            
            # D. Günlük ST KIRMIZI
            else: 
                 veri["STRATEJİK YORUM"] = f"⏳ DÜZELTME: Kısa vade satıcılı. Haftalık Destek: {round(st_deger_w,1)} TL."
        
        # SENARYO 4: TOPARLANMA
        else:
            veri["STRATEJİK YORUM"] = "🌤️ TOPARLANMA: Günlük düzeldi ama Haftalık direnç var."

        return veri
    except Exception as e:
        return None

# --- ARAYÜZ MANTIĞI ---
if st.button("🚀 Portföyümü Analiz Et"):
    st.info("Portföy verileri çekiliyor... Lütfen bekleyiniz.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    sonuclar = []
    
    total = len(HISSELER)
    
    for i, hisse in enumerate(HISSELER):
        status_text.text(f"Analiz ediliyor: {hisse} ({i+1}/{total})")
        
        ham_veri = veri_cek_ve_hazirla(hisse)
        if ham_veri is not None:
            islenmis_veri = indikatorleri_hesapla(ham_veri, hisse)
            if islenmis_veri is not None:
                analiz = strateji_analizi(islenmis_veri, hisse)
                if analiz: sonuclar.append(analiz)
        
        # İlerleme çubuğunu güncelle
        progress_bar.progress((i + 1) / total)

    status_text.text("Analiz Tamamlandı!")
    progress_bar.progress(1.0)

    df_sonuc = pd.DataFrame(sonuclar)

    if not df_sonuc.empty:
        # Sıralama: Önce Haftalık Trend, Sonra Günlük Trend
        df_sonuc = df_sonuc.sort_values(by=["S.Trend(H)", "S.Trend(G)"], ascending=[False, False])
        
        st.success("✅ Rapor Hazır!")
        
        # Tabloyu Göster
        st.dataframe(df_sonuc, use_container_width=True, height=600)
        
        # Excel İndirme Butonu
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_sonuc.to_excel(writer, index=False, sheet_name="Portfoy_Raporu")
            
        st.download_button(
            label="📥 Excel Raporunu İndir",
            data=buffer,
            file_name="Portfoy_Analiz_Raporu.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:

        st.error("❌ Veri çekilemedi. Lütfen daha sonra tekrar deneyiniz.")
