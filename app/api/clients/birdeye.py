"""Birdeye API client."""
import datetime
import time
import logging
from typing import Optional, Dict, Any
from .base_client import BaseApiClient
from ...core.config import settings
from ..schemas.birdeye import (
	TransactionsResponse,
	TopTradersResponse,
	WalletTransactionsResponse,
	WalletTokenListResponse,
	NewListingsResponse,
	TokenSecurityResponse,
	TokenOverviewResponse,
	TokenTrendingResponse,
)

logger = logging.getLogger(__name__)


class BirdeyeClient(BaseApiClient):
	"""Client for Birdeye public API."""

	def __init__(self, api_key: Optional[str] = None):
		super().__init__(base_url="https://public-api.birdeye.so", timeout=30)
		self.api_key = api_key or settings.BIRDEYE_API_KEY

	def _get_headers(self, chain: str = "solana") -> Dict[str, str]:
		"""Get common headers for Birdeye API requests."""
		return {
			"accept": "application/json",
			"x-chain": chain,
			"X-API-KEY": self.api_key,
		}

	# 某个币的交易记录
	async def get_token_transactions(
		self,
		token_address: str,
		tx_type: str = "swap",
		offset: int = 0,
		limit: int = 100,
		before_time: Optional[int] = None,
		after_time: Optional[int] = None,
		ui_amount_mode: str = "scaled",
		chain: str = "solana"
	) -> TransactionsResponse:
		"""
		Get token transactions by time.
		
		Args:
			token_address: Token address to query
			tx_type: Transaction type (e.g., "swap", "add", "remove", "all")
			offset: Pagination offset (0 to 10000)
			limit: Number of results to return (1 to 100)
			before_time: Unix timestamp to fetch transactions before
			after_time: Unix timestamp to fetch transactions after
			ui_amount_mode: Whether to use scaled amount ("scaled" or "raw")
			chain: Blockchain network (default: "solana")
			
		Returns:
			TransactionsResponse: Parsed transaction data
		"""
		logger.info(f"Fetching transactions for token {token_address}")
		
		# API requires either before_time or after_time parameter
		# If neither is provided, use current time as before_time to fetch recent transactions
		if before_time is None and after_time is None:
			before_time = int(time.time())
			logger.debug(f"No time filter provided, using current time as before_time: {before_time}")
		
		# Build query parameters
		params = {
			"address": token_address,
			"tx_type": tx_type,
			"offset": offset,
			"limit": min(limit, 100),  # API limit max 100
			"ui_amount_mode": ui_amount_mode,
		}
		
		# Add time filters
		if before_time:
			params["before_time"] = before_time
		if after_time:
			params["after_time"] = after_time
		
		# Use GET request with query parameters (not POST)
		data = await self.get(
			"/defi/txs/token/seek_by_time",
			params=params,
			headers=self._get_headers(chain)
		)
		return TransactionsResponse(**data)


	# 查询某个币赚钱最多的钱包地址
	async def get_top_traders(
		self,
		token_address: str,
		time_range: str = "24h",
		offset: int = 0,
		limit: int = 10,
		chain: str = "solana"
	) -> TopTradersResponse:
		"""
		Get top traders for a specific token.
		
		Args:
			token_address: Token address to query
			time_range: Time range for analysis (e.g., "24h", "7d")
			offset: Pagination offset
			limit: Number of results to return
			chain: Blockchain network (default: "solana")
			
		Returns:
			TopTradersResponse: Top traders data
		"""
		logger.info(f"Fetching top traders for token {token_address}")
		params = {
			"address": token_address,
			"type": time_range,
			"offset": offset,
			"limit": limit,
		}
		data = await self.get(
			"/defi/v2/tokens/top_traders",
			params=params,
			headers=self._get_headers(chain)
		)
		return TopTradersResponse(**data)

	# 查询某个钱包地址的历史交易接口
	async def get_wallet_transactions(
		self,
		wallet_address: str,
		before: Optional[int] = None,
		limit: int = 10,
		chain: str = "solana"
	) -> WalletTransactionsResponse:
		"""
		Get transaction history for a wallet address.
		
		Args:
			wallet_address: Wallet address to query
			before: Unix timestamp to fetch transactions before
			limit: Number of results to return
			chain: Blockchain network (default: "solana")
			
		Returns:
			WalletTransactionsResponse: Wallet transaction history
		"""
		logger.info(f"Fetching transactions for wallet {wallet_address}")
		params = {
			"wallet": wallet_address,
			"limit": limit,
		}
		if before:
			params["before"] = before
		
		data = await self.get(
			"/v1/wallet/tx_list",
			params=params,
			headers=self._get_headers(chain)
		)
		return WalletTransactionsResponse(**data)

	# 查询钱包地址的投资组合
	async def get_wallet_portfolio(
		self,
		wallet_address: str,
		chain: str = "solana"
	) -> WalletTokenListResponse:
		"""
		Get token portfolio for a wallet address.
		
		Args:
			wallet_address: Wallet address to query
			chain: Blockchain network (default: "solana")
			
		Returns:
			WalletTokenListResponse: Wallet token holdings
		"""
		logger.info(f"Fetching portfolio for wallet {wallet_address}")
		params = {"wallet": wallet_address}
		data = await self.get(
			"/v1/wallet/token_list",
			params=params,
			headers=self._get_headers(chain)
		)
		return WalletTokenListResponse(**data)

	# 查询最近新上币的接口
	async def get_new_listings(
		self,
		limit: int = 20,
		meme_platform_enabled: bool = False,
		chain: str = "solana"
	) -> NewListingsResponse:
		"""
		Get newly listed tokens.
		
		Args:
			limit: Number of results to return (1-20, default: 20)
			meme_platform_enabled: Enable to receive token new listing from meme platforms (eg: pump.fun)
			chain: Blockchain network (default: "solana")
			
		Returns:
			NewListingsResponse: New token listings
		"""
		# 确保 limit 在有效范围内 (1-20)
		limit = max(1, min(limit, 20))
		
		logger.info(f"Fetching new token listings (limit={limit}, meme_platform_enabled={meme_platform_enabled})")
		params = {
			"time_to": int(time.time()),
			"limit": limit,
			"meme_platform_enabled": meme_platform_enabled,
		}
		data = await self.get(
			"/defi/v2/tokens/new_listing",
			params=params,
			headers=self._get_headers(chain)
		)
		return NewListingsResponse(**data)

	# 检查币是否为貔貅
	async def get_token_security(
		self,
		token_address: str,
		chain: str = "solana"
	) -> TokenSecurityResponse:
		"""
		Get security information for a token (e.g., check if it's a honeypot).
		
		Args:
			token_address: Token address to check
			chain: Blockchain network (default: "solana")
			
		Returns:
			TokenSecurityResponse: Token security analysis
		"""
		logger.info(f"Fetching security info for token {token_address}")
		params = {"address": token_address}
		data = await self.get(
			"/defi/token_security",
			params=params,
			headers=self._get_headers(chain)
		)
		return TokenSecurityResponse(**data)

	# 查看币的流动性
	async def get_token_overview(
		self,
		token_address: str,
		chain: str = "solana"
	) -> TokenOverviewResponse:
		"""
		Get comprehensive overview and metrics for a token.
		
		Args:
			token_address: Token address to query
			chain: Blockchain network (default: "solana")
			
		Returns:
			TokenOverviewResponse: Token overview with liquidity, price, volume, etc.
		"""
		logger.info(f"Fetching overview for token {token_address}")
		params = {"address": token_address}
		data = await self.get(
			"/defi/token_overview",
			params=params,
			headers=self._get_headers(chain)
		)
		return TokenOverviewResponse(**data)

	# 获取热门/趋势代币数据
	async def get_token_trending(
		self,
		sort_by: str = "rank",
		sort_type: str = "asc",
		interval: str = "24h",
		offset: int = 0,
		limit: int = 20,
		chain: str = "solana"
	) -> TokenTrendingResponse:
		"""
		Get trending/hot tokens data.
		
		Args:
			sort_by: Sort field (rank, volumeUSD, liquidity)
			sort_type: Sort order (asc or desc)
			interval: Time interval (1h, 4h, 24h)
			offset: Pagination offset
			limit: Number of results to return (1-20)
			chain: Blockchain network (default: "solana")
			
		Returns:
			TokenTrendingResponse: Trending tokens data
		"""
		logger.info(f"Fetching token trending (offset={offset}, limit={limit})")
		params = {
			"sort_by": sort_by,
			"sort_type": sort_type,
			"interval": interval,
			"offset": offset,
			"limit": min(limit, 20),  # API限制最大20
		}
		data = await self.get(
			"/defi/token_trending",
			params=params,
			headers=self._get_headers(chain)
		)
		return TokenTrendingResponse(**data)


