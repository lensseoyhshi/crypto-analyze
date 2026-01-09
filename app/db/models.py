"""Database models."""
import json
from typing import List, Dict, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Index, BigInteger, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class RawApiResponse(Base):
	"""Model for storing raw API responses from external services."""
	
	__tablename__ = "raw_api_responses"

	id = Column(Integer, primary_key=True, index=True, autoincrement=True)
	source = Column(String(64), nullable=False, index=True, comment="API source (e.g., 'dexscreener', 'birdeye')")
	endpoint = Column(String(256), nullable=False, comment="API endpoint path")
	response_json = Column(Text, nullable=False, comment="Raw JSON response as text")
	status_code = Column(Integer, nullable=False, default=200, comment="HTTP status code")
	error_message = Column(Text, nullable=True, comment="Error message if request failed")
	created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="Timestamp when response was saved")
	
	__table_args__ = (
		Index('idx_source_endpoint_created', 'source', 'endpoint', 'created_at'),
	)


# ============================================================================
# Dexscreener Models
# ============================================================================

class DexscreenerTokenBoost(Base):
	"""Dexscreener 热度排名高的币"""
	
	__tablename__ = "dexscreener_token_boosts"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True)
	url = Column(String(255), nullable=True, comment="DexScreener 的详情页链接")
	chainId = Column(String(25), nullable=True, index=True, comment="链名")
	tokenAddress = Column(String(255), nullable=True, index=True, comment="代币合约地址")
	description = Column(String(255), nullable=True, comment="项目简介")
	icon = Column(String(255), nullable=True, comment="代币的 Logo 图标")
	header = Column(String(255), nullable=True, comment="详情页顶部的横幅大图 (Banner)")
	openGraph = Column(String(255), nullable=True, comment="社交分享预览图 (你在推特发链接时显示的那个大卡片图)")
	links = Column(String(1024), nullable=True, comment="json, 社交链接列表")
	totalAmount = Column(BigInteger, nullable=True, comment="Boost 总数 (付费推广量)")
	created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间")
	
	__table_args__ = (
		Index('idx_chainId_tokenAddress', 'chainId', 'tokenAddress'),
		Index('idx_tokenAddress_created', 'tokenAddress', 'created_at'),
	)
	
	@property
	def links_list(self) -> Optional[List[Dict[str, str]]]:
		"""解析 links JSON 字符串为列表
		
		Returns:
			List of dicts with 'type' and 'url' keys, or None if links is empty
			Example: [{"type": "twitter", "url": "https://x.com/..."}]
		"""
		if not self.links:
			return None
		try:
			return json.loads(self.links)
		except (json.JSONDecodeError, TypeError):
			return None
	
	def get_link_by_type(self, link_type: str) -> Optional[str]:
		"""根据类型获取链接URL
		
		Args:
			link_type: 链接类型 (twitter, telegram, website, etc)
			
		Returns:
			URL string or None if not found
		"""
		links = self.links_list
		if not links:
			return None
		
		for link in links:
			if link.get('type') == link_type:
				return link.get('url')
		return None
	
	@property
	def twitter_link(self) -> Optional[str]:
		"""获取 Twitter 链接"""
		return self.get_link_by_type('twitter')
	
	@property
	def telegram_link(self) -> Optional[str]:
		"""获取 Telegram 链接"""
		return self.get_link_by_type('telegram')
	
	@property
	def website_link(self) -> Optional[str]:
		"""获取 Website 链接"""
		return self.get_link_by_type('website')


# ============================================================================
# Birdeye Models
# ============================================================================

class BirdeyeTokenTransaction(Base):
	"""获取指定代币在特定时间段内的交易列表"""
	
	__tablename__ = "birdeye_token_transactions"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True)
	quote = Column(String(1024), nullable=True, comment="计价货币，json字符串")
	base = Column(String(1024), nullable=True, comment="目标代币，json字符串")
	basePrice = Column(Float, nullable=True, comment="目标币 (Poppy) 的单价 (USD)")
	quotePrice = Column(Float, nullable=True, comment="计价币 (SOL) 的单价 (USD)")
	pricePair = Column(Float, nullable=True, comment="兑换比率,举例：1 个 SOL 可以买 36,144,566 个 Poppy")
	tokenPrice = Column(Float, nullable=True, comment="这里通常指 Quote Token 的价格，举例：SOL")
	txHash = Column(String(255), nullable=True, index=True, comment="交易哈希。Solscan 浏览器上通过这个字符串查到这笔交易的")
	source = Column(String(255), nullable=True, comment="交易来源。这笔交易发生在 Pump.fun 平台上")
	blockUnixTime = Column(BigInteger, nullable=True, index=True, comment="交易时间戳（秒级）")
	txType = Column(String(25), nullable=True, comment="swap 交易	buy / sell	直接涨跌	正常市场波动")
	owner = Column(String(255), nullable=True, index=True, comment="交易买家的钱包地址")
	side = Column(String(25), nullable=True, comment="方向: buy,sell")
	poolId = Column(String(255), nullable=True, comment="流动性池地址。交易是在这个池子里完成的")
	from_data = Column('from', String(1024), nullable=True, comment="从哪个币")
	to_data = Column('to', String(1024), nullable=True, comment="交易到哪个币")
	block_time = Column(DateTime, nullable=True, comment="blockUnixTime 时间格式化")
	
	__table_args__ = (
		Index('idx_txHash', 'txHash'),
		Index('idx_owner', 'owner'),
		Index('idx_blockUnixTime', 'blockUnixTime'),
	)
	
	@property
	def quote_info(self) -> Optional[Dict]:
		"""解析 quote JSON 字符串为字典
		
		Returns:
			Dict with token info (symbol, decimals, address, amount, uiAmount, price, etc)
			Example: {
				"symbol": "SOL",
				"decimals": 9,
				"address": "So11111111111111111111111111111111111111112",
				"amount": "4676700",
				"uiAmount": 0.0046767,
				"price": 139.48612659068803,
				...
			}
		"""
		if not self.quote:
			return None
		try:
			return json.loads(self.quote)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def base_info(self) -> Optional[Dict]:
		"""解析 base JSON 字符串为字典
		
		Returns:
			Dict with token info (symbol, decimals, address, amount, uiAmount, price, etc)
		"""
		if not self.base:
			return None
		try:
			return json.loads(self.base)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def from_info(self) -> Optional[Dict]:
		"""解析 from JSON 字符串为字典
		
		Returns:
			Dict with token info for the source token
		"""
		if not self.from_data:
			return None
		try:
			return json.loads(self.from_data)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def to_info(self) -> Optional[Dict]:
		"""解析 to JSON 字符串为字典
		
		Returns:
			Dict with token info for the destination token
		"""
		if not self.to_data:
			return None
		try:
			return json.loads(self.to_data)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def quote_symbol(self) -> Optional[str]:
		"""获取计价币符号"""
		info = self.quote_info
		return info.get('symbol') if info else None
	
	@property
	def base_symbol(self) -> Optional[str]:
		"""获取目标币符号"""
		info = self.base_info
		return info.get('symbol') if info else None
	
	@property
	def quote_ui_amount(self) -> Optional[float]:
		"""获取计价币UI数量"""
		info = self.quote_info
		return info.get('uiAmount') if info else None
	
	@property
	def base_ui_amount(self) -> Optional[float]:
		"""获取目标币UI数量"""
		info = self.base_info
		return info.get('uiAmount') if info else None


class BirdeyeTopTrader(Base):
	"""某个币赚钱最多的钱包地址"""
	
	__tablename__ = "birdeye_top_traders"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True)
	tokenAddress = Column(String(255), nullable=True, index=True, comment="币的地址")
	owner = Column(String(255), nullable=True, index=True, comment="交易买家的钱包地址")
	tags = Column(String(25), nullable=True, comment='标签；["bot"] (机器人), ["sniper"] (狙击手), ["insider"] (内部人士)')
	type = Column(String(25), nullable=True, comment="统计时间窗口")
	volume = Column(Float, nullable=True, comment="总交易额;USD (美元)")
	volumeBuy = Column(Float, nullable=True, comment="买入总额")
	volumeSell = Column(Float, nullable=True, comment="卖出总额")
	trade = Column(Integer, nullable=True, comment="总交易笔数 (买 + 卖)")
	tradeBuy = Column(Integer, nullable=True, comment="买入次数")
	tradeSell = Column(Integer, nullable=True, comment="卖出次数")
	
	__table_args__ = (
		Index('idx_tokenAddress_owner', 'tokenAddress', 'owner'),
		Index('idx_tokenAddress_volume', 'tokenAddress', 'volume'),
	)
	
	@property
	def tags_list(self) -> Optional[List[str]]:
		"""解析 tags 字符串为列表
		
		Returns:
			List of tags like ["bot", "sniper", "insider"] or None
		"""
		if not self.tags:
			return None
		try:
			return json.loads(self.tags)
		except (json.JSONDecodeError, TypeError):
			# 如果不是 JSON 格式，尝试按逗号分割
			return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
	
	@property
	def is_bot(self) -> bool:
		"""是否为机器人"""
		tags = self.tags_list
		return tags and 'bot' in tags if tags else False
	
	@property
	def is_sniper(self) -> bool:
		"""是否为狙击手"""
		tags = self.tags_list
		return tags and 'sniper' in tags if tags else False
	
	@property
	def is_insider(self) -> bool:
		"""是否为内部人士"""
		tags = self.tags_list
		return tags and 'insider' in tags if tags else False
	
	@property
	def profit_ratio(self) -> Optional[float]:
		"""计算盈利比率 (卖出额 / 买入额)"""
		if self.volumeBuy and self.volumeBuy > 0:
			return self.volumeSell / self.volumeBuy
		return None
	
	@property
	def net_volume(self) -> Optional[float]:
		"""计算净交易额 (卖出 - 买入)"""
		if self.volumeBuy and self.volumeSell:
			return self.volumeSell - self.volumeBuy
		return None


class BirdeyeWalletTransaction(Base):
	"""Birdeye钱包历史交易记录表"""
	
	__tablename__ = "birdeye_wallet_transactions"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
	tx_hash = Column(String(128), nullable=False, unique=True, index=True, comment="交易哈希 (txHash), 唯一索引")
	block_number = Column(BigInteger, nullable=True, index=True, comment="区块高度 (blockNumber)")
	block_time = Column(DateTime, nullable=True, index=True, comment="交易时间 (blockTime ISO格式转换)")
	status = Column(Boolean, default=True, comment="交易状态 (status): 1=成功, 0=失败")
	from_address = Column('from', String(255), nullable=False, index=True, comment="发起交易的钱包地址 (from)")
	to_address = Column('to', String(255), nullable=True, comment="交互目标地址 (to)")
	fee = Column(BigInteger, nullable=True, comment="交易手续费 (fee), 单位: Lamports")
	main_action = Column(String(50), nullable=True, comment="主要动作类型 (mainAction)")
	balance_change = Column(String(2048), nullable=True, comment="余额变动数组 (balanceChange)，json字符串")
	contract_label = Column(String(2048), nullable=True, comment="合约标签信息 (contractLabel)，json字符串")
	token_transfers = Column(String(2048), nullable=True, comment="代币流转明细 (tokenTransfers)，json字符串")
	create_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="数据入库时间")
	update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="最后更新时间")
	
	__table_args__ = (
		Index('uk_tx_hash', 'tx_hash', unique=True),
		Index('idx_from', 'from'),
		Index('idx_block_time', 'block_time'),
		Index('idx_block_number', 'block_number'),
	)
	
	@property
	def balance_change_list(self) -> Optional[List[Dict]]:
		"""解析 balance_change JSON 字符串为列表
		
		Returns:
			List of balance change objects with amount, symbol, name, decimals, address, etc.
			Example: [
				{
					"amount": -502601304,
					"symbol": "SOL",
					"name": "Wrapped SOL",
					"decimals": 9,
					"address": "So11111111111111111111111111111111111111112",
					...
				}
			]
		"""
		if not self.balance_change:
			return None
		try:
			return json.loads(self.balance_change)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def contract_label_info(self) -> Optional[Dict]:
		"""解析 contract_label JSON 字符串为字典
		
		Returns:
			Dict with contract info (address, name, metadata)
			Example: {
				"address": "11111111111111111111111111111111",
				"name": "System Program",
				"metadata": {"icon": ""}
			}
		"""
		if not self.contract_label:
			return None
		try:
			return json.loads(self.contract_label)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def token_transfers_list(self) -> Optional[List[Dict]]:
		"""解析 token_transfers JSON 字符串为列表
		
		Returns:
			List of token transfer objects
			Example: [
				{
					"fromTokenAccount": "...",
					"toTokenAccount": "...",
					"fromUserAccount": "...",
					"toUserAccount": "...",
					"tokenAmount": 0.0004,
					"mint": "So11111111...",
					"transferNative": true,
					...
				}
			]
		"""
		if not self.token_transfers:
			return None
		try:
			return json.loads(self.token_transfers)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def contract_name(self) -> Optional[str]:
		"""获取合约名称"""
		info = self.contract_label_info
		return info.get('name') if info else None
	
	@property
	def contract_address(self) -> Optional[str]:
		"""获取合约地址"""
		info = self.contract_label_info
		return info.get('address') if info else None
	
	@property
	def sol_balance_change(self) -> Optional[float]:
		"""获取 SOL 余额变化（UI金额）"""
		changes = self.balance_change_list
		if not changes:
			return None
		
		for change in changes:
			if change.get('symbol') == 'SOL':
				amount = change.get('amount', 0)
				decimals = change.get('decimals', 9)
				return amount / (10 ** decimals)
		return None
	
	@property
	def total_token_transfers_count(self) -> int:
		"""获取代币转账总数"""
		transfers = self.token_transfers_list
		return len(transfers) if transfers else 0


class BirdeyeWalletToken(Base):
	"""Wallet token holdings (portfolio)."""
	
	__tablename__ = "birdeye_wallet_tokens"
	
	id = Column(Integer, primary_key=True, autoincrement=True)
	wallet_address = Column(String(128), nullable=False, index=True, comment="Wallet address")
	token_address = Column(String(128), nullable=False, index=True, comment="Token address")
	
	symbol = Column(String(32), nullable=True, comment="Token symbol")
	name = Column(String(128), nullable=True, comment="Token name")
	decimals = Column(Integer, nullable=False, comment="Token decimals")
	
	balance = Column(String(64), nullable=False, comment="Raw balance")
	ui_amount = Column(Float, nullable=False, comment="UI amount")
	price_usd = Column(Float, nullable=True, comment="Price in USD")
	value_usd = Column(Float, nullable=True, comment="Total value in USD")
	
	chain_id = Column(String(32), nullable=True, comment="Chain ID")
	logo_uri = Column(String(512), nullable=True, comment="Logo URL")
	
	snapshot_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="Snapshot timestamp")
	created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
	
	__table_args__ = (
		Index('idx_wallet_token_snapshot', 'wallet_address', 'token_address', 'snapshot_at'),
		Index('idx_wallet_value', 'wallet_address', 'value_usd'),
	)


class BirdeyeNewListing(Base):
	"""Birdeye新币上线监控表"""
	
	__tablename__ = "birdeye_new_listings"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
	address = Column(String(255), nullable=False, unique=True, comment="代币合约地址 (address)")
	symbol = Column(String(32), nullable=True, comment="代币符号 (symbol)")
	name = Column(String(255), nullable=True, comment="代币名称 (name), 支持Emoji")
	decimals = Column(Integer, nullable=True, comment="精度 (decimals)")
	source = Column(String(64), nullable=True, index=True, comment="上线来源/DEX (source), 如 meteora, raydium")
	liquidity = Column(Float, nullable=True, comment="初始流动性USD (liquidity)")
	liquidity_added_at = Column(DateTime, nullable=True, index=True, comment="添加流动性时间 (liquidityAddedAt)")
	logo_uri = Column(String(512), nullable=True, comment="Logo图片链接 (logoURI)")
	create_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="数据抓取入库时间")
	update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="最后更新时间")
	
	__table_args__ = (
		Index('uk_address', 'address', unique=True),
		Index('idx_liquidity_time', 'liquidity_added_at'),
		Index('idx_source', 'source'),
	)


class BirdeyeTokenSecurity(Base):
	"""Birdeye代币安全检测报告"""
	
	__tablename__ = "birdeye_token_security"
	
	id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
	token_address = Column(String(255), nullable=False, unique=True, comment="代币合约地址 (输入参数)")
	creator_address = Column(String(255), nullable=True, index=True, comment="创建者地址 (creatorAddress)")
	creator_owner_address = Column(String(255), nullable=True, comment="创建者所属Owner (creatorOwnerAddress)")
	owner_address = Column(String(255), nullable=True, comment="当前所有者地址 (ownerAddress)")
	owner_of_owner_address = Column(String(255), nullable=True, comment="所有者的所有者 (ownerOfOwnerAddress)")
	
	creation_tx = Column(String(128), nullable=True, comment="创建代币的交易哈希 (creationTx)")
	creation_time = Column(BigInteger, nullable=True, comment="创建时间戳 (creationTime)")
	creation_slot = Column(BigInteger, nullable=True, comment="创建时的Slot高度 (creationSlot)")
	mint_tx = Column(String(128), nullable=True, comment="铸币交易哈希 (mintTx)")
	mint_time = Column(BigInteger, nullable=True, comment="铸币时间戳 (mintTime)")
	mint_slot = Column(BigInteger, nullable=True, comment="铸币Slot高度 (mintSlot)")
	
	creator_balance = Column(Float, nullable=True, comment="创建者持仓余额 (creatorBalance)")
	creator_percentage = Column(Float, nullable=True, comment="创建者持仓占比 (creatorPercentage)")
	owner_balance = Column(Float, nullable=True, comment="所有者持仓余额 (ownerBalance)")
	owner_percentage = Column(Float, nullable=True, comment="所有者持仓占比 (ownerPercentage)")
	total_supply = Column(Float, nullable=True, comment="总供应量 (totalSupply)")
	
	metaplex_update_authority = Column(String(255), nullable=True, comment="元数据更新权限地址 (metaplexUpdateAuthority)")
	metaplex_owner_update_authority = Column(String(255), nullable=True, comment="元数据更新权限的所有者 (metaplexOwnerUpdateAuthority)")
	metaplex_update_authority_balance = Column(Float, nullable=True, comment="更新权限地址的余额")
	metaplex_update_authority_percent = Column(Float, nullable=True, comment="更新权限地址的持仓占比")
	mutable_metadata = Column(Boolean, default=False, comment="元数据是否可更改 (mutableMetadata): 1=是, 0=否")
	
	top10_holder_balance = Column(Float, nullable=True, comment="前10持仓总余额 (top10HolderBalance)")
	top10_holder_percent = Column(Float, nullable=True, comment="前10持仓占比 (top10HolderPercent)")
	top10_user_balance = Column(Float, nullable=True, comment="前10普通用户(非合约)余额 (top10UserBalance)")
	top10_user_percent = Column(Float, nullable=True, comment="前10普通用户占比 (top10UserPercent)")
	
	pre_market_holder = Column(String(2048), nullable=True, comment="盘前持仓列表 (preMarketHolder)")
	lock_info = Column(String(2048), nullable=True, comment="锁仓信息 (lockInfo)")
	transfer_fee_data = Column(String(2048), nullable=True, comment="转账费详情 (transferFeeData)")
	
	is_true_token = Column(Boolean, nullable=True, comment="是否为真币 (isTrueToken)")
	is_token_2022 = Column(Boolean, default=False, comment="是否为Token2022标准 (isToken2022)")
	freezeable = Column(Boolean, nullable=True, comment="是否可冻结 (freezeable)")
	freeze_authority = Column(String(255), nullable=True, comment="冻结权限地址 (freezeAuthority)")
	transfer_fee_enable = Column(Boolean, nullable=True, comment="是否开启转账费 (transferFeeEnable)")
	non_transferable = Column(Boolean, nullable=True, comment="是否不可转账 (nonTransferable)")
	
	create_time = Column(DateTime, default=datetime.utcnow, nullable=False, comment="入库时间")
	update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="最后更新时间")
	
	__table_args__ = (
		Index('uk_token_address', 'token_address', unique=True),
		Index('idx_creator', 'creator_address'),
	)
	
	@property
	def pre_market_holder_list(self) -> Optional[List]:
		"""解析 pre_market_holder JSON 字符串为列表
		
		Returns:
			List of pre-market holders or None
		"""
		if not self.pre_market_holder:
			return None
		try:
			return json.loads(self.pre_market_holder)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def lock_info_dict(self) -> Optional[Dict]:
		"""解析 lock_info JSON 字符串为字典
		
		Returns:
			Dict with lock information or None
		"""
		if not self.lock_info:
			return None
		try:
			return json.loads(self.lock_info)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def transfer_fee_data_dict(self) -> Optional[Dict]:
		"""解析 transfer_fee_data JSON 字符串为字典
		
		Returns:
			Dict with transfer fee details or None
		"""
		if not self.transfer_fee_data:
			return None
		try:
			return json.loads(self.transfer_fee_data)
		except (json.JSONDecodeError, TypeError):
			return None
	
	@property
	def is_risky(self) -> bool:
		"""判断代币是否存在风险
		
		风险因素：
		1. 元数据可变 (mutable_metadata)
		2. 可冻结 (freezeable)
		3. 前10持有者占比过高 (>50%)
		4. 不可转账 (non_transferable)
		
		Returns:
			True if risky, False otherwise
		"""
		# 元数据可变
		if self.mutable_metadata:
			return True
		
		# 可冻结
		if self.freezeable:
			return True
		
		# 前10持有者占比过高
		if self.top10_holder_percent and self.top10_holder_percent > 50:
			return True
		
		# 不可转账
		if self.non_transferable:
			return True
		
		return False
	
	@property
	def risk_level(self) -> str:
		"""评估风险等级
		
		Returns:
			'high', 'medium', 'low', or 'unknown'
		"""
		risk_score = 0
		
		# 不可转账 - 极高风险
		if self.non_transferable:
			return 'high'
		
		# 可冻结 - 高风险
		if self.freezeable:
			risk_score += 3
		
		# 元数据可变 - 中风险
		if self.mutable_metadata:
			risk_score += 2
		
		# 前10持有者占比
		if self.top10_holder_percent:
			if self.top10_holder_percent > 80:
				risk_score += 3
			elif self.top10_holder_percent > 50:
				risk_score += 2
			elif self.top10_holder_percent > 30:
				risk_score += 1
		
		# 创建者持仓占比
		if self.creator_percentage:
			if self.creator_percentage > 50:
				risk_score += 2
			elif self.creator_percentage > 20:
				risk_score += 1
		
		if risk_score >= 5:
			return 'high'
		elif risk_score >= 3:
			return 'medium'
		elif risk_score > 0:
			return 'low'
		else:
			return 'safe'


class BirdeyeTokenOverview(Base):
	"""Comprehensive token overview and metrics."""
	
	__tablename__ = "birdeye_token_overview"
	
	id = Column(Integer, primary_key=True, autoincrement=True)
	token_address = Column(String(128), nullable=False, index=True, comment="Token address")
	
	# Basic info
	price = Column(Float, nullable=True, comment="Current price")
	market_cap = Column(Float, nullable=True, index=True, comment="Market cap")
	fdv = Column(Float, nullable=True, comment="Fully diluted valuation")
	liquidity = Column(Float, nullable=True, index=True, comment="Total liquidity")
	
	# Supply and holders
	total_supply = Column(Float, nullable=True)
	circulating_supply = Column(Float, nullable=True)
	holder = Column(Integer, nullable=True, comment="Number of holders")
	number_markets = Column(Integer, nullable=True, comment="Number of markets")
	
	# 24h metrics
	price_change_24h_percent = Column(Float, nullable=True, comment="24h price change %")
	v24h = Column(Float, nullable=True, comment="24h volume")
	v24h_usd = Column(Float, nullable=True, comment="24h volume USD")
	trade_24h = Column(Integer, nullable=True, comment="24h trades")
	buy_24h = Column(Integer, nullable=True)
	sell_24h = Column(Integer, nullable=True)
	unique_wallet_24h = Column(Integer, nullable=True, comment="24h unique wallets")
	
	# 1h metrics
	price_change_1h_percent = Column(Float, nullable=True)
	v1h = Column(Float, nullable=True)
	v1h_usd = Column(Float, nullable=True)
	
	# 30m metrics
	v30m = Column(Float, nullable=True)
	v30m_usd = Column(Float, nullable=True)
	
	last_trade_unix_time = Column(BigInteger, nullable=True, comment="Last trade timestamp")
	last_trade_human_time = Column(DateTime, nullable=True, comment="Last trade time")
	
	created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
	
	__table_args__ = (
		Index('idx_token_overview_created', 'token_address', 'created_at'),
		Index('idx_market_cap_liquidity', 'market_cap', 'liquidity'),
	)


