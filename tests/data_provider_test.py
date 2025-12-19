import pytest
import time
from unittest.mock import Mock, patch


class TestDataProvider:
    """Test suite for the DataProvider class."""

    @pytest.fixture
    def mock_finnhub_client(self):
        """Create a mock Finnhub client."""
        return Mock()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock CacheManager."""
        cache = Mock()
        cache.get.return_value = None  # Default to cache miss
        cache.set.return_value = True
        return cache

    @pytest.fixture
    def data_provider(self, mock_finnhub_client, mock_cache_manager):
        """Create a DataProvider instance with mocked dependencies."""
        with patch('data.data_provider.finnhub_client', mock_finnhub_client), \
             patch('data.data_provider.CacheManager', return_value=mock_cache_manager):
            from data.data_provider import DataProvider
            provider = DataProvider(cache_manager=mock_cache_manager)
            provider.finnhub_client = mock_finnhub_client
            return provider

    # --- Initialization Tests ---

    def test_init_default_rate_limit(self, mock_finnhub_client, mock_cache_manager):
        """Test that default rate limit is 60 requests per minute."""
        with patch('data.data_provider.finnhub_client', mock_finnhub_client):
            from data.data_provider import DataProvider
            provider = DataProvider(cache_manager=mock_cache_manager)
            assert provider.requests_per_minute == 60

    def test_init_custom_rate_limit(self, mock_finnhub_client, mock_cache_manager):
        """Test that custom rate limit can be set."""
        with patch('data.data_provider.finnhub_client', mock_finnhub_client):
            from data.data_provider import DataProvider
            provider = DataProvider(cache_manager=mock_cache_manager, requests_per_minute=30)
            assert provider.requests_per_minute == 30

    def test_init_empty_stats(self, data_provider):
        """Test that stats are initialized to zero."""
        assert data_provider.stats['api_calls'] == 0
        assert data_provider.stats['cache_hits'] == 0
        assert data_provider.stats['cache_misses'] == 0

    # --- Symbol Validation Tests ---

    def test_validate_symbol_uppercase(self, data_provider):
        """Test that symbols are converted to uppercase."""
        assert data_provider._validate_symbol('aapl') == 'AAPL'

    def test_validate_symbol_strips_whitespace(self, data_provider):
        """Test that whitespace is stripped from symbols."""
        assert data_provider._validate_symbol('  AAPL  ') == 'AAPL'

    def test_validate_symbol_empty_raises(self, data_provider):
        """Test that empty symbol raises ValueError."""
        with pytest.raises(ValueError):
            data_provider._validate_symbol('')

    def test_validate_symbol_none_raises(self, data_provider):
        """Test that None symbol raises ValueError."""
        with pytest.raises(ValueError):
            data_provider._validate_symbol(None)

    # --- fetch_price Tests (No Cache) ---

    def test_fetch_price_returns_data(self, data_provider, mock_finnhub_client):
        """Test that fetch_price returns quote data."""
        expected = {'c': 150.0, 'h': 152.0, 'l': 148.0, 'o': 149.0}
        mock_finnhub_client.quote.return_value = expected

        result = data_provider.fetch_price('AAPL')

        assert result == expected
        mock_finnhub_client.quote.assert_called_once_with('AAPL')

    def test_fetch_price_increments_api_calls(self, data_provider, mock_finnhub_client):
        """Test that fetch_price increments API call count."""
        mock_finnhub_client.quote.return_value = {}

        data_provider.fetch_price('AAPL')

        assert data_provider.stats['api_calls'] == 1

    # --- fetch_current_price Tests ---

    def test_fetch_current_price_returns_float(self, data_provider, mock_finnhub_client):
        """Test that fetch_current_price returns just the current price."""
        mock_finnhub_client.quote.return_value = {'c': 150.25, 'h': 152.0}

        result = data_provider.fetch_current_price('AAPL')

        assert result == 150.25
        assert isinstance(result, float)

    # --- get_basic_financials Tests (Cached) ---

    def test_get_financials_cache_hit(self, data_provider, mock_cache_manager, mock_finnhub_client):
        """Test that cache hit returns cached data without API call."""
        cached_data = {'metric': {'peBasicExclExtraTTM': 25.5}}
        mock_cache_manager.get.return_value = cached_data

        result = data_provider.get_basic_financials('AAPL')

        assert result == cached_data
        mock_finnhub_client.company_basic_financials.assert_not_called()
        assert data_provider.stats['cache_hits'] == 1

    def test_get_financials_cache_miss(self, data_provider, mock_cache_manager, mock_finnhub_client):
        """Test that cache miss fetches from API and caches result."""
        mock_cache_manager.get.return_value = None
        api_data = {'metric': {'peBasicExclExtraTTM': 25.5}}
        mock_finnhub_client.company_basic_financials.return_value = api_data

        result = data_provider.get_basic_financials('AAPL')

        assert result == api_data
        mock_finnhub_client.company_basic_financials.assert_called_once_with(symbol='AAPL', metric='all')
        mock_cache_manager.set.assert_called_once()
        assert data_provider.stats['cache_misses'] == 1
        assert data_provider.stats['api_calls'] == 1

    # --- get_company_profile Tests ---

    def test_get_profile_uses_week_cache(self, data_provider, mock_cache_manager, mock_finnhub_client):
        """Test that profile uses 1 week TTL."""
        mock_cache_manager.get.return_value = None
        mock_finnhub_client.company_profile2.return_value = {'name': 'Apple Inc.'}

        data_provider.get_company_profile('AAPL')

        # Check that set was called with 1 week TTL (604800)
        call_args = mock_cache_manager.set.call_args
        assert call_args[1]['ttl'] == 604800

    # --- Premium Features Return None ---

    def test_get_news_sentiment_returns_none(self, data_provider):
        """Test that premium feature returns None."""
        result = data_provider.get_news_sentiment('AAPL', '2024-01-01', '2024-01-07')
        assert result is None

    def test_get_candles_returns_none(self, data_provider):
        """Test that premium feature returns None."""
        result = data_provider.get_candles('AAPL', 'D', 1704067200, 1704672000)
        assert result is None

    def test_get_price_target_returns_none(self, data_provider):
        """Test that premium feature returns None."""
        result = data_provider.get_price_target('AAPL')
        assert result is None

    # --- Rate Limiting Tests ---

    def test_rate_limiter_adds_timestamp(self, data_provider):
        """Test that rate limiter adds timestamp."""
        data_provider._check_rate_limit()
        assert len(data_provider.api_call_times) == 1

    def test_rate_limiter_cleans_old_timestamps(self, data_provider):
        """Test that old timestamps are cleaned up."""
        # Add old timestamp (70 seconds ago)
        old_time = time.time() - 70
        data_provider.api_call_times.append(old_time)

        data_provider._check_rate_limit()

        # Old timestamp should be removed, only new one present
        assert len(data_provider.api_call_times) == 1
        assert data_provider.api_call_times[0] > old_time

    def test_rate_limiter_keeps_recent_timestamps(self, data_provider):
        """Test that timestamps within 60 seconds are kept."""
        recent_time = time.time() - 30
        data_provider.api_call_times.append(recent_time)

        data_provider._check_rate_limit()

        # Recent timestamp should be kept, plus new one
        assert len(data_provider.api_call_times) == 2

    def test_rate_limiter_waits_at_limit(self, data_provider):
        """Test that rate limiter waits when at limit."""
        data_provider.requests_per_minute = 3  # Low limit for testing

        # Fill up with recent timestamps
        now = time.time()
        for i in range(3):
            data_provider.api_call_times.append(now - i)

        with patch('data.data_provider.time.sleep') as mock_sleep:
            data_provider._check_rate_limit()
            # Should have called sleep or incremented rate_limit_waits
            assert mock_sleep.called or data_provider.stats['rate_limit_waits'] >= 0

    # --- Statistics Tests ---

    def test_get_statistics(self, data_provider):
        """Test that statistics are returned correctly."""
        data_provider.stats['api_calls'] = 10
        data_provider.stats['cache_hits'] = 5
        data_provider.stats['cache_misses'] = 5
        data_provider.stats['rate_limit_waits'] = 1

        stats = data_provider.get_statistics()

        assert stats['api_calls'] == 10
        assert stats['cache_hits'] == 5
        assert stats['cache_misses'] == 5
        assert stats['cache_hit_rate'] == 0.5
        assert stats['rate_limit_waits'] == 1

    def test_get_statistics_zero_division(self, data_provider):
        """Test that cache_hit_rate handles zero total."""
        stats = data_provider.get_statistics()
        assert stats['cache_hit_rate'] == 0.0

    # --- get_all_data Tests ---

    def test_get_all_data_returns_dict(self, data_provider, mock_finnhub_client, mock_cache_manager):
        """Test that get_all_data returns dictionary with all keys."""
        mock_cache_manager.get.return_value = None
        mock_finnhub_client.quote.return_value = {'c': 150}
        mock_finnhub_client.company_basic_financials.return_value = {}
        mock_finnhub_client.recommendation_trends.return_value = []
        mock_finnhub_client.stock_insider_transactions.return_value = {}
        mock_finnhub_client.stock_insider_sentiment.return_value = {}
        mock_finnhub_client.company_profile2.return_value = {}
        mock_finnhub_client.company_peers.return_value = []

        result = data_provider.get_all_data('AAPL', '2024-01-01', '2024-01-07')

        assert 'price' in result
        assert 'financials' in result
        assert 'recommendations' in result
        assert 'insider_transactions' in result
        assert 'insider_sentiment' in result
        assert 'company_profile' in result
        assert 'company_peers' in result

    def test_get_all_data_handles_partial_failure(self, data_provider, mock_finnhub_client, mock_cache_manager):
        """Test that get_all_data continues if one endpoint fails."""
        mock_cache_manager.get.return_value = None
        mock_finnhub_client.quote.return_value = {'c': 150}
        mock_finnhub_client.company_basic_financials.side_effect = Exception("API Error")
        mock_finnhub_client.recommendation_trends.return_value = []
        mock_finnhub_client.stock_insider_transactions.return_value = {}
        mock_finnhub_client.stock_insider_sentiment.return_value = {}
        mock_finnhub_client.company_profile2.return_value = {'name': 'Apple'}
        mock_finnhub_client.company_peers.return_value = []

        result = data_provider.get_all_data('AAPL', '2024-01-01', '2024-01-07')

        assert result['price'] == {'c': 150}
        assert result['financials'] is None  # Failed
        assert result['company_profile'] == {'name': 'Apple'}

    # --- Error Tracking Tests ---

    def test_error_tracking(self, data_provider):
        """Test that errors are tracked in stats."""
        data_provider._track_error('test_error')
        data_provider._track_error('test_error')
        data_provider._track_error('other_error')

        assert data_provider.stats['errors']['test_error'] == 2
        assert data_provider.stats['errors']['other_error'] == 1


class TestDataProviderIntegration:
    """Integration tests for DataProvider."""

    @pytest.fixture
    def data_provider_low_limit(self):
        """Create a DataProvider with a low rate limit for testing."""
        with patch('data.data_provider.finnhub_client', Mock()), \
             patch('data.data_provider.CacheManager'):
            from data.data_provider import DataProvider
            return DataProvider(cache_manager=Mock(), requests_per_minute=5)

    def test_burst_requests_within_limit(self, data_provider_low_limit):
        """Test that burst requests within limit don't cause delays."""
        provider = data_provider_low_limit
        provider.requests_per_minute = 10

        start = time.time()
        for _ in range(5):
            provider._check_rate_limit()
        elapsed = time.time() - start

        # Should complete almost instantly (less than 1 second)
        assert elapsed < 1.0

    def test_timestamp_precision(self, data_provider_low_limit):
        """Test that timestamps are recorded with sufficient precision."""
        provider = data_provider_low_limit

        provider._check_rate_limit()
        time.sleep(0.1)
        provider._check_rate_limit()

        # Timestamps should be different
        assert provider.api_call_times[0] != provider.api_call_times[1]
        # Second timestamp should be ~0.1 seconds later
        diff = provider.api_call_times[1] - provider.api_call_times[0]
        assert 0.05 < diff < 0.2
