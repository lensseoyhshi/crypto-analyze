"""Background task scheduler for periodic API polling."""
import asyncio
import logging
from typing import Set, Optional
from fastapi import FastAPI
from ..api.clients.dexscreener import DexscreenerClient
from ..api.clients.birdeye import BirdeyeClient
from ..db.session import get_async_session
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
		# (_dexscreener_poller(), "Dexscreener poller", settings.DEXSCREENER_FETCH_INTERVAL),  # Temporarily disabled
		(_birdeye_new_listings_poller(), "Birdeye new listings", settings.BIRDEYE_NEW_LISTINGS_INTERVAL),
		(_birdeye_token_overview_poller(), "Birdeye token overview", settings.BIRDEYE_TOKEN_OVERVIEW_INTERVAL),
		# (_birdeye_token_security_poller(), "Birdeye token security", settings.BIRDEYE_TOKEN_SECURITY_INTERVAL),
		# (_birdeye_token_transactions_poller(), "Birdeye token transactions", settings.BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL),
		# (_birdeye_top_traders_poller(), "Birdeye top traders", settings.BIRDEYE_TOP_TRADERS_INTERVAL),  # 现在由 trending poller 触发
		(_birdeye_wallet_portfolio_poller(), "Birdeye wallet portfolio", settings.BIRDEYE_WALLET_PORTFOLIO_INTERVAL),
		(_birdeye_token_trending_poller(), "Birdeye token trending", settings.BIRDEYE_TOKEN_TRENDING_INTERVAL),
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
# Helper Functions for Async Token Data Fetching
# ============================================================================

async def _fetch_token_security_async(token_address: str):
	"""
	Asynchronously fetch token security information and save to database.
	If token already exists in database, update it; otherwise insert new record.
	
	Args:
		token_address: Token address to check
	"""
	birdeye_client = BirdeyeClient()
	try:
		logger.info(f"[Async] Fetching token security for {token_address}")
		response = await birdeye_client.get_token_security(token_address)
		
		if response.success:
			async for session in get_async_session():
				birdeye_repo = BirdeyeRepository(session)
				await birdeye_repo.save_or_update_token_security(token_address, response.data)
				logger.info(f"[Async] Token security saved/updated for {token_address}")
				break
		else:
			logger.warning(f"[Async] Failed to fetch security for {token_address}: {response.dict()}")
			
	except asyncio.CancelledError:
		logger.debug(f"[Async] Token security fetch cancelled for {token_address}")
		raise  # Re-raise to properly cancel the task
	except Exception as e:
		logger.error(f"[Async] Error fetching token security for {token_address}: {str(e)}", exc_info=True)
	finally:
		await birdeye_client.close()


async def _fetch_token_transactions_async(
	token_address: str, 
	max_transactions: int = 200,
	tx_type: str = "swap",
	before_time: Optional[int] = None,
	after_time: Optional[int] = None,
	fetch_wallet_data: bool = True  # 新增：是否获取钱包数据
):
	"""
	Asynchronously fetch token transactions with pagination and save to database.
	If transaction (txHash) exists in database, update it; otherwise insert new record.
	Also extracts wallet addresses and fetches wallet transactions and portfolio data.
	
	Args:
		token_address: Token address to query
		max_transactions: Maximum number of transactions to fetch (will use pagination)
		tx_type: Transaction type - "swap", "add", "remove", or "all"
		before_time: Unix timestamp to fetch transactions before
		after_time: Unix timestamp to fetch transactions after
		fetch_wallet_data: Whether to fetch wallet transactions and portfolio data
	"""
	birdeye_client = BirdeyeClient()
	try:
		logger.info(f"[Async] Fetching token transactions for {token_address} (tx_type={tx_type}, max={max_transactions})")
		
		total_saved = 0
		all_wallet_addresses = set()  # 收集所有钱包地址
		offset = 0
		limit = 100  # API max limit per request
		max_pages = (max_transactions + limit - 1) // limit  # Calculate number of pages needed
		
		# 分页获取 transactions
		for page in range(max_pages):
			try:
				response = await birdeye_client.get_token_transactions(
					token_address=token_address,
					tx_type=tx_type,
					offset=offset,
					limit=limit,
					before_time=before_time,
					after_time=after_time
				)
				
				if response.success and response.data.items:
					async for session in get_async_session():
						birdeye_repo = BirdeyeRepository(session)
						count = await birdeye_repo.save_or_update_token_transactions_batch(
							token_address, 
							response.data.items
						)
						total_saved += count
						logger.info(f"[Async] Page {page + 1}: Saved/Updated {count} transactions for {token_address}")
						break
					
					# 收集钱包地址
					if fetch_wallet_data:
						for tx in response.data.items:
							if tx.owner:  # owner 就是钱包地址
								all_wallet_addresses.add(tx.owner)
					
					# 如果返回的数量少于 limit，说明已经到最后一页了
					if len(response.data.items) < limit:
						logger.info(f"[Async] Reached last page at page {page + 1} for {token_address}")
						break
					
					# 准备下一页
					offset += limit
					
					# 延迟避免请求过快
					await asyncio.sleep(0.2)
				else:
					logger.warning(f"[Async] No more transactions at offset {offset} for {token_address}")
					break
					
			except Exception as e:
				logger.error(f"[Async] Error fetching page {page + 1} for {token_address}: {str(e)}")
				break
		
		logger.info(f"[Async] Completed: Total saved/updated {total_saved} transactions for {token_address}")
		
		# 为收集到的钱包地址创建后台任务获取钱包数据
		# if fetch_wallet_data and all_wallet_addresses:
		# 	logger.info(f"[Async] Found {len(all_wallet_addresses)} unique wallet addresses, creating background tasks...")
		# 	for wallet_address in all_wallet_addresses:
		# 		# 为每个钱包地址创建异步任务获取交易历史和投资组合
		# 		asyncio.create_task(_fetch_wallet_transactions_async(wallet_address))
		# 		asyncio.create_task(_fetch_wallet_portfolio_async(wallet_address))
		# 	logger.info(f"[Async] Created wallet data fetch tasks for {len(all_wallet_addresses)} wallets")
			
	except asyncio.CancelledError:
		logger.debug(f"[Async] Token transactions fetch cancelled for {token_address}")
		raise  # Re-raise to properly cancel the task
	except Exception as e:
		logger.error(f"[Async] Error fetching token transactions for {token_address}: {str(e)}", exc_info=True)
	finally:
		await birdeye_client.close()


async def _fetch_wallet_transactions_async(wallet_address: str, limit: int = 10):
	"""
	Asynchronously fetch wallet transaction history and save to database.
	
	Args:
		wallet_address: Wallet address to query
		limit: Number of transactions to fetch
	"""
	birdeye_client = BirdeyeClient()
	try:
		logger.info(f"[Async] Fetching wallet transactions for {wallet_address}")
		response = await birdeye_client.get_wallet_transactions(wallet_address, limit=limit)
		
		if response.success and response.data:
			async for session in get_async_session():
				birdeye_repo = BirdeyeRepository(session)
				# 保存钱包交易历史
				count = 0
				for tx in response.data:
					try:
						await birdeye_repo.save_wallet_transaction(wallet_address, tx)
						count += 1
					except Exception as e:
						logger.debug(f"[Async] Failed to save wallet transaction {tx.txHash}: {str(e)}")
						continue
				logger.info(f"[Async] Saved {count} wallet transactions for {wallet_address}")
				break
		else:
			logger.debug(f"[Async] No wallet transactions found for {wallet_address}")
			
	except asyncio.CancelledError:
		logger.debug(f"[Async] Wallet transactions fetch cancelled for {wallet_address}")
		raise
	except Exception as e:
		logger.error(f"[Async] Error fetching wallet transactions for {wallet_address}: {str(e)}", exc_info=True)
	finally:
		await birdeye_client.close()


async def _fetch_wallet_portfolio_async(wallet_address: str):
	"""
	Asynchronously fetch wallet portfolio (token holdings) and save to database.
	
	Args:
		wallet_address: Wallet address to query
	"""
	birdeye_client = BirdeyeClient()
	try:
		logger.info(f"[Async] Fetching wallet portfolio for {wallet_address}")
		response = await birdeye_client.get_wallet_portfolio(wallet_address)
		
		if response.success and response.data.items:
			async for session in get_async_session():
				birdeye_repo = BirdeyeRepository(session)
				# 保存钱包投资组合
				count = await birdeye_repo.save_or_update_wallet_tokens_batch(
					wallet_address,
					response.data.items
				)
				logger.info(f"[Async] Saved/Updated {count} tokens for wallet {wallet_address}")
				break
		else:
			logger.debug(f"[Async] No tokens found in wallet {wallet_address}")
			
	except asyncio.CancelledError:
		logger.debug(f"[Async] Wallet portfolio fetch cancelled for {wallet_address}")
		raise
	except Exception as e:
		logger.error(f"[Async] Error fetching wallet portfolio for {wallet_address}: {str(e)}", exc_info=True)
	finally:
		await birdeye_client.close()


async def _fetch_token_top_traders_async(
	token_address: str, 
	time_frame: str = "24h", 
	max_traders: int = 100,
	sort_by: str = "volume"
):
	"""
	Asynchronously fetch token top traders with pagination and save to database.
	If tokenAddress + owner combination exists in database, update it; otherwise insert new record.
	
	Args:
		token_address: Token address to query
		time_frame: Time frame for top traders (e.g., "24h", "7d", "30d")
		max_traders: Maximum number of top traders to fetch (will use pagination)
		sort_by: Sort field - "volume" or "trade"
	"""
	birdeye_client = BirdeyeClient()
	try:
		logger.info(f"[Async] Fetching top traders for {token_address} (time_frame={time_frame}, max={max_traders})")
		
		total_saved = 0
		offset = 0
		limit = 10  # API max limit per request
		max_pages = (max_traders + limit - 1) // limit  # Calculate number of pages needed
		
		# 分页获取 top traders
		for page in range(max_pages):
			try:
				response = await birdeye_client.get_top_traders(
					token_address=token_address,
					time_frame=time_frame,
					sort_by=sort_by,
					sort_type="desc",
					offset=offset,
					limit=limit
				)
				
				if response.success and response.data.items:
					async for session in get_async_session():
						birdeye_repo = BirdeyeRepository(session)
						count = await birdeye_repo.save_or_update_top_traders_batch(
							token_address, 
							response.data.items
						)
						total_saved += count
						logger.info(f"[Async] Page {page + 1}: Saved/Updated {count} top traders for {token_address}")
						break
					
					# 如果返回的数量少于 limit，说明已经到最后一页了
					if len(response.data.items) < limit:
						logger.info(f"[Async] Reached last page at page {page + 1} for {token_address}")
						break
					
					# 准备下一页
					offset += limit
					
					# 延迟避免请求过快
					await asyncio.sleep(0.3)
				else:
					logger.warning(f"[Async] No more top traders at offset {offset} for {token_address}")
					break
					
			except Exception as e:
				logger.error(f"[Async] Error fetching page {page + 1} for {token_address}: {str(e)}")
				break
		
		logger.info(f"[Async] Completed: Total saved/updated {total_saved} top traders for {token_address}")
			
	except asyncio.CancelledError:
		logger.debug(f"[Async] Top traders fetch cancelled for {token_address}")
		raise  # Re-raise to properly cancel the task
	except Exception as e:
		logger.error(f"[Async] Error fetching top traders for {token_address}: {str(e)}", exc_info=True)
	finally:
		await birdeye_client.close()


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
				
				# Save to structured tables
				async for session in get_async_session():
					# Save or update structured data
					dex_repo = DexscreenerRepository(session)
					
					for item in response.items:
						# Check if token exists in database and save or update
						await dex_repo.save_or_update_token_boost(item)
						
						# Add tokens to tracking list
						add_tracked_token(item.tokenAddress)
						
						# Create background tasks to asynchronously fetch token security and transactions
						token_address = item.tokenAddress
						
						# Create background tasks for each token
						asyncio.create_task(_fetch_token_security_async(token_address))
						asyncio.create_task(_fetch_token_transactions_async(token_address, max_transactions=200))
					
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

# 按时间 查询最近新上币的接口
async def _birdeye_new_listings_poller():
	"""Fetch new listings from Birdeye and save to database."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		logger.info("[Birdeye] New listings poller started - executing first fetch immediately")
		
		while True:
			poll_count += 1
			try:
				logger.info(f"[Birdeye] Fetching new listings (poll #{poll_count})")
				
				# Fetch new listings (API limit: max 20 per request)
				response = await client.get_new_listings(limit=20)
				
				if response.success:
					async for session in get_async_session():
						# Save or update structured data (check by address)
						birdeye_repo = BirdeyeRepository(session)
						await birdeye_repo.save_or_update_new_listings_batch(response.data.items)
						
						# Add new tokens to tracking list
						for listing in response.data.items:
							add_tracked_token(listing.address)
							
							# Optionally fetch security and overview for new listings
							if settings.TRACK_NEW_LISTINGS_SECURITY:
								try:
									security = await client.get_token_security(listing.address)
									if security.success:
										await birdeye_repo.save_or_update_token_security(listing.address, security.data)
								except Exception as e:
									logger.warning(f"[Birdeye] Failed to fetch security for {listing.address}: {str(e)}")
							
							if settings.TRACK_NEW_LISTINGS_OVERVIEW:
								try:
									overview = await client.get_token_overview(listing.address)
									if overview.success:
										await birdeye_repo.save_token_overview(listing.address, overview.data)
								except Exception as e:
									logger.warning(f"[Birdeye] Failed to fetch overview for {listing.address}: {str(e)}")
						
						logger.info(f"[Birdeye] Saved/Updated {len(response.data.items)} new listings (poll #{poll_count})")
						break
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in new listings poller: {str(e)}", exc_info=True)
			
			logger.info(f"[Birdeye] Next new listings fetch in {settings.BIRDEYE_NEW_LISTINGS_INTERVAL} seconds")
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
	"""Fetch token transactions for tracked tokens with pagination support."""
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
				total_saved = 0
				
				for token_address in list(_tracked_tokens):
					try:
						# 分页获取 transactions
						offset = 0
						limit = 100  # API max limit
						max_transactions = 200  # 每个代币最多获取 200 笔交易
						token_saved = 0
						
						for page in range((max_transactions + limit - 1) // limit):
							response = await client.get_token_transactions(
								token_address=token_address,
								tx_type="swap",
								offset=offset,
								limit=limit
							)
							
							if response.success and response.data.items:
								async for session in get_async_session():
									birdeye_repo = BirdeyeRepository(session)
									count = await birdeye_repo.save_or_update_token_transactions_batch(
										token_address,
										response.data.items
									)
									token_saved += count
									break
								
								# 如果返回的数量少于 limit，说明已经到最后一页了
								if len(response.data.items) < limit:
									break
								
								offset += limit
								await asyncio.sleep(0.2)
							else:
								break
						
						total_saved += token_saved
						logger.debug(f"[Birdeye] Saved {token_saved} transactions for {token_address}")
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch transactions for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved/Updated {total_saved} transactions total (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in token transactions poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Token transactions poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_top_traders_poller():
	"""Fetch top traders for tracked tokens with pagination support."""
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
				total_saved = 0
				
				for token_address in list(_tracked_tokens):
					try:
						# 分页获取 top traders
						offset = 0
						limit = 10
						max_traders = 50  # 每个代币最多获取 50 个 top traders
						token_saved = 0
						
						for page in range((max_traders + limit - 1) // limit):
							response = await client.get_top_traders(
								token_address=token_address,
								time_frame="24h",
								sort_by="volume",
								sort_type="desc",
								offset=offset,
								limit=limit
							)
							
							if response.success and response.data.items:
								async for session in get_async_session():
									birdeye_repo = BirdeyeRepository(session)
									count = await birdeye_repo.save_or_update_top_traders_batch(
										token_address,
										response.data.items
									)
									token_saved += count
									break
								
								# 如果返回的数量少于 limit，说明已经到最后一页了
								if len(response.data.items) < limit:
									break
								
								offset += limit
								await asyncio.sleep(0.3)
							else:
								break
						
						total_saved += token_saved
						logger.debug(f"[Birdeye] Saved {token_saved} top traders for {token_address}")
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch top traders for {token_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved/Updated {total_saved} top traders total (poll #{poll_count})")
						
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
								count = await birdeye_repo.save_or_update_wallet_tokens_batch(
									wallet_address,
									response.data.items
								)
								saved_count += count
								break
						
						await asyncio.sleep(0.5)
						
					except Exception as e:
						logger.warning(f"[Birdeye] Failed to fetch portfolio for {wallet_address}: {str(e)}")
				
				logger.info(f"[Birdeye] Saved/Updated {saved_count} wallet tokens (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in wallet portfolio poller: {str(e)}", exc_info=True)
			
			await asyncio.sleep(settings.BIRDEYE_WALLET_PORTFOLIO_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Wallet portfolio poller cancelled")
		raise
	finally:
		await client.close()


async def _birdeye_token_trending_poller():
	"""Fetch trending tokens from Birdeye and save to database with pagination."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		# 立即执行第一次，不等待
		logger.info("[Birdeye] Token trending poller started - executing first fetch immediately")
		
		while True:
			poll_count += 1
			try:
				logger.info(f"[Birdeye] Fetching token trending (poll #{poll_count})")
				
				total_saved = 0
				offset = 0
				limit = 20  # API max limit per request
				max_pages = 50  # 最多获取50页，避免无限循环
				
				# 分页查询
				for page in range(max_pages):
					try:
						# Fetch trending tokens
						response = await client.get_token_trending(
							sort_by="rank",
							sort_type="asc",
							interval="24h",
							offset=offset,
							limit=limit
						)
						
						if response.success and response.data.tokens:
							async for session in get_async_session():
								# Save or update structured data (check by address)
								birdeye_repo = BirdeyeRepository(session)
								count = await birdeye_repo.save_or_update_token_trending_batch(
									response.data.tokens
								)
								total_saved += count
								
								logger.info(f"[Birdeye] Page {page + 1}: Saved/Updated {count} trending tokens")
								
								# Create background tasks for each token
								# 为每个热门代币创建后台任务：获取安全信息、交易记录和 top traders
								for token in response.data.tokens:
									address = token.address
									# 异步获取代币安全信息
									asyncio.create_task(_fetch_token_security_async(address))
									# 异步获取代币交易记录（分页获取，最多 200 笔）
									asyncio.create_task(_fetch_token_transactions_async(
										address, 
										max_transactions=200,
										tx_type="swap"
									))
									# 异步获取代币 top traders（分页获取，最多 50 个）
									asyncio.create_task(_fetch_token_top_traders_async(
										address, 
										time_frame="24h", 
										max_traders=50,
										sort_by="volume"
									))
								
								logger.info(f"[Birdeye] Created background tasks (security, transactions, top traders) for {len(response.data.tokens)} tokens")
								break
							
							# 如果返回的数量少于limit，说明已经到最后一页了
							if len(response.data.tokens) < limit:
								logger.info(f"[Birdeye] Reached last page at page {page + 1}")
								break
							
							# 准备下一页
							offset += limit
							
							# 延迟避免请求过快
							await asyncio.sleep(1)
						else:
							logger.warning(f"[Birdeye] No more trending tokens at offset {offset}")
							break
							
					except Exception as e:
						logger.error(f"[Birdeye] Error fetching page {page + 1}: {str(e)}", exc_info=True)
						break
				
				logger.info(f"[Birdeye] Completed trending fetch: Total saved/updated {total_saved} tokens (poll #{poll_count})")
						
			except Exception as e:
				logger.error(f"[Birdeye] Error in token trending poller: {str(e)}", exc_info=True)
			
			# 执行完成后等待下一个周期
			logger.info(f"[Birdeye] Next trending fetch in {settings.BIRDEYE_TOKEN_TRENDING_INTERVAL} seconds ({settings.BIRDEYE_TOKEN_TRENDING_INTERVAL/3600:.1f} hours)")
			await asyncio.sleep(settings.BIRDEYE_TOKEN_TRENDING_INTERVAL)
			
	except asyncio.CancelledError:
		logger.info("[Birdeye] Token trending poller cancelled")
		raise
	finally:
		await client.close()

