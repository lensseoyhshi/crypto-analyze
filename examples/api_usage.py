"""
Example usage of Dexscreener and Birdeye API clients.

Run this script to see how to use the various API endpoints.
"""
import asyncio
import logging
from app.api.clients.dexscreener import DexscreenerClient
from app.api.clients.birdeye import BirdeyeClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_dexscreener():
    """Example: Fetch top token boosts from Dexscreener."""
    logger.info("=== Dexscreener Example ===")
    
    client = DexscreenerClient()
    try:
        response = await client.fetch_top_boosts()
        logger.info(f"Found {len(response.items)} token boosts")
        
        for i, item in enumerate(response.items[:5], 1):
            logger.info(f"\n{i}. Token Boost:")
            logger.info(f"   Chain: {item.chainId}")
            logger.info(f"   Token: {item.tokenAddress}")
            logger.info(f"   Description: {item.description}")
            logger.info(f"   Total Amount: {item.totalAmount}")
            logger.info(f"   URL: {item.url}")
    finally:
        await client.close()


async def example_birdeye_token_overview(token_address: str):
    """Example: Get token overview from Birdeye."""
    logger.info(f"\n=== Birdeye Token Overview Example ===")
    logger.info(f"Token: {token_address}")
    
    client = BirdeyeClient()
    try:
        overview = await client.get_token_overview(token_address)
        
        if overview.success:
            data = overview.data
            logger.info(f"\nToken Overview:")
            logger.info(f"  Address: {data.address}")
            logger.info(f"  Price: ${data.price}")
            logger.info(f"  Market Cap: ${data.marketCap:,.2f}" if data.marketCap else "  Market Cap: N/A")
            logger.info(f"  Liquidity: ${data.liquidity:,.2f}" if data.liquidity else "  Liquidity: N/A")
            logger.info(f"  24h Volume: ${data.v24hUSD:,.2f}" if data.v24hUSD else "  24h Volume: N/A")
            logger.info(f"  24h Price Change: {data.priceChange24hPercent:.2f}%" if data.priceChange24hPercent else "  24h Price Change: N/A")
            logger.info(f"  Holders: {data.holder}" if data.holder else "  Holders: N/A")
        else:
            logger.error("Failed to fetch token overview")
    finally:
        await client.close()


async def example_birdeye_token_security(token_address: str):
    """Example: Check token security (honeypot detection)."""
    logger.info(f"\n=== Birdeye Token Security Example ===")
    logger.info(f"Checking security for: {token_address}")
    
    client = BirdeyeClient()
    try:
        security = await client.get_token_security(token_address)
        
        if security.success:
            data = security.data
            logger.info(f"\nSecurity Analysis:")
            logger.info(f"  Creator: {data.creatorAddress}")
            logger.info(f"  Owner: {data.ownerAddress}")
            logger.info(f"  Mutable Metadata: {data.mutableMetadata}")
            logger.info(f"  Freezeable: {data.freezeable}")
            logger.info(f"  Is Token2022: {data.isToken2022}")
            logger.info(f"  Top 10 Holder %: {data.top10HolderPercent}" if data.top10HolderPercent else "  Top 10 Holder %: N/A")
            
            # Warnings
            warnings = []
            if data.mutableMetadata:
                warnings.append("⚠️  Metadata is mutable")
            if data.freezeable:
                warnings.append("⚠️  Token is freezeable")
            if data.top10HolderPercent and data.top10HolderPercent > 50:
                warnings.append("⚠️  Top 10 holders own >50% of supply")
            
            if warnings:
                logger.warning("\nSecurity Warnings:")
                for warning in warnings:
                    logger.warning(f"  {warning}")
            else:
                logger.info("\n✅ No major security concerns detected")
        else:
            logger.error("Failed to fetch security data")
    finally:
        await client.close()


async def example_birdeye_top_traders(token_address: str):
    """Example: Get top traders for a token."""
    logger.info(f"\n=== Birdeye Top Traders Example ===")
    logger.info(f"Token: {token_address}")
    
    client = BirdeyeClient()
    try:
        traders = await client.get_top_traders(token_address, time_frame="24h", limit=5)
        
        if traders.success:
            logger.info(f"\nTop 5 Traders (24h):")
            for i, trader in enumerate(traders.data.items, 1):
                logger.info(f"\n{i}. Wallet: {trader.owner}")
                logger.info(f"   Total Volume: ${trader.volume:,.2f}")
                logger.info(f"   Total Trades: {trader.trade}")
                logger.info(f"   Buys: {trader.tradeBuy} (${trader.volumeBuy:,.2f})")
                logger.info(f"   Sells: {trader.tradeSell} (${trader.volumeSell:,.2f})")
        else:
            logger.error("Failed to fetch top traders")
    finally:
        await client.close()


async def example_birdeye_wallet_portfolio(wallet_address: str):
    """Example: Get wallet token portfolio."""
    logger.info(f"\n=== Birdeye Wallet Portfolio Example ===")
    logger.info(f"Wallet: {wallet_address}")
    
    client = BirdeyeClient()
    try:
        portfolio = await client.get_wallet_portfolio(wallet_address)
        
        if portfolio.success:
            data = portfolio.data
            logger.info(f"\nPortfolio Summary:")
            logger.info(f"  Wallet: {data.wallet}")
            logger.info(f"  Total Value: ${data.totalUsd:,.2f}")
            logger.info(f"  Number of Tokens: {len(data.items)}")
            
            logger.info(f"\nTop 5 Holdings:")
            sorted_items = sorted(data.items, key=lambda x: x.valueUsd, reverse=True)[:5]
            for i, item in enumerate(sorted_items, 1):
                logger.info(f"\n{i}. {item.symbol} ({item.name})")
                logger.info(f"   Balance: {item.uiAmount:,.2f}")
                logger.info(f"   Value: ${item.valueUsd:,.2f}")
                logger.info(f"   Price: ${item.priceUsd:.8f}")
        else:
            logger.error("Failed to fetch wallet portfolio")
    finally:
        await client.close()


async def example_birdeye_new_listings():
    """Example: Get newly listed tokens."""
    logger.info(f"\n=== Birdeye New Listings Example ===")
    
    client = BirdeyeClient()
    try:
        listings = await client.get_new_listings(limit=5)
        
        if listings.success:
            logger.info(f"\nTop 5 New Listings:")
            for i, listing in enumerate(listings.data.items, 1):
                logger.info(f"\n{i}. {listing.symbol} - {listing.name}")
                logger.info(f"   Address: {listing.address}")
                logger.info(f"   Liquidity: ${listing.liquidity:,.2f}")
                logger.info(f"   Source: {listing.source}")
                logger.info(f"   Listed At: {listing.liquidityAddedAt}")
        else:
            logger.error("Failed to fetch new listings")
    finally:
        await client.close()


async def main():
    """Run all examples."""
    logger.info("Starting API Examples\n")
    
    # Dexscreener example
    await example_dexscreener()
    
    # Birdeye examples with example token (Solana USDC)
    example_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    example_wallet = "8XKhq1Ygeznsx54sTHvdjhvLXDM8j2oJeqknd1kRpBjQ"
    
    await example_birdeye_token_overview(example_token)
    await example_birdeye_token_security(example_token)
    await example_birdeye_top_traders(example_token)
    await example_birdeye_wallet_portfolio(example_wallet)
    await example_birdeye_new_listings()
    
    logger.info("\n=== All Examples Completed ===")


if __name__ == "__main__":
    asyncio.run(main())

