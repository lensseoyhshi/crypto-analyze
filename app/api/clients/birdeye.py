"""Birdeye API client."""
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
		chain: str = "solana"
	) -> TransactionsResponse:
		"""
		Get token transactions by time.
		
		Args:
			token_address: Token address to query
			tx_type: Transaction type (e.g., "swap")
			offset: Pagination offset
			limit: Number of results to return
			chain: Blockchain network (default: "solana")
			
		Returns:
			TransactionsResponse: Parsed transaction data
		"""
		logger.info(f"Fetching transactions for token {token_address}")
		payload = {
			"address": token_address,
			"tx_type": tx_type,
			"offset": offset,
			"limit": limit,
		}
		data = await self.post(
			"/defi/txs/token/seek_by_time",
			json=payload,
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
		sort_by: str = "liquidity",
		sort_type: str = "desc",
		offset: int = 0,
		limit: int = 50,
		chain: str = "solana"
	) -> NewListingsResponse:
		"""
		Get newly listed tokens.
		
		Args:
			sort_by: Field to sort by (e.g., "liquidity", "volume")
			sort_type: Sort direction ("asc" or "desc")
			offset: Pagination offset
			limit: Number of results to return
			chain: Blockchain network (default: "solana")
			
		Returns:
			NewListingsResponse: New token listings
		"""
		logger.info("Fetching new token listings")
		params = {
			"sort_by": sort_by,
			"sort_type": sort_type,
			"offset": offset,
			"limit": limit,
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


