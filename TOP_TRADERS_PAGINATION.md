# Top Traders 分页查询实现

## 📋 更新概述

为 `get_top_traders` 接口添加完整的分页查询支持，可以获取超过 10 个 top traders 的数据。

## 🔄 核心变更

### 1. 分页参数说明

根据 API 文档，`get_top_traders` 接口支持以下分页参数：

| 参数 | 类型 | 范围 | 默认值 | 说明 |
|-----|------|-----|--------|------|
| `offset` | integer | 0 - 10000 | 0 | 分页偏移量 |
| `limit` | integer | 1 - 10 | 10 | 每页返回数量 |

**重要提示**: 
- `offset + limit <= 10000` （API 限制）
- 单次请求最多返回 10 条记录
- 需要分页获取才能获得更多数据

### 2. 异步分页函数更新

**文件**: `app/services/scheduler.py`

#### 更新的 `_fetch_token_top_traders_async` 函数

```python
async def _fetch_token_top_traders_async(
    token_address: str, 
    time_frame: str = "24h", 
    max_traders: int = 100,      # 新增：最大获取数量
    sort_by: str = "volume"       # 新增：排序字段
):
```

**主要功能**:
- ✅ 自动分页获取多个 top traders
- ✅ 智能停止：当返回数量 < limit 时停止
- ✅ 速率限制：每页之间延迟 0.3 秒
- ✅ 支持自定义最大获取数量
- ✅ 支持按 volume 或 trade 排序

**分页逻辑**:
```python
offset = 0
limit = 10  # API 单次最大限制
max_pages = (max_traders + limit - 1) // limit

for page in range(max_pages):
    response = await client.get_top_traders(
        token_address=token_address,
        time_frame=time_frame,
        sort_by=sort_by,
        sort_type="desc",
        offset=offset,
        limit=limit
    )
    
    if response.success and response.data.items:
        # 保存数据
        await save_to_database(response.data.items)
        
        # 检查是否到达最后一页
        if len(response.data.items) < limit:
            break
        
        offset += limit
        await asyncio.sleep(0.3)  # 速率限制
```

### 3. 在 Trending Poller 中的应用

**文件**: `app/services/scheduler.py` (第 620-633 行)

```python
# 为每个热门代币异步获取 top traders
asyncio.create_task(_fetch_token_top_traders_async(
    address, 
    time_frame="24h", 
    max_traders=50,      # 每个代币最多获取 50 个 top traders
    sort_by="volume"     # 按交易量排序
))
```

**配置说明**:
- `max_traders=50`: 每个热门代币获取前 50 个交易者
- 需要 5 次 API 请求 (50 / 10 = 5 页)
- 总延迟约 1.5 秒 (5 页 × 0.3 秒)

### 4. 独立 Top Traders Poller 更新

**文件**: `app/services/scheduler.py` (第 474-553 行)

虽然该 poller 目前被注释掉了，但也已更新为支持分页：

```python
async def _birdeye_top_traders_poller():
    """Fetch top traders for tracked tokens with pagination support."""
    # ...
    for token_address in list(_tracked_tokens):
        # 分页获取每个代币的 top traders
        offset = 0
        limit = 10
        max_traders = 50
        
        for page in range((max_traders + limit - 1) // limit):
            response = await client.get_top_traders(...)
            # 保存数据并检查是否继续
```

## 📊 使用示例

### 示例 1: 基础分页（获取 30 个 traders）

```python
from app.api.clients.birdeye import BirdeyeClient

client = BirdeyeClient()
all_traders = []
offset = 0
limit = 10

# 获取 3 页数据（30 个 traders）
for page in range(3):
    response = await client.get_top_traders(
        token_address="So11111111111111111111111111111111111111112",
        time_frame="24h",
        sort_by="volume",
        sort_type="desc",
        offset=offset,
        limit=limit
    )
    
    if response.success and response.data.items:
        all_traders.extend(response.data.items)
        offset += limit
        await asyncio.sleep(0.3)
    else:
        break

print(f"Total fetched: {len(all_traders)} traders")
```

### 示例 2: 使用辅助函数（推荐）

```python
async def fetch_all_top_traders(token_address: str, max_traders: int = 50):
    """Fetch all top traders with pagination."""
    client = BirdeyeClient()
    all_traders = []
    offset = 0
    limit = 10
    max_pages = (max_traders + limit - 1) // limit
    
    try:
        for page in range(max_pages):
            response = await client.get_top_traders(
                token_address=token_address,
                time_frame="24h",
                sort_by="volume",
                sort_type="desc",
                offset=offset,
                limit=limit
            )
            
            if response.success and response.data.items:
                all_traders.extend(response.data.items)
                
                # 如果返回数量 < limit，说明没有更多数据了
                if len(response.data.items) < limit:
                    break
                
                offset += limit
                await asyncio.sleep(0.3)
            else:
                break
    finally:
        await client.close()
    
    return all_traders

# 使用
traders = await fetch_all_top_traders("token_address", max_traders=100)
```

### 示例 3: 按交易次数分页

```python
# 获取交易次数最多的前 50 个交易者
traders_by_trade = []
offset = 0

for page in range(5):  # 5 页 × 10 = 50 traders
    response = await client.get_top_traders(
        token_address="token_address",
        time_frame="24h",
        sort_by="trade",      # 按交易次数排序
        sort_type="desc",
        offset=offset,
        limit=10
    )
    
    if response.success and response.data.items:
        traders_by_trade.extend(response.data.items)
        offset += 10
        await asyncio.sleep(0.3)
```

## 🎯 性能优化建议

### 1. 速率限制
```python
# 建议在每次请求之间添加延迟
await asyncio.sleep(0.3)  # 300ms 延迟
```

### 2. 智能停止
```python
# 当返回数量 < limit 时停止，避免不必要的请求
if len(response.data.items) < limit:
    break
```

### 3. 合理设置 max_traders
```python
# 根据需求设置合理的最大值
max_traders = 50   # 适中，5 次请求
max_traders = 100  # 较多，10 次请求
max_traders = 200  # 很多，20 次请求
```

### 4. 批量保存数据
```python
# 在每一页都保存数据，而不是等所有页获取完成
if response.success and response.data.items:
    await repository.save_or_update_top_traders_batch(
        token_address, 
        response.data.items
    )
```

## 📈 数据统计示例

### 统计所有 traders 的总交易量

```python
traders = await fetch_all_top_traders("token_address", max_traders=100)

total_volume = sum(t.volume for t in traders)
total_trades = sum(t.trade for t in traders)
avg_volume_per_trader = total_volume / len(traders)

print(f"Total traders: {len(traders)}")
print(f"Total volume: ${total_volume:,.2f}")
print(f"Total trades: {total_trades:,}")
print(f"Average volume per trader: ${avg_volume_per_trader:,.2f}")
```

### 分析交易者类型分布

```python
from collections import Counter

trader_types = Counter(t.type for t in traders)
print(f"Trader types distribution: {dict(trader_types)}")

# 统计有标签的交易者
tagged_traders = [t for t in traders if t.tags]
print(f"Traders with tags: {len(tagged_traders)}")
```

## 🚀 运行 Demo

### 完整的分页 Demo

```bash
# 运行包含分页示例的 demo
python examples/birdeye_top_traders_demo.py
```

Demo 包含以下场景：
1. ✅ 单页获取（10 个 traders）
2. ✅ 多页获取（30 个 traders）
3. ✅ 按交易次数排序并分页（20 个 traders）
4. ✅ 数据统计分析

### 测试输出示例

```
📊 Fetching up to 30 top traders with pagination...
   Fetching page 1... (offset=0)
   ✅ Got 10 traders
   Fetching page 2... (offset=10)
   ✅ Got 10 traders
   Fetching page 3... (offset=20)
   ✅ Got 10 traders
✅ Total fetched: 30 traders

📈 Statistics from 30 traders:
   Total Volume: $12,345,678.90
   Total Trades: 1,234
   Average Volume per Trader: $411,522.63
```

## ⚙️ 配置参数

### 推荐配置（在 scheduler 中）

```python
# 热门代币：获取更多 top traders
max_traders=50  # 前 50 个交易者
time_frame="24h"
sort_by="volume"

# 普通代币：获取较少 top traders
max_traders=20  # 前 20 个交易者
time_frame="24h"
sort_by="volume"
```

### API 限制

- **单次最大返回**: 10 条记录
- **最大偏移量**: 10000
- **最大可获取**: 10000 条记录（理论上）
- **建议获取量**: 50-100 条（实际使用）

## ✅ 更新文件清单

- ✅ `app/services/scheduler.py` - 异步函数支持分页
- ✅ `app/services/scheduler.py` - trending poller 调用更新
- ✅ `app/services/scheduler.py` - top traders poller 支持分页
- ✅ `examples/birdeye_top_traders_demo.py` - 添加分页示例

## 🔍 验证方法

### 查看日志

启动服务后，查看日志输出：

```
[Async] Fetching top traders for So111... (time_frame=24h, max=50)
[Async] Page 1: Saved/Updated 10 top traders for So111...
[Async] Page 2: Saved/Updated 10 top traders for So111...
[Async] Page 3: Saved/Updated 10 top traders for So111...
[Async] Page 4: Saved/Updated 10 top traders for So111...
[Async] Page 5: Saved/Updated 10 top traders for So111...
[Async] Completed: Total saved/updated 50 top traders for So111...
```

### 数据库验证

```sql
-- 查看某个代币的 top traders 数量
SELECT COUNT(*) as trader_count
FROM birdeye_top_traders
WHERE tokenAddress = 'So11111111111111111111111111111111111111112';

-- 应该看到 50 条记录（如果 max_traders=50）

-- 查看交易量分布
SELECT 
    tokenAddress,
    COUNT(*) as trader_count,
    SUM(volume) as total_volume,
    AVG(volume) as avg_volume
FROM birdeye_top_traders
GROUP BY tokenAddress
ORDER BY total_volume DESC
LIMIT 10;
```

---

**更新时间**: 2026-01-11
**版本**: v1.2
**状态**: ✅ 已完成分页支持

