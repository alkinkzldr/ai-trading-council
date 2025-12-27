from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path

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


    def __init__(self):
        pass

    def classify_regime(self) -> Enum:
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
        if market is None:
            raise ValueError("Market data is required for regime classification.")
        
        return regime

    def should_veto() -> bool:
        pass