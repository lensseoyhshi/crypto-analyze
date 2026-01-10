# 🔒 正确的 SSL 和网络配置指南

## ❌ 不推荐的做法

```python
# ❌ 禁用 SSL 验证（不安全！）
verify=False

# ❌ 禁用代理（可能导致无法连接）
trust_env=False
```

## ✅ 正确的做法

### 1. 修复 SSL 证书问题（一劳永逸）

#### 步骤 1：安装 certifi

```bash
pip install --upgrade certifi
```

#### 步骤 2：运行 Python 证书安装脚本

macOS 上 Python 需要手动安装证书：

```bash
# 方法 1：运行官方安装脚本
# 找到你的 Python 版本对应的路径
/Applications/Python\ 3.10/Install\ Certificates.command

# 方法 2：如果上面的路径不存在，手动安装
pip install --upgrade certifi
python3 << 'EOF'
import certifi
import ssl
import os

# 显示证书路径
print(f"Certifi 证书位置: {certifi.where()}")

# 创建链接（如果需要）
cert_path = certifi.where()
if os.path.exists(cert_path):
    print("✅ 证书已正确安装")
else:
    print("❌ 证书未找到，请重新安装 certifi")
EOF
```

#### 步骤 3：验证证书安装

```bash
# 测试 1：检查证书路径
python3 -c "import certifi; print(certifi.where())"

# 测试 2：检查 SSL 配置
python3 -c "import ssl; print(ssl.get_default_verify_paths())"

# 测试 3：实际测试 HTTPS 连接
python3 << 'EOF'
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("https://api.dexscreener.com/token-boosts/top/v1")
            print(f"✅ 成功! 状态码: {resp.status_code}")
        except Exception as e:
            print(f"❌ 失败: {e}")

asyncio.run(test())
EOF
```

---

### 2. 检查和配置代理（如果需要）

#### 检查当前代理设置

```bash
# 查看系统代理
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"
echo "http_proxy: $http_proxy"
echo "https_proxy: $https_proxy"

# 查看 macOS 系统代理
networksetup -getwebproxy Wi-Fi
networksetup -getsecurewebproxy Wi-Fi
```

#### 如果不需要代理

```bash
# 临时清除代理（当前终端会话）
unset HTTP_PROXY
unset HTTPS_PROXY
unset http_proxy
unset https_proxy

# 或者在 ~/.zshrc 或 ~/.bash_profile 中添加
export HTTP_PROXY=""
export HTTPS_PROXY=""
```

#### 如果需要代理

在项目的 `.env` 文件中配置：

```bash
# 配置代理
HTTP_PROXY=http://proxy-server:port
HTTPS_PROXY=http://proxy-server:port

# 如果代理需要认证
# HTTP_PROXY=http://username:password@proxy-server:port
# HTTPS_PROXY=http://username:password@proxy-server:port

# 不走代理的地址
NO_PROXY=localhost,127.0.0.1,.local
```

---

### 3. 解决连接超时问题

#### 方法 1：检查防火墙

```bash
# macOS 防火墙设置
# 系统偏好设置 → 安全性与隐私 → 防火墙

# 确保 Python 被允许接受传入连接
```

#### 方法 2：检查网络连接

```bash
# 测试 DNS
nslookup api.dexscreener.com

# 测试连接
ping -c 3 api.dexscreener.com

# 测试 HTTPS
curl -I https://api.dexscreener.com/token-boosts/top/v1

# 如果 curl 成功，问题在于 Python 配置
```

#### 方法 3：增加超时时间

在 `app/core/config.py` 或代码中：

```python
# 增加超时时间
timeout = 60  # 从 30 秒增加到 60 秒
```

---

### 4. 完整的测试脚本

保存为 `test_connection.py`：

```python
#!/usr/bin/env python3
"""测试网络连接和 SSL 配置"""

import httpx
import asyncio
import certifi
import ssl


def check_ssl_config():
    """检查 SSL 配置"""
    print("=" * 60)
    print("SSL 配置检查")
    print("=" * 60)
    
    # 1. certifi 证书路径
    print(f"Certifi 证书: {certifi.where()}")
    
    # 2. SSL 默认路径
    paths = ssl.get_default_verify_paths()
    print(f"OpenSSL CA 文件: {paths.openssl_cafile}")
    print(f"OpenSSL CA 路径: {paths.openssl_capath}")
    
    # 3. 环境变量
    import os
    print(f"\nSSL_CERT_FILE: {os.getenv('SSL_CERT_FILE', 'Not set')}")
    print(f"REQUESTS_CA_BUNDLE: {os.getenv('REQUESTS_CA_BUNDLE', 'Not set')}")


async def test_https_connection():
    """测试 HTTPS 连接"""
    print("\n" + "=" * 60)
    print("测试 HTTPS 连接（启用 SSL 验证）")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        # 使用默认配置（启用 SSL 验证）
        async with httpx.AsyncClient(
            timeout=30.0,
            verify=True  # ← 启用 SSL 验证
        ) as client:
            print(f"正在连接: {url}")
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            print(f"\n✅ 连接成功!")
            print(f"状态码: {response.status_code}")
            print(f"返回数据: {len(data)} 个代币")
            
            if data:
                print(f"\n第一个代币: {data[0].get('description')}")
            
            return True
            
    except httpx.ConnectTimeout:
        print("\n❌ 连接超时")
        print("可能原因:")
        print("  1. 网络问题")
        print("  2. 代理配置不正确")
        print("  3. 防火墙阻止")
        return False
        
    except ssl.SSLError as e:
        print(f"\n❌ SSL 错误: {e}")
        print("\n解决方案:")
        print("  1. 运行: pip install --upgrade certifi")
        print("  2. 运行证书安装脚本:")
        print("     /Applications/Python 3.X/Install Certificates.command")
        return False
        
    except Exception as e:
        print(f"\n❌ 其他错误: {e}")
        return False


async def main():
    """运行所有测试"""
    check_ssl_config()
    success = await test_https_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过! 可以正常使用了。")
    else:
        print("❌ 测试失败，请按照上述提示修复。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

运行测试：

```bash
python3 test_connection.py
```

---

## 📋 完整的修复流程

### 第 1 步：修复 SSL 证书

```bash
# 1. 升级 certifi
pip install --upgrade certifi

# 2. 安装 Python 证书（macOS）
/Applications/Python\ 3.10/Install\ Certificates.command

# 3. 验证
python3 -c "import certifi; print(certifi.where())"
```

### 第 2 步：清理代理设置（如果不需要）

```bash
# 在 ~/.zshrc 添加
export HTTP_PROXY=""
export HTTPS_PROXY=""

# 然后
source ~/.zshrc
```

### 第 3 步：测试连接

```bash
# 使用 curl 测试
curl https://api.dexscreener.com/token-boosts/top/v1

# 使用 Python 测试
python3 examples/simple_demo.py
```

### 第 4 步：启动项目

```bash
# 启动项目
uvicorn app.main:app --reload
```

---

## 🎯 总结

| 问题 | 正确的解决方案 | ❌ 错误的做法 |
|------|---------------|-------------|
| SSL 错误 | 安装 certifi 证书 | 禁用 SSL 验证 |
| 连接超时 | 检查网络/代理配置 | 禁用代理 |
| 代理问题 | 正确配置代理地址 | trust_env=False |

**记住：永远不要在生产环境禁用 SSL 验证！** 🔒

---

## 💡 如果还是不行

运行诊断脚本：

```bash
python3 examples/network_diagnostic.py
```

然后把输出结果告诉我，我们一起找到问题！

