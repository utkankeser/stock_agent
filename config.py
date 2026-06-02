"""
BIST Teknik Analiz Ajanı - Konfigürasyon
15 Teknik İndikatör ile Kapsamlı Analiz
"""

import os
from dotenv import load_dotenv

# .env dosyasından gizli anahtarları yükle
load_dotenv()

# Flask Ayarları
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Gemini AI API Anahtarı (.env dosyasından okunur — BURAYA YAZMAYIN!)
# Ücretsiz key: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Veri Çekme Ayarları
DEFAULT_PERIOD = "6mo"  # Varsayılan veri periyodu (1mo, 3mo, 6mo, 1y, 2y)
DATA_INTERVAL = "1d"     # Veri aralığı (1d, 1wk, 1mo)

# =============================================
# Teknik Analiz Parametreleri
# =============================================

# RSI (Relative Strength Index)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD (Moving Average Convergence Divergence)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# SMA (Simple Moving Average)
SMA_SHORT = 20
SMA_LONG = 50

# EMA (Exponential Moving Average)
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
ADX_STRONG_TREND = 25

# CCI (Commodity Channel Index)
CCI_PERIOD = 20
CCI_OVERBOUGHT = 100
CCI_OVERSOLD = -100

# Williams %R
WILLIAMS_PERIOD = 14
WILLIAMS_OVERBOUGHT = -20
WILLIAMS_OVERSOLD = -80

# OBV (On Balance Volume)
OBV_SMA_PERIOD = 20  # OBV eğilimini ölçmek için SMA periyodu

# MFI (Money Flow Index)
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20

# Parabolic SAR
PSAR_AF = 0.02    # Acceleration Factor
PSAR_MAX_AF = 0.2

# Ichimoku Cloud
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN = 26
ICHIMOKU_SENKOU = 52

# ROC (Rate of Change)
ROC_PERIOD = 12

# CMF (Chaikin Money Flow)
CMF_PERIOD = 20
CMF_BULLISH = 0.05
CMF_BEARISH = -0.05

# ATR (Average True Range)
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.5

# McGinley Dynamic
MCGINLEY_PERIOD = 14

# SMI (Stochastic Momentum Index)
SMI_FAST = 5
SMI_SLOW = 20
SMI_SIGNAL = 5

# Zigzag
ZIGZAG_DEVIATION = 5.0


# =============================================
# Sinyal Motoru Ağırlıkları (toplam teknik = 1.0)
# 19 indikatör, dengelenmiş ağırlıklar
# =============================================
WEIGHT_RSI = 0.06
WEIGHT_MACD = 0.06
WEIGHT_SMA = 0.05
WEIGHT_EMA = 0.05
WEIGHT_BOLLINGER = 0.05
WEIGHT_STOCHASTIC = 0.05
WEIGHT_ADX = 0.05
WEIGHT_CCI = 0.05
WEIGHT_WILLIAMS = 0.05
WEIGHT_OBV = 0.05
WEIGHT_MFI = 0.05
WEIGHT_PSAR = 0.05
WEIGHT_ICHIMOKU = 0.05
WEIGHT_ROC = 0.05
WEIGHT_CMF = 0.05
WEIGHT_ATR = 0.06
WEIGHT_MCGINLEY = 0.05
WEIGHT_SMI = 0.06
WEIGHT_ZIGZAG = 0.05

# Haber ağırlığı (genel skordaki)
WEIGHT_NEWS = 0.15

# Sinyal Eşik Değerleri
SIGNAL_BUY_THRESHOLD = 60
SIGNAL_SELL_THRESHOLD = 40

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
