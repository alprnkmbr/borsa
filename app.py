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
st.set_page_config(page_title="Portföy Analiz Botu V3", page_icon="📊", layout="wide")

st.title("📊 Kişisel Portföy Analiz Raporu (Sadeleştirilmiş)")
st.markdown("Bu uygulama, **V10.0 Stratejisi** (3'lü EMA + MACD + Günlük SuperTrend + RSI + Hacim) ile analiz yapar.")

# --- AYARLAR ---
HISSELER = [
    "TUPRS.IS", "ASTOR.IS", "DOAS.IS", 
    "MGROS.IS", "BIMAS.IS", "SOKM.IS", 
    "AKBNK.IS", "YKBNK.IS",
    "EDATA.IS", "RUBNS.IS", 
    "VESBE.IS", "TEHOL.IS",
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
        
        # HAFTALIK VERİ (Sadece Hedef Kanalı İçin Tutuyoruz)
        df_w = yf.download(sembol, period="5y", interval="1wk", progress=False)
        if df_w.empty: return None
        if isinstance(df_w.columns, pd.MultiIndex): df_w.columns = df_w.columns.get_level_values(0)
        
        # Haftalık LRC (Uzun Vade Hedef)
        df_w['LRC_MID_W'] = ta.linreg(df_w['Close'], length=50)
        if df_w['LRC_MID_W'] is not None:
            stdev_w = df_w['Close'].rolling(window=50).std()
            df_w['LRC_UPPER_W'] = df_w['LRC_MID_W'] + (2 * stdev_w)
        else:
            df_w['LRC_UPPER_W'] = 0
             
        # Lookahead Bias Önlemi
        haftalik_sinyaller = df_w[['LRC_UPPER_W']].shift(1)
        
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
        st_yon_d = bugun['ST_YON_D'] # 1: Yeşil (Al), -1: Kırmızı (Sat)
        rsi = bugun['RSI']
        
        # MACD Değerleri
        macd_val = bugun.get('MACD_12_26_9')
        macd_sig = bugun.get('MACDs_12_26_9')
        macd_al = macd_val > macd_sig
        
        # HEDEFLER
        hedef_gunluk = bugun['LRC_UPPER_D']
        hedef_haftalik = bugun['LRC_UPPER_W'] # Hala hedef için tutuyoruz
        bb_mid = bugun['BB_MID']

        # Hacim
        rvol = bugun['RVOL'] if not pd.isna(bugun['RVOL']) else 1.0
        hacim_ikon = "🔋" if rvol > 1.2 else ("🪫" if rvol < 0.8 else "▪️")
        
        # ANA TREND KONTROLÜ (SuperTrend H Yerine EMA 200)
        fiyat_ema200_ustunde = fiyat > ema_200
        
        # Mesafeler
        bb_uzaklik = (fiyat - bb_mid) / fiyat
        tavan_uzaklik_d = (hedef_gunluk - fiyat) / fiyat
        st_uzaklik_d = abs((fiyat - st_deger_d) / fiyat)

        # Etiketler
        etiket_st_d = "🟢" if st_yon_d == 1 else "🔴"
        macd_etiket = "🟢 AL" if macd_al else "🔴 SAT"

        # --- TABLO VERİSİ ---
        veri = {
            "Hisse": sembol.replace(".IS", ""),
            "Fiyat": round(fiyat, 2),
            "EMA(50)": round(ema_50, 2),
            "EMA(100)": round(ema_100, 2),
            "EMA(200)": round(ema_200, 2), 
            "MACD": macd_etiket,
            "RSI": round(rsi, 0),
            "Hacim": f"{hacim_ikon} %{int(rvol*100)}",
            "S.Trend(G)": etiket_st_d, 
            "STOP (G)": round(st_deger_d, 2),
            "HEDEF (G)": round(hedef_gunluk, 2), 
            "STRATEJİK YORUM": ""
        }

        # --- YORUM MANTIĞI (SADELEŞTİRİLMİŞ) ---
        
        # SENARYO 1: EMA 200 ALTI (Ayı Piyasası)
        if not fiyat_ema200_ustunde:
            if rsi < 30:
                veri["STRATEJİK YORUM"] = "⚡ TEPKİ: EMA200 altı ama aşırı ucuz (RSI<30)."
            elif macd_al and st_yon_d == 1:
                 veri["STRATEJİK YORUM"] = "🚀 DİP DÖNÜŞÜ?: EMA200 altı ama ST ve MACD Al verdi. Riskli alım."
            else:
                veri["STRATEJİK YORUM"] = "⛔ UZAK DUR: Fiyat EMA200 altında. Trend Negatif."

        # SENARYO 2: EMA 200 ÜSTÜ (Boğa Bölgesi)
        else:
            # 1. Kar Al Bölgesi
            if rsi > 70:
                veri["STRATEJİK YORUM"] = f"⚠️ KAR AL: RSI şişti ({rsi}). Düzeltme gelebilir."
            elif tavan_uzaklik_d < 0.02:
                 veri["STRATEJİK YORUM"] = f"🧱 DİRENÇTE: Kısa vade tavana ({round(hedef_gunluk,2)}) değdi."
            
            # 2. Trend Kontrolü (S.Trend Günlük + MACD)
            elif st_yon_d == 1: # Günlük Trend Pozitif
                ek_mesaj = " (Hacim Zayıf!)" if rvol < 0.8 else " (Hacim Güçlü🚀)" if rvol > 1.3 else ""
                
                if macd_al:
                    # En Güçlü Senaryo: Fiyat > EMA200 + ST Yeşil + MACD Al
                    if 0 < bb_uzaklik < 0.03:
                        veri["STRATEJİK YORUM"] = f"✅ EKLEME: Ortalamalara yakın, tam yol ileri.{ek_mesaj}"
                    else:
                        risk = round(st_uzaklik_d * 100, 1)
                        veri["STRATEJİK YORUM"] = f"⚖️ GİRİŞ/TUT: Stop Risk %{risk}. Trend çok güçlü.{ek_mesaj}"
                else:
                    # Trend Yeşil ama MACD Sat (Yorgunluk)
                    veri["STRATEJİK YORUM"] = f"⚠️ YORGUNLUK: Trend yukarı ama MACD negatife döndü. Temkinli ol."
            
            # 3. Düzeltme Modu (Fiyat > EMA200 ama ST Kırmızı)
            else: 
                if macd_al:
                    veri["STRATEJİK YORUM"] = f"👀 TAKİP: Düzeltme bitiyor olabilir (MACD Al)."
                else:
                    veri["STRATEJİK YORUM"] = f"⏳ DÜZELTME: Kısa vade satıcılı. EMA200'e çekilme olabilir."

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
        # Sıralama: Önce EMA 200 Üstünde olanlar, Sonra Günlük ST, Sonra MACD
        df_sonuc = df_sonuc.sort_values(by=["S.Trend(G)", "RSI"], ascending=[False, False])
        
        st.success("✅ Rapor Hazır! (Haftalık ST Kaldırıldı, Odak EMA 200)")
        
        # Tabloyu Göster
        st.dataframe(df_sonuc, use_container_width=True, height=600)
        
        # Excel İndirme Butonu
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_sonuc.to_excel(writer, index=False, sheet_name="Portfoy_Raporu")
            
        st.download_button(
            label="📥 Excel Raporunu İndir",
            data=buffer,
            file_name="Portfoy_Analiz_Raporu_V10.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.error("❌ Veri çekilemedi. Lütfen daha sonra tekrar deneyiniz.")

