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

    def __post_init__(self):
        self.cache = cache_manager.CacheManager()
        self.mc = market_calculator.MarketCalculator()

    def get_market_data(self, symbol: str, ttl: int = 120) -> dict:
        """Fetch market data with caching.

        Args:
            symbol: Stock symbol
            ttl: Cache time-to-live in seconds (default: 2 minutes)

        Returns:
            Market data dictionary
        """
        cache_key = f"market:{symbol}"
        return self.cache.get_or_set(
            cache_key,
            lambda: self.mc.fetch_market(symbol),
            ttl=ttl
        )

    def classify_regime(self, symbol) -> str:
        """Classify the market regime based on the provided data.

        CONDITIONS:
        - BULL_TREND: Sustained upward movement in prices, higher highs and higher lows.
        - BEAR_TREND: Sustained downward movement in prices, lower highs and lower lows.
        - VOLATILITY_SPIKE: Sudden large price movements, increased VIX index.
        - STAGNATION: Minimal price movement over a defined period, low volume.
        - RANGE_BOUND: Prices oscillating between defined support and resistance levels.
        - LOW_LIQUIDITY: Reduced trading volume, wider bid-ask spreads.

        Args:
            symbol (str): Stock symbol to analyze

        Returns:
            str: The classified market regime.
        """
        data = self.get_market_data(symbol)
        
        # Extract indicators
        vix = data.get("vix", 0)
        adx = data.get("adx", 0)
        macd_result = data.get("macd_result")  # 0: strong bullish, 1: bullish, 2: strong bearish, 3: bearish, 4: no signal
        ma = data.get("ma", {})
        price_position = ma.get("price_position")  # "above" or "below"
        obv_trend = data.get("obv_trend")  # "bullish", "bearish", "neutral"
        bollinger = data.get("bollinger_bands", {})
        bandwidth = bollinger.get("bandwidth", 100)
        volume_data = data.get("volume", {})
        
        # 1. Check VOLATILITY_SPIKE first (highest priority)
        if vix > 30:
            regime = "VOLATILITY_SPIKE"
            return regime
        
        # 2. Check LOW_LIQUIDITY
        if volume_data.get("liquidity") == "low":
            regime = "LOW_LIQUIDITY"
            return regime
        
        # 3. Check for trends (ADX > 25)
        if adx > 25:
            # Check bullish alignment
            bullish_macd = macd_result in [0, 1]  # strong bullish or bullish
            bullish_ma = price_position == "above"
            bullish_obv = obv_trend == "bullish"
            
            if bullish_macd and bullish_ma and bullish_obv:
                regime = "BULL_TREND"
                return regime
            
            # Check bearish alignment
            bearish_macd = macd_result in [2, 3]  # strong bearish or bearish
            bearish_ma = price_position == "below"
            bearish_obv = obv_trend == "bearish"
            
            if bearish_macd and bearish_ma and bearish_obv:
                regime = "BEAR_TREND"
                return regime
            
            # Trend exists but indicators don't align (conflicting signals)
            regime = "RANGE_BOUND"
            return regime
        
        # 4. Check STAGNATION (very weak trend + narrow bands)
        if adx < 15 and bandwidth < 0.05:
            regime = "STAGNATION"
            return regime
        
        # 5. Default to RANGE_BOUND
        regime = "RANGE_BOUND"
        return regime



    def should_veto(self, symbol: str, regime: str, data: dict) -> tuple:
        """
        Determine if trade should be vetoed despite favorable regime
        
        Args:
            symbol (str): Stock symbol
            regime (str): Classified market regime
            data (dict): Market indicators from fetch_market()
        
        Returns:
            tuple: (should_veto: bool, reason: str, severity: str)
                - should_veto: True if trade should be blocked
                - reason: Explanation for veto (or None if no veto)
                - severity: "CRITICAL", "HIGH", "MEDIUM" (or None if no veto)
        """
        veto_reasons = []
                
        # Extract indicators
        rsi = data.get("rsi", 50)
        obv_divergence = data.get("obv_divergence")
        volume_data = data.get("volume", {})
        volume_liquidity = volume_data.get("liquidity")
        bollinger = data.get("bollinger_bands", {})
        bollinger_position = bollinger.get("position")
        vix = data.get("vix", 15)
        adx = data.get("adx", 0)
        macd_result = data.get("macd_result")
        
        # ========================================
        # CRITICAL VETOS (Always block trade)
        # ========================================
        
        if regime == "VOLATILITY_SPIKE":
            return (True, "Market volatility too high (VIX > 30)", "CRITICAL")
        
        if regime == "LOW_LIQUIDITY":
            return (True, "Insufficient market liquidity", "CRITICAL")
        
        if volume_liquidity == "low":
            return (True, "Low trading volume detected", "CRITICAL")
        
        # ========================================
        # HIGH PRIORITY VETOS (Regime-specific)
        # ========================================
        
        if regime == "BULL_TREND":
            if rsi > 75:
                veto_reasons.append("Severely overbought (RSI > 75)")
            
            if obv_divergence == "bearish":
                veto_reasons.append("Bearish volume divergence - smart money exiting")
            
            if bollinger_position in ["far_above", "above_upper"]:
                veto_reasons.append("Price overextended above Bollinger upper band")
            
            if vix > 25:
                veto_reasons.append("VIX elevated despite bullish setup")
        
        elif regime == "BEAR_TREND":
            if rsi < 25:
                veto_reasons.append("Severely oversold (RSI < 25)")
            
            if obv_divergence == "bullish":
                veto_reasons.append("Bullish volume divergence - smart money accumulating")
            
            if bollinger_position in ["far_below", "below_lower"]:
                veto_reasons.append("Price overextended below Bollinger lower band")
            
            if vix > 40:
                veto_reasons.append("VIX extremely high - panic selling, reversal risk")
        
        elif regime == "RANGE_BOUND":
            if volume_liquidity == "low":
                veto_reasons.append("Low volume in range - false breakout risk")
            
            if adx > 20 and adx < 25:
                veto_reasons.append("ADX rising - range may be breaking soon")
            
            bandwidth = bollinger.get("bandwidth", 1.0)
            if bandwidth < 0.05:
                veto_reasons.append("Bollinger bands extremely narrow - breakout imminent")
        
        elif regime == "STAGNATION":
            veto_reasons.append("Market stagnant - low profit opportunity")
        
        # ========================================
        # MEDIUM PRIORITY VETOS (Cross-indicator conflicts)
        # ========================================
        
        # Strong trend but MACD shows no signal
        if adx > 25 and macd_result == 4:
            veto_reasons.append("Trend present but MACD unclear - momentum conflict")
        
        # RSI extreme readings
        if rsi > 80:
            veto_reasons.append("RSI extremely overbought (>80)")
        elif rsi < 20:
            veto_reasons.append("RSI extremely oversold (<20)")
        
        # VIX warning for any regime
        if vix > 35:
            veto_reasons.append("VIX very high (>35) - extreme uncertainty")
        
        # ========================================
        # RETURN VETO DECISION
        # ========================================
        
        if veto_reasons:
            severity = "HIGH" if len(veto_reasons) > 1 else "MEDIUM"
            reason = "; ".join(veto_reasons)
            return (True, reason, severity)
        
        # No veto
        return (False, None, None)





if __name__ == "__main__":
    import json

    rg = RegimeGuardian()
    symbol = "AMZN"

    # Inspect cache
    print("=== CACHE INSPECTION ===")
    cache = rg.cache

    # Show all cached market keys
    keys = cache.client.keys("market:*")
    print(f"Cached keys: {keys}")

    for key in keys:
        ttl = cache.get_ttl(key)
        data = cache.get(key)
        print(f"\n{key} (TTL: {ttl}s):")
        print(json.dumps(data, indent=2, default=str))

    # Show cache stats
    print(f"\nCache stats: {cache.get_stats()}")
    print("========================\n")

    # Run normal flow
    data = rg.get_market_data(symbol)
    regime = rg.classify_regime(symbol)
    print(f"Regime: {regime}")
    veto, reason, severity = rg.should_veto(symbol, regime, data)
    print(f"Veto: {veto}, Reason: {reason}, Severity: {severity}")


