#!/usr/bin/env python3
"""
测试 GMGN 网站访问情况
"""
import socket
import subprocess
import sys

def test_dns_resolution():
    """测试 DNS 解析"""
    print("=" * 60)
    print("1. 测试 DNS 解析")
    print("=" * 60)
    try:
        ip = socket.gethostbyname("gmgn.ai")
        print(f"✅ DNS 解析成功: gmgn.ai -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS 解析失败: {e}")
        return False

def test_ping():
    """测试网络连通性"""
    print("\n" + "=" * 60)
    print("2. 测试网络连通性 (ping)")
    print("=" * 60)
    try:
        result = subprocess.run(
            ["ping", "-c", "3", "gmgn.ai"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Ping 成功")
            print(result.stdout)
            return True
        else:
            print("❌ Ping 失败")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("⏰ Ping 超时")
        return False
    except Exception as e:
        print(f"❌ Ping 出错: {e}")
        return False

def test_curl():
    """测试 HTTP 访问"""
    print("\n" + "=" * 60)
    print("3. 测试 HTTP 访问 (curl)")
    print("=" * 60)
    try:
        result = subprocess.run(
            ["curl", "-I", "-m", "10", "https://gmgn.ai"],
            capture_output=True,
            text=True,
            timeout=15
        )
        print(result.stdout)
        if "200" in result.stdout or "301" in result.stdout or "302" in result.stdout:
            print("✅ HTTP 访问成功")
            return True
        else:
            print("⚠️ HTTP 返回异常状态码")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ HTTP 请求超时")
        return False
    except Exception as e:
        print(f"❌ HTTP 请求出错: {e}")
        return False

def check_proxy_settings():
    """检查代理设置"""
    print("\n" + "=" * 60)
    print("4. 检查系统代理设置")
    print("=" * 60)
    import os
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    
    if http_proxy or https_proxy:
        print(f"🔧 HTTP Proxy: {http_proxy or '未设置'}")
        print(f"🔧 HTTPS Proxy: {https_proxy or '未设置'}")
    else:
        print("📌 系统未设置代理环境变量")

if __name__ == "__main__":
    print("\n🔍 开始诊断 GMGN.ai 访问情况...\n")
    
    dns_ok = test_dns_resolution()
    ping_ok = test_ping()
    http_ok = test_curl()
    check_proxy_settings()
    
    print("\n" + "=" * 60)
    print("📊 诊断结果汇总")
    print("=" * 60)
    print(f"DNS 解析: {'✅ 正常' if dns_ok else '❌ 失败'}")
    print(f"网络连通: {'✅ 正常' if ping_ok else '❌ 失败'}")
    print(f"HTTP 访问: {'✅ 正常' if http_ok else '❌ 失败'}")
    
    print("\n" + "=" * 60)
    print("💡 建议")
    print("=" * 60)
    
    if not dns_ok:
        print("❌ DNS 解析失败 - 可能原因：")
        print("   - 网络未连接")
        print("   - DNS 服务器问题")
        print("   - 该域名被屏蔽")
    elif not ping_ok and not http_ok:
        print("❌ 无法连接到 GMGN - 可能原因：")
        print("   - 防火墙拦截")
        print("   - ISP 限制")
        print("   - 需要使用代理/VPN")
        print("\n🔧 解决方案：")
        print("   1. 确认你能在 Chrome/Safari 中正常访问 https://gmgn.ai")
        print("   2. 如果需要代理，请配置代理设置")
        print("   3. 如果在中国大陆，可能需要科学上网工具")
    elif http_ok:
        print("✅ 网络连接正常！")
        print("   Playwright 应该能正常工作")
        print("   如果仍然失败，可能是 Playwright 配置问题")
    
    print("\n" + "=" * 60)
