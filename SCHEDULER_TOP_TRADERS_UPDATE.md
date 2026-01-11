# Scheduler Top Traders 集成更新说明

## 📝 修改概述

将 `_birdeye_top_traders_poller` 从独立定时任务改为由 `_birdeye_token_trending_poller` 触发的异步任务。

## 🔄 主要修改

### 1. 注释独立的 Top Traders 定时任务

**文件**: `app/services/scheduler.py`

**修改位置**: 第 35 行

```python
# 修改前
(_birdeye_top_traders_poller(), "Birdeye top traders", settings.BIRDEYE_TOP_TRADERS_INTERVAL),

# 修改后
# (_birdeye_top_traders_poller(), "Birdeye top traders", settings.BIRDEYE_TOP_TRADERS_INTERVAL),  # 现在由 trending poller 触发
```

**说明**: 不再将 top traders 作为独立的定时任务启动，而是由 trending poller 在发现热门代币时触发。

---

### 2. 新增异步 Top Traders 获取函数

**文件**: `app/services/scheduler.py`

**新增位置**: 第 133-163 行

```python
async def _fetch_token_top_traders_async(token_address: str, time_range: str = "24h", limit: int = 10):
    """
    Asynchronously fetch token top traders and save to database.
    If tokenAddress + owner combination exists in database, update it; otherwise insert new record.
    
    Args:
        token_address: Token address to query
        time_range: Time range for top traders (e.g., "24h", "7d")
        limit: Number of top traders to fetch
    """
```

**功能说明**:
- 异步获取指定代币的 top traders 数据
- 使用 `save_or_update_top_traders_batch` 方法保存数据
- 如果 `tokenAddress + owner` 组合已存在，则更新记录
- 如果不存在，则插入新记录
- 自动处理异常和资源清理

---

### 3. 在 Token Trending Poller 中触发 Top Traders 获取

**文件**: `app/services/scheduler.py`

**修改位置**: 第 575-586 行

```python
# Create background tasks for each token
# 为每个热门代币创建后台任务：获取安全信息、交易记录和 top traders
for token in response.data.tokens:
    address = token.address
    # 异步获取代币安全信息
    asyncio.create_task(_fetch_token_security_async(address))
    # 异步获取代币交易记录
    asyncio.create_task(_fetch_token_transactions_async(address, limit=50))
    # 异步获取代币 top traders（根据 tokenAddress 查询）
    asyncio.create_task(_fetch_token_top_traders_async(address, time_range="24h", limit=10))

logger.info(f"[Birdeye] Created background tasks (security, transactions, top traders) for {len(response.data.tokens)} tokens")
```

**执行流程**:
1. Token trending poller 获取热门代币列表
2. 保存热门代币数据到数据库
3. 为每个热门代币创建 3 个后台异步任务：
   - 获取代币安全信息
   - 获取代币交易记录
   - **获取代币 top traders** (新增)

---

## 🎯 优势

### ✅ 资源优化
- 不需要独立的定时任务轮询所有 tracked tokens
- 只为热门代币获取 top traders 数据
- 减少不必要的 API 调用

### ✅ 数据时效性
- 热门代币的 top traders 数据会在发现时立即获取
- 不需要等待独立的定时任务周期

### ✅ 灵活性
- 可以根据代币的热度动态调整获取频率
- trending poller 的执行频率控制整体节奏

### ✅ 数据完整性
- 使用 `save_or_update_top_traders_batch` 确保数据不重复
- `tokenAddress + owner` 唯一性约束自动处理

---

## 🔍 数据库操作说明

### Repository 方法
使用 `BirdeyeRepository.save_or_update_top_traders_batch()` 方法

### 判断逻辑
```python
# 检查记录是否存在
query = select(BirdeyeTopTrader).where(
    BirdeyeTopTrader.tokenAddress == token_address,
    BirdeyeTopTrader.owner == trader.owner
)
```

### 操作结果
- **存在**: 更新该记录的所有字段 (volume, trade, volumeBuy, volumeSell, etc.)
- **不存在**: 插入新记录

---

## 📊 执行示例

### 日志输出
```
[Birdeye] Fetching token trending (poll #1)
[Birdeye] Page 1: Saved/Updated 20 trending tokens
[Birdeye] Created background tasks (security, transactions, top traders) for 20 tokens
[Async] Fetching top traders for So11111111111111111111111111111111111111112
[Async] Saved/Updated 10 top traders for So11111111111111111111111111111111111111112
...
```

### 性能指标
- 每个热门代币获取 10 个 top traders
- 每批次 20 个代币 = 200 个 top traders
- 使用异步并发，不阻塞主流程

---

## ⚙️ 配置参数

### Top Traders 参数
```python
time_range="24h"  # 时间范围：24小时
limit=10          # 每个代币获取前 10 个 top traders
```

### 可调整项
- `time_range`: 可以改为 "7d", "30d" 等
- `limit`: 可以调整为 20, 50 等（需考虑 API 限制）

---

## 🚀 测试建议

### 运行方式
```bash
# 启动服务（top traders 会自动随 trending 任务执行）
python -m app.main
```

### 验证数据
```sql
-- 查看最近保存的 top traders
SELECT * FROM birdeye_top_traders 
ORDER BY id DESC 
LIMIT 20;

-- 查看某个代币的 top traders
SELECT * FROM birdeye_top_traders 
WHERE tokenAddress = 'YOUR_TOKEN_ADDRESS'
ORDER BY volume DESC;

-- 查看数据更新情况（同一 tokenAddress + owner 只有一条记录）
SELECT tokenAddress, owner, COUNT(*) as count
FROM birdeye_top_traders
GROUP BY tokenAddress, owner
HAVING count > 1;  -- 应该返回空结果
```

---

## 📌 注意事项

1. **API 调用频率**: 确保不超过 Birdeye API 的速率限制
2. **数据库连接**: 异步任务会创建多个数据库会话，注意连接池配置
3. **错误处理**: 单个代币的 top traders 获取失败不会影响其他代币
4. **日志监控**: 关注 `[Async]` 标记的日志，了解异步任务执行情况

---

## 🔗 相关文件

- `app/services/scheduler.py` - 调度器主文件
- `app/repositories/birdeye_repository.py` - Top traders 数据库操作
- `app/api/clients/birdeye.py` - Birdeye API 客户端
- `app/db/models.py` - BirdeyeTopTrader 模型定义

---

## ✅ 完成状态

- ✅ 注释独立的 top traders poller
- ✅ 创建异步 top traders 获取函数
- ✅ 在 trending poller 中集成 top traders 获取
- ✅ 使用 save_or_update 方法确保数据不重复
- ✅ 完善日志输出
- ✅ 异常处理和资源清理

---

**更新时间**: 2026-01-11
**版本**: v1.0

