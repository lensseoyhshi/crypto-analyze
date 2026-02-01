# GMGN 多标签监听说明

## 📋 概述

系统已配置为监听并保存GMGN的四种类型的钱包数据：
1. **聪明钱 (Smart Degen)**
2. **知名KOL (Renowned)**
3. **热门追踪 (Top Followed)**
4. **热门备注 (Top Renamed)**

## 🔗 监听的API地址

所有API都是同一个接口，只是通过`tag`参数区分：

```
基础URL: https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d

1. 聪明钱：    ?tag=smart_degen
2. 知名KOL：   ?tag=renowned
3. 热门追踪：  ?tag=top_followed
4. 热门备注：  ?tag=top_renamed
```

## 🏷️ 标签映射规则

系统会根据API返回的`tags`字段自动映射到数据库字段：

| GMGN Tag | 数据库字段 | 说明 |
|----------|-----------|------|
| `smart_degen` | `is_smart_money = 1` | 聪明钱标识 |
| `renowned` | `is_kol = 1` | KOL/知名钱包 |
| `top_followed` | `is_hot_followed = 1` | 热门追踪 |
| `top_renamed` | `is_hot_remarked = 1` | 热门备注 |
| `whale` | `is_whale = 1` | 巨鲸 |
| `sniper` | `is_sniper = 1` | 狙击手 |
| `trojan` | `uses_trojan = 1` | 使用Trojan工具 |
| `bullx` | `uses_bullx = 1` | 使用BullX工具 |
| `photon` | `uses_photon = 1` | 使用Photon工具 |
| `axiom` | `uses_axiom = 1` | 使用Axiom工具 |
| `bot` | `uses_bot = 1` | 使用Bot脚本 |

**注意**：一个钱包可能同时拥有多个标签，系统会自动设置所有对应的字段。

## 🚀 使用方法

### 方法1：使用Chrome扩展（推荐）

1. **启动后端服务器**
   ```bash
   cd /Users/shizhenqiang/code/Python/jiaoyi/crypto/crypto-analyze
   python3 gmgn_server.py
   ```
   服务器会在 `http://localhost:8899` 启动

2. **安装Chrome扩展**
   - 打开Chrome浏览器
   - 访问 `chrome://extensions/`
   - 开启"开发者模式"
   - 点击"加载已解压的扩展程序"
   - 选择项目中的 `chrome-extension` 文件夹

3. **访问GMGN网站并切换标签**
   
   访问以下任意页面，扩展会自动捕获数据：
   
   - 聪明钱：https://gmgn.ai/?chain=sol&tab=smart_degen
   - 知名KOL：访问gmgn.ai后手动切换到"知名"标签
   - 热门追踪：访问gmgn.ai后手动切换到"热门追踪"标签
   - 热门备注：访问gmgn.ai后手动切换到"热门备注"标签

4. **查看数据**
   
   扩展会自动：
   - 拦截GMGN的API请求
   - 提取钱包数据
   - 发送到本地服务器
   - 保存到数据库（`smart_wallets`和`smart_wallets_snapshot`表）

### 方法2：使用Playwright爬虫

```bash
python3 gmgn_monitor.py
```

需要修改 `gmgn_monitor.py` 中的 `TARGET_URL` 来监听不同的标签。

## 📊 数据存储

数据会存储到两个表：

### 1. smart_wallets（实时表）
- 每个钱包地址只保存一条最新记录
- 更新频率：每次抓取时更新（UPSERT操作）
- 用途：查询最新的钱包状态

### 2. smart_wallets_snapshot（快照表）
- 每个钱包每天一条记录
- 存储历史快照，用于分析趋势
- 主键：(address, snapshot_date)

## 🧪 测试

运行测试脚本验证标签映射：

```bash
python3 test_tags_mapping.py
```

## 📝 示例数据

假设GMGN API返回以下钱包：

```json
{
  "address": "ABC123...",
  "tags": ["smart_degen", "renowned", "trojan"],
  "pnl_7d": 50000,
  "win_rate_7d": 0.75
}
```

系统会将其映射为：

```python
{
  "address": "ABC123...",
  "is_smart_money": 1,    # 因为有 smart_degen
  "is_kol": 1,            # 因为有 renowned
  "uses_trojan": 1,       # 因为有 trojan
  "pnl_7d": 50000,
  "win_rate_7d": 75.0     # 转换为百分比
}
```

## ⚠️ 注意事项

1. **标签的来源**：标签是由GMGN API返回的，不是通过URL的tag参数判断的
2. **多标签**：一个钱包可能同时拥有多个标签（如既是聪明钱又是KOL）
3. **数据去重**：实时表通过address去重，快照表通过(address, date)去重
4. **Chrome扩展自动捕获所有tag**：扩展会监听所有`/rank/sol/wallets`接口，无需手动配置

## 🔍 查询示例

### 查询所有聪明钱
```python
from dao.smart_wallet_dao import SmartWalletDAO
from config.database import get_session

session = get_session()
dao = SmartWalletDAO(session)

# 获取聪明钱列表
smart_wallets = dao.get_all_smart_money(limit=100)

for wallet in smart_wallets:
    print(f"{wallet.address}: {wallet.pnl_7d}")
```

### 查询所有KOL
```python
kol_wallets = dao.get_all_kol(limit=50)
```

### 查询热门追踪
```python
hot_followed = dao.get_hot_followed(limit=50)
```

### 查询热门备注
```python
hot_remarked = dao.get_hot_remarked(limit=50)
```

## 📈 统计信息

```python
stats = dao.get_statistics()
print(f"总钱包数: {stats['total_wallets']}")
print(f"聪明钱数: {stats['smart_money_count']}")
print(f"KOL数: {stats['kol_count']}")
```
