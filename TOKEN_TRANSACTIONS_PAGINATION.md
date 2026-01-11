# Token Transactions 分页查询实现

## 📋 更新概述

为 `get_token_transactions` 接口添加完整的分页查询支持，可以获取大量历史交易记录。

## 🔄 API 参数说明

根据 Birdeye API 文档，`get_token_transactions` 接口支持以下参数：

| 参数 | 类型 | 范围/选项 | 默认值 | 说明 |
|-----|------|----------|--------|------|
| `address` | string | - | required | 代币合约地址 |
| `offset` | integer | 0 - 10000 | 0 | 分页偏移量 |
| `limit` | integer | 1 - 100 | 100 | 每页返回数量 |
| `tx_type` | string enum | swap, add, remove, all | swap | 交易类型 |
| `before_time` | integer | 1 - 10000000000 | - | Unix 时间戳（秒）- 查询此时间之前的交易 |
| `after_time` | integer | 1 - 10000000000 | - | Unix 时间戳（秒）- 查询此时间之后的交易 |
| `ui_amount_mode` | string enum | raw, scaled | scaled | Solana 代币数量模式 |

**重要说明**:
- ✅ `offset + limit <= 10000` （API 限制）
- ✅ 单次最多返回 100 条记录（比 top_traders 的 10 大得多）
- ✅ 支持时间范围过滤（before_time 和 after_time）
- ✅ 支持多种交易类型过滤

## 🆕 核心变更

### 1. 异步分页函数更新

**文件**: `app/services/scheduler.py` (第 101-175 行)

#### 更新的 `_fetch_token_transactions_async` 函数

```python
async def _fetch_token_transactions_async(
    token_address: str, 
    max_transactions: int = 200,      # 新增：最大获取数量
    tx_type: str = "swap",           # 新增：交易类型
    before_time: Optional[int] = None,  # 新增：时间过滤
    after_time: Optional[int] = None    # 新增：时间过滤
):
```

**主要功能**:
- ✅ 自动分页获取多笔交易记录
- ✅ 智能停止：当返回数量 < limit 时停止
- ✅ 速率限制：每页之间延迟 0.2 秒
- ✅ 支持自定义最大获取数量
- ✅ 支持交易类型过滤（swap/add/remove/all）
- ✅ 支持时间范围过滤

**分页逻辑**:
```python
offset = 0
limit = 100  # API 单次最大限制
max_pages = (max_transactions + limit - 1) // limit

for page in range(max_pages):
    response = await client.get_token_transactions(
        token_address=token_address,
        tx_type=tx_type,
        offset=offset,
        limit=limit,
        before_time=before_time,
        after_time=after_time
    )
    
    if response.success and response.data.items:
        # 保存数据
        await save_to_database(response.data.items)
        
        # 检查是否到达最后一页
        if len(response.data.items) < limit:
            break
        
        offset += limit
        await asyncio.sleep(0.2)  # 速率限制
```

### 2. 在 Trending Poller 中的应用

**文件**: `app/services/scheduler.py` (第 697-702 行)

```python
# 为每个热门代币异步获取交易记录
asyncio.create_task(_fetch_token_transactions_async(
    address, 
    max_transactions=200,    # 最多获取 200 笔交易
    tx_type="swap"          # 只获取 swap 交易
))
```

**配置说明**:
- `max_transactions=200`: 每个代币获取最近 200 笔交易
- 需要 2 次 API 请求 (200 / 100 = 2 页)
- 总延迟约 0.2 秒 (1 次分页 × 0.2 秒)

### 3. 在 Dexscreener Poller 中的应用

**文件**: `app/services/scheduler.py` (第 292 行)

```python
asyncio.create_task(_fetch_token_transactions_async(
    token_address, 
    max_transactions=200
))
```

### 4. 独立 Transactions Poller 更新

**文件**: `app/services/scheduler.py` (第 470-537 行)

虽然目前被注释，但已更新为完整的分页实现：

```python
async def _birdeye_token_transactions_poller():
    """Fetch token transactions for tracked tokens with pagination support."""
    # ...
    for token_address in list(_tracked_tokens):
        # 分页获取每个代币的交易记录
        offset = 0
        limit = 100
        max_transactions = 200
        
        for page in range((max_transactions + limit - 1) // limit):
            response = await client.get_token_transactions(...)
            # 保存数据并检查是否继续
```

## 📊 使用场景

### 场景 1: 获取最近的交易（默认）

```python
# 获取最近 200 笔 swap 交易
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=200,
    tx_type="swap"
)
```

### 场景 2: 获取所有类型的交易

```python
# 获取最近 500 笔所有类型的交易
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=500,
    tx_type="all"  # swap, add, remove 都包括
)
```

### 场景 3: 获取特定时间范围的交易

```python
import time

# 获取最近 24 小时的交易
after_time = int(time.time()) - 86400  # 24小时前
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=1000,
    tx_type="swap",
    after_time=after_time
)
```

### 场景 4: 获取历史交易

```python
# 获取某个时间点之前的交易
before_time = 1704067200  # 2024-01-01 00:00:00 UTC
await _fetch_token_transactions_async(
    token_address="So11111111111111111111111111111111111111112",
    max_transactions=500,
    tx_type="swap",
    before_time=before_time
)
```

## 🎯 交易类型说明

| tx_type | 说明 | 使用场景 |
|---------|------|---------|
| `swap` | 代币交换交易 | 默认，最常用，分析交易活跃度 |
| `add` | 添加流动性 | 分析流动性提供者行为 |
| `remove` | 移除流动性 | 分析流动性撤出情况 |
| `all` | 所有类型交易 | 完整分析代币活动 |

## 📈 性能优化

### 1. 大 limit 值（相比 top_traders）

```python
# Transactions: limit 最大 100（效率高）
limit = 100  # 单次请求获取 100 条

# Top Traders: limit 最大 10（需要更多请求）
limit = 10   # 单次请求获取 10 条
```

### 2. 合理的速率限制

```python
# 每页之间延迟 0.2 秒（比 top_traders 的 0.3 秒快）
await asyncio.sleep(0.2)
```

### 3. 智能停止

```python
# 当返回数量 < limit 时停止
if len(response.data.items) < limit:
    break
```

### 4. 使用时间过滤优化

```python
# 只获取最近的交易，避免获取过多历史数据
import time
before_time = int(time.time())  # 当前时间
after_time = before_time - 3600  # 1小时前

# 这样可以精确控制获取的时间范围
```

## 📝 完整示例

### 示例 1: 基础分页（200 笔交易）

```python
from app.api.clients.birdeye import BirdeyeClient

client = BirdeyeClient()
all_transactions = []
offset = 0
limit = 100

# 获取 2 页数据（200 笔交易）
for page in range(2):
    response = await client.get_token_transactions(
        token_address="So11111111111111111111111111111111111111112",
        tx_type="swap",
        offset=offset,
        limit=limit
    )
    
    if response.success and response.data.items:
        all_transactions.extend(response.data.items)
        offset += limit
        await asyncio.sleep(0.2)
    else:
        break

print(f"Total fetched: {len(all_transactions)} transactions")
```

### 示例 2: 获取最近 24 小时的所有交易

```python
import time

async def fetch_recent_24h_transactions(token_address: str):
    """获取最近 24 小时的所有交易"""
    client = BirdeyeClient()
    all_transactions = []
    offset = 0
    limit = 100
    after_time = int(time.time()) - 86400  # 24小时前
    
    try:
        while offset < 10000:  # API 限制
            response = await client.get_token_transactions(
                token_address=token_address,
                tx_type="all",
                offset=offset,
                limit=limit,
                after_time=after_time
            )
            
            if response.success and response.data.items:
                all_transactions.extend(response.data.items)
                
                if len(response.data.items) < limit:
                    break
                
                offset += limit
                await asyncio.sleep(0.2)
            else:
                break
    finally:
        await client.close()
    
    return all_transactions

# 使用
transactions = await fetch_recent_24h_transactions("token_address")
print(f"Found {len(transactions)} transactions in last 24h")
```

### 示例 3: 分析交易类型分布

```python
from collections import Counter

# 获取所有类型的交易
transactions = await fetch_transactions(token_address, tx_type="all", max_transactions=500)

# 统计交易类型
tx_types = Counter(t.txType for t in transactions)
print(f"Transaction types: {dict(tx_types)}")

# 统计买卖方向（针对 swap）
swap_transactions = [t for t in transactions if t.txType == "swap"]
sides = Counter(t.side for t in swap_transactions)
print(f"Swap sides: {dict(sides)}")

# 计算总交易量
total_volume = sum(float(t.quotePrice or 0) * float(t.quote_info.get('uiAmount', 0)) 
                   for t in swap_transactions if t.quote_info)
print(f"Total volume: ${total_volume:,.2f}")
```

## ⚙️ 配置建议

### 热门代币（高流动性）

```python
max_transactions=500   # 更多交易记录
tx_type="swap"         # 只关注 swap
limit=100              # 使用最大 limit
```

### 普通代币（中等流动性）

```python
max_transactions=200   # 适中的记录数
tx_type="swap"
limit=100
```

### 新币（低流动性）

```python
max_transactions=100   # 较少记录
tx_type="all"          # 所有类型都分析
limit=100
```

## 🚀 日志输出示例

```
[Async] Fetching token transactions for So111... (tx_type=swap, max=200)
[Async] Page 1: Saved/Updated 100 transactions for So111...
[Async] Page 2: Saved/Updated 100 transactions for So111...
[Async] Completed: Total saved/updated 200 transactions for So111...
```

## 🔍 数据库验证

```sql
-- 查看某个代币的交易记录数量
SELECT COUNT(*) as tx_count
FROM birdeye_token_transactions
WHERE base LIKE '%So11111111111111111111111111111111111111112%';

-- 查看交易类型分布
SELECT 
    txType,
    side,
    COUNT(*) as count,
    SUM(CAST(JSON_EXTRACT(quote, '$.uiAmount') AS DECIMAL(20,8))) as total_amount
FROM birdeye_token_transactions
WHERE base LIKE '%So11111111111111111111111111111111111111112%'
GROUP BY txType, side
ORDER BY count DESC;

-- 查看最近的交易
SELECT 
    txHash,
    txType,
    side,
    FROM_UNIXTIME(blockUnixTime) as tx_time,
    JSON_EXTRACT(quote, '$.symbol') as quote_symbol,
    JSON_EXTRACT(base, '$.symbol') as base_symbol
FROM birdeye_token_transactions
ORDER BY blockUnixTime DESC
LIMIT 10;
```

## 📌 对比：Transactions vs Top Traders

| 特性 | Transactions | Top Traders |
|-----|-------------|-------------|
| 单次最大 limit | 100 | 10 |
| 分页效率 | 高（更少请求） | 低（更多请求） |
| 数据量 | 可以很大（10000+） | 相对较小（通常<100） |
| 时间过滤 | ✅ 支持 | ❌ 不支持 |
| 类型过滤 | ✅ 支持 4 种 | ❌ 不支持 |
| 推荐 max 值 | 200-500 | 50-100 |
| 延迟设置 | 0.2 秒 | 0.3 秒 |

## ✅ 更新文件清单

- ✅ `app/services/scheduler.py` - 添加 Optional 导入
- ✅ `app/services/scheduler.py` - 异步函数支持分页（第 101-175 行）
- ✅ `app/services/scheduler.py` - dexscreener poller 调用更新（第 292 行）
- ✅ `app/services/scheduler.py` - trending poller 调用更新（第 697-702 行）
- ✅ `app/services/scheduler.py` - transactions poller 支持分页（第 470-537 行）

## 🎉 完成状态

- ✅ 分页逻辑实现
- ✅ 支持交易类型过滤
- ✅ 支持时间范围过滤
- ✅ 智能停止机制
- ✅ 速率限制优化
- ✅ 所有调用点更新
- ✅ 无 linter 错误

---

**更新时间**: 2026-01-11
**版本**: v1.0
**状态**: ✅ 已完成分页支持

