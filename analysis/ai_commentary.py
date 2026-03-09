"""
Gemini AI Yorum Modülü
Teknik analiz sonuçlarını Google Gemini'ye gönderip doğal dilde yorum alır.
Ücretsiz API: https://aistudio.google.com/apikey
"""

import os
import google.generativeai as genai

# API key
_api_key = os.environ.get("GEMINI_API_KEY", "")
_model = None


def set_api_key(key):
    """API key'i ayarla ve modeli başlat."""
    global _api_key, _model
    _api_key = key
    if key:
        genai.configure(api_key=key)
        _model = genai.GenerativeModel("gemini-2.5-flash")


def get_ai_commentary(result):
    """
    Teknik analiz sonuçlarından Gemini ile yorum üretir.

    Args:
        result: analyze_stock() çıktısı

    Returns:
        str: AI tarafından üretilmiş Türkçe yorum
    """
    if not _api_key or not _model:
        return "⚠️ Gemini API anahtarı ayarlanmamış. .env dosyasına GEMINI_API_KEY ekleyin.\n\nAPI key almak için: https://aistudio.google.com/apikey"

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

    # Fiyat bilgileri
    indicators = result.get("indicators", {})
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
3. Kısa ve orta vadeli beklentileri ayrı değerlendir
4. Olası risk ve fırsatları belirt
5. Sonunda net bir özet cümle ver
6. Bu bir yatırım tavsiyesi DEĞİLDİR uyarısını ekle
7. Yorum profesyonel ama anlaşılır olsun"""

    return prompt
