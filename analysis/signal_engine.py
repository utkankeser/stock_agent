"""
Sinyal Üretme ve Öneri Motoru
Teknik analiz ve haber verilerini birleştirerek AL/SAT/TUT önerisi üretir.
Çoklu hisse analizinde ThreadPoolExecutor ile paralel çalışır.
"""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from analysis.data_fetcher import fetch_stock_data
from analysis.technical import calculate_indicators, get_technical_score
from analysis.news_scraper import fetch_news, get_news_score
from data.bist_stocks import get_stock_name

# Paralel analiz için max worker sayısı
MAX_WORKERS = 10


def analyze_stock(ticker, period=None, skip_news=False):
    """
    Bir hisse için kapsamlı analiz yapar.
    
    Args:
        ticker: yfinance ticker (ör: "THYAO.IS")
        period: Veri periyodu
        skip_news: True ise haber analizi atlanır (hızlı tarama)
    
    Returns:
        dict: Tüm analiz sonuçları
    """
    stock_name = get_stock_name(ticker)
    stock_code = ticker.replace(".IS", "")
    
    result = {
        "ticker": ticker,
        "code": stock_code,
        "name": stock_name,
        "indicators": None,
        "news": [],
        "technical_score": 50,
        "news_score": 50,
        "overall_score": 50,
        "signal": "TUT",
        "signal_class": "hold",
        "summary": "",
        "details": [],
        "error": None,
    }
    
    # 1. Fiyat verilerini çek
    df = fetch_stock_data(ticker, period)
    if df is None:
        result["error"] = f"{stock_code} için fiyat verisi bulunamadı"
        return result
    
    # 2. Teknik analiz yap
    indicators = calculate_indicators(df)
    if indicators is None:
        result["error"] = f"{stock_code} için yeterli veri yok (min {config.SMA_LONG} gün gerekli)"
        return result
    
    result["indicators"] = indicators
    
    # 3. Haberleri çek (skip_news modunda atla)
    if not skip_news:
        try:
            news = fetch_news(ticker)
            result["news"] = news
        except Exception:
            result["news"] = []
    
    # 4. Skorları hesapla
    tech_score = get_technical_score(indicators)
    news_sc = get_news_score(result["news"])
    
    result["technical_score"] = tech_score
    result["news_score"] = news_sc
    
    # 5. Genel skor = Teknik (%85) + Haber (%15) 
    # (haber yoksa skor %100 teknik)
    if skip_news or not result["news"]:
        overall = tech_score
    else:
        tech_weight = 1 - config.WEIGHT_NEWS
        overall = round(tech_score * tech_weight + news_sc * config.WEIGHT_NEWS)
    
    result["overall_score"] = overall
    
    # 6. Sinyal üret
    if overall >= config.SIGNAL_BUY_THRESHOLD:
        result["signal"] = "AL"
        result["signal_class"] = "buy"
    elif overall <= config.SIGNAL_SELL_THRESHOLD:
        result["signal"] = "SAT"
        result["signal_class"] = "sell"
    else:
        result["signal"] = "TUT"
        result["signal_class"] = "hold"
    
    # 7. Özet oluştur
    result["summary"] = _generate_summary(result)
    result["details"] = _generate_details(result)
    
    return result


def _safe_analyze(args):
    """Thread-safe wrapper for analyze_stock."""
    ticker, period, skip_news, index, total = args
    try:
        print(f"[{index}/{total}] {ticker} analiz ediliyor...")
        return analyze_stock(ticker, period, skip_news)
    except Exception as e:
        print(f"  [HATA] {ticker}: {e}")
        return {
            "ticker": ticker,
            "code": ticker.replace(".IS", ""),
            "name": ticker.replace(".IS", ""),
            "indicators": None,
            "news": [],
            "technical_score": 50,
            "news_score": 50,
            "overall_score": 50,
            "signal": "TUT",
            "signal_class": "hold",
            "summary": "",
            "details": [],
            "error": str(e),
        }


def analyze_multiple(tickers, period=None, skip_news=False, max_stocks=None):
    """
    Birden fazla hisseyi PARALEL olarak analiz eder.
    
    Args:
        tickers: Analiz edilecek ticker listesi
        period: Veri periyodu
        skip_news: True ise haber analizi atlanır (çok daha hızlı)
        max_stocks: Maksimum analiz edilecek hisse sayısı
    
    Returns:
        list: Analiz sonuçları listesi (skora göre sıralı)
    """
    # Hisse sayısını sınırla
    if max_stocks and len(tickers) > max_stocks:
        print(f"⚠️  {len(tickers)} hisseden ilk {max_stocks} tanesi analiz edilecek.")
        tickers = tickers[:max_stocks]
    
    total = len(tickers)
    mode = "Hızlı Tarama (habersiz)" if skip_news else "Detaylı Analiz"
    print(f"\n{'='*60}")
    print(f"  📊 {total} hisse analiz ediliyor... [{mode}]")
    print(f"  ⚡ {MAX_WORKERS} paralel worker aktif")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    results = []
    
    # Paralel analiz
    args_list = [
        (ticker, period, skip_news, i, total)
        for i, ticker in enumerate(tickers, 1)
    ]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_safe_analyze, args): args[0] for args in args_list}
        
        for future in as_completed(futures):
            try:
                result = future.result(timeout=60)  # 60 saniye timeout per stock
                results.append(result)
            except Exception as e:
                ticker = futures[future]
                print(f"  [TIMEOUT] {ticker}: {e}")
                results.append({
                    "ticker": ticker,
                    "code": ticker.replace(".IS", ""),
                    "name": ticker.replace(".IS", ""),
                    "indicators": None, "news": [],
                    "technical_score": 50, "news_score": 50, "overall_score": 50,
                    "signal": "TUT", "signal_class": "hold",
                    "summary": "", "details": [],
                    "error": f"Zaman aşımı: {e}",
                })
    
    elapsed = round(time.time() - start_time, 1)
    success_count = sum(1 for r in results if not r.get("error"))
    print(f"\n✅ {success_count}/{total} hisse başarıyla analiz edildi ({elapsed} saniye)")
    
    # Skora göre sırala (yüksek skor = daha iyi alım fırsatı)
    results.sort(key=lambda x: x["overall_score"], reverse=True)
    
    return results


def _generate_summary(result):
    """Analiz sonucu için Türkçe özet oluşturur."""
    name = result["name"]
    code = result["code"]
    signal = result["signal"]
    score = result["overall_score"]
    tech = result["technical_score"]
    news = result["news_score"]
    
    price_info = result.get("indicators", {}).get("price_info", {})
    price = price_info.get("current", "?")
    change = price_info.get("change_1d", 0)
    change_sign = "+" if change >= 0 else ""
    
    if signal == "AL":
        action = "Alım fırsatı görünüyor"
        reason = "Teknik göstergeler olumlu sinyal veriyor"
    elif signal == "SAT":
        action = "Satış düşünülebilir"
        reason = "Teknik göstergeler olumsuz sinyal veriyor"
    else:
        action = "Bekle ve izle"
        reason = "Teknik göstergeler kararsız"
    
    return (
        f"{name} ({code}) | Fiyat: ₺{price} ({change_sign}{change}%) | "
        f"Genel Skor: {score}/100 | Teknik: {tech} | Haber: {news} | "
        f"Öneri: {signal} → {action}. {reason}."
    )


def _generate_details(result):
    """Detaylı analiz maddeleri oluşturur (9 indikatör + haber)."""
    details = []
    indicators = result.get("indicators", {})
    
    if not indicators:
        return details
    
    # RSI
    if "rsi" in indicators:
        rsi = indicators["rsi"]
        details.append({
            "indicator": "RSI",
            "value": str(rsi["value"]),
            "signal": rsi["signal"],
            "description": rsi["description"]
        })
    
    # MACD
    if "macd" in indicators:
        macd = indicators["macd"]
        details.append({
            "indicator": "MACD",
            "value": f"{macd['macd_line']}",
            "signal": macd["signal"],
            "description": macd["description"]
        })
    
    # SMA
    if "sma" in indicators:
        sma = indicators["sma"]
        details.append({
            "indicator": f"SMA ({config.SMA_SHORT}/{config.SMA_LONG})",
            "value": f"{sma['sma_short']} / {sma['sma_long']}",
            "signal": sma["signal"],
            "description": sma["description"]
        })
    
    # EMA
    if "ema" in indicators:
        ema = indicators["ema"]
        details.append({
            "indicator": f"EMA ({config.EMA_SHORT}/{config.EMA_LONG})",
            "value": f"{ema['ema_short']} / {ema['ema_long']}",
            "signal": ema["signal"],
            "description": ema["description"]
        })
    
    # Bollinger
    if "bollinger" in indicators:
        bb = indicators["bollinger"]
        details.append({
            "indicator": "Bollinger",
            "value": f"{bb['lower']} - {bb['upper']}",
            "signal": bb["signal"],
            "description": bb["description"]
        })
    
    # Stokastik
    if "stochastic" in indicators:
        stoch = indicators["stochastic"]
        details.append({
            "indicator": "Stokastik",
            "value": f"%K:{stoch['k']} %D:{stoch['d']}",
            "signal": stoch["signal"],
            "description": stoch["description"]
        })
    
    # ADX
    if "adx" in indicators:
        adx = indicators["adx"]
        details.append({
            "indicator": "ADX",
            "value": f"{adx['value']} (+DI:{adx['plus_di']} -DI:{adx['minus_di']})",
            "signal": adx["signal"],
            "description": adx["description"]
        })
    
    # CCI
    if "cci" in indicators:
        cci = indicators["cci"]
        details.append({
            "indicator": "CCI",
            "value": str(cci["value"]),
            "signal": cci["signal"],
            "description": cci["description"]
        })
    
    # Williams %R
    if "williams" in indicators:
        williams = indicators["williams"]
        details.append({
            "indicator": "Williams %R",
            "value": str(williams["value"]),
            "signal": williams["signal"],
            "description": williams["description"]
        })
    
    # Haber
    news_score = result.get("news_score", 50)
    news_count = len(result.get("news", []))
    if news_count > 0:
        if news_score > 60:
            label = "Olumlu haberler ağırlıkta"
        elif news_score < 40:
            label = "Olumsuz haberler ağırlıkta"
        else:
            label = "Haberler nötr"
        
        details.append({
            "indicator": "Haber Analizi",
            "value": f"{news_count} haber",
            "signal": "AL" if news_score > 60 else ("SAT" if news_score < 40 else "TUT"),
            "description": label
        })
    
    return details

