# 🔒 SSL 证书错误解决方案

## ❌ 错误信息

```
[SSL] unknown error (_ssl.c:997)
```

这是 macOS 上常见的 SSL 证书验证问题。

---

## ✅ 解决方案（按推荐顺序）

### 方案 1：安装 Python SSL 证书（最推荐 ⭐）

macOS 的 Python 不会自动使用系统证书，需要手动安装：

```bash
# 方法 1：运行 Python 自带的证书安装脚本
/Applications/Python\ 3.10/Install\ Certificates.command

# 或者如果是 Python 3.11
/Applications/Python\ 3.11/Install\ Certificates.command

# 方法 2：使用 pip 安装/更新 certifi
pip install --upgrade certifi

# 方法 3：使用 pip3
pip3 install --upgrade certifi
```

**然后重启应用即可。**

---

### 方案 2：在 .env 中临时禁用 SSL 验证（仅开发环境）

**⚠️ 警告：仅在本地开发环境使用，不要在生产环境禁用 SSL！**

在 `.env` 文件中添加：

```bash
# 临时禁用 SSL 验证（仅开发）
VERIFY_SSL=false
```

然后重启应用：

```bash
# 停止应用（Ctrl+C）
# 重新启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

你会看到警告信息：
```
⚠️  SSL verification is DISABLED. This should only be used in development!
```

---

### 方案 3：使用 Homebrew 的 Python

Homebrew 安装的 Python 通常证书配置更好：

```bash
# 安装 Homebrew Python
brew install python@3.11

# 使用 Homebrew Python 创建虚拟环境
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 方案 4：手动配置证书路径

```bash
# 安装 certifi
pip install certifi

# 获取证书路径
python3 -c "import certifi; print(certifi.where())"

# 设置环境变量（添加到 .env 文件）
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE=$(python3 -c "import certifi; print(certifi.where())")
```

---

## 🔍 检查 SSL 配置

### 1. 检查 certifi 是否安装

```bash
python3 -c "import certifi; print(certifi.where())"
```

应该输出类似：
```
/path/to/site-packages/certifi/cacert.pem
```

### 2. 测试 SSL 连接

```python
import ssl
import certifi

# 检查默认证书位置
print("Default CA bundle:", ssl.get_default_verify_paths())

# 检查 certifi 证书
print("Certifi CA bundle:", certifi.where())
```

### 3. 测试 HTTPS 请求

```python
import httpx

# 测试连接
async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.dexscreener.com/token-boosts/top/v1")
        print("Status:", resp.status_code)

import asyncio
asyncio.run(test())
```

---

## 📋 完整的 .env 配置示例

```bash
# 应用配置
APP_NAME=crypto-analyze
DEBUG=True

# 数据库
DATABASE_URL=mysql+aiomysql://root:12345678@localhost:3306/crypto_analyze

# API 密钥
BIRDEYE_API_KEY=9c1c446225f246f69ec5ebd6103f1502

# SSL 配置（可选）
# 开发环境可以临时禁用，生产环境必须为 true 或不设置
VERIFY_SSL=false

# 轮询间隔
DEXSCREENER_FETCH_INTERVAL=6
BIRDEYE_NEW_LISTINGS_INTERVAL=60
```

---

## 🎯 推荐流程

### 1️⃣ 首先尝试方案 1（安装证书）

```bash
# 安装/更新 certifi
pip install --upgrade certifi

# 重启应用
uvicorn app.main:app --reload
```

### 2️⃣ 如果还不行，使用方案 2（临时禁用）

在 `.env` 中添加：
```bash
VERIFY_SSL=false
```

### 3️⃣ 正常工作后，记得修复证书问题

禁用 SSL 只是临时方案，建议最终还是要正确配置证书。

---

## ❓ 常见问题

### Q: 为什么会出现这个错误？

**A:** macOS 的 Python（特别是从官网下载的）不会自动使用系统的证书库，需要安装 `certifi` 包。

### Q: 禁用 SSL 验证安全吗？

**A:** 
- ✅ 本地开发：可以临时使用
- ❌ 生产环境：绝对不要禁用！会有中间人攻击风险

### Q: Homebrew 安装的 Python 会有这个问题吗？

**A:** 通常不会，Homebrew 的 Python 证书配置更好。

### Q: 我应该用哪个方案？

**A:** 
1. 首选：安装证书（方案 1）
2. 临时：禁用 SSL（方案 2）- 仅开发环境
3. 长期：使用 Homebrew Python（方案 3）

---

## 🔒 安全提醒

**⚠️ 重要提示：**
- 禁用 SSL 验证会让你的应用容易受到中间人攻击
- 只在本地开发环境临时使用
- 生产环境**必须**启用 SSL 验证
- 修复证书问题后，记得移除 `VERIFY_SSL=false`

---

## 📚 相关链接

- [Python SSL 文档](https://docs.python.org/3/library/ssl.html)
- [certifi 文档](https://github.com/certifi/python-certifi)
- [HTTPX SSL 配置](https://www.python-httpx.org/advanced/#ssl-certificates)

---

## ✅ 总结

**最快的解决方案：**

```bash
# 1. 安装 certifi
pip install --upgrade certifi

# 2. 如果还不行，在 .env 添加
echo "VERIFY_SSL=false" >> .env

# 3. 重启应用
uvicorn app.main:app --reload
```

**记得：这只是临时方案，最终要正确配置证书！** 🔒

