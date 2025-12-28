from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data import data_provider
from data import cache_manager
from data import market_calculator
from config import settings


class MarketRegime(Enum):
    BULL_TREND = "BULL_TREND" # Strong upward market trend
    BEAR_TREND = "BEAR_TREND" # Strong downward market trend
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE" # Sudden increase in market volatility
    STAGNATION = "STAGNATION" # Little to no market movement
    RANGE_BOUND = "RANGE_BOUND" # Market moving within a defined range
    LOW_LIQUIDITY = "LOW_LIQUIDITY" # Reduced market liquidity conditions

@dataclass
class RegimeGuardian:

    def classify_regime(self, symbol) -> Enum:
        """Classify the market regime based on the provided data.
        CONDITIONS:
        - BULL_TREND: Sustained upward movement in prices, higher highs and higher lows.
        - BEAR_TREND: Sustained downward movement in prices, lower highs and lower
        - VOLATILITY_SPIKE: Sudden large price movements, increased VIX index.
        - STAGNATION: Minimal price movement over a defined period, low volume.
        - RANGE_BOUND: Prices oscillating between defined support and resistance levels.
        - LOW_LIQUIDITY: Reduced trading volume, wider bid-ask spreads.

        Args:
            data (dict): A dictionary containing market indicators.

        Returns:
            Enum: The classified market regime.
        """
        mc = market_calculator.MarketCalculator()
        data = mc.fetch_market(symbol)
        
        if data.get("vix") > 30:
            regime = "VOLATILITY_SPIKE"
        elif data.



    def should_veto() -> bool:
        pass





if __name__ == "__main__":
    mc = market_calculator.MarketCalculator()
    dp = data_provider.DataProvider()
    # bec of 60 api call limit, test 20 random symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "FB", "BRK.B", "JNJ", "V", "WMT",
               "JPM", "MA", "PG", "UNH", "NVDA", "HD", "DIS", "PYPL", "BAC", "VZ"] 
    results = mc.fetch_market("AMZN")
    df = pd.DataFrame([results])
    df.to_csv("results.csv", index=True)

    
    print("Market data fetched successfully.")
