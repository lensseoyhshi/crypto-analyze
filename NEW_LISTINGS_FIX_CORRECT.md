# Birdeye New Listings API 400 错误修复（正确版本）

## 问题描述

### 错误信息
```
Error in new listings poller: Client error '400 Bad Request' for url 
'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038655&limit=50'
```

### 现象
- ❌ 应用中的定时任务失败，返回 400 错误
- ✅ 使用 curl 命令（limit=10）可以成功获取数据

## 真正的原因 🎯

### API 参数限制
根据 Birdeye API 文档，`/defi/v2/tokens/new_listing` 接口的实际参数为：

| 参数名 | 类型 | 范围/说明 | 默认值 |
|--------|------|-----------|--------|
| time_to | integer | 1 to 10000000000 | - |
| limit | integer | **1 to 20** ⚠️ | 10 |
| meme_platform_enabled | boolean | true/false | false |

### 问题根源
代码中使用了 `limit=50`，但 **API 最大只允许 limit=20**！

```python
# ❌ 错误：超出限制
response = await client.get_new_listings(limit=50)
```

这就是为什么您的 curl 命令能成功（使用 limit=10），而代码失败（使用 limit=50）。

## 修复方案

### 修改文件
1. `app/api/clients/birdeye.py` - 更正 API 参数和限制
2. `app/services/scheduler.py` - 调整调用参数

### 修复详情

#### 1. 更正 API 客户端方法

**修复前**（错误的参数）:
```python
async def get_new_listings(
    self,
    sort_by: str = "liquidity",      # ❌ 不存在的参数
    sort_type: str = "desc",         # ❌ 不存在的参数
    offset: int = 0,                 # ❌ 不存在的参数
    limit: int = 50,                 # ❌ 超出范围（最大20）
    chain: str = "solana"
):
    params = {
        "time_to": int(time.time()),
        "sort_by": sort_by,          # ❌ API不支持
        "sort_type": sort_type,      # ❌ API不支持
        "offset": offset,            # ❌ API不支持
        "limit": limit,              # ❌ 值太大
    }
```

**修复后**（正确的参数）:
```python
async def get_new_listings(
    self,
    limit: int = 20,                 # ✅ 默认最大值20
    meme_platform_enabled: bool = False,  # ✅ 正确的参数
    chain: str = "solana"
):
    # 确保 limit 在有效范围内 (1-20)
    limit = max(1, min(limit, 20))   # ✅ 强制限制在1-20之间
    
    params = {
        "time_to": int(time.time()),
        "limit": limit,              # ✅ 符合API要求
        "meme_platform_enabled": meme_platform_enabled,  # ✅ 正确参数
    }
```

#### 2. 更新调度器调用

**修复前**:
```python
response = await client.get_new_listings(limit=50)  # ❌ 超出限制
```

**修复后**:
```python
response = await client.get_new_listings(limit=20)  # ✅ 符合API限制
```

## API 参数说明

### time_to
- **类型**: integer
- **范围**: 1 到 10000000000
- **说明**: 使用 Unix 时间戳指定结束时间（秒）
- **示例**: `1726704000` (2024-01-10)

### limit
- **类型**: integer
- **范围**: **1 到 20** ⚠️（重要！）
- **默认值**: 10
- **说明**: 限制返回的记录数
- **注意**: 如果传递超过20的值，API会返回400错误

### meme_platform_enabled
- **类型**: boolean
- **可选值**: true / false
- **默认值**: false
- **说明**: 是否接收来自 meme 平台（如 pump.fun）的新币
- **仅支持**: Solana 链

## 对比验证

### 为什么 curl 命令能成功？

您的 curl 命令：
```bash
curl 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&limit=10'
```
- ✅ `limit=10` 在有效范围内（1-20）

代码中的请求（修复前）：
```
https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038655&limit=50
```
- ❌ `limit=50` 超出范围（>20）

### 修复后的请求
```
https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038655&limit=20&meme_platform_enabled=false
```
- ✅ `limit=20` 符合API要求
- ✅ 包含所有正确参数

## 测试验证

### 方法1: 使用正确的 curl 命令测试

**成功的请求（limit=10）**:
```bash
curl --location 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&limit=10' \
--header 'x-chain: solana' \
--header 'X-API-KEY: 9c1c446225f246f69ec5ebd6103f1502'
```

**失败的请求（limit=50）**:
```bash
curl --location 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&limit=50' \
--header 'x-chain: solana' \
--header 'X-API-KEY: 9c1c446225f246f69ec5ebd6103f1502'
```
应该会返回 400 错误。

**修复后的请求（limit=20）**:
```bash
curl --location 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&limit=20&meme_platform_enabled=false' \
--header 'x-chain: solana' \
--header 'X-API-KEY: 9c1c446225f246f69ec5ebd6103f1502'
```

### 方法2: 运行测试脚本

创建测试脚本：
```python
# examples/test_new_listings_correct.py
import asyncio
from app.api.clients.birdeye import BirdeyeClient

async def test():
    client = BirdeyeClient()
    try:
        # 测试正确的参数
        print("Testing with limit=20...")
        response = await client.get_new_listings(limit=20)
        print(f"✅ Success! Got {len(response.data.items)} listings")
        
        # 测试不同的 meme_platform_enabled
        print("\nTesting with meme_platform_enabled=true...")
        response2 = await client.get_new_listings(
            limit=15,
            meme_platform_enabled=True
        )
        print(f"✅ Success! Got {len(response2.data.items)} listings (with meme)")
        
    finally:
        await client.close()

asyncio.run(test())
```

运行测试：
```bash
python examples/test_new_listings_correct.py
```

### 方法3: 重启应用验证

```bash
# 重启应用
docker-compose restart app

# 查看日志
docker-compose logs -f app | grep "new listings"
```

应该看到成功日志：
```
[INFO] [Birdeye] Fetching new listings (limit=20, meme_platform_enabled=False)
[INFO] [Birdeye] Saved/Updated 20 new listings (poll #1)
```

## 分页处理

由于 API 限制每次最多返回20条，如果需要获取更多数据，需要多次调用：

```python
async def fetch_multiple_pages():
    """获取多页新币数据"""
    client = BirdeyeClient()
    all_listings = []
    
    try:
        # 第一次调用
        response1 = await client.get_new_listings(limit=20)
        all_listings.extend(response1.data.items)
        
        # 可以根据时间戳继续获取
        if response1.data.items:
            last_time = response1.data.items[-1].liquidityAddedAt
            # 使用最后一个币的时间作为下一次查询的 time_to
            # (需要转换为 Unix 时间戳)
        
        print(f"Total fetched: {len(all_listings)} listings")
        
    finally:
        await client.close()
```

## 使用建议

### 1. 基本使用（获取最新20个）
```python
response = await client.get_new_listings(limit=20)
```

### 2. 获取较少数量
```python
response = await client.get_new_listings(limit=10)
```

### 3. 包含 meme 平台币
```python
response = await client.get_new_listings(
    limit=20,
    meme_platform_enabled=True  # 包含 pump.fun 等平台
)
```

### 4. 安全的参数传递（自动限制）
```python
# 即使传入超过20，也会自动限制为20
response = await client.get_new_listings(limit=100)  
# 实际使用: limit=20
```

## 影响范围

### 修改的代码
1. ✅ `app/api/clients/birdeye.py` - 更正 API 参数
2. ✅ `app/services/scheduler.py` - 调整 limit 从50到20

### 受影响的功能
1. ✅ `_birdeye_new_listings_poller()` - 定时任务（已修复）
2. ✅ 每次获取的新币数量从50减少到20
3. ✅ 移除了不存在的参数（sort_by, sort_type, offset）
4. ✅ 添加了正确的参数（meme_platform_enabled）

### 性能影响
- **修复前**: 试图获取50个（失败）
- **修复后**: 成功获取20个
- **建议**: 如需更多数据，可以增加调用频率

## 错误原因总结

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 400 Bad Request | `limit=50` 超出范围 | 改为 `limit=20` |
| 参数错误 | 使用了不存在的参数 | 移除 sort_by, sort_type, offset |
| 缺少参数 | 未传递 meme_platform_enabled | 添加该参数（默认false）|

## 最终修复

**文件1**: `app/api/clients/birdeye.py`
```python
async def get_new_listings(
    self,
    limit: int = 20,  # ✅ 符合API限制（1-20）
    meme_platform_enabled: bool = False,  # ✅ 正确的参数
    chain: str = "solana"
) -> NewListingsResponse:
    limit = max(1, min(limit, 20))  # ✅ 强制限制
    params = {
        "time_to": int(time.time()),
        "limit": limit,
        "meme_platform_enabled": meme_platform_enabled,
    }
    # ... rest of code
```

**文件2**: `app/services/scheduler.py`
```python
# Line 206
response = await client.get_new_listings(limit=20)  # ✅ 符合限制
```

---

## 总结

### 问题
❌ `limit=50` 超出 API 允许的最大值（20）

### 解决方案
✅ 将 `limit` 改为 `20`，并移除错误的参数

### 验证
- [x] 更正 API 参数
- [x] 添加范围限制
- [x] 更新调度器调用
- [x] 创建测试脚本

**修复完成！** 🎉

现在 `_birdeye_new_listings_poller` 定时任务应该能够正常工作了。

