"""
Gemini AI Yorum Modülü
Teknik analiz sonuçlarını Google Gemini'ye gönderip doğal dilde yorum alır.
Ücretsiz API: https://aistudio.google.com/apikey
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# .env dosyasından gizli anahtarları yükle
load_dotenv()

# API key ve model
_api_key = os.environ.get("GEMINI_API_KEY", "")
_model = None

def set_api_key(key):
    """API key'i ayarla ve modeli başlat."""
    global _api_key, _model
    _api_key = key
    if key:
        genai.configure(api_key=key)
        _model = genai.GenerativeModel("gemini-3.5-flash")

# Import anında anahtar varsa otomatik başlat
if _api_key:
    set_api_key(_api_key)


def get_ai_commentary(result):
    """
    Teknik analiz veya fon sonuçlarından Gemini ile yorum üretir.

    Args:
        result: analyze_stock() veya fon analizi çıktısı

    Returns:
        str: AI tarafından üretilmiş Türkçe yorum
    """
    if not _api_key or not _model:
        return "⚠️ Gemini API anahtarı ayarlanmamış. .env dosyasına GEMINI_API_KEY ekleyin.\n\nAPI key almak için: https://aistudio.google.com/apikey"

    if result.get("type") == "Yatırım Fonu":
        prompt = _build_fund_prompt(result)
    else:
        prompt = _build_prompt(result)

    try:
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Gemini API hatası: {str(e)}"


def _build_prompt(result):
    """Analiz sonuçlarından Gemini prompt'u oluşturur."""
    code = result.get("code", "?")
    name = result.get("name", "?")
    signal = result.get("signal", "?")
    overall = result.get("overall_score", 50)
    tech = result.get("technical_score", 50)
    news = result.get("news_score", 50)
    interval = result.get("interval", "1d")
    
    interval_name = "Günlük (Orta Vade - 1 Günlük Mumlar)"
    if interval == "1h":
        interval_name = "Saatlik (Kısa Vade - 1 Saatlik Mumlar)"
    elif interval == "1wk":
        interval_name = "Haftalık (Uzun Vade - 1 Haftalık Mumlar)"

    # Fiyat bilgileri
    indicators = result.get("indicators", {}) or {}
    price_info = indicators.get("price_info", {})
    price = price_info.get("current", "?")
    change_1d = price_info.get("change_1d", 0)
    change_1w = price_info.get("change_1w", 0)
    change_1m = price_info.get("change_1m", 0)

    # İndikatör özetleri
    indicator_lines = []
    details = result.get("details", [])
    for d in details:
        indicator_lines.append(f"- {d['indicator']}: {d['value']} → {d['signal']} ({d['description']})")

    indicators_text = "\n".join(indicator_lines) if indicator_lines else "İndikatör verisi yok"

    prompt = f"""Sen bir profesyonel borsa analisti ve yatırım danışmanısın. Aşağıdaki BIST hissesinin teknik analiz sonuçlarını inceleyip Türkçe bir yorum yaz.

**Hisse:** {name} ({code})
**Fiyat:** ₺{price}
**Analiz Edilen Mum Süresi (Zaman Dilimi):** {interval_name}
**Günlük değişim:** %{change_1d}
**Haftalık değişim:** %{change_1w}
**Aylık değişim:** %{change_1m}

**Teknik Skor:** {tech}/100
**Haber Skoru:** {news}/100
**Genel Skor:** {overall}/100
**Sistem Önerisi:** {signal}

**15 İndikatör Detayları:**
{indicators_text}

Şu kurallara uyarak 3-4 paragraf yorum yaz:
1. Her indikatörün ne anlama geldiğini basitçe açıkla
2. AL, SAT ve NÖTR sinyallerinin nedenlerini belirt
3. Analiz edilen mum süresine ({interval_name}) göre kısa veya uzun vadeli beklentileri ayrı değerlendir
4. Olası risk ve fırsatları belirt
5. Sonunda net bir özet cümle ver
6. Bu bir yatırım tavsiyesi DEĞİLDİR uyarısını ekle
7. Yorum profesyonel ama anlaşılır olsun"""

    return prompt


def _build_fund_prompt(result):
    """Yatırım fonu analiz sonuçlarından Gemini prompt'u oluşturur."""
    code = result.get("code", "?")
    name = result.get("name", "?")
    category = result.get("category", "?")
    price = result.get("price", 0.0)
    daily_ret = result.get("daily_return", 0.0)
    weekly_ret = result.get("weekly_return", 0.0)
    monthly_ret = result.get("monthly_return", 0.0)
    three_month_ret = result.get("three_month_return", 0.0)
    six_month_ret = result.get("six_month_return", 0.0)
    yearly_ret = result.get("yearly_return", 0.0)
    portfolio_size = result.get("portfolio_size", 0.0)
    investors = result.get("investor_count", 0)
    risk_value = result.get("risk_value", 3)
    score = result.get("score", 50)
    signal = result.get("signal", "?")

    # Format portfolio size as Million TL
    portfolio_m_tl = portfolio_size / 1_000_000.0 if portfolio_size else 0.0

    prompt = f"""Sen profesyonel bir fon yöneticisi ve yatırım danışmanısın. Aşağıdaki TEFAS Yatırım Fonunun performans ve risk verilerini analiz edip Türkçe kapsamlı bir yorum yaz.

**Fon:** {name} ({code})
**Kategori:** {category}
**Güncel Fiyat:** ₺{price:.6f}
**Portföy Büyüklüğü:** ₺{portfolio_m_tl:,.2f} Milyon TL
**Yatırımcı Sayısı:** {investors:,}
**Risk Değeri (1-7):** {risk_value} (1 en düşük, 7 en yüksek risk)

**Dönemlik Getiri Performansı:**
- Günlük Getiri: %{daily_ret:+.2f}
- Haftalık Getiri: %{weekly_ret:+.2f}
- Aylık Getiri: %{monthly_ret:+.2f}
- 3 Aylık Getiri: %{three_month_ret:+.2f}
- 6 Aylık Getiri: %{six_month_ret:+.2f}
- 1 Yıllık Getiri: %{yearly_ret:+.2f}

**Momentum Trend Skoru:** {score}/100
**Sistem Getiri Sinyali:** {signal}

Şu kurallara uyarak 3-4 paragraf yorum yaz:
1. Fonun kategorisini ve risk değerini değerlendirerek hangi yatırımcı profiline (muhafazakar, dengeli, agresif) uygun olduğunu açıkla.
2. Kısa vadeli (haftalık, aylık) ve orta/uzun vadeli (3 ay, 6 ay, 1 yıl) getiri performansını enflasyon ve genel piyasa koşulları çerçevesinde yorumla.
3. Fonun momentum skoru ve sinyaline göre ("GÜÇLÜ TREND", "NÖTR", "ZAYIF TREND") fona yeni giriş veya mevcut pozisyonları koruma/azaltma durumunu değerlendir.
4. Bu fona yatırım yaparken dikkat edilmesi gereken olası riskleri (kur riski, hisse senedi piyasası oynaklığı, faiz riski vb.) ve avantajları belirt.
5. Sonunda net bir özet cümle ver.
6. Bu bir yatırım tavsiyesi DEĞİLDİR uyarısını ekle.
7. Yorum profesyonel ama anlaşılır olsun."""

    return prompt


def get_ai_portfolio_recommendation(budget, period, top_assets):
    """
    Kullanıcının yatırım bütçesi ve vadesine göre Gemini AI'dan portföy dağılım önerisi alır.
    """
    if not _api_key or not _model:
        return "⚠️ Gemini API anahtarı ayarlanmamış. .env dosyasına GEMINI_API_KEY ekleyin."

    assets_text = ""
    for idx, asset in enumerate(top_assets, 1):
        atype = asset.get("type", "Hisse")
        code = asset.get("code", asset.get("ticker", "?"))
        name = asset.get("name", "?")
        score = asset.get("score", asset.get("overall_score", 50))
        signal = asset.get("signal", "?")
        price = asset.get("price", 0.0)
        daily_return = asset.get("daily_return", 0.0)
        monthly_return = asset.get("monthly_return", 0.0)
        category = asset.get("category", "?")
        
        assets_text += f"{idx}. [{atype}] Kod: {code} | İsim: {name} | Kategori: {category} | Fiyat: ₺{price} | Günlük Getiri: %{daily_return:.2f} | Aylık Getiri: %{monthly_return:.2f} | Skor: {score}/100 | Sinyal: {signal}\n"

    prompt = f"""Sen dünya çapında yetkili ve deneyimli bir Türk finansal portföy yöneticisi, borsa analisti ve yatırım danışmanısın.
Kullanıcının belirtmiş olduğu yatırım bütçesi, yatırım vadesi ve elimizde bulunan canlı teknik analiz verilerine dayanarak kişiselleştirilmiş, dengeli ve çeşitlendirilmiş bir portföy dağılım önerisi hazırlayacaksın.

**Yatırım Bütçesi:** ₺{budget:,.2f} TL
**Yatırım Hedef Vadesi (Getiri Süresi):** {period}

Aşağıda, sistemimizin canlı olarak yfinance ve TEFAS üzerinden çektiği, puanı ve performansı en yüksek olan hisse ve yatırım fonlarının listesi bulunmaktadır. Portföy dağıtımını yaparken bu listedeki varlıkları referans almalısın:

**Mevcut En İyi Performans Gösteren Aday Varlıklar:**
{assets_text}

Senden istenenler:
1. **Bütçe Dağılım Tablosu**: ₺{budget:,.2f} TL'lik toplam bütçeyi tam olarak kaça böleceğini (TL ve yüzde bazında) gösteren temiz bir Markdown tablosu oluştur. Tabloda: Varlık Türü (Hisse/Fon), Varlık Kodu ve Adı, Dağılım Yüzdesi (%), Ayrılan Tutar (TL), Kısa Gerekçe sütunları bulunsun. Sadece listedeki varlıkları kullanmaya özen göster, bütçeyi küsuratlı bırakma, toplamı tam ₺{budget:,.2f} TL ve %100 olsun.
2. **Stratejik Dağılım Gerekçesi**: Neden bu vadeye ({period}) ve bu bütçeye ({budget:,.2f} TL) bu dağılımı uygun gördüğünü profesyonelce açıkla. Örneğin, çok kısa vadede para piyasası fonları veya likit hisseler ağırlıklı olabilir, uzun vadede ise hisse yoğun fonlar ve büyüme hisseleri öne çıkabilir.
3. **Risk Yönetimi ve Stop-Loss Önerileri**: Yatırımcının kayıp yaşamaması için alabileceği tedbirleri, stop-loss seviyelerini ve risk yönetimi tüyolarını paylaş.
4. **Vadeye Özel AI İpuçları**: Seçilen vadeye ({period}) özel olarak yatırımcının nelere dikkat etmesi gerektiğini maddeler halinde yaz.
5. **Yatırım Tavsiyesi Değildir (YTD) Uyarısı**: En sona belirgin bir şekilde ekle.

Lütfen cevabı son derece profesyonel, anlaşılır, yatırımcıyı heyecanlandıracak ve bilgilendirecek şekilde Türkçe olarak yaz. Markdown formatını en estetik şekilde kullan (kalın yazılar, listeler, tablolar)."""

    try:
        response = _model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Gemini API hatası: {str(e)}"
