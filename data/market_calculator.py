import numpy as np
from data import data_provider
import os
from dotenv import load_dotenv

from data.cache_manager import CacheManager
from config.settings import CACHE_TTL, RATE_LIMIT_PER_MINUTE


# Load env variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

RegimeConditions = {
    "BULL_CONDITION": "bull_condition",
}



class MarketCalculator:
    
    def __init__(self):
        self.cache_manager = CacheManager(ttl=CACHE_TTL)
        self.data_provider = data_provider.DataProvider(rate_limit=RATE_LIMIT_PER_MINUTE)

    def prepare_data(self, raw_data):
        # Implement data preparation logic here
        pass


    ########################
    #### Calculations ####
    ########################

    def calculate_vix(self, prices, lookback_period=30) -> float:
        # Implement VIX calculation logic here
        # 1. set a range of call and put strikes on lookback_period
        # Formula: 

        #fecth proice with data provider
        sp500_price = self.data_provider.fetch_price("SP500")
        pass
