"""
BIST Teknik Analiz Ajanı - Konfigürasyon
"""

# Flask Ayarları
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Veri Çekme Ayarları
DEFAULT_PERIOD = "6mo"  # Varsayılan veri periyodu (1mo, 3mo, 6mo, 1y, 2y)
DATA_INTERVAL = "1d"     # Veri aralığı (1d, 1wk, 1mo)

# =============================================
# Teknik Analiz Parametreleri
# =============================================

# RSI
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# SMA (Basit Hareketli Ortalama)
SMA_SHORT = 20
SMA_LONG = 50

# EMA (Üssel Hareketli Ortalama)
EMA_SHORT = 12
EMA_LONG = 26

# Bollinger Bantları
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0

# Stokastik Osilatör
STOCH_K = 14
STOCH_D = 3
STOCH_SMOOTH = 3
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20

# ADX (Average Directional Index)
ADX_PERIOD = 14
ADX_STRONG_TREND = 25  # Bu değerin üstü güçlü trend

# CCI (Commodity Channel Index)
CCI_PERIOD = 20
CCI_OVERBOUGHT = 100
CCI_OVERSOLD = -100

# Williams %R
WILLIAMS_PERIOD = 14
WILLIAMS_OVERBOUGHT = -20
WILLIAMS_OVERSOLD = -80

# =============================================
# Sinyal Motoru Ağırlıkları (toplam teknik = 1.0)
# =============================================
WEIGHT_RSI = 0.15
WEIGHT_MACD = 0.15
WEIGHT_SMA = 0.10
WEIGHT_EMA = 0.10
WEIGHT_BOLLINGER = 0.10
WEIGHT_STOCHASTIC = 0.10
WEIGHT_ADX = 0.10
WEIGHT_CCI = 0.10
WEIGHT_WILLIAMS = 0.10

# Haber ağırlığı (genel skordaki)
WEIGHT_NEWS = 0.15

# Sinyal Eşik Değerleri
SIGNAL_BUY_THRESHOLD = 60     # Bu skorun üstü = AL
SIGNAL_SELL_THRESHOLD = 40    # Bu skorun altı = SAT
# Arada kalan = TUT

# Haber Ayarları
NEWS_MAX_ARTICLES = 10
NEWS_CACHE_MINUTES = 30

# Duygu Analizi Anahtar Kelimeleri
POSITIVE_KEYWORDS = [
    "yükseliş", "artış", "kar", "rekor", "büyüme", "pozitif", "güçlü",
    "toparlanma", "ralli", "talep", "iyimser", "beklentilerin üzerinde",
    "temettü", "yatırım", "ihracat", "gelir artışı", "hedef yükseltti",
    "al", "öneriyor", "olumlu", "destek", "kırılım", "aşım", "fırsat"
]

NEGATIVE_KEYWORDS = [
    "düşüş", "gerileme", "zarar", "kayıp", "kriz", "negatif", "zayıf",
    "risk", "satış baskısı", "belirsizlik", "endişe", "beklentilerin altında",
    "borç", "dava", "ceza", "soruşturma", "hedef düşürdü", "küçülme",
    "sat", "uyarı", "olumsuz", "direnç", "kırılma", "tehdit", "daralma"
]
