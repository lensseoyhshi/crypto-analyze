# 钱包平均持仓时间计算工具使用指南

## 功能说明

这个工具用于计算和更新 `smart_wallets` 表中的 `avg_hold_time_7d` 字段（7日平均持仓时间）。

### 计算逻辑

1. **获取交易记录**: 查询钱包最近7天的交易记录（排除系统地址 `11111111111111111111111111111111`）
2. **提取代币操作**: 从交易的 `token_transfers` 和 `balance_change` 字段中提取每个代币的买入/卖出操作
3. **计算持仓时间**: 对每个代币，计算第一次买入到最后一次卖出的时间差
4. **取中位数**: 将所有代币的持仓时间取中位数作为平均持仓时间
5. **更新数据库**: 将计算结果更新到 `smart_wallets.avg_hold_time_7d` 字段

## 使用方式

### 1. 更新所有钱包

```bash
python update_hold_time.py all
```

这会遍历 `smart_wallets` 表中的所有钱包，逐个计算并更新持仓时间。

### 2. 测试模式（推荐首次使用）

```bash
python update_hold_time.py test
```

只处理前 10 个钱包，用于测试功能是否正常。

### 3. 更新单个钱包

```bash
python update_hold_time.py 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
```

只更新指定地址的钱包。

### 4. 默认模式（无参数）

```bash
python update_hold_time.py
```

等同于测试模式，处理前 10 个钱包。

## 输出示例

```
======================================================================
开始计算并更新钱包平均持仓时间（最近 7 天）
======================================================================

1. 获取所有钱包...

处理第 1 到 100 个钱包...
  处理钱包: 7xKXtg2CW8...
    找到 45 笔交易
    涉及 8 个代币
      代币 EPjFWdd5Au... 持仓时间: 3600 秒 (1.00 小时)
      代币 So11111111... 持仓时间: 7200 秒 (2.00 小时)
      代币 4k3Dyjzvzp... 持仓时间: 10800 秒 (3.00 小时)
    ✓ 平均持仓时间（中位数）: 7200 秒 (2.00 小时)
    ✓ 已更新到数据库

======================================================================
计算完成！
总处理: 100 个钱包
成功更新: 85 个钱包
======================================================================
```

## 工作原理

### 1. 交易查询

```sql
SELECT * FROM birdeye_wallet_transactions 
WHERE `from` = '钱包地址' 
AND `to` != '11111111111111111111111111111111'
AND block_time >= '7天前'
ORDER BY block_time ASC
```

### 2. 代币操作识别

从 `token_transfers` 字段解析：
- 如果 `to` 是当前钱包 → **买入**
- 如果 `from` 是当前钱包 → **卖出**

从 `balance_change` 字段解析：
- 金额为正 → **买入**
- 金额为负 → **卖出**

### 3. 持仓时间计算

```
持仓时间 = 最后一次卖出时间 - 第一次买入时间
```

### 4. 中位数计算

```python
avg_hold_time = median([token1_hold_time, token2_hold_time, ...])
```

## 注意事项

### ⚠️ 数据要求

1. **交易记录完整性**: 需要有完整的买入和卖出记录
2. **JSON 格式正确**: `token_transfers` 和 `balance_change` 必须是有效的 JSON
3. **时间字段有效**: `block_time` 不能为空

### ⚠️ 性能考虑

1. **批量处理**: 每次处理 100 个钱包，避免内存溢出
2. **数据库连接**: 使用连接池，支持长时间运行
3. **异常处理**: 单个钱包失败不影响其他钱包

### ⚠️ 边界情况

以下情况无法计算持仓时间：

- 没有交易记录
- 只有买入没有卖出（或相反）
- 交易记录少于 2 笔
- JSON 解析失败

## 集成到定时任务

### 使用 Cron（Linux/Mac）

```bash
# 每天凌晨 2 点更新
0 2 * * * cd /path/to/crypto-analyze && /path/to/venv/bin/python update_hold_time.py all >> /var/log/hold_time.log 2>&1
```

### 使用 Python 定时任务

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from update_hold_time import HoldTimeCalculator

def update_job():
    with HoldTimeCalculator() as calculator:
        calculator.update_all_wallets_hold_time(days=7)

scheduler = BlockingScheduler()
scheduler.add_job(update_job, 'cron', hour=2)  # 每天凌晨2点
scheduler.start()
```

## 扩展功能

### 计算 30 日持仓时间

修改代码中的 `days` 参数：

```python
# 在 HoldTimeCalculator 类中添加方法
def update_all_wallets_hold_time_30d(self):
    """更新 30 日平均持仓时间"""
    # ... 类似逻辑，但更新 avg_hold_time_30d 字段
```

### 自定义代币过滤

在 `extract_token_operations` 方法中添加过滤逻辑：

```python
# 跳过某些代币
if token in ['SOL', 'USDC', 'USDT']:
    continue
```

## 常见问题

### Q1: 为什么有些钱包无法计算？

**A**: 可能原因：
- 交易记录不完整
- 只有单向交易（只买入或只卖出）
- 时间范围内没有完成的交易对

### Q2: 计算速度慢？

**A**: 优化建议：
- 减少查询的天数
- 使用批量更新
- 添加数据库索引

### Q3: 中位数为什么比平均值更好？

**A**: 中位数可以：
- 避免极端值的影响
- 更真实反映典型持仓时间
- 减少异常交易的干扰

### Q4: 如何验证计算结果？

**A**: 手动验证：

```python
from update_hold_time import HoldTimeCalculator

with HoldTimeCalculator() as calc:
    # 查看某个钱包的详细计算过程
    calc.update_single_wallet_hold_time('钱包地址')
```

## 代码结构

```python
HoldTimeCalculator
├── get_wallet_transactions()          # 获取交易记录
├── extract_token_operations()         # 提取代币操作
├── calculate_token_hold_time()        # 计算单个代币持仓时间
├── calculate_wallet_avg_hold_time()   # 计算钱包平均持仓时间
├── update_all_wallets_hold_time()     # 批量更新所有钱包
└── update_single_wallet_hold_time()   # 更新单个钱包
```

## 监控和日志

建议添加日志记录：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hold_time_update.log'),
        logging.StreamHandler()
    ]
)
```

## 性能数据（参考）

- **单个钱包**: ~1-3 秒
- **100 个钱包**: ~2-5 分钟
- **1000 个钱包**: ~20-50 分钟

实际时间取决于：
- 交易记录数量
- 数据库性能
- 网络延迟

## 相关文件

- `update_hold_time.py` - 主脚本
- `dao/smart_wallet_dao.py` - 钱包数据访问
- `dao/birdeye_transaction_dao.py` - 交易数据访问
- `models/smart_wallet.py` - 钱包实体
- `models/birdeye_transaction.py` - 交易实体
