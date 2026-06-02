"""
TEFAS Yatırım Fonları Canlı Veri Çekme ve Analiz Modülü
TEFAS API'sinden tefasfon kütüphanesi aracılığıyla fonları dinamik çeker,
momentum skoru (0-100) ve trend sinyali ("GÜÇLÜ TREND", "NÖTR", "ZAYIF TREND") hesaplar.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import tefasfon

# Cache dosyası
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CACHE_FILE = os.path.join(_CACHE_DIR, "tefas_cache.json")
_CACHE_EXPIRY_HOURS = 12  # Fon fiyatları günde 1 kez açıklandığı için cache süresi
_HISTORY_CACHE_FILE = os.path.join(_CACHE_DIR, "tefas_history_cache.json")

def _load_history_cache():
    """Tarihsel verileri cache'den yükler."""
    try:
        if os.path.exists(_HISTORY_CACHE_FILE):
            with open(_HISTORY_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"  [UYARI] Fon geçmiş verileri cache'i yüklenemedi: {e}")
    return {}

def _save_history_cache(cache_data):
    """Tarihsel verileri cache'e kaydeder."""
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_HISTORY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [UYARI] Fon geçmiş verileri cache'i kaydedilemedi: {e}")

def _load_cache():
    """Cache dosyasından fon analizlerini yükler."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # Cache süresi kontrolü
            cached_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01"))
            if datetime.now() - cached_time < timedelta(hours=_CACHE_EXPIRY_HOURS):
                return cache_data.get("funds", [])
    except Exception as e:
        print(f"  [UYARI] Fon cache yüklenemedi: {e}")
    return None

def _save_cache(funds):
    """Fon analizlerini cache dosyasına kaydeder."""
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(funds),
            "funds": funds
        }
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [UYARI] Fon cache kaydedilemedi: {e}")

def _find_active_dates():
    """
    Kendi kendine iyileşen tarih bulucu.
    Bugünden başlayarak geriye doğru en güncel ve 7 gün önceki aktif işlem günlerini bulur.
    """
    print("[BILGI] TEFAS veri tarihleri sorgulanıyor...")
    
    # 1. En güncel aktif günü bul
    latest_dt = datetime.now()
    df_latest = None
    latest_date_str = ""
    
    for i in range(10):
        date_str = latest_dt.strftime("%d.%m.%Y")
        try:
            df = tefasfon.get_funds('SEC', date_str, date_str)
            if df is not None and len(df) > 100:
                df_latest = df
                latest_date_str = date_str
                print(f"  -> En güncel aktif gün bulundu: {latest_date_str} ({len(df_latest)} fon)")
                break
        except Exception:
            pass
        latest_dt -= timedelta(days=1)
        
    if df_latest is None:
        raise ValueError("Son 10 gün içinde TEFAS verisi bulunamadı.")
        
    # 2. 7 gün önceki aktif günü bul (1 haftalık getiri hesabı için)
    past_dt = latest_dt - timedelta(days=7)
    df_past = None
    past_date_str = ""
    
    for i in range(10):
        date_str = past_dt.strftime("%d.%m.%Y")
        try:
            df = tefasfon.get_funds('SEC', date_str, date_str)
            if df is not None and len(df) > 100:
                df_past = df
                past_date_str = date_str
                print(f"  -> 1 hafta önceki aktif gün bulundu: {past_date_str} ({len(df_past)} fon)")
                break
        except Exception:
            pass
        past_dt -= timedelta(days=1)
        
    return latest_date_str, df_latest, past_date_str, df_past

def fetch_and_analyze_funds(top_n=250, force_refresh=False):
    """
    Tüm TEFAS yatırım fonlarını canlı çekip analiz eder.
    
    Args:
        top_n (int): Portföy büyüklüğüne göre seçilecek fon sayısı.
        force_refresh (bool): Cache'i es geçip zorla güncelleme yapar.
        
    Returns:
        list: Analiz edilmiş fon listesi.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            print(f"[CACHE] Cache'den {len(cached)} TEFAS fonu yüklendi.")
            return cached
            
    try:
        # 1. Aktif tarihleri ve fon fiyat listelerini çek
        latest_date_str, df_latest, past_date_str, df_past = _find_active_dates()
        
        # 2. Güncel periyodik getirileri çek (RB basis)
        print("  -> TEFAS tarihsel getiri verileri indiriliyor...")
        df_returns = tefasfon.get_returns('SEC', 'RB')
        print(f"    [OK] {len(df_returns)} fonun getiri verileri alındı.")
        
        # 3. Veri setlerini birleştir
        # df_latest kolonları: ['fonKodu', 'fonUnvan', 'tarih', 'fiyat', 'tedPaySayisi', 'kisiSayisi', 'portfoyBuyukluk', 'borsaBultenFiyat']
        # df_returns kolonları: ['fonKodu', 'fonUnvan', 'fonTurAciklama', 'tefasDurum', 'getiri1a', 'getiri3a', 'getiri6a', 'getiri1y', 'getiriyb', 'getiri3y', 'getiri5y', 'getiriOrani', 'riskDegeri']
        
        # DataFrame birleştirmeleri
        df_latest = df_latest.set_index('fonKodu')
        df_returns = df_returns.set_index('fonKodu')
        
        # 1 hafta önceki fiyatları sözlük yapısına al
        past_prices = {}
        if df_past is not None:
            past_prices = dict(zip(df_past['fonKodu'], df_past['fiyat']))
            
        merged_list = []
        
        import math
        def _clean_val(v):
            try:
                fv = float(v)
                if math.isnan(fv) or math.isinf(fv):
                    return 0.0
                return fv
            except Exception:
                return 0.0

        for code, row in df_latest.iterrows():
            # Temel bilgiler
            name = row['fonUnvan']
            price = _clean_val(row['fiyat'])
            investors = int(row['kisiSayisi']) if row['kisiSayisi'] is not None and not pd.isna(row['kisiSayisi']) else 0
            
            # Portföy büyüklüğü (Milyon TL cinsinden formatlamak için 1,000,000'a böl)
            portfolio_val = _clean_val(row['portfoyBuyukluk'])
            
            # Getiri tablosundaki eşleşmeyi al
            category = "Diğer"
            daily_ret = 0.0
            ret_1m = 0.0
            ret_3m = 0.0
            ret_6m = 0.0
            ret_1y = 0.0
            risk_value = 3
            
            if code in df_returns.index:
                ret_row = df_returns.loc[code]
                category = ret_row['fonTurAciklama'] if 'fonTurAciklama' in df_returns.columns and pd.notna(ret_row['fonTurAciklama']) else "Diğer"
                daily_ret = _clean_val(ret_row['getiriOrani']) if 'getiriOrani' in df_returns.columns else 0.0
                ret_1m = _clean_val(ret_row['getiri1a']) if 'getiri1a' in df_returns.columns else 0.0
                ret_3m = _clean_val(ret_row['getiri3a']) if 'getiri3a' in df_returns.columns else 0.0
                ret_6m = _clean_val(ret_row['getiri6a']) if 'getiri6a' in df_returns.columns else 0.0
                ret_1y = _clean_val(ret_row['getiri1y']) if 'getiri1y' in df_returns.columns else 0.0
                
                try:
                    risk_val_raw = ret_row['riskDegeri']
                    risk_value = int(risk_val_raw) if pd.notna(risk_val_raw) else 3
                except Exception:
                    risk_value = 3
            
            # 1 haftalık getiriyi hesapla
            ret_1w = 0.0
            if code in past_prices:
                past_price = _clean_val(past_prices[code])
                if past_price > 0:
                    ret_1w = _clean_val(((price - past_price) / past_price) * 100.0)
            
            # Listeye ekle
            merged_list.append({
                "code": code,
                "name": name,
                "type": "Yatırım Fonu",
                "category": category,
                "price": price,
                "daily_return": daily_ret,
                "weekly_return": ret_1w,
                "monthly_return": ret_1m,
                "three_month_return": ret_3m,
                "six_month_return": ret_6m,
                "yearly_return": ret_1y,
                "portfolio_size": portfolio_val,
                "investor_count": investors,
                "risk_value": risk_value,
                "date": latest_date_str
            })
            
        if not merged_list:
            return []
            
        # 4. Portföy Büyüklüğüne göre sıralayıp en büyük N fonu filtreleme
        df_all = pd.DataFrame(merged_list)
        df_all = df_all.sort_values(by="portfolio_size", ascending=False)
        
        # En büyük top_n adedini seç (BYF'leri ve önemli fonları kaçırmamak için geniş tutulur)
        df_top = df_all.head(top_n).copy()
        
        # 5. Getiri Yüzdeliklerine (Percentile Rank) Göre Momentum Trend Skoru Hesaplama
        # Ağırlıklar: 1W: 0.15, 1M: 0.25, 3M: 0.30, 6M: 0.20, 1Y: 0.10
        weights = {
            "weekly_return": 0.15,
            "monthly_return": 0.25,
            "three_month_return": 0.30,
            "six_month_return": 0.20,
            "yearly_return": 0.10
        }
        
        # Yüzdelik dilimleri (Percentile Rank) hesapla
        percentiles = {}
        for col in weights.keys():
            # Yüzdelikleri 0-100 arasına çek
            percentiles[col] = df_top[col].rank(pct=True) * 100.0
            
        # Ağırlıklı skoru hesapla
        scores = pd.Series(0.0, index=df_top.index)
        weight_sum = pd.Series(0.0, index=df_top.index)
        
        for col, weight in weights.items():
            # Değeri 0 olmayan veya NaN olmayan fonların yüzdeliğini hesaba kat
            # Yeni fonlar için geçmiş yoksa NaN kalır, bunu ele alalım
            valid_mask = df_top[col].notna() & (df_top[col] != 0.0)
            scores.loc[valid_mask] += percentiles[col].loc[valid_mask] * weight
            weight_sum.loc[valid_mask] += weight
            
        # Ağırlıkları normalize et (Eksik verisi olan fonlar için)
        # Eğer hiçbir verisi yoksa veya ağırlık toplamı 0 ise varsayılan 50 ver
        final_scores = pd.Series(50.0, index=df_top.index)
        valid_weight_mask = weight_sum > 0
        final_scores.loc[valid_weight_mask] = scores.loc[valid_weight_mask] / weight_sum.loc[valid_weight_mask]
        
        # Skorları yuvarla
        df_top["score"] = final_scores.round(1)
        
        # 6. Sinyalleri ata
        # GÜÇLÜ TREND: score >= 70
        # NÖTR: 40 <= score < 70
        # ZAYIF TREND: score < 40
        def get_signal(score):
            if score >= 70:
                return "GÜÇLÜ TREND"
            elif score >= 40:
                return "NÖTR"
            else:
                return "ZAYIF TREND"
                
        df_top["signal"] = df_top["score"].apply(get_signal)
        
        # Sözlük listesine geri dönüştür
        result_funds = df_top.to_dict(orient="records")
        
        # Cache'e kaydet
        _save_cache(result_funds)
        print(f"[OK] {len(result_funds)} adet TEFAS fonu başarıyla analiz edildi ve kaydedildi.")
        return result_funds
        
    except Exception as e:
        print(f"[HATA] TEFAS fon analizi yapılamadı: {e}")
        # Can simidi: Hata durumunda cache'de ne varsa onu döndür
        try:
            if os.path.exists(_CACHE_FILE):
                print("  -> [CAN SİMİDİ] Hata nedeniyle eski cache verileri yükleniyor...")
                with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                return cache_data.get("funds", [])
        except Exception as cache_err:
            print(f"  [UYARI] Can simidi cache de yüklenemedi: {cache_err}")
            
        import traceback
        traceback.print_exc()
        return []

def get_fund_historical_data(fund_code, days=90):
    """
    Belirli bir fonun tarihsel fiyatlarını ve hacimlerini detay sayfasında çizdirmek için çeker.
    
    Args:
        fund_code (str): Fon kodu (örn: AFT, YAS)
        days (int): Geriye dönük kaç günlük veri çekileceği.
        
    Returns:
        list: Tarihsel fiyat noktaları [{"date": "YYYY-MM-DD", "price": 12.3}, ...]
    """
    # 1. Cache kontrolü
    cache = _load_history_cache()
    fund_cache = cache.get(fund_code)
    
    if fund_cache:
        cached_time = datetime.fromisoformat(fund_cache.get("timestamp", "2000-01-01"))
        cached_days = fund_cache.get("days", 0)
        
        # Eğer cache 12 saatten yeniyse ve istenen gün sayısı cached gün sayısından küçük veya eşitse cache'den kullan
        if datetime.now() - cached_time < timedelta(hours=_CACHE_EXPIRY_HOURS) and cached_days >= days:
            cached_data = fund_cache.get("data", [])
            if cached_data:
                # İstenen gün sayısına göre son verileri filtrele
                limit_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                filtered_data = [d for d in cached_data if d.get("date") >= limit_date]
                print(f"[CACHE] {fund_code} için {len(filtered_data)} adet tarihsel veri cache'den yüklendi.")
                return filtered_data
                
    # 2. Cache yoksa veya eskiyse TEFAS'tan çek
    print(f"[BILGI] {fund_code} için canlı tarihsel veri çekiliyor (Son {days} gün)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_date_str = start_date.strftime("%d.%m.%Y")
    end_date_str = end_date.strftime("%d.%m.%Y")
    
    try:
        df = tefasfon.get_funds('SEC', start_date_str, end_date_str, fund_codes=[fund_code])
        if df is not None and not df.empty:
            # Tarihe göre sırala
            df = df.sort_values(by="tarih")
            # Tarih formatını standartlaştır
            df['date_parsed'] = pd.to_datetime(df['tarih'], errors='coerce')
            df = df.dropna(subset=['date_parsed']).sort_values(by="date_parsed")
            
            import math
            def _clean_val(v):
                try:
                    fv = float(v)
                    if math.isnan(fv) or math.isinf(fv):
                        return 0.0
                    return fv
                except Exception:
                    return 0.0

            history = []
            for _, row in df.iterrows():
                history.append({
                    "date": row['date_parsed'].strftime("%Y-%m-%d"),
                    "price": _clean_val(row['fiyat']),
                    "investor_count": int(row['kisiSayisi']) if 'kisiSayisi' in row and row['kisiSayisi'] is not None and not pd.isna(row['kisiSayisi']) else 0,
                    "portfolio_size": _clean_val(row['portfoyBuyukluk']) if 'portfoyBuyukluk' in row else 0.0
                })
                
            # Cache'e kaydet
            cache[fund_code] = {
                "timestamp": datetime.now().isoformat(),
                "days": days,
                "data": history
            }
            _save_history_cache(cache)
            return history
    except Exception as e:
        print(f"[UYARI] {fund_code} için geçmiş veriler çekilemedi: {e}")
        
    # Hata durumunda cache'de eski veri varsa onu can simidi olarak döndür
    if fund_cache:
        print(f"[UYARI] TEFAS hatası nedeniyle {fund_code} için eski cache verisi kullanılıyor.")
        return fund_cache.get("data", [])
        
    return []
