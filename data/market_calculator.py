import numpy as np
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
import yfinance as yf
import anthropic
import finnhub
import ta
import pandas as pd


sys.path.append(str(Path(__file__).resolve().parents[1]))

from data import data_provider
from data import cache_manager
from config import settings


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
        self.cache_manager = cache_manager.CacheManager()
        self.data_provider = data_provider.DataProvider(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

    def prepare_data(self, raw_data):
        # Implement data preparation logic here
        pass

    def fetch_market(self, symbol):
        """Fetch market data for a specific symbol.

        Args:
            symbol (str): The stock symbol to fetch data for.

        Returns:
            dict: A dictionary containing various market indicators.
        """
        vix = self.calculate_vix(symbol)
        vix_condition = self.check_vix_condition(vix)
        ma = self.calculate_ma(symbol)
        rsi = self.calculate_rsi(symbol)
        rsi_condition = self.check_rsi_condition(rsi)
        macd = self.calculate_macd(symbol)
        macd_condition = self.check_macd_condition(macd)
        bollinger_bands = self.calculate_bollinger_bands(symbol)
        bollinger_condition = self.check_bollinger_condition(bollinger_bands, symbol)
        adx = self.calculate_adx(symbol)

        return {
            "vix": vix,
            "vix_condition": vix_condition,
            "ma": ma,
            "rsi": rsi,
            "rsi_condition": rsi_condition,
            "macd": macd,
            "macd_condition": macd_condition,
            "bollinger_bands": bollinger_bands,
            "bollinger_condition": bollinger_condition,
            "adx": adx
        }

    def fetch_all_markets(self, symbols: list) -> dict:
        market_data = {}
        for symbol in symbols:
            market_data[symbol] = self.fetch_market(symbol)
        return market_data


    ########################
    #### Calculations ####
    ########################

    def calculate_vix(self, symbol) -> float:
        # Implement VIX calculation logic here
        # 1. set a range of call and put strikes on lookback_period
        # Formula: 

        #fecth proice with data provider
        history = self.data_provider.historical_30_data(symbol)
        closings = history['Close']
        daily_returns = closings.pct_change().dropna()

        # volatility meaning: standard deviation of daily returns, meaning how much the price fluctuates on a daily basis
        volatility = daily_returns.std()
        vix = volatility * np.sqrt(252) * 100 # Annualize the volatility
        return vix

    
    def calculate_ma(self, symbol: str) -> tuple:
        """
        Calculate 50-day and 200-day moving averages and determine trend.
        ma = Moving Average = indicates trend direction
        Args:
            symbol (str): _stock symbol_
        Returns:
            tuple: _ma50, ma200, trend_
        """
        ticker = yf.Ticker(symbol)
        current_price = self.data_provider.get_current_price(symbol)
        #history = self.data_provider.historical_30_data(symbol)
        history50 = ticker.history(period="50d")
        history200 = ticker.history(period="200d")
        ma50 = float(np.mean(history50['Close'].rolling(window=50).mean().iloc[-1]))
        ma200 = float(np.mean(history200['Close'].rolling(window=200).mean().iloc[-1]))

        trend = {
            "strong uptrend": current_price > ma50 > ma200,
            "uptrend": current_price > ma50 and ma50 < ma200,
            "holding": current_price < ma50 > ma200,
            "downtrend": current_price < ma50 < ma200,
            "unknown": True,
        }

        for key, value in trend.items():
            if value:
                return current_price, ma50, ma200, key

        return current_price, ma50, ma200, "unknown"
    
    def calculate_rsi(self, symbol: str, period: int = 14) -> float:
        """RSI = Measures if a stock is "overbought" (too expensive) or "oversold" (too cheap)

        Args:
            symbol (str): _stock symbol_
            period (int, optional): _lookback period_. Defaults to 14.

        Returns:
            float: _RSI value_
        """
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="max")
        close = history['Close']

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]


    def calculate_macd(self, symbol: str) -> tuple:
        """Calculate MACD and signal line
        MACD = Shows momentum (how fast price is changing) and trend direction


        Args:
            symbol (str): _stock symbol_

        Returns:
            tuple: _MACD value, signal line value_
        """
        #default periods
        short_period = 12
        long_period = 26
        signal_period = 9

        ticker = yf.Ticker(symbol)
        calc_period = short_period + long_period + signal_period
        history = ticker.history(period="{}d".format(calc_period))
        close = history['Close']

        if len(close) < calc_period:
            return {
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0
            }
        
        macd_indicator = ta.trend.MACD(close, window_slow=long_period, window_fast=short_period, window_sign=signal_period)
        
        #current values
        macd = macd_indicator.macd().iloc[-1]
        signal_line = macd_indicator.macd_signal().iloc[-1]
        histogram = macd_indicator.macd_diff().iloc[-1]

        # Handle NaN
        if pd.isna(macd):
            macd = 0.0
        if pd.isna(signal_line):
            signal_line = 0.0
        if pd.isna(histogram):
            histogram = 0.0

        return {
        'macd': float(macd),
        'signal': float(signal_line),
        'histogram': float(histogram)
    }

        
    def calculate_bollinger_bands(self, symbol: str) -> tuple:
        """Calculate Bollinger Bands
        Bollinger Bands = Indicates volatility and potential overbought/oversold conditions
        upper band: indicates overbought
        lower band: indicates oversold
        middle band: indicates trend direction

        Args:
            symbol (str): The stock symbol to calculate Bollinger Bands for.

        Returns:
            tuple: A tuple containing the upper band, lower band, and middle band.
        """
        period = 20
        num_std_dev = 2

        ticker = yf.Ticker(symbol)
        history = ticker.history(period="max")
        close = history['Close']

        middle_band = close.rolling(window=period).mean()
        std_dev = close.rolling(window=period).std()
        upper_band = middle_band + (std_dev * num_std_dev)
        lower_band = middle_band - (std_dev * num_std_dev)

        return upper_band.iloc[-1], lower_band.iloc[-1], middle_band.iloc[-1]
    
    
    def calculate_adx(self, symbol: str) -> float:
        """Calculate Average Directional Index (ADX)
        ADX = Measures trend strength (not direction)

        Args:
            symbol (str): The stock symbol to calculate ADX for.

        Returns:
            float: The ADX value.
        """
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="max")
        high = history['High']
        low = history['Low']
        close = history['Close']

        # Calculate True Range (TR)
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        # Calculate ADX
        adx = tr.rolling(window=14).mean()
        return adx.iloc[-1]


    ######################
    ### Checkers ##########
    ######################

    def check_bollinger_condition(self, bands: tuple, symbol: str) -> str:
        """Check Bollinger Bands condition

        Args:
            bands (tuple): The Bollinger Bands (upper, lower, middle).
            symbol (str): The stock symbol to check.

        Returns:
            str: The Bollinger Bands condition.
        """
        upper_band, lower_band, middle_band = bands
        current_price = self.data_provider.get_current_price(symbol)

        if current_price > upper_band:
            return "overbought"
        elif current_price < lower_band:
            return "oversold"
        else:
            return "neutral"


    def check_macd_condition(self, macd_data: dict) -> tuple:
        """Check MACD condition
        MACD = Shows momentum (how fast price is changing) and trend direction
        if:
            macd > signal and histogram > 0: BUY
            macd < signal and histogram < 0: SELL
            macd above zero = uptrend bias
            macd below zero = downtrend bias

        Args:
            macd_data (dict): Dictionary with 'macd', 'signal', 'histogram' keys.

        Returns:
            tuple: A tuple containing the MACD condition, confidence level, and message.
        """
        macd = macd_data['macd']
        signal = macd_data['signal']
        histogram = macd_data['histogram']
        

        # Check crossover
        if macd > signal and histogram > 0:
            if histogram > 0.5:  # Strong momentum
                return "STRONG_BUY", 0.85, f"Bullish crossover with strong momentum (hist={histogram:.2f})"
            else:
                return "BUY", 0.70, f"Bullish crossover (hist={histogram:.2f})"

        elif macd < signal and histogram < 0:
            if histogram < -0.5:  # Strong bearish
                return "STRONG_SELL", 0.85, f"Bearish crossover with strong momentum (hist={histogram:.2f})"
            else:
                return "SELL", 0.70, f"Bearish crossover (hist={histogram:.2f})"

        # MACD above zero = uptrend bias
        elif macd > 0:
            return "HOLD", 0.55, "Uptrend but no clear signal"

        # MACD below zero = downtrend bias
        else:
            return "HOLD", 0.45, "Downtrend but no clear signal"
        
    
    def check_rsi_condition(self, rsi: float) -> str:
        """Define RSI condition

        Args:
            rsi (float): _RSI value_

        Returns:
            str: _RSI condition_
        """
        if rsi < 30:
            return "oversold"
        elif rsi > 70:
            return "overbought"
        else:
            return "neutral"
        
    def check_vix_condition(self, vix: float) -> str:
        vix_classes = {
            "extremely_calm": vix < 10,
            "very_calm": 10 <= vix < 15,
            "calm": 15 <= vix < 20,
            "slightly_nervous": 20 <= vix < 25,
            "getting_worried": 25 <= vix < 30,
            "fear": 30 <= vix < 40,
            "extreme_fear": vix >= 40,
            "extreme_panic": vix > 50,
        }

        for condition, is_met in vix_classes.items():
            if is_met:
                return condition

        return "unknown"

    def check_adx_condition(self, adx: float) -> str:
        """Define ADX condition

        Args:
            adx (float): _ADX value_

        Returns:
            str: _ADX condition_
        """
        if adx < 20:
            return "weak trend"
        elif 20 <= adx < 40:
            return "moderate trend"
        elif 40 <= adx < 60:
            return "strong trend"
        else:
            return "very strong trend"


if __name__ == "__main__":
    mc = MarketCalculator()
    dp = data_provider.DataProvider()
    # bec of 60 api call limit, test 20 random symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "FB", "BRK.B", "JNJ", "V", "WMT",
               "JPM", "MA", "PG", "UNH", "NVDA", "HD", "DIS", "PYPL", "BAC", "VZ"] 
    results = mc.fetch_market("AMZN")
    print(results)
    print("Market data fetched successfully.")
    all_results = mc.fetch_all_markets(symbols)
    print(all_results)
    print("All market data fetched successfully.")