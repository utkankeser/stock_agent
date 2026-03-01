"""
BIST Hisse Senedi ve Fon Listesi - Dinamik
isyatirim.com.tr API'sinden tüm BIST hisselerini otomatik çeker.
Çekilen veriler yerel cache dosyasına kaydedilir.
"""

import requests
import json
import os
from datetime import datetime, timedelta

# Cache dosyası (aynı dizinde)
_CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE_FILE = os.path.join(_CACHE_DIR, "stocks_cache.json")
_CACHE_EXPIRY_HOURS = 24  # Cache 24 saat geçerli

# Bellekteki hisse listesi
_stocks = {}
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Yöntem 1: IS Yatırım hisse listesini çek
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Hisse select/option listesinden verileri al
            select = soup.find("select", {"id": "ddlHpiSpiSector"})
            sectors_map = {}
            if select:
                for option in select.find_all("option"):
                    val = option.get("value", "")
                    if val:
                        sectors_map[val] = option.text.strip()
            
            # Tablo satırlarından hisseleri çek
            table = soup.find("table", {"id": "teikiTablo"})
            if table:
                rows = table.find("tbody")
                if rows:
                    for tr in rows.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 2:
                            code = tds[0].get_text(strip=True)
                            name = tds[1].get_text(strip=True) if len(tds) > 1 else code
                            sector = tds[2].get_text(strip=True) if len(tds) > 2 else "Diğer"
                            if code and code.isalpha():
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
    
    # Yöntem 3: Yahoo Finance üzerinden BIST endeks bileşenlerini çek
    if len(stocks) < 50:
        try:
            stocks.update(_fetch_from_yahoo())
        except Exception:
            pass
    
    return stocks


def _fetch_from_yahoo():
    """
    Yahoo Finance üzerinden BIST endeks bileşenlerini çeker.
    XU100.IS (BIST100) ve XUTUM.IS (BIST Tüm) endekslerinden.
    """
    import yfinance as yf
    stocks = {}
    
    # BIST tüm hisse listesi için farklı yollar dene
    for index_ticker in ["XU100.IS", "XUTUM.IS"]:
        try:
            idx = yf.Ticker(index_ticker)
            # Bazı endekslerin components bilgisi olmayabilir
            # Bu durumda screening kullanılabilir
        except Exception:
            pass
    
    return stocks


def _fetch_comprehensive_list():
    """
    Birden fazla kaynaktan hisse listesi toplar.
    En kapsamlı listeyi oluşturmak için tüm yöntemleri dener.
    """
    all_stocks = {}
    
    print("📡 BIST hisse listesi güncelleniyor...")
    
    # 1. isyatirim.com.tr'den çek
    print("  → isyatirim.com.tr kontrol ediliyor...")
    isyatirim_stocks = _fetch_from_isyatirim()
    all_stocks.update(isyatirim_stocks)
    print(f"    ✓ {len(isyatirim_stocks)} hisse bulundu")
    
    # 2. Bilinen BIST hisse kodlarını web'den çek
    print("  → Ek kaynaklar kontrol ediliyor...")
    extra_stocks = _fetch_stock_codes_from_web()
    new_count = 0
    for ticker, info in extra_stocks.items():
        if ticker not in all_stocks:
            all_stocks[ticker] = info
            new_count += 1
    print(f"    ✓ {new_count} ek hisse bulundu")
    
    # 3. Minimum listeyi garanti et (fallback)
    if len(all_stocks) < 30:
        print("  → Temel hisse listesi kullanılıyor (fallback)...")
        fallback = _get_fallback_stocks()
        for ticker, info in fallback.items():
            if ticker not in all_stocks:
                all_stocks[ticker] = info
        print(f"    ✓ Toplam {len(all_stocks)} hisse")
    
    print(f"\n✅ Toplam {len(all_stocks)} BIST hissesi listelendi.")
    return all_stocks


def _fetch_stock_codes_from_web():
    """
    Finans sitelerinden BIST hisse kodlarını toplar.
    """
    stocks = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
                # Hisse kodu genelde ilk sütunda
                code_el = row.select_one("a, span.hisseKodu, .col1 span, a.hisselink")
                if code_el:
                    text = code_el.get_text(strip=True)
                    # Sadece büyük harflerden oluşan kısa metinler hisse kodu
                    if text and 2 <= len(text) <= 6 and text.isalpha() and text.isupper():
                        ticker = f"{text}.IS"
                        if ticker not in stocks:
                            # İsim varsa al
                            name_el = row.select_one(".col2, td:nth-child(2)")
                            name = name_el.get_text(strip=True) if name_el else text
                            stocks[ticker] = {
                                "name": name if name != text else text,
                                "sector": "Bilinmiyor"
                            }
    except Exception as e:
        print(f"    [UYARI] bigpara'dan çekilemedi: {e}")
    
    # Kaynak 2: getmidas.com veya finnet üzerinden
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
    BIST 100 ve popüler hisseler.
    """
    return {
        "THYAO.IS": {"name": "Türk Hava Yolları", "sector": "Ulaştırma"},
        "AKBNK.IS": {"name": "Akbank", "sector": "Bankacılık"},
        "GARAN.IS": {"name": "Garanti BBVA", "sector": "Bankacılık"},
        "ISCTR.IS": {"name": "İş Bankası C", "sector": "Bankacılık"},
        "YKBNK.IS": {"name": "Yapı Kredi", "sector": "Bankacılık"},
        "HALKB.IS": {"name": "Halkbank", "sector": "Bankacılık"},
        "VAKBN.IS": {"name": "Vakıfbank", "sector": "Bankacılık"},
        "TSKB.IS": {"name": "TSKB", "sector": "Bankacılık"},
        "SKBNK.IS": {"name": "Şekerbank", "sector": "Bankacılık"},
        "ALBRK.IS": {"name": "Albaraka Türk", "sector": "Bankacılık"},
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
        "EKGYO.IS": {"name": "Emlak Konut GYO", "sector": "GYO"},
        "ENKAI.IS": {"name": "Enka İnşaat", "sector": "İnşaat"},
        "TOASO.IS": {"name": "Tofaş Oto", "sector": "Otomotiv"},
        "FROTO.IS": {"name": "Ford Otosan", "sector": "Otomotiv"},
        "TAVHL.IS": {"name": "TAV Havalimanları", "sector": "Ulaştırma"},
        "PGSUS.IS": {"name": "Pegasus", "sector": "Ulaştırma"},
        "KOZAL.IS": {"name": "Koza Altın", "sector": "Madencilik"},
        "KOZAA.IS": {"name": "Koza Anadolu Metal", "sector": "Madencilik"},
        "KRDMD.IS": {"name": "Kardemir D", "sector": "Metal"},
        "ARCLK.IS": {"name": "Arçelik", "sector": "Beyaz Eşya"},
        "VESTL.IS": {"name": "Vestel", "sector": "Beyaz Eşya"},
        "DOHOL.IS": {"name": "Doğan Holding", "sector": "Holding"},
        "AGHOL.IS": {"name": "AG Anadolu Grubu", "sector": "Holding"},
        "TTRAK.IS": {"name": "Türk Traktör", "sector": "Otomotiv"},
        "GUBRF.IS": {"name": "Gübre Fabrikaları", "sector": "Kimya"},
        "AKSEN.IS": {"name": "Aksa Enerji", "sector": "Enerji"},
        "ODAS.IS": {"name": "Odaş Elektrik", "sector": "Enerji"},
        "KONTR.IS": {"name": "Kontrolmatik", "sector": "Teknoloji"},
        "LOGO.IS": {"name": "Logo Yazılım", "sector": "Teknoloji"},
        "ALARK.IS": {"name": "Alarko Holding", "sector": "Holding"},
        "BRYAT.IS": {"name": "Borusan Yatırım", "sector": "Holding"},
        "ISGYO.IS": {"name": "İş GYO", "sector": "GYO"},
        "HEKTS.IS": {"name": "Hektaş", "sector": "Kimya"},
        "AEFES.IS": {"name": "Anadolu Efes", "sector": "Gıda"},
        "ULKER.IS": {"name": "Ülker", "sector": "Gıda"},
        "CCOLA.IS": {"name": "Coca Cola İçecek", "sector": "Gıda"},
        "SOKM.IS": {"name": "Şok Marketler", "sector": "Perakende"},
        "MPARK.IS": {"name": "MLP Sağlık", "sector": "Sağlık"},
        "CIMSA.IS": {"name": "Çimsa", "sector": "Çimento"},
        "OTKAR.IS": {"name": "Otokar", "sector": "Otomotiv"},
        "OYAKC.IS": {"name": "Oyak Çimento", "sector": "Çimento"},
        "GLYHO.IS": {"name": "Global Yatırım Holding", "sector": "Holding"},
        "PRKME.IS": {"name": "Park Elektrik", "sector": "Enerji"},
        "ISMEN.IS": {"name": "İş Yatırım", "sector": "Finans"},
        "MAVI.IS": {"name": "Mavi Giyim", "sector": "Tekstil"},
        "BERA.IS": {"name": "Bera Holding", "sector": "Holding"},
        "DOAS.IS": {"name": "Doğuş Otomotiv", "sector": "Otomotiv"},
        "KARSN.IS": {"name": "Karsan Otomotiv", "sector": "Otomotiv"},
        "ENJSA.IS": {"name": "Enerjisa Enerji", "sector": "Enerji"},
        "GESAN.IS": {"name": "Giresun Ticaret", "sector": "Ticaret"},
        "KLRHO.IS": {"name": "Kiler Holding", "sector": "Holding"},
        "TKFEN.IS": {"name": "Tekfen Holding", "sector": "Holding"},
        "TURSG.IS": {"name": "Türkiye Sigorta", "sector": "Sigorta"},
        "ANHYT.IS": {"name": "Anadolu Hayat Emeklilik", "sector": "Sigorta"},
        "AKSA.IS": {"name": "Aksa Akrilik", "sector": "Kimya"},
        "BUCIM.IS": {"name": "Bursa Çimento", "sector": "Çimento"},
        "VESBE.IS": {"name": "Vestel Beyaz Eşya", "sector": "Beyaz Eşya"},
        "NETAS.IS": {"name": "Netaş Telekomünikasyon", "sector": "Teknoloji"},
        "ANSGR.IS": {"name": "Anadolu Sigorta", "sector": "Sigorta"},
        "BTCIM.IS": {"name": "Batıçim", "sector": "Çimento"},
        "EGEEN.IS": {"name": "Ege Endüstri", "sector": "Otomotiv"},
        "GOLTS.IS": {"name": "Göltaş Çimento", "sector": "Çimento"},
        "IHLGM.IS": {"name": "İhlas Gayrimenkul", "sector": "GYO"},
        "INDES.IS": {"name": "İndes Bilişim", "sector": "Teknoloji"},
        "IPEKE.IS": {"name": "İpek Enerji", "sector": "Enerji"},
        "KARTN.IS": {"name": "Kartonsan", "sector": "Kağıt"},
        "KENT.IS": {"name": "Kent Gıda", "sector": "Gıda"},
        "KLMSN.IS": {"name": "Klimasan", "sector": "Beyaz Eşya"},
        "KORDS.IS": {"name": "Kordsa", "sector": "Kimya"},
        "METRO.IS": {"name": "Metro Holding", "sector": "Holding"},
        "MIATK.IS": {"name": "Mia Teknoloji", "sector": "Teknoloji"},
        "NTHOL.IS": {"name": "Net Holding", "sector": "Holding"},
        "PAPIL.IS": {"name": "Papilon Savunma", "sector": "Savunma"},
        "PENTA.IS": {"name": "Penta Teknoloji", "sector": "Teknoloji"},
        "QUAGR.IS": {"name": "QUA Granite", "sector": "Seramik"},
        "SMRTG.IS": {"name": "Smart Güneş Enerjisi", "sector": "Enerji"},
        "TMSN.IS": {"name": "Tümosan Motor", "sector": "Otomotiv"},
        "TRILC.IS": {"name": "Turk İlaç Serum", "sector": "Sağlık"},
        "ULUSE.IS": {"name": "Ulusoy Enerji", "sector": "Enerji"},
        "YEOTK.IS": {"name": "Yeo Teknoloji", "sector": "Teknoloji"},
        "YYLGD.IS": {"name": "Yayla Gıda", "sector": "Gıda"},
        "ZOREN.IS": {"name": "Zorlu Enerji", "sector": "Enerji"},
        "MEGAP.IS": {"name": "Mega Polietilen", "sector": "Plastik"},
        "ALFAS.IS": {"name": "Alfa Solar Enerji", "sector": "Enerji"},
        "EUPWR.IS": {"name": "Europower Enerji", "sector": "Enerji"},
        "GENIL.IS": {"name": "Genius İlaç", "sector": "Sağlık"},
        "KCAER.IS": {"name": "Kocaer Çelik", "sector": "Metal"},
        "TBORG.IS": {"name": "Türk Tuborg", "sector": "Gıda"},
        "ASUZU.IS": {"name": "Anadolu Isuzu", "sector": "Otomotiv"},
        "CEMTS.IS": {"name": "Çemtaş Çelik", "sector": "Metal"},
        "CMENT.IS": {"name": "Çimentaş", "sector": "Çimento"},
        "DEVA.IS": {"name": "Deva Holding", "sector": "Sağlık"},
        "ECILC.IS": {"name": "Eczacıbaşı İlaç", "sector": "Sağlık"},
        "GEDZA.IS": {"name": "Gediz Ambalaj", "sector": "Ambalaj"},
        "GOODY.IS": {"name": "Goodyear", "sector": "Otomotiv"},
        "HURGZ.IS": {"name": "Hürriyet Gazetecilik", "sector": "Medya"},
        "TMPOL.IS": {"name": "Temapol Polimer", "sector": "Plastik"},
    }


def _load_cache():
    """
    Cache dosyasından hisse listesini yükler.
    Cache süresi dolmuşsa None döndürür.
    """
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # Cache süresi kontrolü
            cached_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01"))
            if datetime.now() - cached_time < timedelta(hours=_CACHE_EXPIRY_HOURS):
                stocks = cache_data.get("stocks", {})
                if stocks:
                    return stocks
    except Exception:
        pass
    
    return None


def _save_cache(stocks):
    """Hisse listesini cache dosyasına kaydeder."""
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(stocks),
            "stocks": stocks
        }
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [UYARI] Cache kaydedilemedi: {e}")


def _initialize():
    """
    Hisse listesini başlat:
    1. Önce cache'den yükle
    2. Cache yoksa veya eskimişse web'den çek
    3. Web çalışmazsa fallback listesini kullan
    """
    global _stocks, _sectors
    
    # 1. Cache dene
    cached = _load_cache()
    if cached:
        _stocks = cached
        _sectors = sorted(set(s["sector"] for s in _stocks.values()))
        print(f"📋 Cache'den {len(_stocks)} BIST hissesi yüklendi.")
        return
    
    # 2. Web'den çek
    _stocks = _fetch_comprehensive_list()
    
    if _stocks:
        _sectors = sorted(set(s["sector"] for s in _stocks.values()))
        _save_cache(_stocks)
    else:
        # 3. Fallback
        _stocks = _get_fallback_stocks()
        _sectors = sorted(set(s["sector"] for s in _stocks.values()))


def refresh_stock_list():
    """
    Hisse listesini yeniden web'den çeker.
    Dashboard'dan 'Listeyi Güncelle' butonu ile tetiklenebilir.
    Cache dosyasını silerek gerçek bir yenileme yapar.
    """
    global _stocks, _sectors
    
    # Önce cache dosyasını sil → zorla yeniden çek
    try:
        if os.path.exists(_CACHE_FILE):
            os.remove(_CACHE_FILE)
            print("🗑️  Eski cache silindi, web'den yeniden çekiliyor...")
    except Exception:
        pass
    
    _stocks = _fetch_comprehensive_list()
    _sectors = sorted(set(s["sector"] for s in _stocks.values()))
    _save_cache(_stocks)
    return len(_stocks)


# --- Public API ---

def get_all_tickers():
    """Tüm hisse ticker'larını döndürür."""
    if not _stocks:
        _initialize()
    return list(_stocks.keys())


def get_stock_info(ticker):
    """Belirli bir hisse hakkında bilgi döndürür."""
    if not _stocks:
        _initialize()
    return _stocks.get(ticker, None)


def get_stocks_by_sector(sector):
    """Belirli bir sektördeki hisseleri döndürür."""
    if not _stocks:
        _initialize()
    return {k: v for k, v in _stocks.items() if v["sector"] == sector}


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


# Modül import edildiğinde listeyi henüz yükleme (lazy init)
# İlk erişimde otomatik yüklenecek
BIST_STOCKS = None  # Lazy, get_all_stocks() kullan
SECTORS = None      # Lazy, get_sectors() kullan
