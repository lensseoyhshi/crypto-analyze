# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-01-09

### 🎉 Major Update: Complete Data Storage Implementation

#### Added

**New Database Tables (8 tables)**
- `dexscreener_token_boosts` - Structured storage for Dexscreener data
- `birdeye_token_transactions` - Token transaction history
- `birdeye_top_traders` - Top profitable traders for tokens
- `birdeye_wallet_transactions` - Wallet transaction history
- `birdeye_wallet_tokens` - Wallet portfolio snapshots
- `birdeye_new_listings` - New token listings
- `birdeye_token_security` - Token security analysis (honeypot detection)
- `birdeye_token_overview` - Comprehensive token metrics

**New Repositories**
- `DexscreenerRepository` - Data access layer for Dexscreener data
- `BirdeyeRepository` - Data access layer for all Birdeye endpoints

**Enhanced Scheduler**
- 7 background tasks running concurrently
- Automatic token tracking from Dexscreener boosts
- Automatic token tracking from new listings
- Dynamic token tracking list
- Configurable fetch intervals for each task

**New Features**
- ✅ **Automatic Token Discovery**: New tokens from Dexscreener and Birdeye are auto-tracked
- ✅ **Honeypot Detection**: Auto-check security for new listings
- ✅ **Smart Money Identification**: Track top traders for each token
- ✅ **Portfolio Monitoring**: Snapshot wallet holdings over time
- ✅ **Transaction Monitoring**: Real-time transaction tracking
- ✅ **Comprehensive Metrics**: Price, liquidity, volume, holders, etc.

**Configuration Options**
- `TRACKED_TOKENS` - Comma-separated list of tokens to track
- `TRACKED_WALLETS` - Comma-separated list of wallets to monitor
- `TRACK_NEW_LISTINGS_SECURITY` - Auto-check security for new tokens
- `TRACK_NEW_LISTINGS_OVERVIEW` - Auto-fetch overview for new tokens
- Configurable intervals for all polling tasks

**Documentation**
- `DATABASE_SCHEMA.md` - Complete database schema documentation
- Updated `README.md` with new features and configuration
- Query examples for common use cases

#### Changed

- **Database Migration**: Added migration `0002_add_detailed_tables.py`
- **Scheduler**: Expanded from 1 task to 7 concurrent tasks
- **Configuration**: Added 12 new configuration options
- **Dependencies**: Added `python-dateutil` for date parsing

#### Technical Details

**Data Flow**
1. APIs are polled on configured intervals
2. Raw responses saved to `raw_api_responses` (audit trail)
3. Structured data parsed and saved to specific tables
4. New tokens automatically added to tracking list
5. All tracked tokens get comprehensive data collection

**Background Tasks**
- **Dexscreener Poller** (6s) → Token boosts
- **New Listings Poller** (60s) → New tokens + auto-security check
- **Token Overview Poller** (300s) → Price, liquidity, volume
- **Token Security Poller** (3600s) → Honeypot detection
- **Transaction Poller** (120s) → Real-time transactions
- **Top Traders Poller** (300s) → Smart money identification
- **Portfolio Poller** (600s) → Wallet holdings snapshots

**Performance**
- Optimized indexes on all tables
- Composite indexes for common query patterns
- Batch operations for high-throughput data

**Error Handling**
- Individual task failures don't affect other tasks
- Automatic retry with exponential backoff
- Comprehensive logging for debugging
- Graceful degradation

---

## [1.0.0] - 2026-01-09

### Initial Release

#### Features

- FastAPI application with async/await
- Dexscreener API client with retry logic
- Birdeye API client for 7 endpoints
- MySQL database with Alembic migrations
- Raw API response storage
- Background task scheduler
- Docker Compose setup
- Comprehensive testing
- CI/CD with GitHub Actions
- Complete documentation

#### API Clients

**Dexscreener**
- Top token boosts

**Birdeye**
- Token transactions
- Top traders
- Wallet transactions
- Wallet portfolio
- New listings
- Token security
- Token overview

#### Infrastructure

- Docker and Docker Compose
- MySQL 8.0 database
- Alembic migrations
- Background task scheduler
- Health check endpoint
- Comprehensive logging
- Error handling with retries

---

## Upgrade Guide: v1.0.0 → v2.0.0

### Database Migration

```bash
# Pull latest code
git pull

# Stop services
docker-compose down

# Start services (migrations run automatically)
docker-compose up --build
```

The new migration `0002_add_detailed_tables` will create all 8 new tables automatically.

### Configuration

Update your `.env` file with new options:

```env
# Add tracking configuration (optional)
TRACKED_TOKENS=
TRACKED_WALLETS=

# Configure auto-tracking for new listings
TRACK_NEW_LISTINGS_SECURITY=true
TRACK_NEW_LISTINGS_OVERVIEW=true

# Adjust fetch intervals if needed (optional)
BIRDEYE_NEW_LISTINGS_INTERVAL=60
BIRDEYE_TOKEN_OVERVIEW_INTERVAL=300
BIRDEYE_TOKEN_SECURITY_INTERVAL=3600
BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL=120
BIRDEYE_TOP_TRADERS_INTERVAL=300
BIRDEYE_WALLET_PORTFOLIO_INTERVAL=600
```

### What's Changed

- **More Data**: Now stores structured data in 8 specialized tables
- **Auto-Tracking**: Tokens are automatically discovered and tracked
- **More Tasks**: 7 background tasks instead of 1
- **Richer Queries**: Query structured data with SQL
- **Better Performance**: Optimized indexes for fast queries

### Breaking Changes

None. All v1.0.0 functionality remains intact. New features are additive.

---

## Future Roadmap

### Planned Features

- [ ] Data aggregation and analytics endpoints
- [ ] Real-time WebSocket updates
- [ ] Advanced filtering and search API
- [ ] Data export (CSV, Excel)
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Alert system for price/volume thresholds
- [ ] Machine learning models for price prediction
- [ ] Token risk scoring
- [ ] Whale wallet detection

### Under Consideration

- GraphQL API
- Redis caching layer
- Multi-chain support
- Historical data analysis
- Token comparison tools
- Portfolio tracking dashboard

---

**For detailed schema information, see [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)**

