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
st.set_page_config(page_title="Portföy Analiz Botu V2", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu (EMA 50/100/200 + MACD)")
st.markdown("Bu uygulama, **V9.0 Stratejisi** (3'lü EMA + MACD + SuperTrend + RSI + Hacim) ile özel portföyünü tarar.")

# --- AYARLAR ---
HISSELER = [
    "TUPRS.IS", "ASTOR.IS", "DOAS.IS", 
    "MGROS.IS", "BIMAS.IS", "SOKM.IS", 
    "AKBNK.IS", "YKBNK.IS",
    "EDATA.IS", "RUBNS.IS", 
    "VESBE.IS", "SASA.IS", "TEHOL.IS",
    "ASELS.IS", "ISCTR.IS", "SAHOL.IS", "KCHOL.IS", "TCELL.IS", "ULKER.IS", "THYAO.IS", 
    "KLRHO.IS", "TERA.IS"
]

# --- FONKSİYONLAR ---
def veri_cek_ve_hazirla(sembol):
    try:
        # GÜNLÜK VERİ
        df_d = yf.download(sembol, period="2y", interval="1d", progress=False)
        if df_d.empty: return None
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        
        # HAFTALIK VERİ
        df_w = yf.download(sembol, period="5y", interval="1wk", progress=False)
        if df_w.empty: return None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        # 1. Haftalık SuperTrend (Trend Yönü İçin)
        st_w = ta.supertrend(df_w['High'], df_w['Low'], df_w['Close'], length=10, multiplier=3)
        if st_w is not None:
             df_w['ST_DEGER_W'] = st_w.iloc[:, 0]
             df_w['ST_YON_W'] = st_w.iloc[:, 1]
        else:
             df_w['ST_DEGER_W'] = 0
             df_w['ST_YON_W'] = 0

        # 2. Haftalık LRC (Uzun Vade Hedef)
        df_w['LRC_MID_W'] = ta.linreg(df_w['Close'], length=50)
        if df_w['LRC_MID_W'] is not None:
            stdev_w = df_w['Close'].rolling(window=50).std()
            df_w['LRC_UPPER_W'] = df_w['LRC_MID_W'] + (2 * stdev_w)
        else:
            df_w['LRC_UPPER_W'] = 0
             
        # Lookahead Bias Önlemi
        haftalik_sinyaller = df_w[['ST_YON_W', 'ST_DEGER_W', 'LRC_UPPER_W']].shift(1)
        
        # Birleştirme
        df_d.index = df_d.index.tz_localize(None)
        haftalik_sinyaller.index = haftalik_sinyaller.index.tz_localize(None)
        df_d = df_d.join(haftalik_sinyaller.reindex(df_d.index, method='ffill'))
        
        return df_d
    except Exception as e:
        return None

def indikatorleri_hesapla(df, sembol):
    try:
        # 1. EMA'lar (Günlük: 50, 100, 200)
        df['EMA_50_D'] = ta.ema(df['Close'], length=50)
        df['EMA_100_D'] = ta.ema(df['Close'], length=100)
        df['EMA_200_D'] = ta.ema(df['Close'], length=200)
        
        # 2. MACD (12, 26, 9)
        # pandas_ta macd sütunları döndürür: MACD_12_26_9, MACDh_12_26_9 (hist), MACDs_12_26_9 (signal)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # 3. SuperTrend GÜNLÜK
        st = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3)
        if st is not None:
            df['ST_DEGER_D'] = st.iloc[:, 0]
            df['ST_YON_D'] = st.iloc[:, 1]
        
        # 4. RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 5. Bollinger (Orta Bant)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            col_mid = [c for c in bb.columns if c.startswith('BBM')][0]
            df['BB_MID'] = bb[col_mid]
        
        # 6. LRC Kanalı GÜNLÜK
        df['LRC_MID_D'] = ta.linreg(df['Close'], length=50)
        stdev = df['Close'].rolling(window=50).std()
        df['LRC_UPPER_D'] = df['LRC_MID_D'] + (2 * stdev)

        # 7. Hacim Analizi
        df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_SMA20']
        
        return df
    except Exception as e:
        return None

def strateji_analizi(df, sembol):
    try:
        bugun = df.iloc[-1]
        fiyat = bugun['Close']
        
        if pd.isna(bugun.get('EMA_200_D')): return None

        # --- DEĞİŞKENLER ---
        ema_50 = bugun['EMA_50_D']
        ema_100 = bugun['EMA_100_D']
        ema_200 = bugun['EMA_200_D']
        
        st_deger_d = bugun['ST_DEGER_D']
        st_deger_w = bugun['ST_DEGER_W']
        
        st_yon_d = bugun['ST_YON_D']
        st_yon_w = bugun['ST_YON_W'] # 1: Yeşil (Al), -1: Kırmızı (Sat)
        rsi = bugun['RSI']
        
        # MACD Değerleri
        # Sütun isimleri pandas_ta varsayılanları:
        macd_val = bugun.get('MACD_12_26_9')
        macd_sig = bugun.get('MACDs_12_26_9')
        
        # MACD Sinyali (Value > Signal = AL)
        macd_al = macd_val > macd_sig
        
        # HEDEFLER
        hedef_gunluk = bugun['LRC_UPPER_D']
        hedef_haftalik = bugun['LRC_UPPER_W']
        bb_mid = bugun['BB_MID']

        # Hacim
        rvol = bugun['RVOL'] if not pd.isna(bugun['RVOL']) else 1.0
        hacim_ikon = "🔋" if rvol > 1.2 else ("🪫" if rvol < 0.8 else "▪️")
        
        # Temel Trend Kontrolleri
        fiyat_ema200_ustunde = fiyat > ema_200
        
        # Mesafeler
        bb_uzaklik = (fiyat - bb_mid) / fiyat
        tavan_uzaklik_d = (hedef_gunluk - fiyat) / fiyat
        st_uzaklik_d = abs((fiyat - st_deger_d) / fiyat)

        # Etiketler
        etiket_st_d = "🟢" if st_yon_d == 1 else "🔴"
        etiket_st_w = "🟢" if st_yon_w == 1 else "🔴"
        
        # MACD Etiketi
        macd_etiket = "🟢 AL" if macd_al else "🔴 SAT"

        # --- TABLO VERİSİ ---
        veri = {
            "Hisse": sembol.replace(".IS", ""),
            "Fiyat": round(fiyat, 2),
            "EMA(50)": round(ema_50, 2),
            "EMA(100)": round(ema_100, 2),
            "EMA(200)": round(ema_200, 2), # Eski Beton Zemin
            "MACD": macd_etiket,
            "RSI": round(rsi, 0),
            "Hacim": f"{hacim_ikon} %{int(rvol*100)}",
            "S.Trend(G)": etiket_st_d, 
            "S.Trend(H)": etiket_st_w,
            "STOP (G)": round(st_deger_d, 2),
            "HEDEF (G)": round(hedef_gunluk, 2), 
            "STRATEJİK YORUM": ""
        }

        # --- YORUM MANTIĞI (GÜNCELLENDİ) ---
        
        # SENARYO 1: EMA 200 ALTI (Ayı Piyasası / Düşen Bıçak)
        if not fiyat_ema200_ustunde:
            if rsi < 30:
                veri["STRATEJİK YORUM"] = "⚡ TEPKİ: EMA200 altı ama aşırı ucuz (RSI<30)."
            else:
                if macd_al:
                     veri["STRATEJİK YORUM"] = "🤔 DİKKAT: EMA200 altı ama MACD Al verdi. (Dip Dönüşü?)"
                else:
                    veri["STRATEJİK YORUM"] = "⛔ UZAK DUR: EMA200 (Beton) altındayız. Trend Negatif."

        # SENARYO 2: EMA 200 ÜSTÜ (Boğa Bölgesi)
        else:
            # 1. Kar Al Bölgesi
            if rsi > 70:
                veri["STRATEJİK YORUM"] = f"⚠️ KAR AL: RSI şişti ({rsi}). Düzeltme gelebilir."
            elif tavan_uzaklik_d < 0.02:
                 veri["STRATEJİK YORUM"] = f"🧱 DİRENÇTE: Kısa vade tavana ({round(hedef_gunluk,2)}) değdi."
            
            # 2. Trend Kontrolü (S.Trend Günlük + Haftalık)
            elif st_yon_d == 1: # Günlük Trend Pozitif
                ek_mesaj = " (Hacim Zayıf!)" if rvol < 0.8 else " (Hacim Güçlü🚀)" if rvol > 1.3 else ""
                
                if st_yon_w == 1: # Haftalık da Pozitif (Ralli Modu)
                    if not macd_al:
                        veri["STRATEJİK YORUM"] = f"⚠️ YORGUNLUK: Trend iyi ama MACD Sat'a döndü. Stoplu git."
                    else:
                        if 0 < bb_uzaklik < 0.03:
                            veri["STRATEJİK YORUM"] = f"✅ EKLEME: Ortalamalara yakın, trend güçlü.{ek_mesaj}"
                        else:
                            risk = round(st_uzaklik_d * 100, 1)
                            veri["STRATEJİK YORUM"] = f"⚖️ TUT/GİR: Stop Risk %{risk}. Yön yukarı.{ek_mesaj}"
                else:
                    veri["STRATEJİK YORUM"] = f"🤔 DİKKAT: Fiyat iyi ama Haftalık Ana Trend (ST) hala Kırmızı."
            
            # 3. Düzeltme Modu (Fiyat > EMA200 ama ST Kırmızı)
            else: 
                if macd_al:
                    veri["STRATEJİK YORUM"] = f"👀 TAKİP: Düzeltme bitiyor olabilir (MACD Al)."
                else:
                    veri["STRATEJİK YORUM"] = f"⏳ DÜZELTME: Kısa vade satıcılı. Destek: {round(st_deger_w,1)} TL."

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
        
        progress_bar.progress((i + 1) / total)

    status_text.text("Analiz Tamamlandı!")
    progress_bar.progress(1.0)

    df_sonuc = pd.DataFrame(sonuclar)

    if not df_sonuc.empty:
        # Sıralama: Önce Haftalık Trend, Sonra MACD Durumu (Yeşil üste)
        df_sonuc = df_sonuc.sort_values(by=["S.Trend(H)", "S.Trend(G)"], ascending=[False, False])
        
        st.success("✅ Rapor Hazır! (EMA 50/100/200 + MACD Dahil Edildi)")
        
        # Tabloyu Göster
        st.dataframe(df_sonuc, use_container_width=True, height=600)
        
        # Excel İndirme Butonu
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_sonuc.to_excel(writer, index=False, sheet_name="Portfoy_Raporu")
            
        st.download_button(
            label="📥 Excel Raporunu İndir",
            data=buffer,
            file_name="Portfoy_Analiz_Raporu_V9.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.error("❌ Veri çekilemedi. Lütfen daha sonra tekrar deneyiniz.")
