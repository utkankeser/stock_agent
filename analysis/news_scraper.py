"""
Haber Toplama Modülü
Finans sitelerinden hisse bazlı haber çeker ve basit duygu analizi yapar.
Sadece son 2 ay içindeki haberler dikkate alınır.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# Haber cache'i (bellekte tutar, tekrar çekmemek için)
_news_cache = {}
_cache_timestamps = {}

# Haberlerin maksimum yaşı (gün)
NEWS_MAX_AGE_DAYS = 60  # 2 ay


def fetch_news(ticker):
    """
    Belirli bir hisse için SON 2 AY içindeki haberleri çeker.
    
    Args:
        ticker: yfinance ticker (ör: "THYAO.IS")
    
    Returns:
        list: Haber dict listesi [{title, source, url, date, sentiment}]
    """
    # Cache kontrolü
    if ticker in _news_cache:
        cache_time = _cache_timestamps.get(ticker)
        if cache_time:
            diff = (datetime.now() - cache_time).total_seconds() / 60
            if diff < config.NEWS_CACHE_MINUTES:
                return _news_cache[ticker]
    
    stock_code = ticker.replace(".IS", "")
    news_list = []
    
    # Kaynak 1: Yahoo Finance haberleri (yfinance üzerinden)
    try:
        yahoo_news = _fetch_yahoo_news(ticker)
        news_list.extend(yahoo_news)
    except Exception as e:
        print(f"  [UYARI] Yahoo haberleri çekilemedi: {e}")
    
    # Kaynak 2: Google arama sonuçları (son 1 ay ile sınırlı)
    try:
        google_news = _fetch_google_results(stock_code)
        news_list.extend(google_news)
    except Exception as e:
        print(f"  [UYARI] Google haberleri çekilemedi: {e}")
    
    # Eski haberleri filtrele (2 aydan eski olanları çıkar)
    cutoff_date = datetime.now() - timedelta(days=NEWS_MAX_AGE_DAYS)
    filtered_news = []
    for news in news_list:
        news_date = _parse_date(news.get("date", ""))
        if news_date and news_date >= cutoff_date:
            filtered_news.append(news)
        elif not news_date:
            # Tarih parse edilemezse, güvenli tarafta kal ve dahil et
            # ama "tarih bilinmiyor" olarak işaretle
            news["date"] = "Tarih bilinmiyor"
            filtered_news.append(news)
    
    news_list = filtered_news
    
    # Duygu analizi yap
    for news in news_list:
        news["sentiment"] = _analyze_sentiment(news["title"])
    
    # En fazla N haber tut
    news_list = news_list[:config.NEWS_MAX_ARTICLES]
    
    # Cache'e kaydet
    _news_cache[ticker] = news_list
    _cache_timestamps[ticker] = datetime.now()
    
    return news_list


def _parse_date(date_str):
    """
    Tarih string'ini datetime objesine çevirir.
    Farklı formatları dener.
    
    Returns:
        datetime veya None
    """
    if not date_str or date_str == "Tarih bilinmiyor":
        return None
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%B %d, %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Göreceli tarih ifadelerini dene (ör: "2 gün önce", "3 hours ago")
    relative = _parse_relative_date(date_str)
    if relative:
        return relative
    
    return None


def _parse_relative_date(text):
    """
    '2 gün önce', '3 saat önce', '1 week ago' gibi göreceli tarihleri parse eder.
    """
    text = text.lower().strip()
    now = datetime.now()
    
    # Türkçe kalıplar
    tr_patterns = [
        (r"(\d+)\s*dakika\s*önce", "minutes"),
        (r"(\d+)\s*saat\s*önce", "hours"),
        (r"(\d+)\s*gün\s*önce", "days"),
        (r"(\d+)\s*hafta\s*önce", "weeks"),
        (r"(\d+)\s*ay\s*önce", "months"),
        (r"dün", "yesterday"),
        (r"bugün", "today"),
    ]
    
    # İngilizce kalıplar
    en_patterns = [
        (r"(\d+)\s*min(?:ute)?s?\s*ago", "minutes"),
        (r"(\d+)\s*hours?\s*ago", "hours"),
        (r"(\d+)\s*days?\s*ago", "days"),
        (r"(\d+)\s*weeks?\s*ago", "weeks"),
        (r"(\d+)\s*months?\s*ago", "months"),
        (r"yesterday", "yesterday"),
        (r"today", "today"),
    ]
    
    for pattern, unit in tr_patterns + en_patterns:
        match = re.search(pattern, text)
        if match:
            if unit == "yesterday":
                return now - timedelta(days=1)
            elif unit == "today":
                return now
            
            amount = int(match.group(1))
            if unit == "minutes":
                return now - timedelta(minutes=amount)
            elif unit == "hours":
                return now - timedelta(hours=amount)
            elif unit == "days":
                return now - timedelta(days=amount)
            elif unit == "weeks":
                return now - timedelta(weeks=amount)
            elif unit == "months":
                return now - timedelta(days=amount * 30)
    
    return None


def _fetch_yahoo_news(ticker):
    """Yahoo Finance'dan haber çeker (yfinance üzerinden). Gerçek tarihlerini çıkarır."""
    import yfinance as yf
    
    news_list = []
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if news:
            for item in news[:8]:  # biraz fazla çek, filtrede azalabilir
                content = item.get("content", {})
                title = content.get("title", item.get("title", ""))
                provider = content.get("provider", {})
                source = provider.get("displayName", "Yahoo Finance") if isinstance(provider, dict) else "Yahoo Finance"
                
                # Gerçek yayın tarihini çıkar
                pub_date = _extract_yahoo_date(item, content)
                
                # URL çıkartma
                url = ""
                canonical_url = content.get("canonicalUrl", {})
                if isinstance(canonical_url, dict):
                    url = canonical_url.get("url", "")
                if not url:
                    click_through = content.get("clickThroughUrl", {})
                    if isinstance(click_through, dict):
                        url = click_through.get("url", "")
                
                if title:
                    news_list.append({
                        "title": title,
                        "source": source,
                        "url": url,
                        "date": pub_date,
                    })
    except Exception:
        pass
    
    return news_list


def _extract_yahoo_date(item, content):
    """
    Yahoo Finance haber verisinden gerçek yayın tarihini çıkarır.
    """
    # 1. content.pubDate alanını dene
    pub_date = content.get("pubDate", "")
    if pub_date:
        parsed = _parse_date(pub_date)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    
    # 2. item düzeyinde providerPublishTime (Unix timestamp)
    pub_time = item.get("providerPublishTime", content.get("providerPublishTime", None))
    if pub_time:
        try:
            dt = datetime.fromtimestamp(int(pub_time))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass
    
    # 3. content.displayDate
    display_date = content.get("displayDate", "")
    if display_date:
        parsed = _parse_date(display_date)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    
    # 4. Bulunamadıysa bilinmiyor olarak işaretle
    return "Tarih bilinmiyor"


def _fetch_google_results(stock_code):
    """
    Google arama sonuçlarından hisse haberi çeker.
    tbs=qdr:m2 parametresi ile sadece son 2 aydaki haberler aranır.
    """
    news_list = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    query = f"{stock_code} hisse borsa haber"
    # tbs=qdr:m2 → son 2 ay içindeki haberler
    url = f"https://www.google.com/search?q={query}&tbm=nws&hl=tr&num=5&tbs=qdr:m2"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Google haber sonuçlarını parse et
            for item in soup.select("div.SoaBEf, div.dbsr, div.g"):
                title_el = item.select_one("div.n0jPhd, div.mCBkyc, h3")
                link_el = item.select_one("a")
                source_el = item.select_one("div.MgUUmf span, span.WF4CUc, cite")
                date_el = item.select_one("span.WG9SHc span, div.OSrXXb span, time, span.r0bn4c")
                
                if title_el:
                    title = title_el.get_text(strip=True)
                    link = link_el.get("href", "") if link_el else ""
                    source = source_el.get_text(strip=True) if source_el else "Web"
                    
                    # Tarih bilgisini çıkar
                    raw_date = date_el.get_text(strip=True) if date_el else ""
                    pub_date = _resolve_news_date(raw_date)
                    
                    # Google redirect URL'sini temizle
                    if "/url?q=" in link:
                        link = link.split("/url?q=")[1].split("&")[0]
                    
                    news_list.append({
                        "title": title,
                        "source": source,
                        "url": link,
                        "date": pub_date,
                    })
    except Exception:
        pass
    
    return news_list


def _resolve_news_date(raw_date):
    """
    Ham tarih bilgisini standart formata çevirir.
    Google sonuçlarındaki '2 gün önce', '1 hafta önce' gibi ifadeleri işler.
    """
    if not raw_date:
        return "Tarih bilinmiyor"
    
    # Göreceli tarihi dene
    parsed = _parse_relative_date(raw_date)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
    
    # Standart tarih formatını dene
    parsed = _parse_date(raw_date)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
    
    return "Tarih bilinmiyor"


def _analyze_sentiment(text):
    """
    Basit Türkçe duygu analizi yapar.
    
    Returns:
        dict: {score: -1 ile 1 arası, label: "pozitif"/"negatif"/"nötr"}
    """
    text_lower = text.lower()
    
    positive_count = sum(1 for word in config.POSITIVE_KEYWORDS if word in text_lower)
    negative_count = sum(1 for word in config.NEGATIVE_KEYWORDS if word in text_lower)
    
    total = positive_count + negative_count
    
    if total == 0:
        return {"score": 0, "label": "nötr"}
    
    score = (positive_count - negative_count) / total
    
    if score > 0.1:
        label = "pozitif"
    elif score < -0.1:
        label = "negatif"
    else:
        label = "nötr"
    
    return {"score": round(score, 2), "label": label}


def get_news_score(news_list):
    """
    Haber listesinden 0-100 arası bir haber skoru hesaplar.
    
    Returns:
        int: 0-100 arası haber skoru
    """
    if not news_list:
        return 50  # Haber yoksa nötr
    
    sentiments = [n.get("sentiment", {}).get("score", 0) for n in news_list]
    avg_sentiment = sum(sentiments) / len(sentiments)
    
    # -1 ile 1 arasındaki skoru 0-100'e dönüştür
    score = int((avg_sentiment + 1) * 50)
    return max(0, min(100, score))
