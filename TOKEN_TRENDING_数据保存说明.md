# Token Trending 数据保存说明

## 问题：为什么 birdeye_token_trending 表没有数据？

### 原因分析

默认情况下，`BIRDEYE_TOKEN_TRENDING_INTERVAL` 配置为 **3600秒（1小时）**。这意味着：

1. **应用启动后**，token trending 后台任务会立即启动
2. **但是第一次数据抓取**要等待 1 小时后才会执行
3. 之后每隔 1 小时执行一次

### 解决方案

#### 方案 1: 修改配置文件（推荐用于测试）

在 `app/core/config.py` 中修改默认间隔时间：

```python
# 从 3600 秒（1小时）改为 60 秒（1分钟）用于测试
BIRDEYE_TOKEN_TRENDING_INTERVAL: int = Field(default=60, description="Seconds between token trending fetches")
```

#### 方案 2: 使用环境变量

在启动应用前设置环境变量：

```bash
# Linux/Mac
export BIRDEYE_TOKEN_TRENDING_INTERVAL=60

# 或者在启动命令中
BIRDEYE_TOKEN_TRENDING_INTERVAL=60 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 方案 3: 手动测试脚本（立即查看效果）

运行测试脚本立即抓取并保存数据：

```bash
# 使用虚拟环境
source .venv/bin/activate

# 运行测试脚本
python examples/test_trending_save.py
```

这个脚本会：
- 立即从 Birdeye API 抓取 trending 数据
- 保存到 `birdeye_token_trending` 表
- 验证数据是否保存成功
- 显示数据库中的记录

## 后台任务启动确认

检查应用启动日志，应该能看到：

```
INFO - Started Birdeye token trending (interval: 3600s)
INFO - Started 6 background tasks
```

## 数据流程

```
启动应用
   ↓
启动后台任务 (_birdeye_token_trending_poller)
   ↓
等待 BIRDEYE_TOKEN_TRENDING_INTERVAL 秒
   ↓
调用 Birdeye API 获取 trending 数据
   ↓
分页抓取（每页20条，最多50页）
   ↓
保存到 birdeye_token_trending 表
   ↓
为每个 token 创建后台任务：
   - 获取 token security
   - 获取 token transactions
   ↓
等待下一个周期
```

## 验证数据

### 方法 1: 使用测试脚本
```bash
python examples/test_trending_save.py
```

### 方法 2: 直接查询数据库
```sql
-- 查看总记录数
SELECT COUNT(*) FROM birdeye_token_trending;

-- 查看最近的记录
SELECT rank, symbol, name, price, marketcap, created_at 
FROM birdeye_token_trending 
ORDER BY rank 
LIMIT 10;

-- 查看最新更新时间
SELECT MAX(created_at) as last_update 
FROM birdeye_token_trending;
```

### 方法 3: 查看应用日志
```bash
# 日志中会显示
[Birdeye] Fetching token trending (poll #1)
[Birdeye] Page 1: Saved/Updated 20 trending tokens
[Birdeye] Created background tasks for 20 tokens
[Birdeye] Completed trending fetch: Total saved/updated 20 tokens (poll #1)
```

## 建议的配置

### 开发/测试环境
```python
BIRDEYE_TOKEN_TRENDING_INTERVAL: int = Field(default=60)  # 1分钟
```

### 生产环境
```python
BIRDEYE_TOKEN_TRENDING_INTERVAL: int = Field(default=1800)  # 30分钟
# 或
BIRDEYE_TOKEN_TRENDING_INTERVAL: int = Field(default=3600)  # 1小时
```

## 注意事项

1. **API 限制**: Birdeye API 可能有请求频率限制，不要设置太短的间隔
2. **数据库压力**: 每次会抓取多页数据并创建大量后台任务
3. **启动等待**: 后台任务会等待一个完整的间隔时间后才执行第一次抓取
4. **数据更新**: 使用 `save_or_update` 策略，相同 address 的记录会被更新而不是重复插入

## 立即触发一次抓取（不等待）

如果想在应用启动时立即执行一次抓取，可以修改 `_birdeye_token_trending_poller` 函数：

```python
async def _birdeye_token_trending_poller():
	"""Fetch trending tokens from Birdeye and save to database with pagination."""
	client = BirdeyeClient()
	poll_count = 0
	
	try:
		while True:
			poll_count += 1
			try:
				logger.info(f"[Birdeye] Fetching token trending (poll #{poll_count})")
				
				# ... 数据抓取逻辑 ...
				
			except Exception as e:
				logger.error(f"[Birdeye] Error in token trending poller: {str(e)}", exc_info=True)
			
			# 将 sleep 移到循环开始前，第一次立即执行
			if poll_count == 1:
				logger.info(f"[Birdeye] First poll completed, waiting {settings.BIRDEYE_TOKEN_TRENDING_INTERVAL}s for next poll")
			
			await asyncio.sleep(settings.BIRDEYE_TOKEN_TRENDING_INTERVAL)
```

或者更简单的方式：将 sleep 从循环末尾移到开头（在执行完第一次后再开始等待）。

