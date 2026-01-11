# Birdeye Top Traders API 参数更新

## 📋 更新概述

根据 Birdeye API 官方文档，更新 `get_top_traders` 方法的参数，以匹配实际的 API 规范。

## 🔄 主要变更

### 1. 参数名称修正

| 旧参数名 | 新参数名 | 说明 |
|---------|---------|------|
| `time_range` | `time_frame` | 时间范围参数名称修正 |
| `chain` (已删除) | - | 删除未使用的 chain 参数 |

### 2. 新增参数

根据 API 文档添加以下参数：

| 参数名 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `sort_type` | string enum | `"desc"` | 排序方向：`desc` 或 `asc` |
| `sort_by` | string enum | `"volume"` | 排序字段：`volume` 或 `trade` |
| `ui_amount_mode` | string enum | `"scaled"` | Solana 代币数量模式：`raw` 或 `scaled` |

### 3. 参数完整规范

```python
async def get_top_traders(
    token_address: str,           # required - 代币合约地址
    time_frame: str = "24h",      # 时间范围：1m, 5m, 1h, 4h, 24h, 7d, 30d
    sort_type: str = "desc",      # 排序方向：desc (降序) 或 asc (升序)
    sort_by: str = "volume",      # 排序字段：volume (交易量) 或 trade (交易次数)
    offset: int = 0,              # 分页偏移量：0 到 10000
    limit: int = 10,              # 返回数量：1 到 10
    ui_amount_mode: str = "scaled" # 仅 Solana：raw 或 scaled
)
```

## 📝 修改的文件

### 1. API 客户端
**文件**: `app/api/clients/birdeye.py`

```python
# 修改前
async def get_top_traders(
    self,
    token_address: str,
    time_range: str = "24h",
    offset: int = 0,
    limit: int = 10,
    chain: str = "solana"
)

# 修改后
async def get_top_traders(
    self,
    token_address: str,
    time_frame: str = "24h",
    sort_type: str = "desc",
    sort_by: str = "volume",
    offset: int = 0,
    limit: int = 10,
    ui_amount_mode: str = "scaled"
)
```

### 2. 调度器
**文件**: `app/services/scheduler.py`

```python
# 修改前
async def _fetch_token_top_traders_async(token_address: str, time_range: str = "24h", limit: int = 10)
response = await birdeye_client.get_top_traders(token_address, time_range=time_range, limit=limit)

# 修改后
async def _fetch_token_top_traders_async(token_address: str, time_frame: str = "24h", limit: int = 10)
response = await birdeye_client.get_top_traders(token_address, time_frame=time_frame, limit=limit)
```

所有调用处（共 3 处）都已更新：
- 第 146 行：`_fetch_token_top_traders_async` 函数内部
- 第 450 行：`_birdeye_top_traders_poller` 函数内部
- 第 584 行：`_birdeye_token_trending_poller` 创建异步任务时

### 3. 示例代码
**文件**: `examples/api_usage.py`

```python
# 修改前
traders = await client.get_top_traders(token_address, time_range="24h", limit=5)

# 修改后
traders = await client.get_top_traders(token_address, time_frame="24h", limit=5)
```

### 4. 新增 Demo
**文件**: `examples/birdeye_top_traders_demo.py` (新建)

完整的 top traders API 使用示例，包含：
- 按交易量排序
- 按交易次数排序
- 不同时间范围（24h, 7d）
- 完整的参数展示

## 🎯 使用示例

### 基础用法
```python
from app.api.clients.birdeye import BirdeyeClient

client = BirdeyeClient()

# 获取 24 小时内交易量最大的前 10 个交易者
response = await client.get_top_traders(
    token_address="So11111111111111111111111111111111111111112",
    time_frame="24h",
    sort_by="volume",
    sort_type="desc",
    limit=10
)
```

### 按交易次数排序
```python
# 获取交易次数最多的交易者
response = await client.get_top_traders(
    token_address="So11111111111111111111111111111111111111112",
    time_frame="24h",
    sort_by="trade",  # 按交易次数排序
    sort_type="desc",
    limit=10
)
```

### 不同时间范围
```python
# 24 小时
response = await client.get_top_traders(token_address, time_frame="24h")

# 7 天
response = await client.get_top_traders(token_address, time_frame="7d")

# 30 天
response = await client.get_top_traders(token_address, time_frame="30d")
```

### 升序排列（从小到大）
```python
# 获取交易量最小的交易者
response = await client.get_top_traders(
    token_address,
    sort_type="asc",  # 升序
    sort_by="volume",
    limit=10
)
```

## 🚀 运行 Demo

```bash
# 运行新的 top traders demo
python examples/birdeye_top_traders_demo.py

# 运行完整的 API 使用示例
python examples/api_usage.py
```

## 📊 API 参数详细说明

### time_frame (时间范围)
根据 API 文档，支持以下值：
- `1m` - 1 分钟
- `5m` - 5 分钟
- `1h` - 1 小时
- `4h` - 4 小时
- `24h` - 24 小时 (默认)
- `7d` - 7 天
- `30d` - 30 天

### sort_by (排序字段)
- `volume` - 按交易量排序 (默认)
- `trade` - 按交易次数排序

### sort_type (排序方向)
- `desc` - 降序 (从大到小，默认)
- `asc` - 升序 (从小到大)

### ui_amount_mode (数量显示模式)
仅适用于 Solana 链：
- `scaled` - 使用缩放后的数量 (默认)
- `raw` - 使用原始数量

### offset & limit (分页)
- `offset`: 0 到 10000，默认 0
- `limit`: 1 到 10，默认 10

## ✅ 兼容性

### 向后兼容
所有调用此方法的代码都已更新，确保：
- ✅ 不会因为参数名变更导致错误
- ✅ 新参数都有合理的默认值
- ✅ 保持原有功能不变

### 代码审查
以下位置已全部更新：
- ✅ `app/api/clients/birdeye.py` - API 客户端定义
- ✅ `app/services/scheduler.py` - 调度器（3 处调用）
- ✅ `examples/api_usage.py` - 示例代码
- ✅ `examples/birdeye_top_traders_demo.py` - 新增完整 demo

## 🔍 测试验证

### 检查调用点
```bash
# 搜索所有使用 get_top_traders 的地方
grep -r "get_top_traders" --include="*.py" .
```

### 预期结果
所有调用都应该使用 `time_frame` 参数，不再使用 `time_range`。

---

**更新时间**: 2026-01-11
**版本**: v1.1
**状态**: ✅ 已完成并测试

