import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'quote': 0,              # No cache (always fresh)
    'news': 0,               # No cache (always fresh)
    'candles': 86400,        # 1 day
    'financials': 86400,     # 1 day
    'profile': 604800,       # 1 week
    'peers': 604800,         # 1 week
    'recommendations': 86400, # 1 day
    'insiders': 86400,       # 1 day
    'earnings': 86400        # 1 day
}

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60
