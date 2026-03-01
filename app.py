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
from analysis.signal_engine import analyze_stock, analyze_multiple

app = Flask(__name__)

# Analiz sonuçları cache'i
_analysis_cache = {}


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
    sector_filter = request.args.get("sector", "all")
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector=sector_filter,
        results=_analysis_cache,
    )


@app.route("/analyze", methods=["POST"])
def run_analysis():
    """Tüm hisseleri analiz et"""
    global _analysis_cache
    
    sector = request.form.get("sector", "all")
    period = request.form.get("period", config.DEFAULT_PERIOD)
    scan_mode = request.form.get("scan_mode", "quick")  # quick veya detailed
    max_stocks_str = request.form.get("max_stocks", "100")
    
    # Max hisse sayısını parse et
    try:
        max_stocks = int(max_stocks_str) if max_stocks_str != "all" else None
    except ValueError:
        max_stocks = 100
    
    skip_news = (scan_mode == "quick")
    
    # Hangi hisseleri analiz edeceğiz
    if sector == "all":
        tickers = get_all_tickers()
    else:
        tickers = list(get_stocks_by_sector(sector).keys())
    
    # Analiz yap (paralel, sınırlı, modlu)
    results = analyze_multiple(tickers, period, skip_news=skip_news, max_stocks=max_stocks)
    
    # Cache'e kaydet
    results_dict = {}
    for r in results:
        _analysis_cache[r["ticker"]] = r
        results_dict[r["ticker"]] = r
    
    # Skora göre sıralı liste oluştur (template için)
    sorted_results = sorted(results_dict.items(), key=lambda x: x[1]["overall_score"], reverse=True)
    
    return render_template(
        "index.html",
        stocks=get_all_stocks(),
        sectors=get_sectors(),
        stock_count=get_stock_count(),
        selected_sector=sector,
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

@app.route("/stock/<ticker>")
def stock_detail(ticker):
    """Hisse detay sayfası"""
    # Eğer cache'de yoksa yeni analiz yap
    if ticker not in _analysis_cache:
        result = analyze_stock(ticker)
        _analysis_cache[ticker] = result
    else:
        result = _analysis_cache[ticker]
    
    return render_template("stock_detail.html", result=result)


@app.route("/api/analyze/<ticker>")
def api_analyze(ticker):
    """Tek hisse API endpoint"""
    period = request.args.get("period", config.DEFAULT_PERIOD)
    result = analyze_stock(ticker, period)
    _analysis_cache[ticker] = result
    
    # DataFrame olmayan alanları JSON olarak döndür
    safe_result = {k: v for k, v in result.items()}
    return jsonify(safe_result)


if __name__ == "__main__":
    print("=" * 60)
    print("  📊 BIST Teknik Analiz Ajanı")
    print("  🌐 http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
