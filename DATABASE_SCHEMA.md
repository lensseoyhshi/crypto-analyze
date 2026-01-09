# Database Schema Documentation

本文档描述了系统中所有数据库表的结构和用途。

## 概览

系统包含 **9 个数据表**，分为 3 类：

1. **原始数据表** (1个): 存储所有 API 原始响应
2. **Dexscreener 数据表** (1个): 存储 Dexscreener 结构化数据
3. **Birdeye 数据表** (7个): 存储 Birdeye 各类结构化数据

---

## 1. 原始数据表

### `raw_api_responses`

存储所有 API 的原始 JSON 响应，用于审计和调试。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| source | String(64) | API 来源 (dexscreener, birdeye) |
| endpoint | String(256) | API 端点路径 |
| response_json | Text | 原始 JSON 响应 |
| status_code | Integer | HTTP 状态码 |
| error_message | Text | 错误信息(如果有) |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_raw_api_responses_source`: source
- `ix_raw_api_responses_created_at`: created_at
- `idx_source_endpoint_created`: (source, endpoint, created_at)

---

## 2. Dexscreener 数据表

### `dexscreener_token_boosts`

存储 Dexscreener Top Token Boosts 数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| chain_id | String(32) | 区块链 ID (solana, ethereum, etc) |
| token_address | String(128) | 代币合约地址 |
| url | String(512) | Dexscreener 链接 |
| description | Text | 代币描述 |
| icon | String(256) | 图标哈希 |
| header | String(512) | 头图 URL |
| open_graph | String(512) | OpenGraph 图片 URL |
| links | JSON | 社交媒体链接 (JSON数组) |
| total_amount | Integer | Boost 总量 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_dexscreener_token_boosts_chain_id`: chain_id
- `ix_dexscreener_token_boosts_token_address`: token_address
- `idx_chain_token`: (chain_id, token_address)
- `idx_token_created`: (token_address, created_at)

**采集频率:** 每 6 秒

---

## 3. Birdeye 数据表

### 3.1 `birdeye_token_transactions`

存储代币交易历史数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| token_address | String(128) | 代币地址 |
| tx_hash | String(128) | 交易哈希 (唯一) |
| block_unix_time | BigInteger | 区块时间戳 |
| tx_type | String(32) | 交易类型 (swap, etc) |
| source | String(64) | 来源 (pump.fun, etc) |
| owner | String(128) | 交易发起者钱包 |
| side | String(16) | buy 或 sell |
| base_price | Float | 基础代币价格 |
| quote_price | Float | 报价代币价格 |
| token_price | Float | 代币价格 |
| price_pair | Float | 价格对比率 |
| base_symbol | String(32) | 基础代币符号 |
| base_amount | String(64) | 基础代币数量 |
| base_ui_amount | Float | 基础代币UI数量 |
| quote_symbol | String(32) | 报价代币符号 |
| quote_amount | String(64) | 报价代币数量 |
| quote_ui_amount | Float | 报价代币UI数量 |
| pool_id | String(128) | 流动性池 ID |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_token_transactions_token_address`: token_address
- `ix_birdeye_token_transactions_tx_hash`: tx_hash
- `ix_birdeye_token_transactions_owner`: owner
- `idx_token_time`: (token_address, block_unix_time)
- `idx_owner_time`: (owner, block_unix_time)

**采集频率:** 每 120 秒 (2分钟)

---

### 3.2 `birdeye_top_traders`

存储代币最赚钱的交易者数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| token_address | String(128) | 代币地址 |
| owner | String(128) | 交易者钱包地址 |
| time_range | String(16) | 时间范围 (24h, 7d, etc) |
| volume | Float | 总交易量 |
| trade_count | Integer | 总交易次数 |
| trade_buy | Integer | 买入次数 |
| trade_sell | Integer | 卖出次数 |
| volume_buy | Float | 买入量 |
| volume_sell | Float | 卖出量 |
| tags | JSON | 交易者标签 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_top_traders_token_address`: token_address
- `ix_birdeye_top_traders_owner`: owner
- `idx_token_owner_range`: (token_address, owner, time_range)
- `idx_token_volume`: (token_address, volume)

**采集频率:** 每 300 秒 (5分钟)

---

### 3.3 `birdeye_wallet_transactions`

存储钱包交易历史。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| wallet_address | String(128) | 钱包地址 |
| tx_hash | String(128) | 交易哈希 (唯一) |
| block_number | BigInteger | 区块号 |
| block_time | DateTime | 区块时间 |
| status | Boolean | 交易状态 |
| from_address | String(128) | 发送地址 |
| to_address | String(128) | 接收地址 |
| fee | BigInteger | 交易手续费 |
| main_action | String(64) | 主要操作类型 |
| balance_change | JSON | 余额变化 (JSON数组) |
| token_transfers | JSON | 代币转账 (JSON数组) |
| contract_label | JSON | 合约标签信息 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_wallet_transactions_wallet_address`: wallet_address
- `ix_birdeye_wallet_transactions_tx_hash`: tx_hash
- `idx_wallet_time`: (wallet_address, block_time)

**采集频率:** 按需采集 (当前未启用定期采集)

---

### 3.4 `birdeye_wallet_tokens`

存储钱包代币持仓(投资组合)。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| wallet_address | String(128) | 钱包地址 |
| token_address | String(128) | 代币地址 |
| symbol | String(32) | 代币符号 |
| name | String(128) | 代币名称 |
| decimals | Integer | 小数位数 |
| balance | String(64) | 原始余额 |
| ui_amount | Float | UI显示数量 |
| price_usd | Float | USD价格 |
| value_usd | Float | USD总价值 |
| chain_id | String(32) | 链 ID |
| logo_uri | String(512) | Logo URL |
| snapshot_at | DateTime | 快照时间 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_wallet_tokens_wallet_address`: wallet_address
- `ix_birdeye_wallet_tokens_token_address`: token_address
- `idx_wallet_token_snapshot`: (wallet_address, token_address, snapshot_at)
- `idx_wallet_value`: (wallet_address, value_usd)

**采集频率:** 每 600 秒 (10分钟) - 仅采集配置中的钱包

---

### 3.5 `birdeye_new_listings`

存储新上币信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| token_address | String(128) | 代币地址 (唯一) |
| symbol | String(32) | 代币符号 |
| name | String(128) | 代币名称 |
| decimals | Integer | 小数位数 |
| source | String(64) | 上币来源 |
| liquidity | Float | 初始流动性 |
| liquidity_added_at | DateTime | 添加流动性时间 |
| logo_uri | String(512) | Logo URL |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_new_listings_token_address`: token_address (unique)
- `ix_birdeye_new_listings_liquidity_added_at`: liquidity_added_at
- `idx_liquidity_time`: (liquidity_added_at, liquidity)

**采集频率:** 每 60 秒 (1分钟)

**特性:** 
- 自动添加新上币到跟踪列表
- 可配置自动获取新币的安全信息和概览

---

### 3.6 `birdeye_token_security`

存储代币安全信息(貔貅币检测)。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| token_address | String(128) | 代币地址 |
| creator_address | String(128) | 创建者地址 |
| creator_owner_address | String(128) | 创建者拥有者地址 |
| owner_address | String(128) | 当前拥有者地址 |
| creation_time | BigInteger | 创建时间戳 |
| creation_tx | String(128) | 创建交易 |
| mint_time | BigInteger | 铸造时间戳 |
| mint_tx | String(128) | 铸造交易 |
| creator_balance | Float | 创建者余额 |
| creator_percentage | Float | 创建者持有百分比 |
| owner_balance | Float | 拥有者余额 |
| owner_percentage | Float | 拥有者持有百分比 |
| top10_holder_balance | Float | Top10 持有者余额 |
| top10_holder_percent | Float | Top10 持有者百分比 |
| top10_user_balance | Float | Top10 用户余额 |
| top10_user_percent | Float | Top10 用户百分比 |
| mutable_metadata | Boolean | 元数据是否可变 |
| freezeable | Boolean | 是否可冻结 |
| freeze_authority | String(128) | 冻结权限地址 |
| is_token2022 | Boolean | 是否是 Token-2022 |
| transfer_fee_enable | Boolean | 是否启用转账费 |
| non_transferable | Boolean | 是否不可转账 |
| total_supply | Float | 总供应量 |
| metaplex_update_authority | String(128) | Metaplex 更新权限 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_token_security_token_address`: token_address
- `ix_birdeye_token_security_owner_address`: owner_address
- `idx_token_security_created`: (token_address, created_at)

**采集频率:** 每 3600 秒 (1小时)

**安全警告判断:**
- `mutable_metadata = true`: 元数据可被修改
- `freezeable = true`: 代币可被冻结
- `top10_holder_percent > 50`: 前10持有者拥有超过50%供应量

---

### 3.7 `birdeye_token_overview`

存储代币全面概览和指标数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| token_address | String(128) | 代币地址 |
| price | Float | 当前价格 |
| market_cap | Float | 市值 |
| fdv | Float | 完全稀释估值 |
| liquidity | Float | 总流动性 |
| total_supply | Float | 总供应量 |
| circulating_supply | Float | 流通供应量 |
| holder | Integer | 持有者数量 |
| number_markets | Integer | 市场数量 |
| price_change_24h_percent | Float | 24小时价格变化百分比 |
| v24h | Float | 24小时交易量 |
| v24h_usd | Float | 24小时交易量 (USD) |
| trade_24h | Integer | 24小时交易次数 |
| buy_24h | Integer | 24小时买入次数 |
| sell_24h | Integer | 24小时卖出次数 |
| unique_wallet_24h | Integer | 24小时唯一钱包数 |
| price_change_1h_percent | Float | 1小时价格变化 |
| v1h | Float | 1小时交易量 |
| v1h_usd | Float | 1小时交易量 (USD) |
| v30m | Float | 30分钟交易量 |
| v30m_usd | Float | 30分钟交易量 (USD) |
| last_trade_unix_time | BigInteger | 最后交易时间戳 |
| last_trade_human_time | DateTime | 最后交易时间 |
| created_at | DateTime | 创建时间 |

**索引:**
- `ix_birdeye_token_overview_token_address`: token_address
- `ix_birdeye_token_overview_market_cap`: market_cap
- `ix_birdeye_token_overview_liquidity`: liquidity
- `idx_token_overview_created`: (token_address, created_at)
- `idx_market_cap_liquidity`: (market_cap, liquidity)

**采集频率:** 每 300 秒 (5分钟)

---

## 数据采集策略

### 自动采集任务

| 任务 | 频率 | 说明 |
|------|------|------|
| Dexscreener Token Boosts | 6秒 | 自动跟踪新代币 |
| Birdeye New Listings | 60秒 | 发现新上币并自动跟踪 |
| Birdeye Token Overview | 300秒 | 跟踪代币实时数据 |
| Birdeye Token Security | 3600秒 | 定期安全检查 |
| Birdeye Token Transactions | 120秒 | 实时交易监控 |
| Birdeye Top Traders | 300秒 | 识别聪明钱 |
| Birdeye Wallet Portfolio | 600秒 | 跟踪配置的钱包 |

### 动态跟踪机制

1. **Dexscreener Boost** → 自动添加到代币跟踪列表
2. **Birdeye New Listings** → 自动添加到代币跟踪列表
3. **跟踪的代币** → 自动采集交易、概览、安全、Top Traders数据
4. **配置的钱包** → 定期采集投资组合快照

---

## 配置选项

在 `.env` 文件中配置:

```env
# 代币跟踪列表 (逗号分隔)
TRACKED_TOKENS=token_address1,token_address2

# 钱包跟踪列表 (逗号分隔)
TRACKED_WALLETS=wallet_address1,wallet_address2

# 新币自动跟踪
TRACK_NEW_LISTINGS_SECURITY=true
TRACK_NEW_LISTINGS_OVERVIEW=true

# 采集频率调整 (秒)
DEXSCREENER_FETCH_INTERVAL=6
BIRDEYE_NEW_LISTINGS_INTERVAL=60
BIRDEYE_TOKEN_OVERVIEW_INTERVAL=300
BIRDEYE_TOKEN_SECURITY_INTERVAL=3600
BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL=120
BIRDEYE_TOP_TRADERS_INTERVAL=300
BIRDEYE_WALLET_PORTFOLIO_INTERVAL=600
```

---

## 查询示例

### 查看最新上币

```sql
SELECT symbol, name, liquidity, liquidity_added_at 
FROM birdeye_new_listings 
ORDER BY created_at DESC 
LIMIT 10;
```

### 查找可疑代币 (貔貅币)

```sql
SELECT token_address, 
       mutable_metadata, 
       freezeable, 
       top10_holder_percent
FROM birdeye_token_security
WHERE mutable_metadata = true 
   OR freezeable = true 
   OR top10_holder_percent > 50
ORDER BY created_at DESC;
```

### 查看代币交易量前10

```sql
SELECT token_address, price, market_cap, liquidity, v24h_usd
FROM birdeye_token_overview
ORDER BY v24h_usd DESC
LIMIT 10;
```

### 查看钱包历史持仓变化

```sql
SELECT snapshot_at, 
       token_address, 
       symbol, 
       ui_amount, 
       value_usd
FROM birdeye_wallet_tokens
WHERE wallet_address = 'YOUR_WALLET_ADDRESS'
ORDER BY snapshot_at DESC, value_usd DESC;
```

### 查看代币买卖比

```sql
SELECT token_address,
       buy_24h,
       sell_24h,
       (buy_24h * 1.0 / NULLIF(sell_24h, 0)) as buy_sell_ratio,
       v24h_usd,
       price_change_24h_percent
FROM birdeye_token_overview
WHERE trade_24h > 100
ORDER BY buy_sell_ratio DESC
LIMIT 20;
```

---

## 数据保留策略

建议根据需要设置数据保留策略:

- **原始响应**: 保留 7 天
- **交易数据**: 保留 30 天
- **快照数据** (概览/持仓): 保留 90 天
- **静态数据** (安全信息/新上币): 永久保留

可以通过定期任务清理旧数据，例如:

```sql
-- 清理30天前的交易数据
DELETE FROM birdeye_token_transactions 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 清理7天前的原始响应
DELETE FROM raw_api_responses 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

## 总结

- **9 张表** 全面覆盖加密货币数据采集需求
- **自动跟踪** 新币和热门币
- **实时监控** 交易、价格、流动性
- **安全分析** 自动识别高风险代币
- **灵活配置** 支持自定义跟踪列表和采集频率
- **高性能索引** 优化查询速度

