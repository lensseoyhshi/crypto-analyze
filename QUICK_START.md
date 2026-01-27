# 快速开始指南

## 安装步骤

### 方式一：使用安装脚本（推荐）

```bash
# 1. 给脚本添加执行权限
chmod +x install.sh

# 2. 运行安装脚本
./install.sh
```

### 方式二：手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件
```

## 配置数据库

### 1. 编辑 .env 文件

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=crypto_db
DB_CHARSET=utf8mb4
```

### 2. 创建数据库

```sql
CREATE DATABASE crypto_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

### 3. 创建表

在项目根目录下有两个表的完整 SQL，执行这些 SQL 创建表：

- `smart_wallets` - 聪明钱数据表
- `birdeye_wallet_transactions` - 钱包交易记录表

## 运行示例

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 运行示例代码
python examples.py
```

## 在你的项目中使用

### 示例 1：创建和查询钱包

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
        is_smart_money=1
    )
    created = dao.create(wallet)
    
    # 查询钱包
    found = dao.get_by_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
    print(found.to_dict())
```

### 示例 2：记录交易

```python
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO
from datetime import datetime

with BirdeyeWalletTransactionDAO() as dao:
    tx_data = {
        "tx_hash": "5YNmS1R9nNSC...",
        "block_time": datetime.now(),
        "from": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "main_action": "SWAP",
        "fee": 5000,
    }
    tx = dao.create_from_dict(tx_data)
```

### 示例 3：统计分析

```python
from dao.smart_wallet_dao import SmartWalletDAO
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO

wallet_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"

# 获取钱包信息
with SmartWalletDAO() as dao:
    wallet = dao.get_by_address(wallet_address)
    print(f"7日盈利: {wallet.pnl_7d}")
    print(f"胜率: {wallet.win_rate_7d}%")

# 获取交易统计
with BirdeyeWalletTransactionDAO() as dao:
    stats = dao.get_wallet_statistics(wallet_address, days=7)
    print(f"总交易数: {stats['total_transactions']}")
    print(f"成功率: {stats['success_rate']:.2f}%")
```

## 常见问题

### Q1: 连接数据库失败

**A**: 检查 `.env` 文件配置是否正确，确保数据库服务已启动。

### Q2: 导入模块失败

**A**: 确保虚拟环境已激活，并且所有依赖已安装。

### Q3: 表不存在

**A**: 确保已执行 SQL 创建表语句。

### Q4: from 字段报错

**A**: 使用 `from_address` 而不是 `from`（Python 关键字）。

## 目录结构说明

```
crypto-analyze/
├── config/          # 数据库配置
├── models/          # ORM 实体模型
├── dao/             # 数据访问层
├── examples.py      # 完整示例代码
├── requirements.txt # Python 依赖
└── .env            # 环境变量配置
```

## 技术栈

- Python 3.8+
- SQLAlchemy 2.0
- PyMySQL
- MySQL 5.7+

## 更多帮助

查看 `README.md` 获取完整文档。
查看 `examples.py` 获取更多使用示例。
