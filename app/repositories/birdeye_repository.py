"""Repository for Birdeye data."""
import json
import logging
from datetime import datetime
from typing import List, Optional
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
	BirdeyeTokenOverview
)
from ..api.schemas.birdeye import (
	TransactionItem,
	TopTraderItem,
	WalletTransaction,
	WalletTokenItem,
	NewListingItem,
	TokenSecurityData,
	TokenOverviewData
)

logger = logging.getLogger(__name__)


class BirdeyeRepository:
	"""Repository for managing Birdeye data."""
	
	def __init__(self, session: AsyncSession):
		self.session = session
	
	# ========================================================================
	# Token Transactions
	# ========================================================================
	
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
		"""Save token overview information."""
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
				price=overview.price,
				market_cap=overview.marketCap,
				fdv=overview.fdv,
				liquidity=overview.liquidity,
				total_supply=overview.totalSupply,
				circulating_supply=overview.circulatingSupply,
				holder=overview.holder,
				number_markets=overview.numberMarkets,
				price_change_24h_percent=overview.priceChange24hPercent,
				v24h=overview.v24h,
				v24h_usd=overview.v24hUSD,
				trade_24h=overview.trade24h,
				buy_24h=overview.buy24h,
				sell_24h=overview.sell24h,
				unique_wallet_24h=overview.uniqueWallet24h,
				price_change_1h_percent=overview.priceChange1hPercent,
				v1h=overview.v1h,
				v1h_usd=overview.v1hUSD,
				v30m=overview.v30m,
				v30m_usd=overview.v30mUSD,
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

