# 从交易记录中提取钱包地址并获取钱包数据

## 📋 功能概述

在获取代币交易记录时，自动提取交易中的钱包地址（owner），然后为这些钱包地址异步获取：
1. **钱包交易历史** (`get_wallet_transactions`)
2. **钱包投资组合** (`get_wallet_portfolio`)

这样可以全面了解与代币交互的钱包信息，用于分析交易行为和持仓情况。

## 🔄 实现逻辑

### 1. 数据流程

```
获取代币交易记录
    ↓
提取交易中的钱包地址 (owner)
    ↓
去重（使用 set）
    ↓
为每个钱包地址创建异步任务
    ├─→ 获取钱包交易历史
    └─→ 获取钱包投资组合
```

### 2. 核心更新

#### `_fetch_token_transactions_async` 函数更新

**文件**: `app/services/scheduler.py` (第 101-186 行)

**新增功能**:
```python
async def _fetch_token_transactions_async(
    token_address: str, 
    max_transactions: int = 200,
    tx_type: str = "swap",
    before_time: Optional[int] = None,
    after_time: Optional[int] = None,
    fetch_wallet_data: bool = True  # 新增参数
):
```

**主要变化**:
1. ✅ 新增 `fetch_wallet_data` 参数控制是否获取钱包数据
2. ✅ 使用 `set()` 收集所有唯一的钱包地址
3. ✅ 为每个钱包地址创建异步任务

**关键代码**:
```python
all_wallet_addresses = set()  # 收集所有钱包地址

# 在获取交易记录时收集钱包地址
if fetch_wallet_data:
    for tx in response.data.items:
        if tx.owner:  # owner 就是钱包地址
            all_wallet_addresses.add(tx.owner)

# 为收集到的钱包地址创建后台任务
if fetch_wallet_data and all_wallet_addresses:
    logger.info(f"[Async] Found {len(all_wallet_addresses)} unique wallet addresses")
    for wallet_address in all_wallet_addresses:
        asyncio.create_task(_fetch_wallet_transactions_async(wallet_address))
        asyncio.create_task(_fetch_wallet_portfolio_async(wallet_address))
```

### 3. 新增钱包交易历史获取函数

**文件**: `app/services/scheduler.py` (第 188-220 行)

```python
async def _fetch_wallet_transactions_async(wallet_address: str, limit: int = 10):
    """
    Asynchronously fetch wallet transaction history and save to database.
    """
```

**功能**:
- 获取钱包的交易历史记录
- 保存到 `birdeye_wallet_transactions` 表
- 默认获取最近 10 笔交易
- 使用 `save_wallet_transaction` 方法保存

### 4. 新增钱包投资组合获取函数

**文件**: `app/services/scheduler.py` (第 223-253 行)

```python
async def _fetch_wallet_portfolio_async(wallet_address: str):
    """
    Asynchronously fetch wallet portfolio (token holdings) and save to database.
    """
```

**功能**:
- 获取钱包持有的所有代币
- 保存到 `birdeye_wallet_tokens` 表
- 使用 `save_or_update_wallet_tokens_batch` 方法保存
- 自动去重（钱包地址 + 代币地址唯一）

## 📊 数据表结构

### 1. birdeye_wallet_transactions (钱包交易历史)

```sql
CREATE TABLE birdeye_wallet_transactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tx_hash VARCHAR(128) UNIQUE,  -- 交易哈希（唯一）
    block_number BIGINT,           -- 区块高度
    block_time DATETIME,           -- 交易时间
    status BOOLEAN,                -- 交易状态
    from_address VARCHAR(255),     -- 发起地址
    to_address VARCHAR(255),       -- 目标地址
    fee BIGINT,                    -- 手续费
    main_action VARCHAR(50),       -- 主要动作
    balance_change TEXT,           -- 余额变动 (JSON)
    token_transfers TEXT,          -- 代币转账 (JSON)
    contract_label TEXT,           -- 合约标签 (JSON)
    INDEX(tx_hash),
    INDEX(from_address),
    INDEX(block_time)
);
```

### 2. birdeye_wallet_tokens (钱包投资组合)

```sql
CREATE TABLE birdeye_wallet_tokens (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    wallet_address VARCHAR(128),   -- 钱包地址
    token_address VARCHAR(128),    -- 代币地址
    symbol VARCHAR(32),            -- 代币符号
    name VARCHAR(128),             -- 代币名称
    decimals INT,                  -- 精度
    balance VARCHAR(64),           -- 余额
    ui_amount FLOAT,               -- UI 数量
    price_usd FLOAT,               -- USD 价格
    value_usd FLOAT,               -- USD 价值
    snapshot_at DATETIME,          -- 快照时间
    INDEX(wallet_address),
    INDEX(token_address),
    UNIQUE KEY(wallet_address, token_address)
);
```

## 🎯 使用场景

### 场景 1: 分析代币的交易者画像

```python
# 获取代币交易记录并自动获取交易者钱包信息
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=200,
    fetch_wallet_data=True  # 启用钱包数据获取
)

# 结果：
# 1. 保存了 200 笔交易记录
# 2. 提取了例如 50 个唯一钱包地址
# 3. 为每个钱包获取了交易历史和持仓信息
# 4. 可以分析这些钱包的交易模式和持仓分布
```

### 场景 2: 只获取交易记录，不获取钱包数据

```python
# 如果只需要交易记录，不需要钱包详细信息
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=200,
    fetch_wallet_data=False  # 禁用钱包数据获取
)
```

### 场景 3: 分析特定时间段的交易者

```python
import time

# 获取最近 1 小时的交易并分析交易者
after_time = int(time.time()) - 3600
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=100,
    after_time=after_time,
    fetch_wallet_data=True
)
```

## 📈 数据分析示例

### 示例 1: 查询某个代币的所有交易者钱包

```sql
-- 获取某个代币的所有唯一交易者
SELECT DISTINCT 
    JSON_UNQUOTE(JSON_EXTRACT(base, '$.address')) as token_address,
    owner as wallet_address,
    COUNT(*) as tx_count
FROM birdeye_token_transactions
WHERE JSON_UNQUOTE(JSON_EXTRACT(base, '$.address')) = 'So11111111111111111111111111111111111111112'
GROUP BY wallet_address
ORDER BY tx_count DESC
LIMIT 20;
```

### 示例 2: 分析交易者的投资组合

```sql
-- 查看某个交易者的持仓情况
SELECT 
    wt.wallet_address,
    wt.symbol,
    wt.ui_amount,
    wt.value_usd,
    wt.snapshot_at
FROM birdeye_wallet_tokens wt
WHERE wt.wallet_address = 'YOUR_WALLET_ADDRESS'
ORDER BY wt.value_usd DESC;
```

### 示例 3: 统计交易者的交易历史

```sql
-- 查看某个钱包的交易历史统计
SELECT 
    from_address as wallet,
    COUNT(*) as total_transactions,
    COUNT(DISTINCT DATE(block_time)) as active_days,
    MIN(block_time) as first_tx,
    MAX(block_time) as last_tx
FROM birdeye_wallet_transactions
WHERE from_address = 'YOUR_WALLET_ADDRESS'
GROUP BY wallet;
```

### 示例 4: 发现活跃交易者

```sql
-- 找出交易次数最多的钱包
SELECT 
    owner as wallet_address,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT JSON_UNQUOTE(JSON_EXTRACT(base, '$.address'))) as unique_tokens,
    SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_count,
    SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_count
FROM birdeye_token_transactions
WHERE blockUnixTime > UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 7 DAY))
GROUP BY owner
ORDER BY transaction_count DESC
LIMIT 50;
```

## 🚀 执行流程示例

### 典型执行场景

```
1. 获取代币交易记录 (200 笔)
   └─ API 请求: 2 次 (每次 100 笔)
   └─ 保存: 200 笔交易记录

2. 提取钱包地址
   └─ 假设 200 笔交易来自 45 个唯一钱包
   └─ 使用 set 去重

3. 创建后台任务 (45 个钱包 × 2 个任务)
   ├─ 45 个任务: 获取钱包交易历史
   └─ 45 个任务: 获取钱包投资组合

4. 并发执行所有钱包任务
   └─ 总共 90 个异步任务并发执行
```

### 日志输出示例

```
[Async] Fetching token transactions for So111... (tx_type=swap, max=200)
[Async] Page 1: Saved/Updated 100 transactions for So111...
[Async] Page 2: Saved/Updated 100 transactions for So111...
[Async] Completed: Total saved/updated 200 transactions for So111...
[Async] Found 45 unique wallet addresses, creating background tasks...
[Async] Created wallet data fetch tasks for 45 wallets
[Async] Fetching wallet transactions for Wallet1...
[Async] Fetching wallet portfolio for Wallet1...
[Async] Fetching wallet transactions for Wallet2...
[Async] Fetching wallet portfolio for Wallet2...
...
[Async] Saved 10 wallet transactions for Wallet1
[Async] Saved/Updated 15 tokens for wallet Wallet1
```

## ⚙️ 配置建议

### 1. 热门代币（大量交易者）

```python
max_transactions=200      # 中等数量的交易
fetch_wallet_data=True   # 启用钱包数据获取
# 预期: 可能有 50-100 个唯一钱包
```

### 2. 普通代币（适中交易量）

```python
max_transactions=100
fetch_wallet_data=True
# 预期: 可能有 20-50 个唯一钱包
```

### 3. 新币（少量交易者）

```python
max_transactions=50
fetch_wallet_data=True
# 预期: 可能有 10-30 个唯一钱包
```

### 4. 只需要交易记录

```python
max_transactions=200
fetch_wallet_data=False  # 不获取钱包数据
# 适用于: 只分析交易本身，不关心交易者
```

## 🔍 性能考虑

### 1. API 调用数量

```
假设获取 200 笔交易，有 50 个唯一钱包：
- 交易记录 API: 2 次 (200/100)
- 钱包交易历史 API: 50 次
- 钱包投资组合 API: 50 次
总计: 102 次 API 调用
```

### 2. 速率限制

```python
# 交易记录分页之间: 0.2 秒
await asyncio.sleep(0.2)

# 钱包任务是异步并发的，不需要额外延迟
# 但 BirdeyeClient 内部会处理速率限制
```

### 3. 数据库性能

- **去重机制**: 
  - `tx_hash` 唯一索引（钱包交易）
  - `wallet_address + token_address` 唯一索引（钱包代币）
- **批量保存**: 使用 batch 方法提高效率
- **索引优化**: 在钱包地址和代币地址上建立索引

## 📊 数据价值

### 1. 交易者分析

- 识别活跃交易者
- 分析交易频率和模式
- 发现机器人和狙击手

### 2. 持仓分析

- 了解交易者的投资组合多样性
- 识别大户和鲸鱼
- 分析持仓集中度

### 3. 行为分析

- 买卖比例
- 交易时间分布
- 持仓周期

### 4. 风险评估

- 识别异常交易模式
- 发现潜在的操纵行为
- 评估代币流动性质量

## ✅ 完成状态

- ✅ 在 `_fetch_token_transactions_async` 中提取钱包地址
- ✅ 创建 `_fetch_wallet_transactions_async` 函数
- ✅ 创建 `_fetch_wallet_portfolio_async` 函数
- ✅ 实现异步并发执行
- ✅ 添加 `fetch_wallet_data` 参数控制
- ✅ 完善日志输出
- ✅ 无 linter 错误

---

**更新时间**: 2026-01-11
**版本**: v1.0
**状态**: ✅ 已完成钱包数据提取功能

