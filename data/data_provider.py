import anthropic
import os
import finnhub
import time
import logging
from typing import Dict, List, Callable, Any
from collections import deque
from dotenv import load_dotenv

from data.cache_manager import CacheManager
from config.settings import CACHE_TTL, RATE_LIMIT_PER_MINUTE


# Load env variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

llm_models = {
    "claude-sonnet-4-5": "claude-sonnet-4-5",  # best model, for active mode
    "claude-haiku-4-5": "claude-haiku-4-5",  # faster, cheaper, for passive mode
    "claude-opus-4-5": "claude-opus-4-5",  # balanced, for general use
    "ollama3.1:latest": "ollama3.1:latest"  # local model
}

# TODO: Add later on with the time zone definer class, in which mode we are operating!


class DataProvider:
    """
    Data provider for Finnhub API with intelligent caching.

    Responsibilities:
    - Fetch data from Finnhub FREE tier endpoints
    - Cache responses using CacheManager
    - Implement rate limiting (60 calls/minute)
    - Handle errors gracefully
    - Track API usage statistics
    """

    def __init__(self, cache_manager: CacheManager = None, requests_per_minute: int = RATE_LIMIT_PER_MINUTE):
        self.anthropic_client = anthropic_client
        self.finnhub_client = finnhub_client
        self.cache = cache_manager or CacheManager()
        self.logger = logging.getLogger(__name__)

        # Rate limiting
        self.requests_per_minute = requests_per_minute
        self.api_call_times: deque = deque(maxlen=self.requests_per_minute)

        # Cache TTL configuration
        self.cache_ttl = CACHE_TTL

        # Statistics tracking
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': {},
            'rate_limit_waits': 0
        }

    #######################################
    ###### Always fresh data methods ######
    #######################################

    def fetch_price(self, symbol: str) -> Dict:
        """Get full price quote. NO CACHE - always fresh."""
        symbol = self._validate_symbol(symbol)
        self.logger.info(f"Fetching price for {symbol}")

        self._check_rate_limit()
        try:
            quote = self.finnhub_client.quote(symbol)
            self.stats['api_calls'] += 1
            return quote
        except Exception as e:
            self._handle_api_error(e, 'quote', symbol)
            raise

    def fetch_current_price(self, symbol: str) -> float:
        """Get current price only. NO CACHE - always fresh."""
        symbol = self._validate_symbol(symbol)
        self.logger.info(f"Fetching current price for {symbol}")

        self._check_rate_limit()
        try:
            quote = self.finnhub_client.quote(symbol)
            self.stats['api_calls'] += 1
            return quote["c"]
        except Exception as e:
            self._handle_api_error(e, 'current_price', symbol)
            raise

    def fetch_company_news(self, symbol: str, from_date: str, to_date: str) -> List[Dict]:
        """Get company news. NO CACHE - always fresh."""
        symbol = self._validate_symbol(symbol)
        self.logger.info(f"Fetching news for {symbol}")

        self._check_rate_limit()
        try:
            news = self.finnhub_client.company_news(symbol, _from=from_date, to=to_date)
            self.stats['api_calls'] += 1
            return news
        except Exception as e:
            self._handle_api_error(e, 'news', symbol)
            raise

    #######################################
    ###### 1 hour cache #################
    #######################################

    def get_news_sentiment(self, symbol: str, from_date: str, to_date: str) -> str:
        # We dont have sentiment analysis access yet, we let our agent handle it
        return None

    #######################################
    ###### 24 hour cache #################
    #######################################

    def get_basic_financials(self, symbol: str) -> Dict:
        """Get financial metrics (P/E, EPS, beta). CACHE 1 DAY."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:financials:{symbol}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.company_basic_financials(symbol=symbol, metric="all"),
            ttl=self.cache_ttl['financials']
        )

    def get_candles(self, symbol: str, resolution: str, start: int, end: int) -> Dict:
        # also a premium feature, but we cant use it
        return None

    def get_recommendations(self, symbol: str) -> List[Dict]:
        """Get analyst recommendations. CACHE 1 DAY."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:recommendations:{symbol}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.recommendation_trends(symbol),
            ttl=self.cache_ttl['recommendations']
        )

    def get_price_target(self, symbol: str) -> Dict:
        # Premium feature, but we can get it
        return None

    def get_insider_transactions(self, symbol: str, from_date: str, to_date: str) -> List[Dict]:
        """Get insider transactions. CACHE 1 DAY."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:insiders:{symbol}:{from_date}:{to_date}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.stock_insider_transactions(symbol),
            ttl=self.cache_ttl['insiders']
        )

    def get_insider_sentiment(self, symbol: str, from_date: str, to_date: str) -> Dict:
        """Get insider sentiment. CACHE 1 DAY."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:insider_sentiment:{symbol}:{from_date}:{to_date}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.stock_insider_sentiment(symbol, from_date, to_date),
            ttl=self.cache_ttl['insiders']
        )

    def get_earnings_calendar(self, from_date: str, to_date: str, symbol: str = None) -> Dict:
        """Get earnings calendar. CACHE 1 DAY."""
        if symbol:
            symbol = self._validate_symbol(symbol)
            cache_key = f"finnhub:earnings:{symbol}:{from_date}:{to_date}"
        else:
            cache_key = f"finnhub:earnings:all:{from_date}:{to_date}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.earnings_calendar(_from=from_date, to=to_date, symbol=symbol),
            ttl=self.cache_ttl['earnings']
        )

    #######################################
    ###### 1 week cache #################
    #######################################

    ### Company profile1 is not free!
    def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile. CACHE 1 WEEK."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:profile:{symbol}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.company_profile2(symbol=symbol),
            ttl=self.cache_ttl['profile']
        )

    def get_company_peers(self, symbol: str) -> List[str]:
        """Get company peers. CACHE 1 WEEK."""
        symbol = self._validate_symbol(symbol)
        cache_key = f"finnhub:peers:{symbol}"

        return self._fetch_with_cache(
            cache_key,
            lambda: self.finnhub_client.company_peers(symbol),
            ttl=self.cache_ttl['peers']
        )

    ###########################################
    ###### ALL AT ONCE #################
    ###########################################

    def get_all_data(self, symbol: str, from_date: str, to_date: str) -> Dict:
        """
        Fetch all available data for a symbol.
        Handles errors gracefully - continues if one endpoint fails.
        """
        symbol = self._validate_symbol(symbol)
        self.logger.info(f"Fetching all data for {symbol}")

        data = {}

        # Define fetchers with their keys
        fetchers = {
            'price': lambda: self.fetch_price(symbol),
            'financials': lambda: self.get_basic_financials(symbol),
            'recommendations': lambda: self.get_recommendations(symbol),
            'insider_transactions': lambda: self.get_insider_transactions(symbol, from_date, to_date),
            'insider_sentiment': lambda: self.get_insider_sentiment(symbol, from_date, to_date),
            'company_profile': lambda: self.get_company_profile(symbol),
            'company_peers': lambda: self.get_company_peers(symbol),
        }

        for key, fetcher in fetchers.items():
            try:
                data[key] = fetcher()
            except Exception as e:
                self.logger.warning(f"Failed to fetch {key} for {symbol}: {e}")
                data[key] = None

        return data

    ########################################
    ###### Helper methods #################
    ########################################

    def _fetch_with_cache(self, cache_key: str, fetch_func: Callable, ttl: int) -> Any:
        """
        Generic cache-aside pattern implementation.

        Args:
            cache_key: Redis cache key
            fetch_func: Function to call if cache miss
            ttl: Time-to-live in seconds (0 = no cache)

        Returns:
            Data from cache or API
        """
        # Check cache (if TTL > 0)
        if ttl > 0:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.logger.debug(f"Cache HIT: {cache_key}")
                self.stats['cache_hits'] += 1
                return cached

            self.logger.debug(f"Cache MISS: {cache_key}")
            self.stats['cache_misses'] += 1

        # Rate limit check
        self._check_rate_limit()

        # Fetch from API with retry logic
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                data = fetch_func()

                # Cache if TTL > 0
                if ttl > 0:
                    self.cache.set(cache_key, data, ttl=ttl)

                # Track API call
                self.stats['api_calls'] += 1

                return data

            except finnhub.FinnhubAPIException as e:
                retry_count += 1
                error_code = getattr(e, 'status_code', None)

                # Rate limit error - sleep and retry
                if error_code == 429:
                    self.logger.warning(f"Rate limit hit (429). Retry {retry_count}/{max_retries}")
                    self._track_error('rate_limit_429')
                    time.sleep(60)
                    continue

                # Server errors - retry with exponential backoff
                elif error_code in (500, 503):
                    self.logger.warning(f"Server error ({error_code}). Retry {retry_count}/{max_retries}")
                    self._track_error(f'server_error_{error_code}')
                    time.sleep(2 ** retry_count)
                    continue

                # Invalid API key - raise immediately
                elif error_code == 401:
                    self.logger.error("Invalid API key (401)")
                    self._track_error('invalid_api_key')
                    raise

                # Invalid symbol - log and return None
                elif error_code == 404:
                    self.logger.warning(f"Invalid symbol (404): {cache_key}")
                    self._track_error('invalid_symbol')
                    return None

                else:
                    self._track_error(f'api_error_{error_code}')
                    raise

            except Exception as e:
                self._track_error('network_error')
                self.logger.error(f"Error fetching data: {e}")
                raise

        raise Exception(f"Failed after {max_retries} retries")

    def _check_rate_limit(self) -> None:
        """
        Ensure we don't exceed rate limit.
        Uses sliding window: track last 60 API calls.
        """
        current_time = time.time()

        # Clean up old timestamps (older than 60 seconds)
        while self.api_call_times and current_time - self.api_call_times[0] > 60:
            self.api_call_times.popleft()

        # Check if we're at the limit
        if len(self.api_call_times) >= self.requests_per_minute:
            oldest_call = self.api_call_times[0]
            wait_time = 60 - (current_time - oldest_call)

            if wait_time > 0:
                self.logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s")
                self.stats['rate_limit_waits'] += 1
                time.sleep(wait_time)

        # Add current call timestamp
        self.api_call_times.append(time.time())

    def _validate_symbol(self, symbol: str) -> str:
        """
        Validate and normalize symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Normalized symbol (uppercase, stripped)

        Raises:
            ValueError: If symbol is invalid
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.strip().upper()

        if not symbol:
            raise ValueError("Symbol cannot be empty")

        return symbol

    def _handle_api_error(self, error: Exception, endpoint: str, symbol: str) -> None:
        """Handle API errors gracefully."""
        error_type = type(error).__name__
        self._track_error(error_type)
        self.logger.error(f"API error on {endpoint} for {symbol}: {error_type} - {error}")

    def _track_error(self, error_type: str) -> None:
        """Track error occurrence in stats."""
        if error_type not in self.stats['errors']:
            self.stats['errors'][error_type] = 0
        self.stats['errors'][error_type] += 1

    def get_statistics(self) -> Dict:
        """
        Get API usage statistics.

        Returns:
            Dictionary with api_calls, cache_hits, cache_misses,
            cache_hit_rate, errors, and rate_limit_waits
        """
        total_cache_access = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_hit_rate = (
            self.stats['cache_hits'] / total_cache_access
            if total_cache_access > 0
            else 0.0
        )

        return {
            'api_calls': self.stats['api_calls'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': cache_hit_rate,
            'errors': self.stats['errors'].copy(),
            'rate_limit_waits': self.stats['rate_limit_waits']
        }

    def interact_anthropic(self, prompt: str) -> str:
        message = self.anthropic_client.messages.create(
            model=llm_models["claude-sonnet-4-5"],
            max_tokens=1024,
            system="You are a data fetcher bot that provides concise and accurate information. For understanding of other roles, build context but do not respond as them.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return message
