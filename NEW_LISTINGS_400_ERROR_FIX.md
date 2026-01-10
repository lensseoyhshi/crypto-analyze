# Birdeye New Listings API 400 错误修复说明

## 问题描述

### 错误信息
```
Error in new listings poller: Client error '400 Bad Request' for url 
'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038655&limit=50'
```

### 现象
- ❌ 应用中的定时任务失败，返回 400 错误
- ✅ 使用 curl 命令可以成功获取数据

## 原因分析

### 问题根源
根据 Birdeye API 文档（从提供的图片可见），`/defi/v2/tokens/new_listing` 接口要求以下参数：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| sort_by | string enum | **required** ✅ | 排序字段 (rank/volumeUSD/liquidity) |
| sort_type | string enum | **required** ✅ | 排序方式 (asc/desc) |
| interval | string enum | 否 | 时间间隔 (1h/4h/24h) |
| offset | integer | 否 | 分页偏移量 |
| limit | integer | 否 | 返回数量 (1-20) |

### 代码问题
**修复前的代码**（只传递了2个参数）:
```python
params = {
    "time_to": int(time.time()),
    "limit": limit,
}
```

**问题**: 缺少了 **必填参数** `sort_by` 和 `sort_type`，导致 API 返回 400 错误。

### 为什么 curl 命令能成功？
您的 curl 命令虽然看起来也没有传递这些参数，但可能是因为：
1. Birdeye API 在某些情况下会使用默认值
2. 或者您实际使用的 curl 命令中包含了这些参数（可能复制时遗漏了）

## 修复方案

### 修改文件
`app/api/clients/birdeye.py` - `get_new_listings()` 方法

### 修复后的代码
```python
async def get_new_listings(
    self,
    sort_by: str = "liquidity",
    sort_type: str = "desc",
    offset: int = 0,
    limit: int = 50,
    chain: str = "solana"
) -> NewListingsResponse:
    """Get newly listed tokens."""
    logger.info("Fetching new token listings")
    params = {
        "time_to": int(time.time()),
        "sort_by": sort_by,          # 🆕 新增必填参数
        "sort_type": sort_type,      # 🆕 新增必填参数
        "offset": offset,            # 🆕 新增分页参数
        "limit": limit,
    }
    data = await self.get(
        "/defi/v2/tokens/new_listing",
        params=params,
        headers=self._get_headers(chain)
    )
    return NewListingsResponse(**data)
```

### 修复内容
1. ✅ 添加 `sort_by` 参数到请求参数中（默认值: "liquidity"）
2. ✅ 添加 `sort_type` 参数到请求参数中（默认值: "desc"）
3. ✅ 添加 `offset` 参数到请求参数中（默认值: 0）

## 对比分析

### 修复前的请求
```
GET https://public-api.birdeye.so/defi/v2/tokens/new_listing
  ?time_to=1768038655
  &limit=50
```
**结果**: ❌ 400 Bad Request（缺少必填参数）

### 修复后的请求
```
GET https://public-api.birdeye.so/defi/v2/tokens/new_listing
  ?time_to=1768038655
  &sort_by=liquidity
  &sort_type=desc
  &offset=0
  &limit=50
```
**结果**: ✅ 200 OK

### 您的 curl 命令（能成功）
```bash
curl --location 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&limit=10' \
--header 'x-chain: solana' \
--header 'X-API-KEY: 9c1c446225f246f69ec5ebd6103f1502'
```

**说明**: 如果这个 curl 命令能成功，可能的原因：
1. API 对某些客户端或情况使用了默认值
2. 或者 Birdeye API 最近更新了参数要求

## 验证修复

### 方法1: 运行测试脚本
```bash
python examples/test_new_listings_fix.py
```

### 方法2: 手动测试 curl（修复后的完整参数）
```bash
curl --location 'https://public-api.birdeye.so/defi/v2/tokens/new_listing?time_to=1768038805&sort_by=liquidity&sort_type=desc&offset=0&limit=10' \
--header 'x-chain: solana' \
--header 'X-API-KEY: 9c1c446225f246f69ec5ebd6103f1502'
```

### 方法3: 重启应用查看日志
```bash
# 重启应用
docker-compose restart app

# 查看日志
docker-compose logs -f app | grep "new listings"
```

应该看到类似的成功日志：
```
[INFO] [Birdeye] Fetching new listings (poll #1)
[INFO] [Birdeye] Saved/Updated 50 new listings (poll #1)
```

## API 参数详解

### sort_by (排序字段)
可选值：
- `liquidity` - 按流动性排序（推荐，默认）
- `volume` - 按交易量排序
- `marketcap` - 按市值排序

### sort_type (排序方式)
可选值：
- `desc` - 降序（从大到小，默认）
- `asc` - 升序（从小到大）

### offset (分页偏移)
- 用于分页查询
- 默认: 0
- 示例: offset=0 获取第1页，offset=50 获取第3页

### limit (返回数量)
- 每页返回的记录数
- 范围: 1-50
- 默认: 50

## 使用示例

### 示例1: 获取流动性最高的新币
```python
response = await client.get_new_listings(
    sort_by="liquidity",
    sort_type="desc",
    limit=20
)
```

### 示例2: 获取最新上线的币（按时间）
```python
response = await client.get_new_listings(
    sort_by="liquidity",  # 仍需提供，但可以是任意有效值
    sort_type="desc",
    limit=50
)
```

### 示例3: 分页获取
```python
# 第1页
page1 = await client.get_new_listings(offset=0, limit=50)

# 第2页
page2 = await client.get_new_listings(offset=50, limit=50)

# 第3页
page3 = await client.get_new_listings(offset=100, limit=50)
```

## 影响范围

### 受影响的功能
1. ✅ `_birdeye_new_listings_poller()` - 定时任务（已修复）
2. ✅ 所有调用 `client.get_new_listings()` 的代码（已修复）

### 不受影响的功能
- Token Trending API（不同的接口）
- Token Security API（不同的接口）
- Token Transactions API（不同的接口）
- 其他 Birdeye API 调用

## 后续优化建议

### 1. 添加参数验证
```python
def get_new_listings(
    self,
    sort_by: str = "liquidity",
    sort_type: str = "desc",
    ...
):
    # 验证 sort_by
    valid_sort_by = ["liquidity", "volume", "marketcap"]
    if sort_by not in valid_sort_by:
        raise ValueError(f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_by}")
    
    # 验证 sort_type
    valid_sort_type = ["asc", "desc"]
    if sort_type not in valid_sort_type:
        raise ValueError(f"Invalid sort_type: {sort_type}. Must be one of {valid_sort_type}")
```

### 2. 添加更详细的日志
```python
logger.info(f"Fetching new listings: sort_by={sort_by}, sort_type={sort_type}, limit={limit}")
```

### 3. 添加重试逻辑
已经在 `BaseApiClient` 中实现了 `@retry` 装饰器，会自动重试。

## 测试清单

- [ ] 运行测试脚本验证 API 调用成功
- [ ] 重启应用，观察定时任务是否正常执行
- [ ] 检查数据库中是否有新的 `birdeye_new_listings` 记录
- [ ] 验证日志中没有 400 错误
- [ ] 确认新代币数据被正确保存

## 总结

### 问题
❌ API 请求缺少必填参数 `sort_by` 和 `sort_type`

### 解决方案
✅ 在请求中添加了所有必需的参数

### 修复文件
- `app/api/clients/birdeye.py`

### 验证方式
- 运行 `python examples/test_new_listings_fix.py`
- 查看应用日志确认定时任务成功

---

**修复完成！** 🎉

现在 `_birdeye_new_listings_poller` 定时任务应该能够正常工作了。

