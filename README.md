# Crypto Analyze - 加密货币钱包分析系统

这是一个用于分析加密货币钱包的 Python 项目，使用 SQLAlchemy ORM 管理 MySQL 数据库。

## 项目结构

```
crypto-analyze/
├── config/                  # 配置模块
│   ├── __init__.py
│   └── database.py         # 数据库配置和连接管理
├── models/                 # 实体模型
│   ├── __init__.py
│   ├── smart_wallet.py    # SmartWallet 实体类
│   └── birdeye_transaction.py  # BirdeyeWalletTransaction 实体类
├── dao/                    # 数据访问对象
│   ├── __init__.py
│   ├── smart_wallet_dao.py      # SmartWallet DAO
│   └── birdeye_transaction_dao.py  # BirdeyeWalletTransaction DAO
├── examples.py            # 使用示例
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量示例
└── README.md             # 项目文档
```

## 功能特性

### 1. SmartWallet（聪明钱数据表）

- ✅ 完整的 CRUD 操作
- ✅ 支持多种钱包类型标记（聪明钱、KOL、巨鲸、狙击手）
- ✅ 工具使用追踪（Trojan、BullX、Photon、Axiom、Bot）
- ✅ 7日和30日交易数据统计
- ✅ 高级筛选和查询功能

### 2. BirdeyeWalletTransaction（钱包交易记录表）

- ✅ 交易记录的增删改查
- ✅ 支持 JSON 字段存储（余额变动、合约标签、代币流转）
- ✅ 基于交易哈希的 Upsert 操作
- ✅ 按钱包地址、时间范围、动作类型查询
- ✅ 交易统计和分析功能

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=crypto_db
DB_CHARSET=utf8mb4
```

### 3. 创建数据库表

使用提供的 SQL 语句创建表：

```sql
-- 创建 smart_wallets 表
CREATE TABLE `smart_wallets` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `address` varchar(44) NOT NULL DEFAULT '' COMMENT '钱包地址',
  `chain` varchar(10) DEFAULT 'SOL' COMMENT '链类型',
  -- ... 其他字段见原始 SQL
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建 birdeye_wallet_transactions 表
CREATE TABLE `birdeye_wallet_transactions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `tx_hash` varchar(128) NOT NULL COMMENT '交易哈希',
  -- ... 其他字段见原始 SQL
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tx_hash` (`tx_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4. 运行示例

```bash
python examples.py
```

## 使用示例

### SmartWallet 基本操作

```python
from dao.smart_wallet_dao import SmartWalletDAO
from models.smart_wallet import SmartWallet
from decimal import Decimal

# 创建钱包
with SmartWalletDAO() as dao:
    wallet = SmartWallet(
        address="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        chain="SOL",
        balance=Decimal("10.5000"),
        is_smart_money=1,
        pnl_7d=Decimal("1500.50"),
        win_rate_7d=Decimal("75.50")
    )
    created = dao.create(wallet)
    print(f"创建成功: {created.address}")
    
    # 查询钱包
    wallet = dao.get_by_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
    
    # 更新钱包
    updated = dao.update(wallet.id, {
        "balance": Decimal("15.0000"),
        "pnl_7d": Decimal("2000.00")
    })
```

### SmartWallet 高级查询

```python
with SmartWalletDAO() as dao:
    # 查询聪明钱钱包
    smart_wallets = dao.get_smart_money_wallets(limit=10)
    
    # 查询 7 日表现最好的钱包
    top_performers = dao.get_top_performers_7d(limit=10, order_by='pnl_7d')
    
    # 条件筛选
    filtered = dao.filter_wallets(
        is_smart_money=True,
        is_sniper=True,
        min_pnl_7d=Decimal("1000.00"),
        limit=10
    )
    
    # 统计各类型数量
    counts = dao.count_by_type()
    print(f"聪明钱数量: {counts['smart_money']}")
```

### BirdeyeWalletTransaction 操作

```python
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO
from datetime import datetime, timedelta

with BirdeyeWalletTransactionDAO() as dao:
    # 创建交易记录
    tx_data = {
        "tx_hash": "5YNmS1R9nNSCDzb...",
        "block_number": 150000000,
        "block_time": datetime.now(),
        "status": True,
        "from": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "main_action": "SWAP",
        "fee": 5000,
        "balance_change": [{"token": "SOL", "amount": -0.5}],
    }
    created = dao.create_from_dict(tx_data)
    
    # 查询钱包交易历史
    transactions = dao.get_by_wallet(
        "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", 
        limit=10
    )
    
    # 查询时间范围内的交易
    start_time = datetime.now() - timedelta(days=7)
    recent_txs = dao.get_by_wallet_and_time_range(
        wallet_address,
        start_time,
        datetime.now()
    )
    
    # 统计钱包交易数据
    stats = dao.get_wallet_statistics(wallet_address, days=7)
    print(f"总交易数: {stats['total_transactions']}")
    print(f"成功率: {stats['success_rate']:.2f}%")
```

## 核心特性

### 1. 数据库连接管理

- 使用连接池提高性能
- 自动重连机制
- 支持上下文管理器

### 2. ORM 映射

- 使用 SQLAlchemy 2.0 最新语法
- 类型注解支持
- 自动类型转换

### 3. DAO 模式

- 统一的数据访问接口
- 异常处理和事务管理
- 支持批量操作

### 4. JSON 字段处理

- 自动序列化/反序列化
- 支持复杂数据结构

## API 文档

### SmartWalletDAO 主要方法

| 方法 | 说明 |
|------|------|
| `create(wallet)` | 创建钱包 |
| `get_by_id(id)` | 根据 ID 查询 |
| `get_by_address(address)` | 根据地址查询 |
| `update(id, data)` | 更新钱包 |
| `delete(id)` | 删除钱包 |
| `get_smart_money_wallets()` | 查询聪明钱钱包 |
| `get_top_performers_7d()` | 查询 7 日表现最好的钱包 |
| `filter_wallets()` | 多条件筛选 |
| `count_by_type()` | 统计各类型数量 |

### BirdeyeWalletTransactionDAO 主要方法

| 方法 | 说明 |
|------|------|
| `create_from_dict(data)` | 从字典创建交易 |
| `upsert(data)` | 插入或更新交易 |
| `get_by_tx_hash(hash)` | 根据交易哈希查询 |
| `get_by_wallet(address)` | 查询钱包交易历史 |
| `get_by_wallet_and_time_range()` | 按时间范围查询 |
| `get_wallet_statistics()` | 获取钱包统计数据 |
| `get_action_distribution()` | 获取交易动作分布 |

## 注意事项

1. **from 字段处理**：因为 `from` 是 Python 关键字，在代码中使用 `from_address` 字段名，但数据库列名保持为 `from`

2. **Decimal 类型**：金额和百分比字段使用 `Decimal` 类型确保精度

3. **JSON 字段**：`balance_change`、`contract_label`、`token_transfers` 会自动进行 JSON 序列化

4. **时间戳**：支持 datetime 和 Unix 时间戳两种格式

## 依赖项

- Python >= 3.8
- SQLAlchemy == 2.0.25
- PyMySQL == 1.1.0
- python-dotenv == 1.0.0
- cryptography == 41.0.7

## 许可证

MIT License

## 作者

Crypto Analyze Team
