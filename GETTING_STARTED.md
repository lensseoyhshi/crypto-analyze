# Getting Started Guide

This guide will help you get the crypto-analyze project up and running in just a few minutes.

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ and MySQL 8.0 (for local development)

## Quick Start with Docker (5 minutes)

### Step 1: Clone and Navigate

```bash
cd crypto-analyze
```

### Step 2: Start Everything

```bash
docker-compose up --build
```

That's it! The application will:
1. Start MySQL database
2. Run migrations automatically
3. Start the FastAPI application
4. Begin collecting data from Dexscreener every 6 seconds

### Step 3: Verify It's Working

Open your browser and visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the application status as "ok".

### Step 4: Check the Data

Access the MySQL database to see collected data:

```bash
# Connect to MySQL container
docker exec -it crypto_analyze_db mysql -u crypto_user -pcrypto_pass crypto_analyze

# Run queries
mysql> SELECT COUNT(*) FROM raw_api_responses;
mysql> SELECT source, endpoint, created_at FROM raw_api_responses ORDER BY created_at DESC LIMIT 5;
mysql> exit
```

### Step 5: View Logs

```bash
# View application logs
docker-compose logs -f app

# View database logs
docker-compose logs -f db
```

## Using the API Clients

### Example: Fetch Dexscreener Data Manually

Create a Python script `test_client.py`:

```python
import asyncio
from app.api.clients.dexscreener import DexscreenerClient

async def main():
    client = DexscreenerClient()
    try:
        response = await client.fetch_top_boosts()
        print(f"Found {len(response.items)} token boosts")
        for item in response.items[:3]:  # Print first 3
            print(f"  - {item.tokenAddress} on {item.chainId}: {item.totalAmount} boosts")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
# If using Docker
docker-compose exec app python test_client.py

# If running locally
python test_client.py
```

### Example: Fetch Birdeye Token Overview

Create `test_birdeye.py`:

```python
import asyncio
from app.api.clients.birdeye import BirdeyeClient

async def main():
    client = BirdeyeClient()
    try:
        # Example token address (Solana USDC)
        token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        overview = await client.get_token_overview(token)
        print(f"Token: {overview.data.address}")
        print(f"Price: ${overview.data.price}")
        print(f"Market Cap: ${overview.data.marketCap:,.2f}")
        print(f"Liquidity: ${overview.data.liquidity:,.2f}")
        print(f"24h Volume: ${overview.data.v24hUSD:,.2f}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Environment Variables

Create a `.env` file to override defaults:

```env
# Database
DATABASE_URL=mysql+aiomysql://crypto_user:crypto_pass@localhost:3306/crypto_analyze

# API Keys
BIRDEYE_API_KEY=your_birdeye_api_key_here

# Scheduler
DEXSCREENER_FETCH_INTERVAL=6

# Application
DEBUG=false
```

### Using Different API Keys

1. Get your Birdeye API key from https://birdeye.so
2. Update the `.env` file or `docker-compose.yml`
3. Restart the application

```bash
docker-compose down
docker-compose up -d
```

## Development Workflow

### Running Tests

```bash
# Using Docker
docker-compose exec app pytest

# Using Makefile
make test

# With coverage
make test-cov
```

### Making Code Changes

1. **Edit code** in your local files
2. **Changes auto-reload** if you started with `docker-compose up` (has --reload flag)
3. **Run tests** to ensure everything works
4. **Check logs** to see your changes in action

```bash
docker-compose logs -f app
```

### Creating Database Migrations

When you modify database models:

```bash
# Create migration
make migrate-create
# Enter description when prompted

# Apply migration
make migrate

# Or manually:
docker-compose exec app alembic revision --autogenerate -m "your message"
docker-compose exec app alembic upgrade head
```

## Common Tasks

### Restart Services

```bash
docker-compose restart
```

### Stop Services

```bash
docker-compose down
```

### Reset Database (Deletes All Data!)

```bash
docker-compose down -v
docker-compose up --build
```

### View Database Schema

```bash
docker exec -it crypto_analyze_db mysql -u crypto_user -pcrypto_pass crypto_analyze -e "DESCRIBE raw_api_responses;"
```

### Export Data

```bash
docker exec crypto_analyze_db mysqldump -u crypto_user -pcrypto_pass crypto_analyze > backup.sql
```

## Troubleshooting

### Port Already in Use

If port 3306 or 8000 is already in use:

Edit `docker-compose.yml`:
```yaml
services:
  db:
    ports:
      - "3307:3306"  # Use different port
  app:
    ports:
      - "8001:8000"  # Use different port
```

### Can't Connect to Database

```bash
# Check if MySQL is ready
docker-compose ps

# Wait for MySQL to be healthy
docker-compose logs db | grep "ready for connections"

# Restart application
docker-compose restart app
```

### Application Not Collecting Data

Check logs:
```bash
docker-compose logs -f app | grep "Dexscreener"
```

Verify configuration:
```bash
docker-compose exec app env | grep DEXSCREENER
```

### Clear All Docker Resources

```bash
docker-compose down -v --remove-orphans
docker system prune -a
```

## Next Steps

1. **Add More API Endpoints**: Implement additional Birdeye API calls in your application
2. **Create Data Analysis**: Write queries to analyze collected data
3. **Set Up Monitoring**: Add Prometheus/Grafana for metrics
4. **Deploy to Production**: Use a cloud provider or your own server

## Useful Commands

```bash
# Using Makefile
make help              # Show all available commands
make install           # Install dependencies
make dev              # Run development server
make test             # Run tests
make lint             # Run linters
make format           # Format code
make docker-up        # Start Docker services
make docker-down      # Stop Docker services
make docker-logs      # View logs
make migrate          # Run migrations
make db-reset         # Reset database

# Docker Compose
docker-compose up -d           # Start in background
docker-compose logs -f app     # Follow app logs
docker-compose exec app bash   # Access app container shell
docker-compose exec db mysql   # Access MySQL CLI
docker-compose ps              # List services
docker-compose top             # Show processes

# Testing
pytest                         # Run all tests
pytest tests/test_repositories.py  # Run specific test file
pytest -v --cov=app           # With coverage
```

## Getting Help

- Check the [README.md](README.md) for detailed documentation
- Review logs: `docker-compose logs -f`
- Open an issue on GitHub
- Check API documentation at http://localhost:8000/docs

## Production Deployment

For production:

1. **Update environment variables** with secure passwords
2. **Use a managed MySQL database** (e.g., AWS RDS, Google Cloud SQL)
3. **Enable HTTPS** with a reverse proxy (Nginx, Caddy)
4. **Set up monitoring** and alerting
5. **Configure backups** for your database
6. **Remove --reload** flag from uvicorn in docker-compose.yml
7. **Set DEBUG=false** in environment

Happy coding! 🚀

