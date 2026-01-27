# 项目概览

## 📁 项目结构

```
crypto-analyze/
│
├── 📄 __init__.py              # 包初始化，导出主要接口
├── 📄 requirements.txt         # Python 依赖列表
├── 📄 .env.example            # 环境变量示例
├── 📄 .gitignore              # Git 忽略文件
├── 📄 README.md               # 完整项目文档
├── 📄 QUICK_START.md          # 快速开始指南
├── 📄 install.sh              # 自动安装脚本
├── 📄 database_schema.sql     # 数据库表创建脚本
├── 📄 test_connection.py      # 数据库连接测试
├── 📄 examples.py             # 完整使用示例
│
├── 📁 config/                 # 配置模块
│   ├── __init__.py
│   └── database.py            # 数据库配置和连接管理
│
├── 📁 models/                 # ORM 实体模型
│   ├── __init__.py
│   ├── smart_wallet.py        # SmartWallet 实体
│   └── birdeye_transaction.py # BirdeyeWalletTransaction 实体
│
└── 📁 dao/                    # 数据访问层
    ├── __init__.py
    ├── smart_wallet_dao.py    # SmartWallet 数据访问对象
    └── birdeye_transaction_dao.py  # BirdeyeWalletTransaction 数据访问对象
```

## 🚀 快速开始（3 步）

### 1️⃣ 安装

```bash
chmod +x install.sh && ./install.sh
```

### 2️⃣ 配置

编辑 `.env` 文件，配置数据库连接：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=crypto_db
```

### 3️⃣ 创建表并运行

```bash
# 导入数据库表
mysql -u root -p crypto_db < database_schema.sql

# 测试连接
python test_connection.py

# 运行示例
python examples.py
```

## 📚 核心功能

### SmartWallet（聪明钱数据表）

- ✅ 钱包信息管理（地址、链类型、余额）
- ✅ 多维度标签（聪明钱、KOL、巨鲸、狙击手）
- ✅ 工具追踪（Trojan、BullX、Photon、Axiom）
- ✅ 7日/30日数据统计（PNL、ROI、胜率、交易量）
- ✅ 高级查询和筛选
- ✅ 统计分析功能

### BirdeyeWalletTransaction（交易记录表）

- ✅ 交易记录完整存储
- ✅ JSON 字段支持（余额变动、合约标签、代币流转）
- ✅ 基于交易哈希的去重机制
- ✅ 多维度查询（钱包、时间、动作类型）
- ✅ 交易统计和分析
- ✅ 动作分布分析

## 💡 核心类说明

### 配置类

| 类名 | 文件 | 说明 |
|------|------|------|
| `DatabaseConfig` | `config/database.py` | 数据库配置管理 |
| `Base` | `config/database.py` | SQLAlchemy 声明式基类 |

### 实体类

| 类名 | 文件 | 说明 |
|------|------|------|
| `SmartWallet` | `models/smart_wallet.py` | 聪明钱实体 |
| `BirdeyeWalletTransaction` | `models/birdeye_transaction.py` | 交易记录实体 |

### DAO 类

| 类名 | 文件 | 说明 |
|------|------|------|
| `SmartWalletDAO` | `dao/smart_wallet_dao.py` | 钱包数据访问 |
| `BirdeyeWalletTransactionDAO` | `dao/birdeye_transaction_dao.py` | 交易数据访问 |

## 🔧 主要方法一览

### SmartWalletDAO

**基础操作**
- `create(wallet)` - 创建钱包
- `get_by_id(id)` - 根据 ID 查询
- `get_by_address(address)` - 根据地址查询
- `update(id, data)` - 更新钱包
- `delete(id)` - 删除钱包
- `batch_create(wallets)` - 批量创建

**高级查询**
- `get_smart_money_wallets()` - 查询聪明钱
- `get_kol_wallets()` - 查询 KOL
- `get_top_performers_7d()` - 7日榜单
- `get_top_performers_30d()` - 30日榜单
- `filter_wallets()` - 多条件筛选

**统计分析**
- `count_all()` - 总数统计
- `count_by_type()` - 分类统计

### BirdeyeWalletTransactionDAO

**基础操作**
- `create_from_dict(data)` - 从字典创建
- `upsert(data)` - 插入或更新
- `get_by_tx_hash(hash)` - 根据哈希查询
- `update(id, data)` - 更新交易
- `delete(id)` - 删除交易
- `batch_create(transactions)` - 批量创建

**查询方法**
- `get_by_wallet(address)` - 查询钱包交易
- `get_by_wallet_and_time_range()` - 时间范围查询
- `get_by_action(action)` - 按动作类型查询
- `get_recent_transactions(days)` - 最近交易

**统计分析**
- `count_by_wallet(address)` - 钱包交易数
- `get_wallet_statistics(address, days)` - 钱包统计
- `get_action_distribution(address, days)` - 动作分布
- `exists_by_tx_hash(hash)` - 检查是否存在

## 📖 使用示例

### 示例 1：创建钱包

```python
from dao.smart_wallet_dao import SmartWalletDAO
from models.smart_wallet import SmartWallet
from decimal import Decimal

with SmartWalletDAO() as dao:
    wallet = SmartWallet(
        address="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        chain="SOL",
        is_smart_money=1,
        pnl_7d=Decimal("1500.50")
    )
    dao.create(wallet)
```

### 示例 2：查询和筛选

```python
with SmartWalletDAO() as dao:
    # 查询表现最好的钱包
    top = dao.get_top_performers_7d(limit=10)
    
    # 条件筛选
    filtered = dao.filter_wallets(
        is_smart_money=True,
        min_pnl_7d=Decimal("1000.00")
    )
```

### 示例 3：记录交易

```python
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO

with BirdeyeWalletTransactionDAO() as dao:
    tx_data = {
        "tx_hash": "5YNmS1R9...",
        "from": "7xKXtg2CW87...",
        "main_action": "SWAP",
        "fee": 5000,
    }
    dao.upsert(tx_data)  # 如果存在则更新，否则创建
```

### 示例 4：统计分析

```python
with BirdeyeWalletTransactionDAO() as dao:
    # 获取钱包统计
    stats = dao.get_wallet_statistics(wallet_address, days=7)
    print(f"成功率: {stats['success_rate']:.2f}%")
    
    # 获取动作分布
    distribution = dao.get_action_distribution(wallet_address, days=7)
    for action, count in distribution.items():
        print(f"{action}: {count}")
```

## 🛠️ 技术栈

- **语言**: Python 3.8+
- **ORM**: SQLAlchemy 2.0
- **数据库驱动**: PyMySQL
- **数据库**: MySQL 5.7+
- **配置管理**: python-dotenv

## 📝 文件说明

| 文件 | 用途 |
|------|------|
| `README.md` | 完整的项目文档 |
| `QUICK_START.md` | 快速开始指南 |
| `PROJECT_OVERVIEW.md` | 项目概览（本文件） |
| `examples.py` | 完整的使用示例代码 |
| `test_connection.py` | 测试数据库连接 |
| `database_schema.sql` | 建表 SQL 脚本 |
| `install.sh` | 自动安装脚本 |

## ⚠️ 重要提示

1. **from 字段**: 因为 `from` 是 Python 关键字，代码中使用 `from_address`
2. **Decimal 类型**: 金额字段使用 `Decimal` 保证精度
3. **JSON 字段**: 会自动进行序列化/反序列化
4. **时区处理**: 使用 `datetime` 对象，注意时区转换
5. **连接池**: 已配置连接池，支持并发访问

## 📞 获取帮助

- 查看 `examples.py` 了解完整用法
- 运行 `python test_connection.py` 测试连接
- 查看 `README.md` 获取详细文档

## ✅ 下一步

1. ✅ 安装依赖和配置环境
2. ✅ 创建数据库表
3. ✅ 运行 `test_connection.py` 验证
4. ✅ 运行 `examples.py` 学习用法
5. 🚀 开始你的项目开发！

---

**Happy Coding! 🎉**
