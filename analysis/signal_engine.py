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
from data.bist_stocks import get_stock_name, get_stock_info
from analysis.tefas_fetcher import fetch_and_analyze_funds

# Paralel analiz için max worker sayısı
MAX_WORKERS = 10


def analyze_stock(ticker, period=None, interval=None, skip_news=False):
    """
    Bir hisse için kapsamlı analiz yapar.
    
    Args:
        ticker: yfinance ticker (ör: "THYAO.IS")
        period: Veri periyodu
        interval: Mum süresi (1h, 1d, 1wk vb.)
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
        "interval": interval or "1d",
        "indicators": None,
        "news": [],
        "technical_score": 50,
        "news_score": 50,
        "overall_score": 50,
        "score": 50,  # fon uyumluluğu için
        "signal": "TUT",
        "signal_class": "hold",
        "type": "Hisse",
        "category": "Diğer",
        "price": 0.0,
        "daily_return": 0.0,
        "weekly_return": 0.0,
        "monthly_return": 0.0,
        "volume_size": 0.0,
        "summary": "",
        "details": [],
        "error": None,
    }
    
    # Sektör bilgisini cache'den hızlıca al
    info = get_stock_info(ticker)
    if info:
        result["category"] = info.get("sector", "Diğer")
    
    # 1. Fiyat verilerini çek
    df = fetch_stock_data(ticker, period, interval)
    if df is None:
        result["error"] = f"{stock_code} için fiyat verisi bulunamadı"
        return result
        
    # yfinance kaynaklı eksik/boş satırları temizle
    df = df.dropna(subset=["Kapanış"])
    
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
    result["score"] = overall
    
    # 6. Sinyal üret
    if overall >= 75:
        result["signal"] = "GÜÇLÜ AL"
        result["signal_class"] = "buy"
    elif overall >= config.SIGNAL_BUY_THRESHOLD:
        result["signal"] = "AL"
        result["signal_class"] = "buy"
    elif overall <= 25:
        result["signal"] = "GÜÇLÜ SAT"
        result["signal_class"] = "sell"
    elif overall <= config.SIGNAL_SELL_THRESHOLD:
        result["signal"] = "SAT"
        result["signal_class"] = "sell"
    else:
        result["signal"] = "TUT"
        result["signal_class"] = "hold"
        
    import math
    def _clean_val(v):
        try:
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                return 0.0
            return fv
        except Exception:
            return 0.0

    # Fiyat, Getiri ve Hacim bilgilerini üst seviyeye çıkar
    if "price_info" in indicators:
        pi = indicators["price_info"]
        result["price"] = _clean_val(pi.get("current", 0.0))
        result["daily_return"] = _clean_val(pi.get("change_1d", 0.0))
        result["weekly_return"] = _clean_val(pi.get("change_1w", 0.0))
        result["monthly_return"] = _clean_val(pi.get("change_1m", 0.0))
        
    # TL cinsinden işlem hacmini hesapla
    try:
        last_price = _clean_val(df["Kapanış"].iloc[-1])
        last_volume = _clean_val(df["Hacim"].iloc[-1]) if "Hacim" in df.columns else 0.0
        result["volume_size"] = _clean_val(last_price * last_volume)
    except Exception:
        result["volume_size"] = 0.0
    
    # 7. Özet oluştur
    result["summary"] = _generate_summary(result)
    result["details"] = _generate_details(result)
    
    return result


def _safe_analyze(args):
    """Thread-safe wrapper for analyze_stock."""
    ticker, period, interval, skip_news, index, total = args
    try:
        print(f"[{index}/{total}] {ticker} analiz ediliyor...")
        return analyze_stock(ticker, period, interval, skip_news)
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
            "score": 50,
            "signal": "TUT",
            "signal_class": "hold",
            "type": "Hisse",
            "category": "Diğer",
            "price": 0.0,
            "daily_return": 0.0,
            "weekly_return": 0.0,
            "monthly_return": 0.0,
            "volume_size": 0.0,
            "summary": "",
            "details": [],
            "error": str(e),
        }


def analyze_multiple(tickers, period=None, interval=None, skip_news=False, max_stocks=None):
    """
    Birden fazla hisseyi PARALEL olarak analiz eder.
    
    Args:
        tickers: Analiz edilecek ticker listesi
        period: Veri periyodu
        interval: Mum süresi (1h, 1d, 1wk vb.)
        skip_news: True ise haber analizi atlanır (çok daha hızlı)
        max_stocks: Maksimum analiz edilecek hisse sayısı
    
    Returns:
        list: Analiz sonuçları listesi (skora göre sıralı)
    """
    if max_stocks and len(tickers) > max_stocks:
        print(f"[UYARI] {len(tickers)} hisseden ilk {max_stocks} tanesi analiz edilecek.")
        tickers = tickers[:max_stocks]
    
    total = len(tickers)
    mode = "Hizli Tarama (habersiz)" if skip_news else "Detayli Analiz"
    print(f"\n{'='*60}")
    print(f"  [ANALIZ] {total} hisse analiz ediliyor... [{mode}]")
    print(f"  [INFO] {MAX_WORKERS} paralel worker aktif")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    results = []
    
    args_list = [
        (ticker, period, interval, skip_news, i, total)
        for i, ticker in enumerate(tickers, 1)
    ]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_safe_analyze, args): args[0] for args in args_list}
        
        for future in as_completed(futures):
            try:
                result = future.result(timeout=60)
                results.append(result)
            except Exception as e:
                ticker = futures[future]
                print(f"  [TIMEOUT] {ticker}: {e}")
                results.append({
                    "ticker": ticker,
                    "code": ticker.replace(".IS", ""),
                    "name": ticker.replace(".IS", ""),
                    "indicators": None, "news": [],
                    "technical_score": 50, "news_score": 50, "overall_score": 50, "score": 50,
                    "signal": "TUT", "signal_class": "hold",
                    "type": "Hisse", "category": "Diğer",
                    "price": 0.0, "daily_return": 0.0, "weekly_return": 0.0, "monthly_return": 0.0, "volume_size": 0.0,
                    "summary": "", "details": [],
                    "error": f"Zaman asimi: {e}",
                })
    
    elapsed = round(time.time() - start_time, 1)
    success_count = sum(1 for r in results if not r.get("error"))
    print(f"\n[OK] {success_count}/{total} hisse basariyla analiz edildi ({elapsed} saniye)")
    
    results.sort(key=lambda x: x["overall_score"], reverse=True)
    return results


def analyze_all_assets(sector="all", period=None, interval=None, scan_mode="quick", max_stocks=100, max_funds=100, force_refresh=False):
    """
    Hem BIST hisselerini hem de TEFAS fonlarını analiz edip tek bir birleşik yapıda birleştirir.
    
    Args:
        sector (str): "all" ise hepsi, değilse belirli bir hisse sektörü (bu durumda fonlar dahil edilmez)
        period (str): Veri periyodu
        interval (str): Mum süresi
        scan_mode (str): "quick" veya "detailed"
        max_stocks (int): Maksimum hisse sayısı
        max_funds (int): Maksimum fon sayısı
        
    Returns:
        list: Birleşik analiz sonuçları
    """
    combined_results = []
    
    # 1. Hisseleri analiz et (Eğer sektör "all" ise veya geçerli bir sektörse)
    from data.bist_stocks import get_all_tickers, get_stocks_by_sector
    
    if sector == "all":
        tickers = get_all_tickers()
    else:
        tickers = list(get_stocks_by_sector(sector).keys())
        
    if tickers:
        skip_news = (scan_mode == "quick")
        stock_results = analyze_multiple(tickers, period, interval, skip_news=skip_news, max_stocks=max_stocks)
        combined_results.extend(stock_results)
        
    # 2. Fonları analiz et (Yalnızca genel taramada 'sector == all' durumunda fonları ekliyoruz)
    if sector == "all" and max_funds and max_funds > 0:
        print("\n[ANALIZ] TEFAS yatırım fonları getirileri ve momentum trendleri hesaplanıyor...")
        try:
            fund_results = fetch_and_analyze_funds(top_n=max_funds, force_refresh=force_refresh)
            
            # Fon sinyallerini stock sinyal_class yapılarına eşle
            # GÜÇLÜ TREND -> buy, NÖTR -> hold, ZAYIF TREND -> sell
            signal_class_map = {
                "GÜÇLÜ TREND": "buy",
                "NÖTR": "hold",
                "ZAYIF TREND": "sell"
            }
            
            for f in fund_results:
                f["signal_class"] = signal_class_map.get(f["signal"], "hold")
                # app.py aramasında ve detay rotalarında uyumluluk için ticker alanını dolduralım
                f["ticker"] = f["code"] 
                # Genel sıralama için overall_score alanını da dolduralım
                f["overall_score"] = f["score"]
                
            combined_results.extend(fund_results)
            print(f"[OK] {len(fund_results)} TEFAS fonu birleşik listeye eklendi.")
        except Exception as e:
            print(f"[HATA] Fon analizleri birleşik listeye eklenemedi: {e}")
            
    # Tüm varlıkları skorlarına göre yeniden sırala
    combined_results.sort(key=lambda x: x.get("score", x.get("overall_score", 50)), reverse=True)
    return combined_results



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
    
    if signal == "GÜÇLÜ AL":
        action = "Güçlü alım fırsatı görünüyor"
        reason = "Teknik göstergelerin neredeyse tamamı çok güçlü alım sinyali veriyor"
    elif signal == "AL":
        action = "Alım fırsatı görünüyor"
        reason = "Teknik göstergeler olumlu sinyal veriyor"
    elif signal == "GÜÇLÜ SAT":
        action = "Güçlü satış baskısı mevcut"
        reason = "Teknik göstergelerin neredeyse tamamı çok güçlü satış sinyali veriyor"
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
    """Detaylı analiz maddeleri oluşturur (15 indikatör + haber)."""
    details = []
    indicators = result.get("indicators", {})
    
    if not indicators:
        return details
    
    # 1. RSI
    if "rsi" in indicators:
        r = indicators["rsi"]
        details.append({"indicator": "RSI", "value": str(r["value"]),
                        "signal": r["signal"], "description": r["description"]})
    
    # 2. MACD
    if "macd" in indicators:
        m = indicators["macd"]
        details.append({"indicator": "MACD", "value": f"{m['macd_line']}",
                        "signal": m["signal"], "description": m["description"]})
    
    # 3. SMA
    if "sma" in indicators:
        s = indicators["sma"]
        details.append({"indicator": f"SMA ({config.SMA_SHORT}/{config.SMA_LONG})",
                        "value": f"{s['sma_short']} / {s['sma_long']}",
                        "signal": s["signal"], "description": s["description"]})
    
    # 4. EMA
    if "ema" in indicators:
        e = indicators["ema"]
        details.append({"indicator": f"EMA ({config.EMA_SHORT}/{config.EMA_LONG})",
                        "value": f"{e['ema_short']} / {e['ema_long']}",
                        "signal": e["signal"], "description": e["description"]})
    
    # 5. Bollinger
    if "bollinger" in indicators:
        b = indicators["bollinger"]
        details.append({"indicator": "Bollinger", "value": f"{b['lower']} - {b['upper']}",
                        "signal": b["signal"], "description": b["description"]})
    
    # 6. Stokastik
    if "stochastic" in indicators:
        st = indicators["stochastic"]
        details.append({"indicator": "Stokastik", "value": f"%K:{st['k']} %D:{st['d']}",
                        "signal": st["signal"], "description": st["description"]})
    
    # 7. ADX
    if "adx" in indicators:
        a = indicators["adx"]
        details.append({"indicator": "ADX",
                        "value": f"{a['value']} (+DI:{a['plus_di']} -DI:{a['minus_di']})",
                        "signal": a["signal"], "description": a["description"]})
    
    # 8. CCI
    if "cci" in indicators:
        c = indicators["cci"]
        details.append({"indicator": "CCI", "value": str(c["value"]),
                        "signal": c["signal"], "description": c["description"]})
    
    # 9. Williams %R
    if "williams" in indicators:
        w = indicators["williams"]
        details.append({"indicator": "Williams %R", "value": str(w["value"]),
                        "signal": w["signal"], "description": w["description"]})
    
    # 10. OBV
    if "obv" in indicators:
        o = indicators["obv"]
        details.append({"indicator": "OBV", "value": f"{o['value']:,}",
                        "signal": o["signal"], "description": o["description"]})
    
    # 11. MFI
    if "mfi" in indicators:
        mf = indicators["mfi"]
        details.append({"indicator": "MFI", "value": str(mf["value"]),
                        "signal": mf["signal"], "description": mf["description"]})
    
    # 12. Parabolic SAR
    if "psar" in indicators:
        ps = indicators["psar"]
        details.append({"indicator": "Parabolic SAR", "value": str(ps["value"]),
                        "signal": ps["signal"], "description": ps["description"]})
    
    # 13. Ichimoku
    if "ichimoku" in indicators:
        ic = indicators["ichimoku"]
        details.append({"indicator": "Ichimoku",
                        "value": f"T:{ic['tenkan']} K:{ic['kijun']}",
                        "signal": ic["signal"], "description": ic["description"]})
    
    # 14. ROC
    if "roc" in indicators:
        rc = indicators["roc"]
        details.append({"indicator": "ROC", "value": f"%{rc['value']}",
                        "signal": rc["signal"], "description": rc["description"]})
    
    # 15. CMF
    if "cmf" in indicators:
        cm = indicators["cmf"]
        details.append({"indicator": "CMF", "value": f"{cm['value']:.4f}",
                        "signal": cm["signal"], "description": cm["description"]})
    
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
            "signal": "AL" if news_score > 60 else ("SAT" if news_score < 40 else "NÖTR"),
            "description": label
        })
    
    return details


