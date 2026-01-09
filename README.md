# Crypto Analyze

A high-performance, scalable data collection system for cryptocurrency data from Dexscreener and Birdeye APIs.

## Features

- 🔄 **Periodic Data Collection**: Automatically fetches top token boosts from Dexscreener every 6 seconds
- 📊 **Multiple API Integrations**: 
  - Dexscreener: Top token boosts
  - Birdeye: Token transactions, top traders, wallet analysis, new listings, token security, and liquidity metrics
- 🗄️ **MySQL Storage**: All API responses stored in MySQL with proper indexing
- 🔁 **Retry Logic**: Automatic retries with exponential backoff for failed requests
- 🏗️ **Clean Architecture**: Repository pattern, dependency injection, and separation of concerns
- 🐳 **Docker Ready**: Full Docker Compose setup with MySQL
- 📝 **Database Migrations**: Alembic for schema versioning and migrations
- 📈 **Async/Await**: Fully asynchronous for high performance

## Architecture

```
crypto-analyze/
├── app/
│   ├── api/
│   │   ├── clients/          # HTTP clients for external APIs
│   │   │   ├── base_client.py    # Base client with retry logic
│   │   │   ├── dexscreener.py    # Dexscreener API client
│   │   │   └── birdeye.py        # Birdeye API client
│   │   └── schemas/          # Pydantic models for API responses
│   │       ├── dexscreener.py
│   │       └── birdeye.py
│   ├── core/
│   │   └── config.py         # Configuration management
│   ├── db/
│   │   ├── models.py         # SQLAlchemy models
│   │   └── session.py        # Database session management
│   ├── repositories/         # Data access layer
│   │   └── raw_api_repository.py
│   ├── services/
│   │   └── scheduler.py      # Background task scheduler
│   └── main.py              # FastAPI application
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Application container
└── requirements.txt        # Python dependencies
```

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**

```bash
git clone <repository-url>
cd crypto-analyze
```

2. **Configure environment (optional)**

Copy `.env.example` to `.env` and modify if needed:

```bash
cp .env.example .env
```

3. **Start the services**

```bash
docker-compose up --build
```

The application will:
- Start MySQL database
- Run database migrations automatically
- Start the FastAPI application on http://localhost:8000
- Begin collecting data from Dexscreener every 6 seconds

4. **Access the API**

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root: http://localhost:8000/

### Local Development

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Set up MySQL database**

```bash
# Start MySQL (example using Docker)
docker run --name crypto-mysql -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=crypto_analyze -e MYSQL_USER=crypto_user \
  -e MYSQL_PASSWORD=crypto_pass -p 3306:3306 -d mysql:8.0
```

3. **Configure environment**

Create `.env` file:

```env
DATABASE_URL=mysql+aiomysql://crypto_user:crypto_pass@localhost:3306/crypto_analyze
BIRDEYE_API_KEY=9c1c446225f246f69ec5ebd6103f1502
DEXSCREENER_FETCH_INTERVAL=6
DEBUG=False
```

4. **Run migrations**

```bash
alembic upgrade head
```

5. **Start the application**

```bash
uvicorn app.main:app --reload
```

## API Clients Usage

### Dexscreener Client

```python
from app.api.clients.dexscreener import DexscreenerClient

client = DexscreenerClient()
response = await client.fetch_top_boosts()
print(response.items)
```

### Birdeye Client

```python
from app.api.clients.birdeye import BirdeyeClient

client = BirdeyeClient()

# Get token transactions
txs = await client.get_token_transactions("token_address")

# Get top traders
traders = await client.get_top_traders("token_address")

# Get wallet portfolio
portfolio = await client.get_wallet_portfolio("wallet_address")

# Get new listings
listings = await client.get_new_listings()

# Check token security (honeypot detection)
security = await client.get_token_security("token_address")

# Get token overview (liquidity, volume, etc.)
overview = await client.get_token_overview("token_address")
```

## Database Schema

The system uses **9 database tables** to store all API data in structured format:

### Tables Overview

1. **raw_api_responses** - Raw API responses for all endpoints (audit trail)
2. **dexscreener_token_boosts** - Token boost data from Dexscreener
3. **birdeye_token_transactions** - Token transaction history
4. **birdeye_top_traders** - Top profitable traders for each token
5. **birdeye_wallet_transactions** - Wallet transaction history
6. **birdeye_wallet_tokens** - Wallet token holdings (portfolio snapshots)
7. **birdeye_new_listings** - Newly listed tokens
8. **birdeye_token_security** - Token security analysis (honeypot detection)
9. **birdeye_token_overview** - Comprehensive token metrics (price, liquidity, volume, etc.)

### Data Collection Schedule

| Task | Frequency | Description |
|------|-----------|-------------|
| Dexscreener Boosts | 6s | Auto-tracks trending tokens |
| New Listings | 60s | Discovers and tracks new tokens |
| Token Overview | 300s (5min) | Real-time token metrics |
| Token Security | 3600s (1h) | Security checks |
| Token Transactions | 120s (2min) | Transaction monitoring |
| Top Traders | 300s (5min) | Identifies smart money |
| Wallet Portfolio | 600s (10min) | Portfolio snapshots for configured wallets |

**See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete schema documentation with all fields, indexes, and query examples.**

### Key Features

- ✅ **Automatic Token Tracking**: New tokens from Dexscreener and Birdeye are automatically added to tracking list
- ✅ **Honeypot Detection**: Automatically checks security for new listings
- ✅ **Smart Money Tracking**: Identifies top traders for each token
- ✅ **Historical Data**: Full transaction history and portfolio snapshots
- ✅ **Optimized Indexes**: Fast queries on any combination of token, time, wallet

## Configuration

All configuration is managed through environment variables:

### Basic Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| APP_NAME | Application name | crypto-analyze |
| DEBUG | Debug mode | False |
| DATABASE_URL | MySQL connection string | mysql+aiomysql://... |
| BIRDEYE_API_KEY | Birdeye API key | Required |

### Fetch Intervals (seconds)

| Variable | Description | Default |
|----------|-------------|---------|
| DEXSCREENER_FETCH_INTERVAL | Dexscreener polling | 6 |
| BIRDEYE_NEW_LISTINGS_INTERVAL | New listings polling | 60 |
| BIRDEYE_TOKEN_OVERVIEW_INTERVAL | Token overview polling | 300 |
| BIRDEYE_TOKEN_SECURITY_INTERVAL | Security checks | 3600 |
| BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL | Transaction polling | 120 |
| BIRDEYE_TOP_TRADERS_INTERVAL | Top traders polling | 300 |
| BIRDEYE_WALLET_PORTFOLIO_INTERVAL | Portfolio polling | 600 |

### Tracking Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| TRACKED_TOKENS | Comma-separated token addresses | token1,token2,token3 |
| TRACKED_WALLETS | Comma-separated wallet addresses | wallet1,wallet2,wallet3 |
| TRACK_NEW_LISTINGS_SECURITY | Auto-check security for new listings | true |
| TRACK_NEW_LISTINGS_OVERVIEW | Auto-fetch overview for new listings | true |

**Note**: Tokens discovered from Dexscreener and new listings are automatically added to the tracking list

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

## Monitoring

The application includes comprehensive logging:

```bash
# View logs
docker-compose logs -f app

# View specific service logs
docker-compose logs -f db
```

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (data will be lost)
docker-compose down -v
```

## Development

### Code Style

- Python 3.11+
- Type hints throughout
- Async/await for all I/O operations
- Pydantic for data validation
- Repository pattern for data access

### Adding New API Endpoints

1. Create schema in `app/api/schemas/`
2. Implement client method in respective client file
3. Add repository methods if needed
4. Create background task in scheduler if periodic

## Troubleshooting

### Database Connection Issues

```bash
# Check if MySQL is running
docker-compose ps

# Restart MySQL
docker-compose restart db
```

### Migration Issues

```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up --build
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


