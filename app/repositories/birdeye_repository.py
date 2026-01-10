"""Repository for Birdeye data."""
import json
import logging
from datetime import datetime
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from dateutil import parser as date_parser

from ..db.models import (
	BirdeyeTokenTransaction,
	BirdeyeTopTrader,
	BirdeyeWalletTransaction,
	BirdeyeWalletToken,
	BirdeyeNewListing,
	BirdeyeTokenSecurity,
	BirdeyeTokenOverview,
	BirdeyeTokenTrending
)
from ..api.schemas.birdeye import (
	TransactionItem,
	TopTraderItem,
	WalletTransaction,
	WalletTokenItem,
	NewListingItem,
	TokenSecurityData,
	TokenOverviewData,
	TokenTrendingItem
)

logger = logging.getLogger(__name__)


# ============================================================================
# 数据清理和验证工具函数
# ============================================================================

def safe_float(value: Union[float, int, None], max_value: float = 1e38) -> Optional[float]:
	"""
	安全地处理浮点数，避免数据库溢出。
	
	MySQL FLOAT 范围: ±3.402823466E+38
	MySQL DOUBLE 范围: ±1.7976931348623157E+308
	
	Args:
		value: 原始值
		max_value: 最大允许值（默认 1e38，适用于 FLOAT）
		
	Returns:
		处理后的安全值，如果超出范围则返回 None
	"""
	if value is None:
		return None
	
	try:
		float_value = float(value)
		
		# 检查是否为无穷大或 NaN
		if not (-max_value <= float_value <= max_value):
			logger.warning(f"Value {value} exceeds max_value {max_value}, setting to None")
			return None
		
		return float_value
	except (ValueError, TypeError, OverflowError) as e:
		logger.warning(f"Failed to convert value {value} to float: {e}")
		return None


def safe_double(value: Union[float, int, None]) -> Optional[float]:
	"""
	安全地处理 DOUBLE 类型的浮点数。
	对于 DOUBLE 类型，使用更大的范围（1e308）
	"""
	return safe_float(value, max_value=1e308)


class BirdeyeRepository:
	"""Repository for managing Birdeye data."""
	
	def __init__(self, session: AsyncSession):
		self.session = session
	
	# ========================================================================
	# Token Transactions
	# ========================================================================
	
	async def save_or_update_token_transaction(
		self,
		token_address: str,
		transaction: TransactionItem
	) -> BirdeyeTokenTransaction:
		"""
		Save or update a token transaction based on txHash.
		If txHash exists, update the record; otherwise insert new record.
		
		Args:
			token_address: Token address
			transaction: TransactionItem schema object
			
		Returns:
			BirdeyeTokenTransaction: The saved or updated database record
		"""
		try:
			# Check if transaction already exists
			query = select(BirdeyeTokenTransaction).where(
				BirdeyeTokenTransaction.txHash == transaction.txHash
			)
			result = await self.session.execute(query)
			existing_tx = result.scalar_one_or_none()
			
			# Convert token info to JSON strings
			quote_json = json.dumps(transaction.quote.dict()) if transaction.quote else None
			base_json = json.dumps(transaction.base.dict()) if transaction.base else None
			from_json = json.dumps(transaction.from_token.dict()) if transaction.from_token else None
			to_json = json.dumps(transaction.to_token.dict()) if transaction.to_token else None
			
			# Convert block time
			block_time = datetime.fromtimestamp(transaction.blockUnixTime) if transaction.blockUnixTime else None
			
			if existing_tx:
				# Update existing record
				existing_tx.quote = quote_json
				existing_tx.base = base_json
				existing_tx.basePrice = safe_double(transaction.basePrice)
				existing_tx.quotePrice = safe_double(transaction.quotePrice)
				existing_tx.pricePair = safe_double(transaction.pricePair)
				existing_tx.tokenPrice = safe_double(transaction.tokenPrice)
				existing_tx.source = transaction.source
				existing_tx.blockUnixTime = transaction.blockUnixTime
				existing_tx.txType = transaction.txType
				existing_tx.owner = transaction.owner
				existing_tx.side = transaction.side
				existing_tx.poolId = transaction.poolId
				existing_tx.from_data = from_json
				existing_tx.to_data = to_json
				existing_tx.block_time = block_time
				
				await self.session.commit()
				await self.session.refresh(existing_tx)
				
				logger.debug(f"Updated transaction: {transaction.txHash}")
				return existing_tx
			else:
				# Insert new record
				db_tx = BirdeyeTokenTransaction(
					quote=quote_json,
					base=base_json,
					basePrice=safe_double(transaction.basePrice),
					quotePrice=safe_double(transaction.quotePrice),
					pricePair=safe_double(transaction.pricePair),
					tokenPrice=safe_double(transaction.tokenPrice),
					txHash=transaction.txHash,
					source=transaction.source,
					blockUnixTime=transaction.blockUnixTime,
					txType=transaction.txType,
					owner=transaction.owner,
					side=transaction.side,
					poolId=transaction.poolId,
					from_data=from_json,
					to_data=to_json,
					block_time=block_time
				)
				
				self.session.add(db_tx)
				await self.session.commit()
				await self.session.refresh(db_tx)
				
				logger.debug(f"Inserted new transaction: {transaction.txHash}")
				return db_tx
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating transaction: {str(e)}")
			raise
	
	async def save_or_update_token_transactions_batch(
		self,
		token_address: str,
		transactions: List[TransactionItem]
	) -> int:
		"""
		Save or update multiple transactions in batch.
		Each transaction is checked by txHash and updated if exists or inserted if not.
		
		Args:
			token_address: Token address
			transactions: List of TransactionItem objects
			
		Returns:
			int: Number of successfully saved/updated transactions
		"""
		saved_count = 0
		for tx in transactions:
			try:
				await self.save_or_update_token_transaction(token_address, tx)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save/update transaction {tx.txHash}: {str(e)}")
				continue
		
		logger.info(f"Saved/Updated {saved_count}/{len(transactions)} transactions for token {token_address}")
		return saved_count
	
	async def save_token_transaction(
		self,
		token_address: str,
		transaction: TransactionItem
	) -> BirdeyeTokenTransaction:
		"""Save a token transaction."""
		try:
			# Convert token info to JSON strings
			quote_json = json.dumps(transaction.quote.dict()) if transaction.quote else None
			base_json = json.dumps(transaction.base.dict()) if transaction.base else None
			from_json = json.dumps(transaction.from_token.dict()) if transaction.from_token else None
			to_json = json.dumps(transaction.to_token.dict()) if transaction.to_token else None
			
			# Convert block time
			block_time = datetime.fromtimestamp(transaction.blockUnixTime) if transaction.blockUnixTime else None
			
			db_tx = BirdeyeTokenTransaction(
				quote=quote_json,
				base=base_json,
				basePrice=transaction.basePrice,
				quotePrice=transaction.quotePrice,
				pricePair=transaction.pricePair,
				tokenPrice=transaction.tokenPrice,
				txHash=transaction.txHash,
				source=transaction.source,
				blockUnixTime=transaction.blockUnixTime,
				txType=transaction.txType,
				owner=transaction.owner,
				side=transaction.side,
				poolId=transaction.poolId,
				from_data=from_json,
				to_data=to_json,
				block_time=block_time
			)
			
			self.session.add(db_tx)
			await self.session.commit()
			await self.session.refresh(db_tx)
			
			logger.debug(f"Saved transaction: {transaction.txHash}")
			return db_tx
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving transaction: {str(e)}")
			raise
	
	async def save_token_transactions_batch(
		self,
		token_address: str,
		transactions: List[TransactionItem]
	) -> int:
		"""Save multiple transactions in batch."""
		saved_count = 0
		for tx in transactions:
			try:
				await self.save_token_transaction(token_address, tx)
				saved_count += 1
			except Exception as e:
				# Skip duplicate transactions (unique constraint on txHash)
				if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
					logger.debug(f"Transaction already exists: {tx.txHash}")
					continue
				logger.warning(f"Failed to save transaction {tx.txHash}: {str(e)}")
				continue
		
		logger.info(f"Saved {saved_count}/{len(transactions)} transactions for token {token_address}")
		return saved_count
	
	# ========================================================================
	# Top Traders
	# ========================================================================
	
	async def save_or_update_top_trader(
		self,
		token_address: str,
		trader: TopTraderItem
	) -> BirdeyeTopTrader:
		"""
		Save or update a top trader based on tokenAddress and owner combination.
		If the combination exists, update the record; otherwise insert new record.
		
		Args:
			token_address: Token address
			trader: TopTraderItem schema object
			
		Returns:
			BirdeyeTopTrader: The saved or updated database record
		"""
		try:
			# Check if top trader already exists (by tokenAddress and owner)
			query = select(BirdeyeTopTrader).where(
				BirdeyeTopTrader.tokenAddress == token_address,
				BirdeyeTopTrader.owner == trader.owner
			)
			result = await self.session.execute(query)
			existing_trader = result.scalar_one_or_none()
			
			# Convert tags list to JSON string
			tags_str = None
			if trader.tags:
				tags_str = json.dumps(trader.tags)
			
			if existing_trader:
				# Update existing record
				existing_trader.type = trader.type
				existing_trader.volume = trader.volume
				existing_trader.trade = trader.trade
				existing_trader.tradeBuy = trader.tradeBuy
				existing_trader.tradeSell = trader.tradeSell
				existing_trader.volumeBuy = trader.volumeBuy
				existing_trader.volumeSell = trader.volumeSell
				existing_trader.tags = tags_str
				
				await self.session.commit()
				await self.session.refresh(existing_trader)
				
				logger.debug(f"Updated top trader: {trader.owner} for token {token_address}")
				return existing_trader
			else:
				# Insert new record
				db_trader = BirdeyeTopTrader(
					tokenAddress=token_address,
					owner=trader.owner,
					type=trader.type,
					volume=trader.volume,
					trade=trader.trade,
					tradeBuy=trader.tradeBuy,
					tradeSell=trader.tradeSell,
					volumeBuy=trader.volumeBuy,
					volumeSell=trader.volumeSell,
					tags=tags_str
				)
				
				self.session.add(db_trader)
				await self.session.commit()
				await self.session.refresh(db_trader)
				
				logger.debug(f"Inserted new top trader: {trader.owner} for token {token_address}")
				return db_trader
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating top trader: {str(e)}")
			raise
	
	async def save_or_update_top_traders_batch(
		self,
		token_address: str,
		traders: List[TopTraderItem]
	) -> int:
		"""
		Save or update multiple top traders in batch.
		Each trader is checked by tokenAddress + owner and updated if exists or inserted if not.
		
		Args:
			token_address: Token address
			traders: List of TopTraderItem objects
			
		Returns:
			int: Number of successfully saved/updated traders
		"""
		saved_count = 0
		for trader in traders:
			try:
				await self.save_or_update_top_trader(token_address, trader)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save/update trader {trader.owner}: {str(e)}")
				continue
		
		logger.info(f"Saved/Updated {saved_count}/{len(traders)} top traders for token {token_address}")
		return saved_count
	
	async def save_top_trader(
		self,
		token_address: str,
		trader: TopTraderItem
	) -> BirdeyeTopTrader:
		"""Save a top trader."""
		try:
			# Convert tags list to JSON string
			tags_str = None
			if trader.tags:
				tags_str = json.dumps(trader.tags)
			
			db_trader = BirdeyeTopTrader(
				tokenAddress=token_address,
				owner=trader.owner,
				type=trader.type,
				volume=trader.volume,
				trade=trader.trade,
				tradeBuy=trader.tradeBuy,
				tradeSell=trader.tradeSell,
				volumeBuy=trader.volumeBuy,
				volumeSell=trader.volumeSell,
				tags=tags_str
			)
			
			self.session.add(db_trader)
			await self.session.commit()
			await self.session.refresh(db_trader)
			
			logger.debug(f"Saved top trader: {trader.owner}")
			return db_trader
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving top trader: {str(e)}")
			raise
	
	async def save_top_traders_batch(
		self,
		token_address: str,
		traders: List[TopTraderItem]
	) -> int:
		"""Save multiple top traders in batch."""
		saved_count = 0
		for trader in traders:
			try:
				await self.save_top_trader(token_address, trader)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save trader {trader.owner}: {str(e)}")
				continue
		
		logger.info(f"Saved {saved_count}/{len(traders)} top traders for token {token_address}")
		return saved_count
	
	# ========================================================================
	# Wallet Transactions
	# ========================================================================
	
	async def save_wallet_transaction(
		self,
		wallet_address: str,
		transaction: WalletTransaction
	) -> BirdeyeWalletTransaction:
		"""Save a wallet transaction."""
		try:
			# Parse block time
			block_time = date_parser.parse(transaction.blockTime) if transaction.blockTime else datetime.utcnow()
			
			# Convert to JSON strings
			balance_change_json = None
			if transaction.balanceChange:
				balance_change_json = json.dumps([bc.dict() for bc in transaction.balanceChange])
			
			token_transfers_json = None
			if transaction.tokenTransfers:
				token_transfers_json = json.dumps([tt.dict() for tt in transaction.tokenTransfers])
			
			contract_label_json = None
			if transaction.contractLabel:
				contract_label_json = json.dumps(transaction.contractLabel.dict())
			
			db_tx = BirdeyeWalletTransaction(
				tx_hash=transaction.txHash,
				block_number=transaction.blockNumber,
				block_time=block_time,
				status=transaction.status,
				from_address=transaction.from_address,
				to_address=transaction.to_address,
				fee=transaction.fee,
				main_action=transaction.mainAction,
				balance_change=balance_change_json,
				token_transfers=token_transfers_json,
				contract_label=contract_label_json,
				create_time=datetime.utcnow(),
				update_time=datetime.utcnow()
			)
			
			self.session.add(db_tx)
			await self.session.commit()
			await self.session.refresh(db_tx)
			
			logger.debug(f"Saved wallet transaction: {transaction.txHash}")
			return db_tx
			
		except Exception as e:
			await self.session.rollback()
			# Skip duplicate transactions
			if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
				logger.debug(f"Wallet transaction already exists: {transaction.txHash}")
				return None
			logger.error(f"Error saving wallet transaction: {str(e)}")
			raise
	
	# ========================================================================
	# Wallet Tokens (Portfolio)
	# ========================================================================
	
	async def save_or_update_wallet_token(
		self,
		wallet_address: str,
		token: WalletTokenItem,
		snapshot_at: Optional[datetime] = None
	) -> BirdeyeWalletToken:
		"""
		Save or update a wallet token holding based on wallet_address and token_address combination.
		If the combination exists, update the record; otherwise insert new record.
		
		Args:
			wallet_address: Wallet address
			token: WalletTokenItem schema object
			snapshot_at: Optional snapshot timestamp
			
		Returns:
			BirdeyeWalletToken: The saved or updated database record
		"""
		try:
			# Check if wallet token already exists (by wallet_address and token_address)
			query = select(BirdeyeWalletToken).where(
				BirdeyeWalletToken.wallet_address == wallet_address,
				BirdeyeWalletToken.token_address == token.address
			).order_by(desc(BirdeyeWalletToken.snapshot_at)).limit(1)
			
			result = await self.session.execute(query)
			existing_token = result.scalar_one_or_none()
			
			snapshot_time = snapshot_at or datetime.utcnow()
			
			if existing_token:
				# Update existing record
				existing_token.symbol = token.symbol
				existing_token.name = token.name
				existing_token.decimals = token.decimals
				existing_token.balance = str(token.balance)
				existing_token.ui_amount = token.uiAmount
				existing_token.price_usd = token.priceUsd
				existing_token.value_usd = token.valueUsd
				existing_token.chain_id = token.chainId
				existing_token.logo_uri = token.logoURI
				existing_token.snapshot_at = snapshot_time
				
				await self.session.commit()
				await self.session.refresh(existing_token)
				
				logger.debug(f"Updated wallet token: {token.symbol} for wallet {wallet_address}")
				return existing_token
			else:
				# Insert new record
				db_token = BirdeyeWalletToken(
					wallet_address=wallet_address,
					token_address=token.address,
					symbol=token.symbol,
					name=token.name,
					decimals=token.decimals,
					balance=str(token.balance),
					ui_amount=token.uiAmount,
					price_usd=token.priceUsd,
					value_usd=token.valueUsd,
					chain_id=token.chainId,
					logo_uri=token.logoURI,
					snapshot_at=snapshot_time,
					created_at=datetime.utcnow()
				)
				
				self.session.add(db_token)
				await self.session.commit()
				await self.session.refresh(db_token)
				
				logger.debug(f"Inserted new wallet token: {token.symbol} for wallet {wallet_address}")
				return db_token
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating wallet token: {str(e)}")
			raise
	
	async def save_or_update_wallet_tokens_batch(
		self,
		wallet_address: str,
		tokens: List[WalletTokenItem]
	) -> int:
		"""
		Save or update multiple wallet tokens in batch.
		Each token is checked by wallet_address + token_address and updated if exists or inserted if not.
		
		Args:
			wallet_address: Wallet address
			tokens: List of WalletTokenItem objects
			
		Returns:
			int: Number of successfully saved/updated tokens
		"""
		snapshot_at = datetime.utcnow()
		saved_count = 0
		
		for token in tokens:
			try:
				await self.save_or_update_wallet_token(wallet_address, token, snapshot_at)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save/update token {token.address}: {str(e)}")
				continue
		
		logger.info(f"Saved/Updated {saved_count}/{len(tokens)} tokens for wallet {wallet_address}")
		return saved_count
	
	async def save_wallet_token(
		self,
		wallet_address: str,
		token: WalletTokenItem,
		snapshot_at: Optional[datetime] = None
	) -> BirdeyeWalletToken:
		"""Save a wallet token holding."""
		try:
			db_token = BirdeyeWalletToken(
				wallet_address=wallet_address,
				token_address=token.address,
				symbol=token.symbol,
				name=token.name,
				decimals=token.decimals,
				balance=str(token.balance),
				ui_amount=token.uiAmount,
				price_usd=token.priceUsd,
				value_usd=token.valueUsd,
				chain_id=token.chainId,
				logo_uri=token.logoURI,
				snapshot_at=snapshot_at or datetime.utcnow(),
				created_at=datetime.utcnow()
			)
			
			self.session.add(db_token)
			await self.session.commit()
			await self.session.refresh(db_token)
			
			logger.debug(f"Saved wallet token: {token.symbol}")
			return db_token
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving wallet token: {str(e)}")
			raise
	
	async def save_wallet_tokens_batch(
		self,
		wallet_address: str,
		tokens: List[WalletTokenItem]
	) -> int:
		"""Save multiple wallet tokens in batch."""
		snapshot_at = datetime.utcnow()
		saved_count = 0
		
		for token in tokens:
			try:
				await self.save_wallet_token(wallet_address, token, snapshot_at)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save token {token.address}: {str(e)}")
				continue
		
		logger.info(f"Saved {saved_count}/{len(tokens)} tokens for wallet {wallet_address}")
		return saved_count
	
	# ========================================================================
	# New Listings
	# ========================================================================
	
	async def save_or_update_new_listing(self, listing: NewListingItem) -> BirdeyeNewListing:
		"""
		Save or update a new token listing based on address.
		If address exists, update the record; otherwise insert new record.
		
		Args:
			listing: NewListingItem schema object
			
		Returns:
			BirdeyeNewListing: The saved or updated database record
		"""
		try:
			# Check if listing already exists
			query = select(BirdeyeNewListing).where(
				BirdeyeNewListing.address == listing.address
			)
			result = await self.session.execute(query)
			existing_listing = result.scalar_one_or_none()
			
			# Parse liquidity added time
			liquidity_added_at = None
			if listing.liquidityAddedAt:
				try:
					liquidity_added_at = date_parser.parse(listing.liquidityAddedAt)
				except:
					pass
			
			if existing_listing:
				# Update existing record
				existing_listing.symbol = listing.symbol
				existing_listing.name = listing.name
				existing_listing.decimals = listing.decimals
				existing_listing.source = listing.source
				existing_listing.liquidity = safe_double(listing.liquidity)
				existing_listing.liquidity_added_at = liquidity_added_at
				existing_listing.logo_uri = listing.logoURI
				existing_listing.update_time = datetime.utcnow()
				
				await self.session.commit()
				await self.session.refresh(existing_listing)
				
				logger.debug(f"Updated new listing: {listing.symbol} ({listing.address})")
				return existing_listing
			else:
				# Insert new record
				db_listing = BirdeyeNewListing(
					address=listing.address,
					symbol=listing.symbol,
					name=listing.name,
					decimals=listing.decimals,
					source=listing.source,
					liquidity=safe_double(listing.liquidity),
					liquidity_added_at=liquidity_added_at,
					logo_uri=listing.logoURI,
					create_time=datetime.utcnow(),
					update_time=datetime.utcnow()
				)
				
				self.session.add(db_listing)
				await self.session.commit()
				await self.session.refresh(db_listing)
				
				logger.debug(f"Inserted new listing: {listing.symbol} ({listing.address})")
				return db_listing
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating new listing: {str(e)}")
			raise
	
	async def save_or_update_new_listings_batch(self, listings: List[NewListingItem]) -> int:
		"""
		Save or update multiple new listings in batch.
		Each listing is checked by address and updated if exists or inserted if not.
		
		Args:
			listings: List of NewListingItem objects
			
		Returns:
			int: Number of successfully saved/updated listings
		"""
		saved_count = 0
		for listing in listings:
			try:
				await self.save_or_update_new_listing(listing)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save/update listing {listing.address}: {str(e)}")
				continue
		
		logger.info(f"Saved/Updated {saved_count}/{len(listings)} new listings")
		return saved_count
	
	async def save_new_listing(self, listing: NewListingItem) -> BirdeyeNewListing:
		"""Save a new token listing."""
		try:
			# Parse liquidity added time
			liquidity_added_at = None
			if listing.liquidityAddedAt:
				try:
					liquidity_added_at = date_parser.parse(listing.liquidityAddedAt)
				except:
					pass
			
			db_listing = BirdeyeNewListing(
				address=listing.address,
				symbol=listing.symbol,
				name=listing.name,
				decimals=listing.decimals,
				source=listing.source,
				liquidity=listing.liquidity,
				liquidity_added_at=liquidity_added_at,
				logo_uri=listing.logoURI,
				create_time=datetime.utcnow(),
				update_time=datetime.utcnow()
			)
			
			self.session.add(db_listing)
			await self.session.commit()
			await self.session.refresh(db_listing)
			
			logger.debug(f"Saved new listing: {listing.symbol}")
			return db_listing
			
		except Exception as e:
			await self.session.rollback()
			# Skip if already exists (unique constraint)
			if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
				logger.debug(f"Listing already exists: {listing.address}")
				return None
			logger.error(f"Error saving new listing: {str(e)}")
			raise
	
	async def save_new_listings_batch(self, listings: List[NewListingItem]) -> int:
		"""Save multiple new listings in batch."""
		saved_count = 0
		for listing in listings:
			try:
				result = await self.save_new_listing(listing)
				if result:
					saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save listing {listing.address}: {str(e)}")
				continue
		
		logger.info(f"Saved {saved_count}/{len(listings)} new listings")
		return saved_count
	
	# ========================================================================
	# Token Security
	# ========================================================================
	
	async def save_or_update_token_security(
		self,
		token_address: str,
		security: TokenSecurityData
	) -> BirdeyeTokenSecurity:
		"""
		Save or update token security information.
		If token_address already exists, update it; otherwise insert new record.
		
		Args:
			token_address: Token address to check/save
			security: TokenSecurityData schema object
			
		Returns:
			BirdeyeTokenSecurity: The saved or updated database record
		"""
		try:
			# Check if token security already exists
			query = select(BirdeyeTokenSecurity).where(
				BirdeyeTokenSecurity.token_address == token_address
			)
			result = await self.session.execute(query)
			existing_security = result.scalar_one_or_none()
			
			# Convert to JSON strings
			pre_market_holder_json = None
			if security.preMarketHolder:
				pre_market_holder_json = json.dumps(security.preMarketHolder)
			
			lock_info_json = None
			if security.lockInfo:
				lock_info_json = json.dumps(security.lockInfo)
			
			transfer_fee_data_json = None
			if security.transferFeeData:
				transfer_fee_data_json = json.dumps(security.transferFeeData)
			
			if existing_security:
				# Update existing record
				existing_security.creator_address = security.creatorAddress
				existing_security.creator_owner_address = security.creatorOwnerAddress
				existing_security.owner_address = security.ownerAddress
				existing_security.owner_of_owner_address = security.ownerOfOwnerAddress
				existing_security.creation_tx = security.creationTx
				existing_security.creation_time = security.creationTime
				existing_security.creation_slot = security.creationSlot
				existing_security.mint_tx = security.mintTx
				existing_security.mint_time = security.mintTime
				existing_security.mint_slot = security.mintSlot
				existing_security.creator_balance = security.creatorBalance
				existing_security.creator_percentage = security.creatorPercentage
				existing_security.owner_balance = security.ownerBalance
				existing_security.owner_percentage = security.ownerPercentage
				existing_security.total_supply = security.totalSupply
				existing_security.metaplex_update_authority = security.metaplexUpdateAuthority
				existing_security.metaplex_owner_update_authority = security.metaplexOwnerUpdateAuthority
				existing_security.metaplex_update_authority_balance = security.metaplexUpdateAuthorityBalance
				existing_security.metaplex_update_authority_percent = security.metaplexUpdateAuthorityPercent
				existing_security.mutable_metadata = security.mutableMetadata
				existing_security.top10_holder_balance = security.top10HolderBalance
				existing_security.top10_holder_percent = security.top10HolderPercent
				existing_security.top10_user_balance = security.top10UserBalance
				existing_security.top10_user_percent = security.top10UserPercent
				existing_security.pre_market_holder = pre_market_holder_json
				existing_security.lock_info = lock_info_json
				existing_security.transfer_fee_data = transfer_fee_data_json
				existing_security.is_true_token = security.isTrueToken
				existing_security.is_token_2022 = security.isToken2022
				existing_security.freezeable = security.freezeable
				existing_security.freeze_authority = security.freezeAuthority
				existing_security.transfer_fee_enable = security.transferFeeEnable
				existing_security.non_transferable = security.nonTransferable
				existing_security.update_time = datetime.utcnow()
				
				await self.session.commit()
				await self.session.refresh(existing_security)
				
				logger.debug(f"Updated token security: {token_address}")
				return existing_security
			else:
				# Insert new record
				db_security = BirdeyeTokenSecurity(
					token_address=token_address,
					creator_address=security.creatorAddress,
					creator_owner_address=security.creatorOwnerAddress,
					owner_address=security.ownerAddress,
					owner_of_owner_address=security.ownerOfOwnerAddress,
					creation_tx=security.creationTx,
					creation_time=security.creationTime,
					creation_slot=security.creationSlot,
					mint_tx=security.mintTx,
					mint_time=security.mintTime,
					mint_slot=security.mintSlot,
					creator_balance=security.creatorBalance,
					creator_percentage=security.creatorPercentage,
					owner_balance=security.ownerBalance,
					owner_percentage=security.ownerPercentage,
					total_supply=security.totalSupply,
					metaplex_update_authority=security.metaplexUpdateAuthority,
					metaplex_owner_update_authority=security.metaplexOwnerUpdateAuthority,
					metaplex_update_authority_balance=security.metaplexUpdateAuthorityBalance,
					metaplex_update_authority_percent=security.metaplexUpdateAuthorityPercent,
					mutable_metadata=security.mutableMetadata,
					top10_holder_balance=security.top10HolderBalance,
					top10_holder_percent=security.top10HolderPercent,
					top10_user_balance=security.top10UserBalance,
					top10_user_percent=security.top10UserPercent,
					pre_market_holder=pre_market_holder_json,
					lock_info=lock_info_json,
					transfer_fee_data=transfer_fee_data_json,
					is_true_token=security.isTrueToken,
					is_token_2022=security.isToken2022,
					freezeable=security.freezeable,
					freeze_authority=security.freezeAuthority,
					transfer_fee_enable=security.transferFeeEnable,
					non_transferable=security.nonTransferable,
					create_time=datetime.utcnow(),
					update_time=datetime.utcnow()
				)
				
				self.session.add(db_security)
				await self.session.commit()
				await self.session.refresh(db_security)
				
				logger.debug(f"Inserted new token security: {token_address}")
				return db_security
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating token security: {str(e)}")
			raise
	
	async def save_token_security(
		self,
		token_address: str,
		security: TokenSecurityData
	) -> BirdeyeTokenSecurity:
		"""Save token security information."""
		try:
			# Convert pre_market_holder to JSON string
			pre_market_holder_json = None
			if security.preMarketHolder:
				pre_market_holder_json = json.dumps(security.preMarketHolder)
			
			# Convert lock_info to JSON string
			lock_info_json = None
			if security.lockInfo:
				lock_info_json = json.dumps(security.lockInfo)
			
			# Convert transfer_fee_data to JSON string
			transfer_fee_data_json = None
			if security.transferFeeData:
				transfer_fee_data_json = json.dumps(security.transferFeeData)
			
			db_security = BirdeyeTokenSecurity(
				token_address=token_address,
				creator_address=security.creatorAddress,
				creator_owner_address=security.creatorOwnerAddress,
				owner_address=security.ownerAddress,
				owner_of_owner_address=security.ownerOfOwnerAddress,
				creation_tx=security.creationTx,
				creation_time=security.creationTime,
				creation_slot=security.creationSlot,
				mint_tx=security.mintTx,
				mint_time=security.mintTime,
				mint_slot=security.mintSlot,
				creator_balance=security.creatorBalance,
				creator_percentage=security.creatorPercentage,
				owner_balance=security.ownerBalance,
				owner_percentage=security.ownerPercentage,
				total_supply=security.totalSupply,
				metaplex_update_authority=security.metaplexUpdateAuthority,
				metaplex_owner_update_authority=security.metaplexOwnerUpdateAuthority,
				metaplex_update_authority_balance=security.metaplexUpdateAuthorityBalance,
				metaplex_update_authority_percent=security.metaplexUpdateAuthorityPercent,
				mutable_metadata=security.mutableMetadata,
				top10_holder_balance=security.top10HolderBalance,
				top10_holder_percent=security.top10HolderPercent,
				top10_user_balance=security.top10UserBalance,
				top10_user_percent=security.top10UserPercent,
				pre_market_holder=pre_market_holder_json,
				lock_info=lock_info_json,
				transfer_fee_data=transfer_fee_data_json,
				is_true_token=security.isTrueToken,
				is_token_2022=security.isToken2022,
				freezeable=security.freezeable,
				freeze_authority=security.freezeAuthority,
				transfer_fee_enable=security.transferFeeEnable,
				non_transferable=security.nonTransferable,
				create_time=datetime.utcnow(),
				update_time=datetime.utcnow()
			)
			
			self.session.add(db_security)
			await self.session.commit()
			await self.session.refresh(db_security)
			
			logger.debug(f"Saved token security: {token_address}")
			return db_security
			
		except Exception as e:
			await self.session.rollback()
			# Skip if already exists (unique constraint)
			if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
				logger.debug(f"Token security already exists: {token_address}")
				return None
			logger.error(f"Error saving token security: {str(e)}")
			raise
	
	# ========================================================================
	# Token Overview
	# ========================================================================
	
	async def save_token_overview(
		self,
		token_address: str,
		overview: TokenOverviewData
	) -> BirdeyeTokenOverview:
		"""Save token overview information with safe float handling."""
		try:
			# Parse last trade time
			last_trade_time = None
			if overview.lastTradeHumanTime:
				try:
					last_trade_time = date_parser.parse(overview.lastTradeHumanTime)
				except:
					pass
			
			db_overview = BirdeyeTokenOverview(
				token_address=token_address,
				price=safe_float(overview.price),
				market_cap=safe_double(overview.marketCap),
				fdv=safe_double(overview.fdv),
				liquidity=safe_double(overview.liquidity),
				total_supply=safe_float(overview.totalSupply),
				circulating_supply=safe_float(overview.circulatingSupply),
				holder=overview.holder,
				number_markets=overview.numberMarkets,
				price_change_24h_percent=safe_float(overview.priceChange24hPercent),
				v24h=safe_double(overview.v24h),
				v24h_usd=safe_double(overview.v24hUSD),
				trade_24h=overview.trade24h,
				buy_24h=overview.buy24h,
				sell_24h=overview.sell24h,
				unique_wallet_24h=overview.uniqueWallet24h,
				price_change_1h_percent=safe_float(overview.priceChange1hPercent),
				v1h=safe_double(overview.v1h),
				v1h_usd=safe_double(overview.v1hUSD),
				v30m=safe_double(overview.v30m),
				v30m_usd=safe_double(overview.v30mUSD),
				last_trade_unix_time=overview.lastTradeUnixTime,
				last_trade_human_time=last_trade_time,
				created_at=datetime.utcnow()
			)
			
			self.session.add(db_overview)
			await self.session.commit()
			await self.session.refresh(db_overview)
			
			logger.debug(f"Saved token overview: {token_address}")
			return db_overview
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving token overview: {str(e)}")
			raise
	
	# ========================================================================
	# Token Trending
	# ========================================================================
	
	async def save_or_update_token_trending(
		self,
		trending: TokenTrendingItem
	) -> BirdeyeTokenTrending:
		"""
		Save or update a trending token based on address.
		If address exists, update the record; otherwise insert new record.
		
		Args:
			trending: TokenTrendingItem schema object
			
		Returns:
			BirdeyeTokenTrending: The saved or updated database record
		"""
		try:
			# 使用 safe_double 处理可能超出范围的大数值
			# DECIMAL(30,30) 实际上是整数部分0位，小数部分30位，只能存储 0-1 之间的数
			# 应该改用 safe_double 让数据库用 DOUBLE 类型存储
			safe_marketcap = safe_double(trending.marketcap)
			safe_fdv = safe_double(trending.fdv)
			safe_liquidity = safe_double(trending.liquidity)
			safe_volume = safe_double(trending.volume24hUSD)
			
			# Check if trending token already exists
			query = select(BirdeyeTokenTrending).where(
				BirdeyeTokenTrending.address == trending.address
			)
			result = await self.session.execute(query)
			existing_trending = result.scalar_one_or_none()
			
			if existing_trending:
				# Update existing record
				existing_trending.symbol = trending.symbol
				existing_trending.name = trending.name
				existing_trending.decimals = trending.decimals
				existing_trending.rank = trending.rank
				existing_trending.price = safe_float(trending.price)
				existing_trending.marketcap = safe_marketcap
				existing_trending.fdv = safe_fdv
				existing_trending.liquidity = safe_liquidity
				existing_trending.volume_24h_usd = safe_volume
				existing_trending.price_24h_change_percent = safe_float(trending.price24hChangePercent)
				existing_trending.volume_24h_change_percent = safe_float(trending.volume24hChangePercent)
				existing_trending.logo_uri = trending.logoURI
				existing_trending.created_at = datetime.utcnow()  # Update timestamp
				
				await self.session.commit()
				await self.session.refresh(existing_trending)
				
				logger.debug(f"Updated trending token: {trending.symbol} ({trending.address})")
				return existing_trending
			else:
				# Insert new record
				db_trending = BirdeyeTokenTrending(
					address=trending.address,
					symbol=trending.symbol,
					name=trending.name,
					decimals=trending.decimals,
					rank=trending.rank,
					price=safe_float(trending.price),
					marketcap=safe_marketcap,
					fdv=safe_fdv,
					liquidity=safe_liquidity,
					volume_24h_usd=safe_volume,
					price_24h_change_percent=safe_float(trending.price24hChangePercent),
					volume_24h_change_percent=safe_float(trending.volume24hChangePercent),
					logo_uri=trending.logoURI,
					data_source="birdeye",
					created_at=datetime.utcnow()
				)
				
				self.session.add(db_trending)
				await self.session.commit()
				await self.session.refresh(db_trending)
				
				logger.debug(f"Inserted new trending token: {trending.symbol} ({trending.address})")
				return db_trending
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving or updating trending token {trending.address}: {str(e)}")
			raise
	
	async def save_or_update_token_trending_batch(
		self,
		trending_tokens: List[TokenTrendingItem]
	) -> int:
		"""
		Save or update multiple trending tokens in batch.
		Each token is checked by address and updated if exists or inserted if not.
		
		Args:
			trending_tokens: List of TokenTrendingItem objects
			
		Returns:
			int: Number of successfully saved/updated tokens
		"""
		saved_count = 0
		for trending in trending_tokens:
			try:
				await self.save_or_update_token_trending(trending)
				saved_count += 1
			except Exception as e:
				logger.warning(f"Failed to save/update trending token {trending.address}: {str(e)}")
				continue
		
		logger.info(f"Saved/Updated {saved_count}/{len(trending_tokens)} trending tokens")
		return saved_count

