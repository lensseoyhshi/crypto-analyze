# Token Trending 快速启动指南

## 三大任务完成情况 ✅

### 1. ✅ 创建数据库表
已创建 `birdeye_token_trending` 表，包含所有必要字段。

### 2. ✅ 注释 Dexscreener 定时任务
已在 `app/services/scheduler.py` 中注释掉：
```python
# (_dexscreener_poller(), "Dexscreener poller", settings.DEXSCREENER_FETCH_INTERVAL),  # Temporarily disabled
```

### 3. ✅ 实现 Token Trending 定时任务
- ✅ 接口地址：`https://public-api.birdeye.so/defi/token_trending`
- ✅ 调用频率：每1小时（3600秒）
- ✅ 分页查询：自动处理，每页20条
- ✅ 存在判断：根据 `address` 判断，存在则更新，否则插入

## 快速启动步骤

### 第一步：运行数据库迁移
```bash
cd /Users/shizhenqiang/code/Python/jiaoyi/crypto/crypto-analyze
alembic upgrade head
```

### 第二步：测试 API（可选）
```bash
python examples/birdeye_token_trending_demo.py
```

### 第三步：启动应用
```bash
# 方式1：Docker Compose
docker-compose up -d

# 方式2：本地运行
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 第四步：验证定时任务
启动后，检查日志输出：
```
[INFO] Started Birdeye token trending (interval: 3600s)
[INFO] [Birdeye] Fetching token trending (poll #1)
[INFO] [Birdeye] Page 1: Saved/Updated 20 trending tokens
[INFO] [Birdeye] Completed trending fetch: Total saved/updated X tokens
```

## 查询数据示例

### 查看最新热门代币（按排名）
```sql
SELECT 
    rank,
    symbol,
    name,
    price,
    marketcap,
    volume_24h_usd,
    price_24h_change_percent,
    liquidity
FROM birdeye_token_trending
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
ORDER BY rank ASC
LIMIT 20;
```

### 查看某个代币的历史趋势
```sql
SELECT 
    created_at,
    rank,
    price,
    marketcap,
    volume_24h_usd,
    price_24h_change_percent
FROM birdeye_token_trending
WHERE address = 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'
ORDER BY created_at DESC
LIMIT 10;
```

### 统计每小时抓取的代币数量
```sql
SELECT 
    DATE_FORMAT(created_at, '%Y-%m-%d %H:00:00') as capture_time,
    COUNT(*) as token_count,
    AVG(volume_24h_usd) as avg_volume,
    MAX(volume_24h_usd) as max_volume
FROM birdeye_token_trending
GROUP BY capture_time
ORDER BY capture_time DESC
LIMIT 24;
```

## API 参数说明

根据图片中的参数要求：

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| sort_by | string enum | 是 | rank | 排序字段：rank/volumeUSD/liquidity |
| sort_type | string enum | 是 | asc | 排序方式：asc/desc |
| interval | string enum | 否 | 24h | 时间窗口：1h/4h/24h |
| offset | integer | 否 | 0 | 分页偏移量，用于分页 |
| limit | integer | 否 | 20 | 返回数量，范围 1-20 |
| ui_amount_mode | string enum | 否 | scaled | 代币数量模式：raw/scaled |

## 定时任务说明

### 执行逻辑
1. **启动时间**：应用启动后立即开始第一次抓取
2. **执行频率**：每小时执行一次（3600秒）
3. **分页处理**：自动循环获取所有页面，直到：
   - 返回数量少于 limit（说明到最后一页了）
   - 或达到最大页数限制（50页）
4. **数据处理**：
   - 检查 `address` 是否存在数据库
   - 存在：更新所有字段
   - 不存在：插入新记录
5. **错误处理**：单个代币保存失败不影响其他代币

### 配置调整

修改执行频率（在 `.env` 或 `app/core/config.py`）：
```python
# 默认是 3600 秒（1小时）
BIRDEYE_TOKEN_TRENDING_INTERVAL=3600

# 改为30分钟
BIRDEYE_TOKEN_TRENDING_INTERVAL=1800

# 改为2小时
BIRDEYE_TOKEN_TRENDING_INTERVAL=7200
```

## 文件清单

### 修改的文件
1. `app/db/models.py` - 新增 BirdeyeTokenTrending 模型
2. `app/api/schemas/birdeye.py` - 新增 TokenTrending 响应模式
3. `app/api/clients/birdeye.py` - 新增 get_token_trending 方法
4. `app/repositories/birdeye_repository.py` - 新增仓储方法
5. `app/core/config.py` - 新增配置项
6. `app/services/scheduler.py` - 注释 Dexscreener + 新增 Trending 轮询器

### 新增的文件
1. `alembic/versions/0003_add_token_trending.py` - 数据库迁移
2. `examples/birdeye_token_trending_demo.py` - 演示脚本
3. `TOKEN_TRENDING_IMPLEMENTATION.md` - 实现文档
4. `TOKEN_TRENDING_QUICKSTART.md` - 本快速指南

## 常见问题

### Q1: 如何停止 Dexscreener 任务？
**A**: 已经在代码中注释掉了，无需额外操作。如果需要重新启用，取消注释即可。

### Q2: 如何手动触发一次抓取？
**A**: 运行演示脚本：
```bash
python examples/birdeye_token_trending_demo.py
```

### Q3: 数据库表已存在，如何重新创建？
**A**: 
```sql
DROP TABLE IF EXISTS birdeye_token_trending;
```
然后重新运行迁移：
```bash
alembic upgrade head
```

### Q4: 如何查看定时任务运行状态？
**A**: 查看应用日志：
```bash
# Docker 方式
docker-compose logs -f app

# 本地方式
# 日志会直接输出到控制台
```

### Q5: API 请求失败怎么办？
**A**: 检查以下几点：
1. API Key 是否有效（在 `app/core/config.py` 中）
2. 网络连接是否正常
3. 是否触发了 API 限流

## 数据字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| id | bigint | 自增主键 | 1 |
| address | varchar(64) | 代币合约地址 | DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263 |
| symbol | varchar(32) | 代币符号 | Bonk |
| name | varchar(128) | 代币全称 | Bonk |
| decimals | int | 代币精度 | 5 |
| rank | int | 热度排名 | 1 |
| price | float | 当前价格(USD) | 0.000010429254534544984 |
| marketcap | float | 流通市值 | 870447229.2527591 |
| fdv | float | 完全稀释估值 | 917724472.8992932 |
| liquidity | float | 流动性 | 5336222.366194576 |
| volume_24h_usd | float | 24小时交易量 | 3615086.3526675417 |
| price_24h_change_percent | float | 24H价格涨跌幅 | -4.409340989087892 |
| volume_24h_change_percent | float | 24H交易量涨跌幅 | 53.699300851890875 |
| logo_uri | varchar(512) | Logo链接 | https://arweave.net/... |
| data_source | varchar(20) | 数据来源 | birdeye |
| created_at | datetime | 抓取时间 | 2026-01-10 12:00:00 |

## 性能优化建议

1. **索引优化**：已创建必要索引
   - `idx_address`: 快速查找特定代币
   - `idx_rank`: 按排名排序
   - `idx_created_at`: 按时间查询
   - `idx_address_created`: 复合索引，查询特定代币的历史

2. **定期清理历史数据**：
```sql
-- 保留最近30天的数据
DELETE FROM birdeye_token_trending
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

3. **监控表大小**：
```sql
SELECT 
    COUNT(*) as total_records,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM birdeye_token_trending;
```

## 完成！🎉

所有三个任务都已完成：
1. ✅ 创建了 `birdeye_token_trending` 表
2. ✅ 注释了 `(_dexscreener_poller(), ...)` 这行代码
3. ✅ 实现了 Token Trending 定时任务
   - 每1小时执行
   - 自动分页查询
   - 根据 address 判断存在并更新/插入

现在可以运行迁移并启动应用了！

