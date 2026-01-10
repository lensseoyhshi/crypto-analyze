# Token Trending 后台任务增强说明

## 功能概述

在 Token Trending 定时任务中，现在会为每个获取到的热门代币自动创建后台任务，异步获取：
1. **代币安全信息** - Token Security（检查是否为貔貅币等）
2. **代币交易记录** - Token Transactions（最近50笔交易）

## 实现细节

### 代码位置
`app/services/scheduler.py` - `_birdeye_token_trending_poller()` 函数

### 核心逻辑

```python
# 保存热门代币数据后
for token in response.data.tokens:
    address = token.address
    # 异步获取代币安全信息
    asyncio.create_task(_fetch_token_security_async(address))
    # 异步获取代币交易记录
    asyncio.create_task(_fetch_token_transactions_async(address, limit=50))

logger.info(f"Created background tasks for {len(response.data.tokens)} tokens")
```

## 工作流程

```
1. 获取热门代币列表（每页20个）
   ↓
2. 保存/更新到 birdeye_token_trending 表
   ↓
3. 为每个代币创建两个后台任务：
   ├─ Task 1: _fetch_token_security_async(address)
   │  └─ 保存到 birdeye_token_security 表
   └─ Task 2: _fetch_token_transactions_async(address, limit=50)
      └─ 保存到 birdeye_token_transactions 表
```

## 任务说明

### Task 1: Token Security（代币安全检查）
**函数**: `_fetch_token_security_async(address)`

**功能**:
- 调用 Birdeye API 获取代币安全信息
- 检查项包括：
  - 创建者地址和持仓占比
  - 前10大持仓者占比
  - 元数据是否可变
  - 是否可冻结
  - 是否为Token2022标准
  - 等等...

**数据存储**:
- 表: `birdeye_token_security`
- 逻辑: 如果 `token_address` 已存在则更新，否则插入

### Task 2: Token Transactions（代币交易记录）
**函数**: `_fetch_token_transactions_async(address, limit=50)`

**功能**:
- 调用 Birdeye API 获取代币最近的交易记录
- 获取最近50笔交易（可配置）
- 包含买入/卖出信息、价格、数量等

**数据存储**:
- 表: `birdeye_token_transactions`
- 逻辑: 如果 `txHash` 已存在则更新，否则插入

## 性能优化

### 1. 异步并发执行
```python
# 使用 asyncio.create_task() 创建后台任务
# 不会阻塞主流程，所有任务并发执行
asyncio.create_task(_fetch_token_security_async(address))
asyncio.create_task(_fetch_token_transactions_async(address, limit=50))
```

### 2. 独立错误处理
每个后台任务都有独立的错误处理：
- 单个代币失败不影响其他代币
- 失败会记录警告日志
- 主流程继续执行

### 3. 资源控制
- 每个API调用之间有延迟（避免限流）
- 后台任务在独立的协程中运行
- 不会影响主定时任务的执行

## 日志示例

```
[INFO] [Birdeye] Fetching token trending (poll #1)
[INFO] [Birdeye] Page 1: Saved/Updated 20 trending tokens
[INFO] [Birdeye] Created background tasks for 20 tokens
[INFO] [Async] Fetching token security for DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
[INFO] [Async] Fetching token transactions for DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
[INFO] [Async] Token security saved/updated for DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
[INFO] [Async] Saved/Updated 50 transactions for DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263
```

## 数据关联查询

### 查询热门代币及其安全信息
```sql
SELECT 
    t.rank,
    t.symbol,
    t.name,
    t.price,
    t.volume_24h_usd,
    s.creator_percentage,
    s.top10_holder_percent,
    s.mutable_metadata,
    s.freezeable
FROM birdeye_token_trending t
LEFT JOIN birdeye_token_security s ON t.address = s.token_address
WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY t.rank ASC
LIMIT 20;
```

### 查询热门代币的最近交易
```sql
SELECT 
    t.rank,
    t.symbol,
    tx.side,
    tx.owner,
    tx.blockUnixTime,
    tx.basePrice
FROM birdeye_token_trending t
JOIN birdeye_token_transactions tx ON t.address = JSON_UNQUOTE(JSON_EXTRACT(tx.base, '$.address'))
WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
  AND tx.blockUnixTime >= UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 1 HOUR))
ORDER BY t.rank ASC, tx.blockUnixTime DESC;
```

## 预期效果

### 数据完整性
每次获取热门代币时，会自动补充：
- ✅ 代币基本信息（从 trending API）
- ✅ 代币安全信息（后台任务）
- ✅ 代币交易记录（后台任务）

### 时间效率
假设获取20个热门代币：
- **同步方式**: 20个代币 × 2个API × 1秒 = 40秒
- **异步方式**: 2-3秒（并发执行） ⚡

### 资源使用
- CPU: 低（异步IO密集型操作）
- 内存: 低（流式处理，不会一次性加载所有数据）
- 网络: 中等（大量API调用，但有限流保护）

## 监控与调试

### 查看后台任务执行情况
```sql
-- 检查安全信息是否已获取
SELECT 
    t.address,
    t.symbol,
    CASE WHEN s.token_address IS NOT NULL THEN '✅' ELSE '❌' END as has_security
FROM birdeye_token_trending t
LEFT JOIN birdeye_token_security s ON t.address = s.token_address
WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY t.rank ASC;

-- 检查交易记录是否已获取
SELECT 
    t.address,
    t.symbol,
    COUNT(tx.id) as transaction_count
FROM birdeye_token_trending t
LEFT JOIN birdeye_token_transactions tx ON t.address = JSON_UNQUOTE(JSON_EXTRACT(tx.base, '$.address'))
WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY t.address, t.symbol
ORDER BY t.rank ASC;
```

### 查看任务失败情况
```bash
# 查看后台任务的警告和错误日志
docker-compose logs app | grep "\[Async\]" | grep -E "(warning|error|failed)"
```

## 配置调整

### 修改交易记录获取数量
在代码中修改 `limit` 参数：
```python
# 默认获取50笔
asyncio.create_task(_fetch_token_transactions_async(address, limit=50))

# 修改为获取100笔
asyncio.create_task(_fetch_token_transactions_async(address, limit=100))
```

### 禁用后台任务
如果不需要自动获取安全信息和交易记录，可以注释掉相关代码：
```python
# 注释这两行即可
# asyncio.create_task(_fetch_token_security_async(address))
# asyncio.create_task(_fetch_token_transactions_async(address, limit=50))
```

## 最佳实践

### 1. 监控API配额
由于会创建大量后台任务，建议监控Birdeye API的使用配额：
- 每小时20个trending代币 × 2个API = 40个API调用
- 如果获取多页，API调用会成倍增加

### 2. 数据清理
定期清理旧数据，避免数据库膨胀：
```sql
-- 清理30天前的交易记录
DELETE FROM birdeye_token_transactions
WHERE blockUnixTime < UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 30 DAY));
```

### 3. 分批处理
如果热门代币数量很多，可以考虑分批创建后台任务：
```python
# 每10个代币一批
for i in range(0, len(response.data.tokens), 10):
    batch = response.data.tokens[i:i+10]
    for token in batch:
        asyncio.create_task(_fetch_token_security_async(token.address))
        asyncio.create_task(_fetch_token_transactions_async(token.address, limit=50))
    await asyncio.sleep(1)  # 批次之间延迟
```

## 总结

通过这个增强功能：
1. ✅ **自动化**: 无需手动获取安全信息和交易记录
2. ✅ **高效**: 异步并发执行，节省时间
3. ✅ **完整**: 热门代币数据更加完整和丰富
4. ✅ **智能**: 自动判断存在并更新
5. ✅ **可靠**: 独立错误处理，不影响主流程

这使得您可以获得更全面的热门代币分析数据！🚀

