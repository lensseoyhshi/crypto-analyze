# 🎉 GMGN 数据采集系统 - 完整文档

## 📋 系统架构

```
Chrome Extension (拦截API)
        ↓
Python Flask Server (接收数据)
        ↓
Database (存储)
   ├── smart_wallets (实时最新数据)
   └── smart_wallets_snapshot (每日快照历史)
```

---

## 🗂️ 数据库设计

### 1. `smart_wallets` - 实时数据表
**用途**：保存每个钱包的最新数据，用于实时查询
**特点**：
- 每个钱包只有一条记录
- 每次采集会更新数据
- 适合查询当前TOP钱包

### 2. `smart_wallets_snapshot` - 历史快照表
**用途**：保存每日快照，用于历史分析
**特点**：
- 每个钱包每天一条记录
- 可以回溯历史数据
- 适合分析趋势变化

---

## 📦 文件说明

### Models
```
models/
├── smart_wallet.py          # 实时数据表 Model
└── smart_wallet_snapshot.py # 快照表 Model
```

### DAO
```
dao/
├── smart_wallet_dao.py          # 实时数据操作
└── smart_wallet_snapshot_dao.py # 快照数据操作
```

### Chrome Extension
```
chrome-extension/
├── manifest.json   # 扩展配置
├── inject.js       # 注入脚本（页面主世界，拦截请求）
├── content.js      # 内容脚本（接收消息，转发到background）
├── background.js   # 后台脚本（发送到Python服务器）
├── popup.html      # 弹出窗口UI
└── popup.js        # 弹出窗口逻辑
```

### Python Server
```
gmgn_server.py      # Flask 服务器
start_gmgn.sh       # 启动脚本
test_dao.py         # 测试脚本
```

---

## 🚀 使用指南

### 1. 启动 Python 服务器

```bash
./start_gmgn.sh
```

或手动启动：
```bash
source .venv/bin/activate
python gmgn_server.py
```

### 2. 安装 Chrome 扩展

1. 打开 `chrome://extensions/`
2. 开启"开发者模式"
3. 点击"加载已解压的扩展程序"
4. 选择 `chrome-extension` 文件夹

### 3. 访问 GMGN 开始采集

访问 https://gmgn.ai，切换到不同的标签（聪明钱、KOL等），数据会自动采集。

---

## 📊 数据字段说明

### 标签字段
- `is_smart_money`: 聪明钱
- `is_kol`: KOL
- `is_whale`: 巨鲸
- `is_sniper`: 狙击手
- `is_hot_followed`: 热门追踪
- `is_hot_remarked`: 热门备注

### 工具字段
- `uses_trojan`: 使用 Trojan
- `uses_bullx`: 使用 BullX
- `uses_photon`: 使用 Photon
- `uses_axiom`: 使用 Axiom
- `uses_bot`: 使用通用Bot

### 性能指标（支持 1D/7D/30D）
- `pnl_Xd`: X日盈利(USD)
- `pnl_Xd_roi`: X日收益率(%)
- `win_rate_Xd`: X日胜率(%)
- `tx_count_Xd`: X日交易次数
- `volume_Xd`: X日交易量(USD)
- `net_inflow_Xd`: X日净流入(USD)
- `avg_hold_time_Xd`: X日平均持仓时长(秒)

---

## 💡 常用查询示例

### 1. 查询TOP聪明钱

```python
from dao.smart_wallet_dao import SmartWalletDAO
from config.database import get_session

session = get_session()
dao = SmartWalletDAO(session)

# 查询TOP 100 聪明钱（按7日盈利排序）
smart_wallets = dao.get_all_smart_money(limit=100)

for w in smart_wallets:
    print(f"{w.address}: ${float(w.pnl_7d):,.2f}")

session.close()
```

### 2. 查询钱包历史趋势

```python
from dao.smart_wallet_snapshot_dao import SmartWalletSnapshotDAO
from config.database import get_session

session = get_session()
dao = SmartWalletSnapshotDAO(session)

# 查询某个钱包最近30天的数据
address = "4gLZztSiwUnQtbqzc6sJrTjfgA5RCweHgokiLgEWPn3u"
history = dao.get_history_by_address(address, days=30)

for snap in history:
    print(f"{snap.snapshot_date}: ${float(snap.pnl_7d):,.2f}")

session.close()
```

### 3. 查询某天的TOP钱包

```python
from datetime import date
from dao.smart_wallet_snapshot_dao import SmartWalletSnapshotDAO
from config.database import get_session

session = get_session()
dao = SmartWalletSnapshotDAO(session)

# 查询2026年1月31日的TOP钱包
snapshot_date = date(2026, 1, 31)
top_wallets = dao.get_top_wallets_by_date(snapshot_date, limit=100)

for w in top_wallets:
    print(f"{w.address}: ${float(w.pnl_7d):,.2f}")

session.close()
```

### 4. 统计信息

```python
from dao.smart_wallet_dao import SmartWalletDAO
from config.database import get_session

session = get_session()
dao = SmartWalletDAO(session)

stats = dao.get_statistics()
print(stats)
# {
#   'total_wallets': 1500,
#   'smart_money_count': 800,
#   'kol_count': 50,
#   'avg_pnl_7d': 12345.67,
#   'avg_win_rate_7d': 65.5,
#   'max_pnl_7d': 150000.00,
#   'min_pnl_7d': -5000.00
# }

session.close()
```

---

## 🧪 测试

运行测试脚本验证数据库操作：

```bash
source .venv/bin/activate
python test_dao.py
```

你会看到：
- 📊 当前数据统计
- 🏆 TOP 钱包列表
- 📅 快照数量
- 📈 历史数据

---

## 🔄 自动化运行

### 方案 1：终端后台运行

```bash
nohup ./start_gmgn.sh > gmgn.log 2>&1 &
```

### 方案 2：使用 supervisor

创建 `/etc/supervisor/conf.d/gmgn.conf`:
```ini
[program:gmgn_server]
command=/path/to/.venv/bin/python /path/to/gmgn_server.py
directory=/path/to/crypto-analyze
autostart=true
autorestart=true
user=your_user
```

### 方案 3：systemd 服务

创建 `/etc/systemd/system/gmgn.service`:
```ini
[Unit]
Description=GMGN Data Collection Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/crypto-analyze
ExecStart=/path/to/.venv/bin/python gmgn_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📈 数据分析建议

### 1. 每日分析
- 对比今天和昨天的TOP钱包变化
- 分析新上榜钱包
- 统计平均盈利趋势

### 2. 周度分析
- 连续7天TOP的钱包（稳定盈利）
- 7日胜率最高的钱包
- 交易量最大的钱包

### 3. 工具分析
- 使用Trojan的钱包盈利情况
- 不同工具的胜率对比
- 工具与盈利的相关性

### 4. 标签分析
- 聪明钱 vs 普通钱包对比
- KOL的表现
- 巨鲸的交易特点

---

## 🐛 故障排查

### 问题1：扩展无法拦截数据
**检查**：
1. F12 -> Console，是否有 "🔍 GMGN 拦截器已注入到页面"
2. F12 -> Console，是否有 "🎯 ✅ XHR 拦截到钱包API"
3. 重新加载扩展（chrome://extensions/）

### 问题2：Python服务器未收到数据
**检查**：
1. 服务器是否运行（http://localhost:8899/api/health）
2. 防火墙是否阻止
3. Chrome控制台是否有CORS错误

### 问题3：数据库插入失败
**检查**：
1. 数据库表是否已创建
2. 数据库连接配置是否正确
3. 查看服务器终端的详细错误信息

---

## 📞 技术支持

遇到问题时，提供以下信息：
1. Python 服务器的终端输出
2. Chrome 控制台（F12 -> Console）的日志
3. 数据库错误信息

---

## 🎊 功能特性总结

✅ **自动采集** - Chrome扩展自动拦截GMGN API  
✅ **实时存储** - 数据实时写入数据库  
✅ **历史快照** - 每日快照，可回溯历史  
✅ **双表设计** - 实时表+快照表，查询灵活  
✅ **标签识别** - 自动识别聪明钱、KOL等标签  
✅ **多维数据** - 支持1D/7D/30D数据  
✅ **工具标记** - 识别Trojan、Photon等工具  
✅ **防重复** - 相同数据不重复插入  
✅ **易扩展** - 支持添加新字段和功能  

祝使用愉快！🚀
