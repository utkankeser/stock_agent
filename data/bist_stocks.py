"""
BIST Hisse Senedi ve Fon Listesi - Dinamik
isyatirim.com.tr API'sinden tüm BIST hisseleri otomatik çeker.
Ardından yfinance ile işlem hacimlerini bulk olarak indirerek hacme göre sıralar.
Çekilen veriler yerel cache dosyasına kaydedilir.
"""

import requests
import json
import os
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# Cache dosyası (aynı dizinde)
_CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE_FILE = os.path.join(_CACHE_DIR, "stocks_cache.json")
_CACHE_EXPIRY_HOURS = 24  # Cache 24 saat geçerli

# Bellekteki hisse listesi ve sıralanmış ticker'lar
_stocks = {}
_sorted_tickers = []
_sectors = []


def _fetch_from_isyatirim():
    """
    isyatirim.com.tr API'sinden tüm BIST hisselerini çeker.
    
    Returns:
        dict: {ticker: {name, sector}} formatında hisse listesi
    """
    stocks = {}
    
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Yöntem 1: IS Yatırım hisse listesini çek
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Tablo satırlarından hisseleri çek
            table = soup.find("table", {"id": "summaryBasicData"}) or soup.find("table", {"id": "teikiTablo"})
            if table:
                rows = table.find("tbody")
                if not rows:
                    rows = table
                if rows:
                    for tr in rows.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 2:
                            code = tds[0].get_text(strip=True)
                            name = tds[1].get_text(strip=True) if len(tds) > 1 else code
                            sector = tds[2].get_text(strip=True) if len(tds) > 2 else "Diğer"
                            if code and code.isalnum() and 2 <= len(code) <= 7:
                                ticker = f"{code}.IS"
                                stocks[ticker] = {
                                    "name": name,
                                    "sector": sector
                                }
    except Exception as e:
        print(f"  [UYARI] isyatirim.com.tr'den veri çekilemedi: {e}")
    
    # Yöntem 2: isyatirim hisse arama API'si
    if len(stocks) < 50:
        try:
            api_url = "https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/Data.aspx/HissseSpi498"
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        code = item.get("HISSE_KODU", item.get("kod", ""))
                        name = item.get("HISSE_ADI", item.get("ad", code))
                        sector = item.get("SEKTOR", item.get("sektor", "Diğer"))
                        if code:
                            ticker = f"{code}.IS"
                            if ticker not in stocks:
                                stocks[ticker] = {"name": name, "sector": sector}
        except Exception:
            pass
    
    return stocks


def _fetch_stock_codes_from_web():
    """
    Finans sitelerinden BIST hisse kodlarını toplar.
    """
    stocks = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Kaynak 1: bigpara.hurriyet.com.tr tüm hisseler sayfası
    try:
        url = "https://bigpara.hurriyet.com.tr/borsa/canli-borsa/"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Hisse tablosundan verileri çek
            rows = soup.select("ul.sortList li, table tbody tr, div.tBody ul li")
            for row in rows:
                code_el = row.select_one("a, span.hisseKodu, .col1 span, a.hisselink")
                if code_el:
                    text = code_el.get_text(strip=True)
                    if text and 2 <= len(text) <= 6 and text.isalpha() and text.isupper():
                        ticker = f"{text}.IS"
                        if ticker not in stocks:
                            name_el = row.select_one(".col2, td:nth-child(2)")
                            name = name_el.get_text(strip=True) if name_el else text
                            stocks[ticker] = {
                                "name": name if name != text else text,
                                "sector": "Bilinmiyor"
                            }
    except Exception as e:
        print(f"    [UYARI] bigpara'dan çekilemedi: {e}")
    
    # Kaynak 2: getmidas.com
    try:
        url2 = "https://www.getmidas.com/canli-borsa/tum-hisseler"
        resp2 = requests.get(url2, headers=headers, timeout=15)
        if resp2.status_code == 200:
            from bs4 import BeautifulSoup
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            
            links = soup2.select("a[href*='/canli-borsa/']")
            for link in links:
                text = link.get_text(strip=True)
                if text and 2 <= len(text) <= 6 and text.isalpha() and text.isupper():
                    ticker = f"{text}.IS"
                    if ticker not in stocks:
                        stocks[ticker] = {
                            "name": text,
                            "sector": "Bilinmiyor"
                        }
    except Exception:
        pass
    
    return stocks


def _get_fallback_stocks():
    """
    Eğer hiçbir kaynak çalışmazsa kullanılacak temel hisse listesi.
    """
    return {
        "THYAO.IS": {"name": "Türk Hava Yolları", "sector": "Ulaştırma"},
        "AKBNK.IS": {"name": "Akbank", "sector": "Bankacılık"},
        "GARAN.IS": {"name": "Garanti BBVA", "sector": "Bankacılık"},
        "ISCTR.IS": {"name": "İş Bankası C", "sector": "Bankacılık"},
        "YKBNK.IS": {"name": "Yapı Kredi", "sector": "Bankacılık"},
        "HALKB.IS": {"name": "Halkbank", "sector": "Bankacılık"},
        "VAKBN.IS": {"name": "Vakıfbank", "sector": "Bankacılık"},
        "SISE.IS": {"name": "Şişe Cam", "sector": "Cam"},
        "ASELS.IS": {"name": "Aselsan", "sector": "Savunma"},
        "TUPRS.IS": {"name": "Tüpraş", "sector": "Enerji"},
        "SAHOL.IS": {"name": "Sabancı Holding", "sector": "Holding"},
        "KCHOL.IS": {"name": "Koç Holding", "sector": "Holding"},
        "EREGL.IS": {"name": "Ereğli Demir Çelik", "sector": "Metal"},
        "BIMAS.IS": {"name": "BİM Mağazalar", "sector": "Perakende"},
        "MGROS.IS": {"name": "Migros", "sector": "Perakende"},
        "SASA.IS": {"name": "SASA Polyester", "sector": "Kimya"},
        "PETKM.IS": {"name": "Petkim", "sector": "Kimya"},
        "TCELL.IS": {"name": "Turkcell", "sector": "Telekomünikasyon"},
        "TTKOM.IS": {"name": "Türk Telekom", "sector": "Telekomünikasyon"},
        "TOASO.IS": {"name": "Tofaş Oto", "sector": "Otomotiv"},
        "FROTO.IS": {"name": "Ford Otosan", "sector": "Otomotiv"},
        "PGSUS.IS": {"name": "Pegasus", "sector": "Ulaştırma"},
        "KOZAL.IS": {"name": "Koza Altın", "sector": "Madencilik"},
        "ARCLK.IS": {"name": "Arçelik", "sector": "Beyaz Eşya"},
        "ALARK.IS": {"name": "Alarko Holding", "sector": "Holding"},
    }


def _fetch_comprehensive_list():
    """
    Birden fazla kaynaktan hisse listesi toplar.
    """
    all_stocks = {}
    
    print("[BILGI] BIST hisse listesi güncelleniyor...")
    
    # 1. isyatirim'dan çek
    isyatirim_stocks = _fetch_from_isyatirim()
    all_stocks.update(isyatirim_stocks)
    print(f"    -> isyatirim.com.tr: {len(isyatirim_stocks)} hisse")
    
    # 2. Ek web kaynakları
    extra_stocks = _fetch_stock_codes_from_web()
    new_count = 0
    for ticker, info in extra_stocks.items():
        if ticker not in all_stocks:
            all_stocks[ticker] = info
            new_count += 1
    print(f"    -> Ek kaynaklar: {new_count} yeni hisse")
    
    # 3. Fallback
    if len(all_stocks) < 30:
        fallback = _get_fallback_stocks()
        for ticker, info in fallback.items():
            if ticker not in all_stocks:
                all_stocks[ticker] = info
                
    return all_stocks


def _sort_tickers_by_volume(stocks):
    """
    Tüm hisselerin 1 günlük TL işlem hacimlerini yfinance ile toplu olarak
    çeker ve en yüksekten en düşüğe sıralar.
    """
    tickers = list(stocks.keys())
    print(f"[BILGI] {len(tickers)} hissenin işlem hacimleri yfinance ile sorgulanıyor...")
    
    try:
        # 1 günlük veriyi toplu indir
        df = yf.download(tickers, period="1d", progress=False)
        if df is not None and not df.empty:
            # Multi-index sütun veya tek kolon olup olmadığını kontrol et
            if 'Close' in df.columns and 'Volume' in df.columns:
                close = df['Close']
                volume = df['Volume']
                
                # Son günün verilerini al
                if len(close) > 0:
                    last_close = close.iloc[-1]
                    last_volume = volume.iloc[-1]
                    
                    # TL Hacim = Kapanış Fiyatı * Hacim
                    volume_tl = last_close * last_volume
                    volume_tl = volume_tl.dropna().sort_values(ascending=False)
                    
                    sorted_list = list(volume_tl.index)
                    
                    # Eksik kalan veya veri gelmeyen ticker'ları listenin sonuna ekle
                    for t in tickers:
                        if t not in sorted_list:
                            sorted_list.append(t)
                            
                    print(f"  [OK] Hacme göre sıralama tamamlandı. En yüksek hacimli hisse: {sorted_list[0] if sorted_list else 'Yok'}")
                    return sorted_list
    except Exception as e:
        print(f"  [UYARI] Hacme göre sıralama yapılamadı, alfabetik sıralamaya geçiliyor: {e}")
        
    # Hata durumunda alfabetik sırala
    return sorted(tickers)


def _load_cache():
    """Cache'den verileri yükler."""
    global _stocks, _sorted_tickers, _sectors
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            cached_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01"))
            if datetime.now() - cached_time < timedelta(hours=_CACHE_EXPIRY_HOURS):
                _stocks = cache_data.get("stocks", {})
                _sorted_tickers = cache_data.get("sorted_tickers", [])
                
                if not _sorted_tickers and _stocks:
                    _sorted_tickers = sorted(list(_stocks.keys()))
                    
                _sectors = sorted(set(s["sector"] for s in _stocks.values()))
                print(f"[CACHE] {len(_stocks)} BIST hissesi cache'den başarıyla yüklendi.")
                return True
    except Exception as e:
        print(f"  [UYARI] Hisse cache yüklenemedi: {e}")
    return False


def _save_cache():
    """Verileri cache dosyasına yazar."""
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(_stocks),
            "stocks": _stocks,
            "sorted_tickers": _sorted_tickers
        }
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [UYARI] Hisse cache kaydedilemedi: {e}")


def _initialize(force_refresh=False):
    """Sistemi başlatır veya cache'i yeniler."""
    global _stocks, _sorted_tickers, _sectors
    
    if not force_refresh and _load_cache():
        return
        
    _stocks = _fetch_comprehensive_list()
    _sorted_tickers = _sort_tickers_by_volume(_stocks)
    _sectors = sorted(set(s["sector"] for s in _stocks.values()))
    
    _save_cache()


def refresh_stock_list():
    """Hisse listesini ve sıralamasını zorla günceller."""
    _initialize(force_refresh=True)
    return len(_stocks)


# --- Public API ---

def get_all_tickers():
    """İşlem hacmine göre sıralı tüm hisse ticker'larını döndürür."""
    if not _sorted_tickers:
        _initialize()
    return _sorted_tickers


def get_stock_info(ticker):
    """Belirli bir hisse hakkında bilgi döndürür."""
    if not _stocks:
        _initialize()
    return _stocks.get(ticker, None)


def get_stocks_by_sector(sector):
    """Belirli bir sektördeki hisseleri döndürür (hacim sırasına göre)."""
    if not _stocks:
        _initialize()
    
    sector_stocks = {}
    for ticker in get_all_tickers():
        info = _stocks.get(ticker)
        if info and info["sector"] == sector:
            sector_stocks[ticker] = info
    return sector_stocks


def get_stock_name(ticker):
    """Ticker'dan hisse adını döndürür."""
    if not _stocks:
        _initialize()
    info = _stocks.get(ticker)
    return info["name"] if info else ticker.replace(".IS", "")


def get_all_stocks():
    """Tüm hisse sözlüğünü döndürür."""
    if not _stocks:
        _initialize()
    return _stocks


def get_sectors():
    """Sektör listesini döndürür."""
    if not _stocks:
        _initialize()
    return _sectors


def get_stock_count():
    """Toplam hisse sayısını döndürür."""
    if not _stocks:
        _initialize()
    return len(_stocks)


# Lazy initialization tanımları
BIST_STOCKS = None
SECTORS = None
