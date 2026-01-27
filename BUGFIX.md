# 问题修复说明

## 遇到的问题

在本地运行时遇到以下错误：

```
TypeError: Additional arguments should be named <dialectname>_<argument>, got 'comment'
```

以及：

```
sqlalchemy.exc.ConstraintColumnNotFoundError: Can't create Index on table 'birdeye_wallet_transactions': no column named 'from_address' is present.
```

## 问题原因

### 1. Index 不支持 comment 参数
SQLAlchemy 的 `Index` 对象不支持直接传入 `comment` 参数。Index 的注释应该在创建索引时在数据库层面添加，而不是在 ORM 模型中。

### 2. 索引列名错误
在 `BirdeyeWalletTransaction` 模型中：
- Python 属性名是 `from_address`（因为 `from` 是 Python 关键字）
- 数据库列名是 `from`（通过 `mapped_column('from', ...)` 指定）
- 索引应该使用数据库列名 `from`，而不是 Python 属性名 `from_address`

## 解决方案

修改了 `models/birdeye_transaction.py` 文件：

```python
# 修改前（错误）
__table_args__ = (
    Index('uk_tx_hash', 'tx_hash', unique=True, comment='防止重复存储同一笔交易'),
    Index('idx_from', 'from_address', comment='用于查询指定钱包的历史'),
    Index('idx_block_time', 'block_time', comment='用于按时间排序查询'),
    Index('idx_block_number', 'block_number'),
    {'comment': 'Birdeye钱包历史交易记录表'}
)

# 修改后（正确）
__table_args__ = (
    Index('uk_tx_hash', 'tx_hash', unique=True),
    Index('idx_from', 'from'),  # 使用数据库中的实际列名
    Index('idx_block_time', 'block_time'),
    Index('idx_block_number', 'block_number'),
    {'comment': 'Birdeye钱包历史交易记录表'}
)
```

## 验证修复

运行测试脚本验证所有模块正常：

```bash
python test_imports.py
```

输出：
```
✓ 数据库配置                                    [config.database]
✓ SmartWallet 实体                           [models.smart_wallet]
✓ BirdeyeWalletTransaction 实体              [models.birdeye_transaction]
✓ SmartWallet DAO                          [dao.smart_wallet_dao]
✓ BirdeyeWalletTransaction DAO             [dao.birdeye_transaction_dao]
✓ 持仓时间计算工具                                 [update_hold_time]

✓ 所有模块导入成功！
```

## 现在可以正常使用

所有功能现在都可以正常使用了：

```bash
# 1. 测试数据库连接
python test_connection.py

# 2. 运行示例
python examples.py

# 3. 测试持仓时间计算
python update_hold_time.py test

# 4. 更新所有钱包的持仓时间
python update_hold_time.py all
```

## 相关文件

- ✅ `models/birdeye_transaction.py` - 已修复
- ✅ `test_imports.py` - 新增测试脚本
- ✅ 所有其他文件保持不变

## 注意事项

如果将来需要在索引上添加注释，应该在创建表的 SQL 中添加，而不是在 SQLAlchemy 的 ORM 模型中。例如：

```sql
CREATE INDEX idx_from ON birdeye_wallet_transactions (`from`) COMMENT '用于查询指定钱包的历史';
```

或者使用 MySQL 特定的语法：

```python
Index('idx_from', 'from', mysql_comment='用于查询指定钱包的历史')
```

但为了保持跨数据库兼容性，建议不在代码中添加索引注释。
