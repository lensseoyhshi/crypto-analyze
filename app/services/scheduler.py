"""Background task scheduler for periodic API polling."""
import asyncio
import logging
from typing import Set
from fastapi import FastAPI
from ..api.clients.dexscreener import DexscreenerClient
from ..api.clients.birdeye import BirdeyeClient
from ..db.session import get_async_session
from ..repositories.raw_api_repository import RawApiRepository
from ..repositories.dexscreener_repository import DexscreenerRepository
from ..repositories.birdeye_repository import BirdeyeRepository
from ..core.config import settings

logger = logging.getLogger(__name__)

_tasks = []
_tracked_tokens: Set[str] = set()  # Dynamic set of tokens to track


def start_background_tasks(app: FastAPI):
	"""Start background periodic tasks. Safe to call once on startup."""
	logger.info("Starting background tasks")
	loop = asyncio.get_event_loop()
	
	# Initialize tracked tokens from config
	_tracked_tokens.update(settings.tracked_tokens_list)
	logger.info(f"Tracking {len(_tracked_tokens)} tokens from config")
	
	# Start all background tasks
	tasks_to_start = [
		(_dexscreener_poller(), "Dexscreener poller", settings.DEXSCREENER_FETCH_INTERVAL),
		(_birdeye_new_listings_poller(), "Birdeye new listings", settings.BIRDEYE_NEW_LISTINGS_INTERVAL),
		(_birdeye_token_overview_poller(), "Birdeye token overview", settings.BIRDEYE_TOKEN_OVERVIEW_INTERVAL),
		(_birdeye_token_security_poller(), "Birdeye token security", settings.BIRDEYE_TOKEN_SECURITY_INTERVAL),
		(_birdeye_token_transactions_poller(), "Birdeye token transactions", settings.BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL),
		(_birdeye_top_traders_poller(), "Birdeye top traders", settings.BIRDEYE_TOP_TRADERS_INTERVAL),
		(_birdeye_wallet_portfolio_poller(), "Birdeye wallet portfolio", settings.BIRDEYE_WALLET_PORTFOLIO_INTERVAL),
	]
	
	for task_coro, name, interval in tasks_to_start:
		task = loop.create_task(task_coro)
		_tasks.append(task)
		logger.info(f"Started {name} (interval: {interval}s)")
	
	logger.info(f"Started {len(_tasks)} background tasks")


async def stop_background_tasks():
	"""Stop all background tasks gracefully."""
	logger.info("Stopping background tasks")
	for task in _tasks:
		task.cancel()
		try:
			await task
		except asyncio.CancelledError:
			pass
	logger.info("All background tasks stopped")


def add_tracked_token(token_address: str):
	"""Add a token to the tracked set."""
	_tracked_tokens.add(token_address)
	logger.info(f"Now tracking {len(_tracked_tokens)} tokens")


# ============================================================================
# Dexscreener Poller
# ============================================================================

async def _dexscreener_poller():
	"""Fetch top token boosts from Dexscreener and save to database."""
	client = DexscreenerClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			try:
				logger.info(f"[Dexscreener] Fetching top boosts (poll #{poll_count})")
				
				# Fetch data from API
				response = await client.fetch_top_boosts()
				
				# Save to both raw and structured tables
				async for session in get_async_session():
					# Save raw response
					raw_repo = RawApiRepository(session)
					await raw_repo.save_response(
						endpoint="/token-boosts/top/v1",
						source="dexscreener",
						response_data=response.dict(),
						status_code=200
					)
					
					# Save structured data
					dex_repo = DexscreenerRepository(session)
					await dex_repo.save_token_boosts_batch(response.items)
					
					# Add tokens to tracking list
					for item in response.items:
						add_tracked_token(item.tokenAddress)
					
					logger.info(f"[Dexscreener] Saved {len(response.items)} boosts (poll #{poll_count})")
					break
					
			except Exception as e:
				logger.error(f"[Dexscreener] Error in poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.DEXSCREENER_FETCH_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Dexscreener] Poller cancelled")
		raise
	finally:
		await client.close()


# ============================================================================
# Birdeye Pollers
# ============================================================================

async def _birdeye_new_listings_poller():
	"""Fetch new listings from Birdeye and save to database."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			try:
				logger.info(f"[Birdeye] Fetching new listings (poll #{poll_count})")
				
				# Fetch new listings
				response = await client.get_new_listings(limit=50)
				
				if response.success:
					async for session in get_async_session():
						# Save raw response
						raw_repo = RawApiRepository(session)
						await raw_repo.save_response(
							endpoint="/defi/v2/tokens/new_listing",
							source="birdeye",
							response_data=response.dict(),
							status_code=200
						)
						
						# Save structured data
						birdeye_repo = BirdeyeRepository(session)
						await birdeye_repo.save_new_listings_batch(response.data.items)
						
						# Add new tokens to tracking list
						for listing in response.data.items:
							add_tracked_token(listing.address)
							
							# Optionally fetch security and overview for new listings
							if settings.TRACK_NEW_LISTINGS_SECURITY:
								try:
									security = await client.get_token_security(listing.address)
									if security.success:
										await birdeye_repo.save_token_security(listing.address, security.data)
								except Exception as e:
									logger.warning(f"[Birdeye] Failed to fetch security for {listing.address}: {str(e)}")
							
							if settings.TRACK_NEW_LISTINGS_OVERVIEW:
								try:
									overview = await client.get_token_overview(listing.address)
									if overview.success:
										await birdeye_repo.save_token_overview(listing.address, overview.data)
								except Exception as e:
									logger.warning(f"[Birdeye] Failed to fetch overview for {listing.address}: {str(e)}")
						
						logger.info(f"[Birdeye] Saved {len(response.data.items)} new listings (poll #{poll_count})")
						break
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in new listings poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_NEW_LISTINGS_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] New listings poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_token_overview_poller():
	"""Fetch token overview for tracked tokens."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			
			if not _tracked_tokens:
				logger.debug("[Birdeye] No tokens to track for overview")
				await asyncio.sleep(settings.BIRDEYE_TOKEN_OVERVIEW_INTERVAL)
				continue
			
			try:
				logger.info(f"[Birdeye] Fetching overview for {len(_tracked_tokens)} tokens (poll #{poll_count})")
				saved_count = 0
				
				for token_address in list(_tracked_tokens):
					try:
						response = await client.get_token_overview(token_address)
						
						if response.success:
							async for session in get_async_session():
								birdeye_repo = BirdeyeRepository(session)
								await birdeye_repo.save_token_overview(token_address, response.data)
								saved_count += 1
								break
						
						# Small delay between requests
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch overview for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved {saved_count} token overviews (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in token overview poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_TOKEN_OVERVIEW_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Token overview poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_token_security_poller():
	"""Fetch token security for tracked tokens."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			
			if not _tracked_tokens:
				logger.debug("[Birdeye] No tokens to track for security")
				await asyncio.sleep(settings.BIRDEYE_TOKEN_SECURITY_INTERVAL)
				continue
			
			try:
				logger.info(f"[Birdeye] Fetching security for {len(_tracked_tokens)} tokens (poll #{poll_count})")
				saved_count = 0
				
				for token_address in list(_tracked_tokens):
					try:
						response = await client.get_token_security(token_address)
						
						if response.success:
							async for session in get_async_session():
								birdeye_repo = BirdeyeRepository(session)
								await birdeye_repo.save_token_security(token_address, response.data)
								saved_count += 1
								break
						
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch security for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved {saved_count} token security checks (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in token security poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_TOKEN_SECURITY_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Token security poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_token_transactions_poller():
	"""Fetch token transactions for tracked tokens."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			
			if not _tracked_tokens:
				logger.debug("[Birdeye] No tokens to track for transactions")
				await asyncio.sleep(settings.BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL)
				continue
			
			try:
				logger.info(f"[Birdeye] Fetching transactions for {len(_tracked_tokens)} tokens (poll #{poll_count})")
				saved_count = 0
				
				for token_address in list(_tracked_tokens):
					try:
						response = await client.get_token_transactions(token_address, limit=50)
						
						if response.success:
							async for session in get_async_session():
								birdeye_repo = BirdeyeRepository(session)
								count = await birdeye_repo.save_token_transactions_batch(
									token_address,
									response.data.items
								)
								saved_count += count
								break
						
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch transactions for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved {saved_count} transactions (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in token transactions poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Token transactions poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_top_traders_poller():
	"""Fetch top traders for tracked tokens."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			
			if not _tracked_tokens:
				logger.debug("[Birdeye] No tokens to track for top traders")
				await asyncio.sleep(settings.BIRDEYE_TOP_TRADERS_INTERVAL)
				continue
			
			try:
				logger.info(f"[Birdeye] Fetching top traders for {len(_tracked_tokens)} tokens (poll #{poll_count})")
				saved_count = 0
				
				for token_address in list(_tracked_tokens):
					try:
						response = await client.get_top_traders(token_address, time_range="24h", limit=10)
						
						if response.success:
							async for session in get_async_session():
								birdeye_repo = BirdeyeRepository(session)
								count = await birdeye_repo.save_top_traders_batch(
									token_address,
									response.data.items
								)
								saved_count += count
								break
						
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch top traders for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved {saved_count} top traders (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in top traders poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_TOP_TRADERS_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Top traders poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_wallet_portfolio_poller():
	"""Fetch wallet portfolios for tracked wallets."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			
			tracked_wallets = settings.tracked_wallets_list
			if not tracked_wallets:
				logger.debug("[Birdeye] No wallets to track for portfolio")
				await asyncio.sleep(settings.BIRDEYE_WALLET_PORTFOLIO_INTERVAL)
				continue
			
			try:
				logger.info(f"[Birdeye] Fetching portfolio for {len(tracked_wallets)} wallets (poll #{poll_count})")
				saved_count = 0
				
				for wallet_address in tracked_wallets:
					try:
						response = await client.get_wallet_portfolio(wallet_address)
						
						if response.success:
							async for session in get_async_session():
								birdeye_repo = BirdeyeRepository(session)
								count = await birdeye_repo.save_wallet_tokens_batch(
									wallet_address,
									response.data.items
								)
								saved_count += count
								break
						
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch portfolio for {wallet_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved {saved_count} wallet tokens (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in wallet portfolio poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_WALLET_PORTFOLIO_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Wallet portfolio poller cancelled")
		raise
	finally:
		await client.close()

