"""add detailed tables for all API endpoints

Revision ID: 0002_add_detailed_tables
Revises: 0001_initial
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "0002_add_detailed_tables"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
	"""Create detailed tables for all API endpoints."""
	
	# Dexscreener Token Boosts
	op.create_table(
		"dexscreener_token_boosts",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("url", sa.String(255), nullable=True, comment="DexScreener 的详情页链接"),
		sa.Column("chainId", sa.String(25), nullable=True, comment="链名"),
		sa.Column("tokenAddress", sa.String(255), nullable=True, comment="代币合约地址"),
		sa.Column("description", sa.String(255), nullable=True, comment="项目简介"),
		sa.Column("icon", sa.String(255), nullable=True, comment="代币的 Logo 图标"),
		sa.Column("header", sa.String(255), nullable=True, comment="详情页顶部的横幅大图 (Banner)"),
		sa.Column("openGraph", sa.String(255), nullable=True, comment="社交分享预览图 (你在推特发链接时显示的那个大卡片图)"),
		sa.Column("links", sa.String(1024), nullable=True, comment="json, 社交链接列表"),
		sa.Column("totalAmount", sa.BigInteger(), nullable=True, comment="Boost 总数 (付费推广量)"),
		sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
	)
	op.create_index("ix_dexscreener_token_boosts_chainId", "dexscreener_token_boosts", ["chainId"])
	op.create_index("ix_dexscreener_token_boosts_tokenAddress", "dexscreener_token_boosts", ["tokenAddress"])
	op.create_index("ix_dexscreener_token_boosts_created_at", "dexscreener_token_boosts", ["created_at"])
	op.create_index("idx_chainId_tokenAddress", "dexscreener_token_boosts", ["chainId", "tokenAddress"])
	op.create_index("idx_tokenAddress_created", "dexscreener_token_boosts", ["tokenAddress", "created_at"])
	
	# Birdeye Token Transactions
	op.create_table(
		"birdeye_token_transactions",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("quote", sa.String(1024), nullable=True, comment="计价货币，json字符串"),
		sa.Column("base", sa.String(1024), nullable=True, comment="目标代币，json字符串"),
		sa.Column("basePrice", sa.Float(), nullable=True, comment="目标币 (Poppy) 的单价 (USD)"),
		sa.Column("quotePrice", sa.Float(), nullable=True, comment="计价币 (SOL) 的单价 (USD)"),
		sa.Column("pricePair", sa.Float(), nullable=True, comment="兑换比率,举例：1 个 SOL 可以买 36,144,566 个 Poppy"),
		sa.Column("tokenPrice", sa.Float(), nullable=True, comment="这里通常指 Quote Token 的价格，举例：SOL"),
		sa.Column("txHash", sa.String(255), nullable=True, comment="交易哈希。Solscan 浏览器上通过这个字符串查到这笔交易的"),
		sa.Column("source", sa.String(255), nullable=True, comment="交易来源。这笔交易发生在 Pump.fun 平台上"),
		sa.Column("blockUnixTime", sa.BigInteger(), nullable=True, comment="交易时间戳（秒级）"),
		sa.Column("txType", sa.String(25), nullable=True, comment="swap 交易	buy / sell	直接涨跌	正常市场波动"),
		sa.Column("owner", sa.String(255), nullable=True, comment="交易买家的钱包地址"),
		sa.Column("side", sa.String(25), nullable=True, comment="方向: buy,sell"),
		sa.Column("poolId", sa.String(255), nullable=True, comment="流动性池地址。交易是在这个池子里完成的"),
		sa.Column("from", sa.String(1024), nullable=True, comment="从哪个币"),
		sa.Column("to", sa.String(1024), nullable=True, comment="交易到哪个币"),
		sa.Column("block_time", sa.DateTime(), nullable=True, comment="blockUnixTime 时间格式化"),
	)
	op.create_index("idx_txHash", "birdeye_token_transactions", ["txHash"])
	op.create_index("idx_owner", "birdeye_token_transactions", ["owner"])
	op.create_index("idx_blockUnixTime", "birdeye_token_transactions", ["blockUnixTime"])
	
	# Birdeye Top Traders
	op.create_table(
		"birdeye_top_traders",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("tokenAddress", sa.String(255), nullable=True, comment="币的地址"),
		sa.Column("owner", sa.String(255), nullable=True, comment="交易买家的钱包地址"),
		sa.Column("tags", sa.String(25), nullable=True, comment='标签；["bot"] (机器人), ["sniper"] (狙击手), ["insider"] (内部人士)'),
		sa.Column("type", sa.String(25), nullable=True, comment="统计时间窗口"),
		sa.Column("volume", sa.Float(), nullable=True, comment="总交易额;USD (美元)"),
		sa.Column("volumeBuy", sa.Float(), nullable=True, comment="买入总额"),
		sa.Column("volumeSell", sa.Float(), nullable=True, comment="卖出总额"),
		sa.Column("trade", sa.Integer(), nullable=True, comment="总交易笔数 (买 + 卖)"),
		sa.Column("tradeBuy", sa.Integer(), nullable=True, comment="买入次数"),
		sa.Column("tradeSell", sa.Integer(), nullable=True, comment="卖出次数"),
	)
	op.create_index("ix_birdeye_top_traders_tokenAddress", "birdeye_top_traders", ["tokenAddress"])
	op.create_index("ix_birdeye_top_traders_owner", "birdeye_top_traders", ["owner"])
	op.create_index("idx_tokenAddress_owner", "birdeye_top_traders", ["tokenAddress", "owner"])
	op.create_index("idx_tokenAddress_volume", "birdeye_top_traders", ["tokenAddress", "volume"])
	
	# Birdeye Wallet Transactions
	op.create_table(
		"birdeye_wallet_transactions",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="主键ID"),
		sa.Column("tx_hash", sa.String(128), nullable=False, comment="交易哈希 (txHash), 唯一索引"),
		sa.Column("block_number", sa.BigInteger(), nullable=True, comment="区块高度 (blockNumber)"),
		sa.Column("block_time", sa.DateTime(), nullable=True, comment="交易时间 (blockTime ISO格式转换)"),
		sa.Column("status", sa.Boolean(), default=True, comment="交易状态 (status): 1=成功, 0=失败"),
		sa.Column("from", sa.String(255), nullable=False, comment="发起交易的钱包地址 (from)"),
		sa.Column("to", sa.String(255), nullable=True, comment="交互目标地址 (to)"),
		sa.Column("fee", sa.BigInteger(), nullable=True, comment="交易手续费 (fee), 单位: Lamports"),
		sa.Column("main_action", sa.String(50), nullable=True, comment="主要动作类型 (mainAction)"),
		sa.Column("balance_change", sa.String(2048), nullable=True, comment="余额变动数组 (balanceChange)，json字符串"),
		sa.Column("contract_label", sa.String(2048), nullable=True, comment="合约标签信息 (contractLabel)，json字符串"),
		sa.Column("token_transfers", sa.String(2048), nullable=True, comment="代币流转明细 (tokenTransfers)，json字符串"),
		sa.Column("create_time", sa.DateTime(), nullable=False, comment="数据入库时间"),
		sa.Column("update_time", sa.DateTime(), nullable=False, comment="最后更新时间"),
	)
	op.create_index("uk_tx_hash", "birdeye_wallet_transactions", ["tx_hash"], unique=True)
	op.create_index("idx_from", "birdeye_wallet_transactions", ["from"])
	op.create_index("idx_block_time", "birdeye_wallet_transactions", ["block_time"])
	op.create_index("idx_block_number", "birdeye_wallet_transactions", ["block_number"])
	
	# Birdeye Wallet Tokens
	op.create_table(
		"birdeye_wallet_tokens",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("wallet_address", sa.String(128), nullable=False, comment="Wallet address"),
		sa.Column("token_address", sa.String(128), nullable=False, comment="Token address"),
		sa.Column("symbol", sa.String(32), nullable=True),
		sa.Column("name", sa.String(128), nullable=True),
		sa.Column("decimals", sa.Integer(), nullable=False),
		sa.Column("balance", sa.String(64), nullable=False),
		sa.Column("ui_amount", sa.Float(), nullable=False),
		sa.Column("price_usd", sa.Float(), nullable=True),
		sa.Column("value_usd", sa.Float(), nullable=True),
		sa.Column("chain_id", sa.String(32), nullable=True),
		sa.Column("logo_uri", sa.String(512), nullable=True),
		sa.Column("snapshot_at", sa.DateTime(), nullable=False, comment="Snapshot timestamp"),
		sa.Column("created_at", sa.DateTime(), nullable=False),
	)
	op.create_index("ix_birdeye_wallet_tokens_wallet_address", "birdeye_wallet_tokens", ["wallet_address"])
	op.create_index("ix_birdeye_wallet_tokens_token_address", "birdeye_wallet_tokens", ["token_address"])
	op.create_index("ix_birdeye_wallet_tokens_snapshot_at", "birdeye_wallet_tokens", ["snapshot_at"])
	op.create_index("idx_wallet_token_snapshot", "birdeye_wallet_tokens", ["wallet_address", "token_address", "snapshot_at"])
	op.create_index("idx_wallet_value", "birdeye_wallet_tokens", ["wallet_address", "value_usd"])
	
	# Birdeye New Listings
	op.create_table(
		"birdeye_new_listings",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="自增主键"),
		sa.Column("address", sa.String(255), nullable=False, comment="代币合约地址 (address)"),
		sa.Column("symbol", sa.String(32), nullable=True, comment="代币符号 (symbol)"),
		sa.Column("name", sa.String(255), nullable=True, comment="代币名称 (name), 支持Emoji"),
		sa.Column("decimals", sa.Integer(), nullable=True, comment="精度 (decimals)"),
		sa.Column("source", sa.String(64), nullable=True, comment="上线来源/DEX (source), 如 meteora, raydium"),
		sa.Column("liquidity", sa.Float(), nullable=True, comment="初始流动性USD (liquidity)"),
		sa.Column("liquidity_added_at", sa.DateTime(), nullable=True, comment="添加流动性时间 (liquidityAddedAt)"),
		sa.Column("logo_uri", sa.String(512), nullable=True, comment="Logo图片链接 (logoURI)"),
		sa.Column("create_time", sa.DateTime(), nullable=False, comment="数据抓取入库时间"),
		sa.Column("update_time", sa.DateTime(), nullable=False, comment="最后更新时间"),
	)
	op.create_index("uk_address", "birdeye_new_listings", ["address"], unique=True)
	op.create_index("idx_liquidity_time", "birdeye_new_listings", ["liquidity_added_at"])
	op.create_index("idx_source", "birdeye_new_listings", ["source"])
	
	# Birdeye Token Security
	op.create_table(
		"birdeye_token_security",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, comment="自增主键"),
		sa.Column("token_address", sa.String(255), nullable=False, comment="代币合约地址 (输入参数)"),
		sa.Column("creator_address", sa.String(255), nullable=True, comment="创建者地址 (creatorAddress)"),
		sa.Column("creator_owner_address", sa.String(255), nullable=True, comment="创建者所属Owner (creatorOwnerAddress)"),
		sa.Column("owner_address", sa.String(255), nullable=True, comment="当前所有者地址 (ownerAddress)"),
		sa.Column("owner_of_owner_address", sa.String(255), nullable=True, comment="所有者的所有者 (ownerOfOwnerAddress)"),
		sa.Column("creation_tx", sa.String(128), nullable=True, comment="创建代币的交易哈希 (creationTx)"),
		sa.Column("creation_time", sa.BigInteger(), nullable=True, comment="创建时间戳 (creationTime)"),
		sa.Column("creation_slot", sa.BigInteger(), nullable=True, comment="创建时的Slot高度 (creationSlot)"),
		sa.Column("mint_tx", sa.String(128), nullable=True, comment="铸币交易哈希 (mintTx)"),
		sa.Column("mint_time", sa.BigInteger(), nullable=True, comment="铸币时间戳 (mintTime)"),
		sa.Column("mint_slot", sa.BigInteger(), nullable=True, comment="铸币Slot高度 (mintSlot)"),
		sa.Column("creator_balance", sa.Float(), nullable=True, comment="创建者持仓余额 (creatorBalance)"),
		sa.Column("creator_percentage", sa.Float(), nullable=True, comment="创建者持仓占比 (creatorPercentage)"),
		sa.Column("owner_balance", sa.Float(), nullable=True, comment="所有者持仓余额 (ownerBalance)"),
		sa.Column("owner_percentage", sa.Float(), nullable=True, comment="所有者持仓占比 (ownerPercentage)"),
		sa.Column("total_supply", sa.Float(), nullable=True, comment="总供应量 (totalSupply)"),
		sa.Column("metaplex_update_authority", sa.String(255), nullable=True, comment="元数据更新权限地址 (metaplexUpdateAuthority)"),
		sa.Column("metaplex_owner_update_authority", sa.String(255), nullable=True, comment="元数据更新权限的所有者 (metaplexOwnerUpdateAuthority)"),
		sa.Column("metaplex_update_authority_balance", sa.Float(), nullable=True, comment="更新权限地址的余额"),
		sa.Column("metaplex_update_authority_percent", sa.Float(), nullable=True, comment="更新权限地址的持仓占比"),
		sa.Column("mutable_metadata", sa.Boolean(), default=False, comment="元数据是否可更改 (mutableMetadata): 1=是, 0=否"),
		sa.Column("top10_holder_balance", sa.Float(), nullable=True, comment="前10持仓总余额 (top10HolderBalance)"),
		sa.Column("top10_holder_percent", sa.Float(), nullable=True, comment="前10持仓占比 (top10HolderPercent)"),
		sa.Column("top10_user_balance", sa.Float(), nullable=True, comment="前10普通用户(非合约)余额 (top10UserBalance)"),
		sa.Column("top10_user_percent", sa.Float(), nullable=True, comment="前10普通用户占比 (top10UserPercent)"),
		sa.Column("pre_market_holder", sa.String(2048), nullable=True, comment="盘前持仓列表 (preMarketHolder)"),
		sa.Column("lock_info", sa.String(2048), nullable=True, comment="锁仓信息 (lockInfo)"),
		sa.Column("transfer_fee_data", sa.String(2048), nullable=True, comment="转账费详情 (transferFeeData)"),
		sa.Column("is_true_token", sa.Boolean(), nullable=True, comment="是否为真币 (isTrueToken)"),
		sa.Column("is_token_2022", sa.Boolean(), default=False, comment="是否为Token2022标准 (isToken2022)"),
		sa.Column("freezeable", sa.Boolean(), nullable=True, comment="是否可冻结 (freezeable)"),
		sa.Column("freeze_authority", sa.String(255), nullable=True, comment="冻结权限地址 (freezeAuthority)"),
		sa.Column("transfer_fee_enable", sa.Boolean(), nullable=True, comment="是否开启转账费 (transferFeeEnable)"),
		sa.Column("non_transferable", sa.Boolean(), nullable=True, comment="是否不可转账 (nonTransferable)"),
		sa.Column("create_time", sa.DateTime(), nullable=False, comment="入库时间"),
		sa.Column("update_time", sa.DateTime(), nullable=False, comment="最后更新时间"),
	)
	op.create_index("uk_token_address", "birdeye_token_security", ["token_address"], unique=True)
	op.create_index("idx_creator", "birdeye_token_security", ["creator_address"])
	
	# Birdeye Token Overview
	op.create_table(
		"birdeye_token_overview",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("token_address", sa.String(128), nullable=False, comment="Token address"),
		sa.Column("price", sa.Float(), nullable=True),
		sa.Column("market_cap", sa.Float(), nullable=True),
		sa.Column("fdv", sa.Float(), nullable=True),
		sa.Column("liquidity", sa.Float(), nullable=True),
		sa.Column("total_supply", sa.Float(), nullable=True),
		sa.Column("circulating_supply", sa.Float(), nullable=True),
		sa.Column("holder", sa.Integer(), nullable=True),
		sa.Column("number_markets", sa.Integer(), nullable=True),
		sa.Column("price_change_24h_percent", sa.Float(), nullable=True),
		sa.Column("v24h", sa.Float(), nullable=True),
		sa.Column("v24h_usd", sa.Float(), nullable=True),
		sa.Column("trade_24h", sa.Integer(), nullable=True),
		sa.Column("buy_24h", sa.Integer(), nullable=True),
		sa.Column("sell_24h", sa.Integer(), nullable=True),
		sa.Column("unique_wallet_24h", sa.Integer(), nullable=True),
		sa.Column("price_change_1h_percent", sa.Float(), nullable=True),
		sa.Column("v1h", sa.Float(), nullable=True),
		sa.Column("v1h_usd", sa.Float(), nullable=True),
		sa.Column("v30m", sa.Float(), nullable=True),
		sa.Column("v30m_usd", sa.Float(), nullable=True),
		sa.Column("last_trade_unix_time", sa.BigInteger(), nullable=True),
		sa.Column("last_trade_human_time", sa.DateTime(), nullable=True),
		sa.Column("created_at", sa.DateTime(), nullable=False),
	)
	op.create_index("ix_birdeye_token_overview_token_address", "birdeye_token_overview", ["token_address"])
	op.create_index("ix_birdeye_token_overview_market_cap", "birdeye_token_overview", ["market_cap"])
	op.create_index("ix_birdeye_token_overview_liquidity", "birdeye_token_overview", ["liquidity"])
	op.create_index("ix_birdeye_token_overview_created_at", "birdeye_token_overview", ["created_at"])
	op.create_index("idx_token_overview_created", "birdeye_token_overview", ["token_address", "created_at"])
	op.create_index("idx_market_cap_liquidity", "birdeye_token_overview", ["market_cap", "liquidity"])


def downgrade():
	"""Drop all detailed tables."""
	op.drop_table("birdeye_token_overview")
	op.drop_table("birdeye_token_security")
	op.drop_table("birdeye_new_listings")
	op.drop_table("birdeye_wallet_tokens")
	op.drop_table("birdeye_wallet_transactions")
	op.drop_table("birdeye_top_traders")
	op.drop_table("birdeye_token_transactions")
	op.drop_table("dexscreener_token_boosts")

