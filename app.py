"""
BIST Teknik Analiz Ajanı - Web Dashboard
Flask tabanlı web arayüzü
"""

from flask import Flask, render_template, request, jsonify
import sys
import os

# Proje ana dizinini sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data.bist_stocks import (
    get_all_tickers, get_stocks_by_sector, get_all_stocks,
    get_sectors, get_stock_count, refresh_stock_list
)
from analysis.signal_engine import analyze_stock, analyze_multiple, analyze_all_assets
from analysis.ai_commentary import get_ai_commentary, set_api_key

app = Flask(__name__)

# Analiz sonuçları cache'i
_analysis_cache = {}
_stock_timeframe_cache = {}

# Son analiz ayarlarını tutan durum objesi (dashboard kararlılığı için)
_last_options = {
    "sector": "all",
    "timeframe": "1d",
    "scan_mode": "quick",
    "max_stocks": "100"
}

# Gemini API key'i ayarla
if config.GEMINI_API_KEY:
    set_api_key(config.GEMINI_API_KEY)


def _score_color(score):
    """Skora göre renk döndürür (template'te kullanılır)."""
    if score >= 60:
        return "#00c853"
    elif score <= 40:
        return "#ff1744"
    return "#ffc107"


# Template'lerde kullanılabilir yap
app.jinja_env.globals["_score_color"] = _score_color


@app.route("/")
def index():
    """Ana sayfa - Dashboard"""
    sector_filter = request.args.get("sector", _last_options["sector"])
    
    # Eğer cache'de önceden yapılmış analizler varsa doğrudan göster
    analysis_done = False
    sorted_results = []
    if _analysis_cache:
        analysis_done = True
        sorted_results = sorted(
            _analysis_cache.items(),
            key=lambda x: x[1].get("score", x[1].get("overall_score", 50)),
            reverse=True
        )
        
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector=sector_filter,
        selected_timeframe=_last_options["timeframe"],
        selected_max_stocks=_last_options["max_stocks"],
        selected_scan_mode=_last_options["scan_mode"],
        results=_analysis_cache,
        sorted_results=sorted_results,
        analysis_done=analysis_done,
        total_analyzed=len(_analysis_cache)
    )


@app.route("/analyze", methods=["POST"])
def run_analysis():
    """Tüm hisseleri ve fonları analiz et"""
    global _analysis_cache
    
    sector = request.form.get("sector", "all")
    timeframe = request.form.get("timeframe", "1d")
    scan_mode = request.form.get("scan_mode", "quick")  # quick veya detailed
    max_stocks_str = request.form.get("max_stocks", "100")
    force_fund_refresh = request.form.get("force_fund_refresh") == "true"
    
    # Zaman dilimini period ve interval'e eşle
    timeframe_map = {
        "1h": ("1mo", "1h"),
        "1d": ("6mo", "1d"),
        "1wk": ("2y", "1wk"),
        "1mo": ("3mo", "1d"),
        "3mo": ("6mo", "1d")
    }
    period, interval = timeframe_map.get(timeframe, ("6mo", "1d"))
    
    # Son tercihleri kaydet (durum kararlılığı için)
    _last_options["sector"] = sector
    _last_options["timeframe"] = timeframe
    _last_options["scan_mode"] = scan_mode
    _last_options["max_stocks"] = max_stocks_str
    
    # Max hisse sayısını parse et
    try:
        max_stocks = int(max_stocks_str) if max_stocks_str != "all" else None
    except ValueError:
        max_stocks = 100
    
    # Birleşik analiz yap (Hisseler + Fonlar)
    results = analyze_all_assets(
        sector=sector,
        period=period,
        interval=interval,
        scan_mode=scan_mode,
        max_stocks=max_stocks,
        max_funds=100,
        force_refresh=force_fund_refresh
    )
    
    # Cache'e kaydet
    results_dict = {}
    for r in results:
        key = r.get("ticker", r.get("code"))
        _analysis_cache[key] = r
        results_dict[key] = r
    
    # Skora göre sıralı liste oluştur (template için)
    sorted_results = sorted(results_dict.items(), key=lambda x: x[1].get("overall_score", 50), reverse=True)
    
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector=sector,
        selected_timeframe=timeframe,
        selected_max_stocks=max_stocks_str,
        selected_scan_mode=scan_mode,
        results=results_dict,
        sorted_results=sorted_results,
        analysis_done=True,
        total_analyzed=len(results),
    )


@app.route("/refresh", methods=["POST"])
def refresh_stocks():
    """Hisse listesini web'den yeniden çek"""
    count = refresh_stock_list()
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector="all",
        results=_analysis_cache,
        refreshed=True,
        refresh_count=count,
    )


@app.route("/search", methods=["POST"])
def search_stock():
    """Hisse veya Fon arama — kod veya isim ile, benzer sonuçlar gösterir"""
    query = request.form.get("query", "").strip()
    if not query:
        return render_template(
            "index.html",
            stocks=get_all_stocks(),
            sectors=get_sectors(),
            stock_count=get_stock_count(),
            selected_sector="all",
            results=_analysis_cache,
            search_error="Lütfen bir hisse veya fon kodu/adı girin.",
        )
    
    query_upper = query.upper()
    all_stocks = get_all_stocks()
    
    # TEFAS fonlarını çek
    from analysis.tefas_fetcher import fetch_and_analyze_funds
    try:
        all_funds = fetch_and_analyze_funds(top_n=500)
    except Exception as e:
        print(f"  [UYARI] Arama için fonlar çekilemedi: {e}")
        all_funds = []
        
    exact_stock = None
    exact_fund = None
    suggestions = []
    
    # Hisse arama
    for ticker, info in all_stocks.items():
        code = ticker.replace(".IS", "")
        name = info.get("name", "").upper()
        
        if code == query_upper:
            exact_stock = ticker
            break
        if code.startswith(query_upper):
            suggestions.append({
                "ticker": ticker,
                "code": code,
                "name": info.get("name"),
                "category": info.get("sector"),
                "type": "Hisse"
            })
        elif query_upper in name:
            suggestions.append({
                "ticker": ticker,
                "code": code,
                "name": info.get("name"),
                "category": info.get("sector"),
                "type": "Hisse"
            })
            
    # Fon arama (eğer tam hisse eşleşmesi yoksa)
    if not exact_stock:
        for f in all_funds:
            code = f["code"]
            name = f["name"].upper()
            
            if code == query_upper:
                exact_fund = f
                break
            if code.startswith(query_upper):
                suggestions.append({
                    "ticker": code,
                    "code": code,
                    "name": f["name"],
                    "category": f["category"],
                    "type": "Yatırım Fonu"
                })
            elif query_upper in name:
                suggestions.append({
                    "ticker": code,
                    "code": code,
                    "name": f["name"],
                    "category": f["category"],
                    "type": "Yatırım Fonu"
                })
    
    # Tam eşleşme hisse ise -> stock_detail sayfasına
    if exact_stock:
        result = analyze_stock(exact_stock)
        _analysis_cache[exact_stock] = result
        return render_template("stock_detail.html", result=result)
        
    # Tam eşleşme fon ise -> fund_detail sayfasına
    if exact_fund:
        signal_class_map = {
            "GÜÇLÜ TREND": "buy",
            "NÖTR": "hold",
            "ZAYIF TREND": "sell"
        }
        exact_fund["signal_class"] = signal_class_map.get(exact_fund["signal"], "hold")
        exact_fund["ticker"] = exact_fund["code"]
        exact_fund["overall_score"] = exact_fund["score"]
        _analysis_cache[exact_fund["code"]] = exact_fund
        
        from analysis.tefas_fetcher import get_fund_historical_data
        history = get_fund_historical_data(exact_fund["code"], days=30)
        return render_template("fund_detail.html", result=exact_fund, history=history)
    
    # Tek bir öneri varsa -> doğrudan detayına git
    if len(suggestions) == 1:
        s = suggestions[0]
        if s["type"] == "Hisse":
            result = analyze_stock(s["ticker"])
            _analysis_cache[s["ticker"]] = result
            return render_template("stock_detail.html", result=result)
        else:
            fund_code = s["code"]
            fund_info = next((f for f in all_funds if f["code"] == fund_code), None)
            if fund_info:
                signal_class_map = {
                    "GÜÇLÜ TREND": "buy",
                    "NÖTR": "hold",
                    "ZAYIF TREND": "sell"
                }
                fund_info["signal_class"] = signal_class_map.get(fund_info["signal"], "hold")
                fund_info["ticker"] = fund_info["code"]
                fund_info["overall_score"] = fund_info["score"]
                _analysis_cache[fund_code] = fund_info
                
                from analysis.tefas_fetcher import get_fund_historical_data
                history = get_fund_historical_data(fund_code, days=30)
                return render_template("fund_detail.html", result=fund_info, history=history)
    
    # Birden fazla öneri veya bulunamadı -> öneri listesi göster
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector="all",
        results=_analysis_cache,
        search_query=query,
        search_suggestions=suggestions[:20],  # Maks 20 öneri
        search_error=f'"{query}" için sonuç bulunamadı.' if not suggestions else None,
    )


@app.route("/stock/<ticker>")
def stock_detail(ticker):
    """Hisse detay sayfası"""
    # 3 farklı zaman dilimini (Saatlik, Günlük, Haftalık) paralel analiz et
    from concurrent.futures import ThreadPoolExecutor
    
    def analyze_tf(tf_interval, tf_period):
        try:
            return analyze_stock(ticker, period=tf_period, interval=tf_interval)
        except Exception as e:
            return {"error": str(e), "interval": tf_interval}
            
    configs = [
        ("1h", "1mo"),
        ("1d", "6mo"),
        ("1wk", "2y")
    ]
    
    timeframes = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(analyze_tf, interval, period): interval for interval, period in configs}
        for future in futures:
            interval = futures[future]
            try:
                timeframes[interval] = future.result()
            except Exception as e:
                timeframes[interval] = {"error": str(e), "interval": interval}
                
    # Timeframe cache'e kaydet
    _stock_timeframe_cache[ticker] = timeframes
    
    # Varsayılan olarak günlük analiz sonucunu result değişkenine bağlayalım
    default_result = timeframes.get("1d")
    
    # Eğer günlük analiz başarılıysa, app seviyesindeki genel cache'e de koyalım (navigasyon uyumluluğu)
    if default_result and not default_result.get("error"):
        _analysis_cache[ticker] = default_result
        
    return render_template("stock_detail.html", timeframes=timeframes, result=default_result)


@app.route("/fund/<code>")
def fund_detail(code):
    """Yatırım fonu detay sayfası"""
    from analysis.tefas_fetcher import fetch_and_analyze_funds, get_fund_historical_data
    
    # Cache'de ara
    fund_info = None
    for key, val in _analysis_cache.items():
        if val.get("type") == "Yatırım Fonu" and val.get("code") == code:
            fund_info = val
            break
            
    if not fund_info:
        # Tekil arama için en büyük 500 fondan arayalım
        funds = fetch_and_analyze_funds(top_n=500)
        for f in funds:
            if f["code"] == code:
                signal_class_map = {
                    "GÜÇLÜ TREND": "buy",
                    "NÖTR": "hold",
                    "ZAYIF TREND": "sell"
                }
                f["signal_class"] = signal_class_map.get(f["signal"], "hold")
                f["ticker"] = f["code"]
                f["overall_score"] = f["score"]
                _analysis_cache[code] = f
                fund_info = f
                break
                
    if not fund_info:
        return "Yatırım fonu bulunamadı", 404
        
    # Tarihsel fiyat verilerini çek (grafik için)
    history = get_fund_historical_data(code, days=30)
    
    return render_template("fund_detail.html", result=fund_info, history=history)


@app.route("/ai-comment/<ticker>")
def ai_comment(ticker):
    """Gemini AI yorum endpoint — AJAX ile çağrılır"""
    interval = request.args.get("interval", "1d")
    
    # Eğer bir fon kodu ise, cache'deki fonlardan arayalım
    fund_info = None
    for key, val in _analysis_cache.items():
        if val.get("type") == "Yatırım Fonu" and val.get("code") == ticker:
            fund_info = val
            break
            
    if fund_info:
        result = fund_info
    else:
        # Hisse ise, önce timeframe cache'de ara
        if ticker in _stock_timeframe_cache and interval in _stock_timeframe_cache[ticker]:
            result = _stock_timeframe_cache[ticker][interval]
        elif ticker in _analysis_cache and _analysis_cache[ticker].get("interval") == interval:
            result = _analysis_cache[ticker]
        else:
            # Yoksa anlık olarak bu interval ile analiz et
            period = "1mo" if interval == "1h" else ("2y" if interval == "1wk" else "6mo")
            result = analyze_stock(ticker, period=period, interval=interval)
            # Zaman dilimi cache'ine kaydet
            if ticker not in _stock_timeframe_cache:
                _stock_timeframe_cache[ticker] = {}
            _stock_timeframe_cache[ticker][interval] = result
    
    commentary = get_ai_commentary(result)
    return jsonify({"commentary": commentary})


@app.route("/api/analyze/<ticker>")
def api_analyze(ticker):
    """Tek hisse/fon API endpoint"""
    # Eğer cache'deki fon ise doğrudan döndür
    for key, val in _analysis_cache.items():
        if val.get("type") == "Yatırım Fonu" and val.get("code") == ticker:
            return jsonify(val)
            
    period = request.args.get("period", config.DEFAULT_PERIOD)
    interval = request.args.get("interval", "1d")
    result = analyze_stock(ticker, period, interval)
    _analysis_cache[ticker] = result
    
    return jsonify(result)


@app.route("/api/ai-portfolio", methods=["POST"])
def ai_portfolio():
    """Kullanıcının bütçesi ve vadesine göre Gemini AI'dan portföy önerisi üretir"""
    data = request.get_json() or {}
    budget_str = data.get("budget", "20000")
    horizon = data.get("horizon", "6m")
    
    # Bütçeyi temizle ve sayıya çevir
    try:
        budget = float(str(budget_str).replace(".", "").replace(",", "").replace("TL", "").strip())
    except ValueError:
        budget = 20000.0
        
    vade_map = {
        "1m": "1 Ay (Çok Kısa Vade)",
        "3m": "3 Ay (Kısa Vade)",
        "6m": "6 Ay (Orta Vade)",
        "1y": "1 Yıl (Uzun Vade)"
    }
    vade_name = vade_map.get(horizon, "6 Ay (Orta Vade)")
    
    # Cache'deki en yüksek puanlı varlıkları seç (top 10 hisse, top 10 fon)
    top_stocks = []
    top_funds = []
    
    for key, val in _analysis_cache.items():
        if val.get("type") == "Hisse":
            top_stocks.append(val)
        elif val.get("type") == "Yatırım Fonu":
            top_funds.append(val)
            
    # Puanlara göre sırala
    top_stocks = sorted(top_stocks, key=lambda x: x.get("score", x.get("overall_score", 50)), reverse=True)[:10]
    top_funds = sorted(top_funds, key=lambda x: x.get("score", x.get("overall_score", 50)), reverse=True)[:10]
    
    # Eğer cache boşsa hızlıca BIST-30 ve büyük fonları analiz edip ekleyelim (sıfır-kurulum uyumluluğu)
    if not top_stocks and not top_funds:
        print("[INFO] AI Portföy için cache boş. Hızlı BIST-30 ve büyük fon taraması başlatılıyor...")
        default_tickers = ["THYAO.IS", "AKBNK.IS", "YKBNK.IS", "BIMAS.IS", "EREGL.IS", "TUPRS.IS"]
        for ticker in default_tickers:
            try:
                res = analyze_stock(ticker, period="6mo", interval="1d")
                top_stocks.append(res)
                _analysis_cache[ticker] = res
            except Exception:
                pass
                
        try:
            from analysis.tefas_fetcher import fetch_and_analyze_funds
            funds = fetch_and_analyze_funds(top_n=10)
            signal_class_map = {"GÜÇLÜ TREND": "buy", "NÖTR": "hold", "ZAYIF TREND": "sell"}
            for f in funds:
                f["signal_class"] = signal_class_map.get(f["signal"], "hold")
                f["ticker"] = f["code"]
                f["overall_score"] = f["score"]
                top_funds.append(f)
                _analysis_cache[f["code"]] = f
        except Exception as e:
            print(f"[UYARI] Hızlı fon analizi başarısız: {e}")
            
    # En iyi varlıkları birleştir
    top_assets = sorted(top_stocks + top_funds, key=lambda x: x.get("score", x.get("overall_score", 50)), reverse=True)[:15]
    
    # Gemini AI portföy tavsiyesi üret
    from analysis.ai_commentary import get_ai_portfolio_recommendation
    recommendation = get_ai_portfolio_recommendation(budget, vade_name, top_assets)
    
    return jsonify({"recommendation": recommendation})


if __name__ == "__main__":
    host = config.FLASK_HOST
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print("=" * 60)
    print("  [ANALIZ] BIST Teknik Analiz ve Fon Ajanı")
    print(f"  [WEB] http://{display_host}:{config.FLASK_PORT}")
    if host == "0.0.0.0":
        print("  [WIFI] Ayni WiFi'daki cihazlardan erisilebilir")
    print("=" * 60)
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
