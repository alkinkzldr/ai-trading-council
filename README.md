# AI Trading Council

A multi-agent trading system with sophisticated risk controls and distributed decision making, powered by Claude AI.

## Vision

The AI Trading Council is designed to democratize intelligent trading decisions by creating an ensemble of AI agents that collectively analyze market conditions, classify market regimes, and make coordinated trading decisions. The system implements built-in veto mechanisms to prevent risky trades during adverse market conditions.

### Core Principles

- **Collective Intelligence**: Multiple AI agents vote on trading decisions, reducing individual bias
- **Risk-First Approach**: A sophisticated veto system prevents trades during dangerous market conditions
- **Transparency**: Every decision is logged with clear reasoning
- **Modularity**: Clean separation between data, analysis, orchestration, and execution layers

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAESTRO                                 │
│              (Orchestration & API Controller)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  DATA LAYER   │    │ REGIME GUARD  │    │  AI AGENTS    │
│               │    │               │    │   (Council)   │
│ • Finnhub API │    │ • 6 Regimes   │    │ • Claude AI   │
│ • Redis Cache │    │ • Veto Logic  │    │ • Voting      │
│ • PostgreSQL  │    │ • Risk Levels │    │ • Consensus   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────┐
                    │  BOT LAYER    │
                    │  (Execution)  │
                    └───────────────┘
```

## Current Status

### Implemented

| Component | Status | Description |
|-----------|--------|-------------|
| **Data Provider** | Complete | Finnhub API integration with rate limiting, retry logic, and statistics tracking |
| **Cache Manager** | Complete | Redis-backed caching with TTL, hit/miss rates, and health checks |
| **Market Calculator** | Complete | 10+ technical indicators (VIX, RSI, MACD, Bollinger Bands, ADX, OBV, etc.) |
| **Regime Guardian** | Complete | 6 market regime classifications with multi-level veto system |
| **Database Schema** | Complete | PostgreSQL tables for price history, signals, and market regimes |
| **Docker Setup** | Complete | Multi-container orchestration with health checks |
| **Test Suite** | Complete | 70+ test cases for data provider |

### In Progress

| Component | Status | Description |
|-----------|--------|-------------|
| **Maestro** | Skeleton | Core orchestration layer - workflow not yet complete |

### Planned

| Component | Status | Description |
|-----------|--------|-------------|
| **AI Agents** | Not Started | Multi-agent council for voting on trade decisions |
| **Bot Layer** | Not Started | Trade execution and portfolio management |
| **Analytics** | Not Started | Performance tracking, backtesting, Sharpe ratio |
| **CLI Interface** | Not Started | Command-line interface for AI council |

## Market Regime Classification

The Regime Guardian classifies markets into 6 distinct conditions:

| Regime | Description | Trading Allowed |
|--------|-------------|-----------------|
| `BULL_TREND` | Strong upward momentum | Yes |
| `BEAR_TREND` | Strong downward momentum | Limited |
| `RANGE_BOUND` | Trading within defined boundaries | Yes |
| `VOLATILITY_SPIKE` | Sudden increase in volatility | Vetoed |
| `STAGNATION` | Low volume, directionless | Limited |
| `LOW_LIQUIDITY` | Insufficient market depth | Vetoed |

### Veto Priority Levels

- **CRITICAL**: Immediately blocks all trading (e.g., volatility spike)
- **HIGH**: Blocks most trades, allows exits only
- **MEDIUM**: Reduces position sizes, increases caution

## Tech Stack

- **Python 3.13** - Core application
- **Anthropic Claude** - AI agent intelligence (Opus, Sonnet, Haiku models)
- **Finnhub** - Real-time market data (free tier)
- **Redis 7** - High-performance caching
- **PostgreSQL 16** - Persistent data storage
- **Docker & Docker Compose** - Containerization
- **TA-Lib** - Technical analysis calculations

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.13+
- API Keys: Anthropic, Finnhub

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-trading-council.git
cd ai-trading-council
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start services:
```bash
docker-compose up -d
```

4. Run tests:
```bash
pytest
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude AI API key | Yes |
| `FINNHUB_API_KEY` | Finnhub market data API key | Yes |
| `POSTGRES_USER` | Database username | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `POSTGRES_DB` | Database name | Yes |
| `REDIS_URL` | Redis connection URL | Yes |

### Tracked Symbols

The system monitors 20 major stocks by default:
`AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, JPM, V, WMT, JNJ, PG, UNH, HD, MA, DIS, PYPL, NFLX, ADBE, CRM`

## Project Structure

```
ai-trading-council/
├── agents/          # AI agent implementations (planned)
├── analytics/       # Performance & backtesting (planned)
├── bot/             # Trade execution (planned)
├── config/
│   ├── settings.py  # Environment configuration
│   └── symbols.py   # Tracked stock symbols
├── core/
│   ├── maestro.py   # Orchestration layer
│   └── regime_guardian.py  # Market regime classifier
├── data/
│   ├── cache_manager.py    # Redis cache
│   ├── data_provider.py    # Finnhub API client
│   ├── database.py         # PostgreSQL connection
│   └── market_calculator.py # Technical indicators
├── tests/           # Test suite
├── docker-compose.yml
└── Dockerfile
```

## Contributing

This project is in active development. Contributions are welcome for:
- Implementing the AI agent voting system
- Adding new technical indicators
- Building the trade execution layer
- Improving test coverage

## License

MIT

---

**Disclaimer**: This software is for educational purposes only. Trading involves substantial risk of loss. Past performance is not indicative of future results. Always do your own research before making investment decisions.
