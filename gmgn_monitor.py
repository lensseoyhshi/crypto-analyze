import asyncio
import json
import time
from playwright.async_api import async_playwright

# ================= 配置区 =================
# GMGN 聪明钱页面的地址 (直接定位到 SOL 链的 Smart Degen)
TARGET_URL = "https://gmgn.ai/?chain=sol&tab=smart_degen"

# 我们要拦截的 API 特征 (匹配 GMGN 的聪明钱排行榜接口)
API_KEYWORD = "rank/sol/wallets/7d"
API_FULL_PATH = "/defi/quotation/v1/rank/sol/wallets/7d"  # 完整路径

# 抓取间隔 (秒) - 建议不要低于 60 秒，避免被封 IP
LOOP_INTERVAL = 60 

# 是否无头模式 (False = 显示浏览器窗口, True = 后台静默运行)
# 刚开始调试建议 False，稳定后可以改为 True
# 注意：对于 Cloudflare 防护的网站，有头模式更容易通过验证
HEADLESS_MODE = False

# 是否使用隐身模式（避免 Cookie 干扰）
USE_STEALTH = True

# 是否显示所有网络请求（调试用）
DEBUG_MODE = True  # 改为 False 减少日志输出
# =========================================

async def intercept_response(response):
    """
    这是回调函数：每当浏览器收到一个响应，都会经过这里
    """
    # 打印所有请求，方便调试
    if DEBUG_MODE and "gmgn.ai" in response.url:
        print(f"[网络请求] {response.status} - {response.url[:120]}...")
    
    # 1. 检查 URL 是否包含我们要找的 API 关键词，且状态码是 200
    if API_KEYWORD in response.url and response.status == 200:
        try:
            print(f"\n🎯 [API匹配] 发现目标接口！")
            print(f"完整URL: {response.url}")
            
            # 2. 获取 JSON 数据
            json_data = await response.json()
            
            print(f"✅ [数据获取] 成功获取 JSON 响应")
            
            # 3. 解析数据 (这里对应 GMGN 的数据结构)
            if json_data.get("code") == 0 and "data" in json_data:
                # GMGN 的数据可能在 data.rank 或者直接在 data 里
                if "rank" in json_data["data"]:
                    wallets = json_data["data"]["rank"]
                elif isinstance(json_data["data"], list):
                    wallets = json_data["data"]
                else:
                    print("⚠️  数据结构未知，尝试打印...")
                    print(f"数据键: {json_data['data'].keys()}")
                    return
                
                print(f"📊 当前榜单共有 {len(wallets)} 个钱包，正在处理...")
                
                # --- 这里执行你的数据库插入逻辑 ---
                process_wallets(wallets, json_data)
                # ------------------------------
            else:
                print(f"⚠️  返回码: {json_data.get('code')}, 可能请求失败")
                if "msg" in json_data:
                    print(f"错误信息: {json_data['msg']}")
                
        except Exception as e:
            print(f"❌ 解析响应失败: {e}")
            import traceback
            traceback.print_exc()

def process_wallets(wallets, full_data=None):
    """
    处理抓取到的钱包列表
    """
    print("-" * 60)
    print(f"🔍 开始分析前 5 个钱包（共 {len(wallets)} 个）")
    print("-" * 60)
    
    for index, w in enumerate(wallets[:5]): # 为了演示，只打印前5个
        address = w.get('address') or w.get('wallet_address')
        pnl_7d = w.get('pnl_7d') or w.get('profit_7d')
        win_rate = w.get('win_rate_7d') or w.get('winrate')
        tags = w.get('tags', []) # 获取标签，如 smart_degen, kol 等
        
        # 打印完整的字段名，方便后续数据库对接
        print(f"\n排名 {index+1}: {address}")
        print(f"  💰 7日盈利: ${pnl_7d if pnl_7d else 'N/A'}")
        print(f"  📈 7日胜率: {win_rate*100 if win_rate else 0:.1f}%")
        print(f"  🏷️  标签: {tags}")
        
        # 打印其他可用字段
        if DEBUG_MODE:
            print(f"  📋 可用字段: {list(w.keys())[:10]}...")  # 只显示前10个字段名
    
    print("-" * 60)
    print(f"✅ 数据展示完毕，共 {len(wallets)} 个钱包已在后台处理")
    print("-" * 60)
    
    # TODO: 在这里调用你的 MySQL INSERT 语句
    # 示例代码：
    # from dao.smart_wallet_dao import SmartWalletDAO
    # from config.database import get_session
    # 
    # session = get_session()
    # dao = SmartWalletDAO(session)
    # 
    # for wallet in wallets:
    #     address = wallet.get('address')
    #     tags = wallet.get('tags', [])
    #     
    #     dao.upsert_wallet(
    #         address=address,
    #         pnl_7d=wallet.get('pnl_7d'),
    #         win_rate_7d=wallet.get('win_rate_7d'),
    #         is_smart_money=1 if 'smart_degen' in tags else 0,
    #         is_kol=1 if 'kol' in tags else 0
    #     )
    # 
    # session.commit()
    # session.close() 

async def run_monitor():
    async with async_playwright() as p:
        print("🚀 正在启动浏览器...")
        
        # 使用更真实的启动参数
        launch_args = [
            "--disable-blink-features=AutomationControlled",  # 隐藏自动化特征
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certifcate-errors",
            "--ignore-certifcate-errors-spki-list",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]
        
        try:
            # 优先使用系统 Chrome
            browser = await p.chromium.launch(
                headless=HEADLESS_MODE,
                channel="chrome",
                args=launch_args,
                timeout=60000
            )
            print("✅ 使用系统 Chrome 浏览器")
        except Exception as e:
            # 回退到 Chromium
            print(f"⚠️  系统 Chrome 不可用，切换到 Chromium")
            browser = await p.chromium.launch(
                headless=HEADLESS_MODE,
                args=launch_args,
                timeout=60000
            )
        
        print("✅ 浏览器启动成功！")
        
        try:
            # 创建上下文 - 模拟真实浏览器环境
            print("🔧 配置浏览器环境（绕过 Cloudflare）...")
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                ignore_https_errors=True,
                # 使用最新的 Chrome User-Agent
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                # 添加真实浏览器的 HTTP 头
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"macOS"',
                    "Cache-Control": "max-age=0"
                }
            )
            
            # 注入强力反检测脚本
            await context.add_init_script("""
                // 覆盖 webdriver 属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                    configurable: true
                });
                
                // 覆盖 plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            name: 'Chrome PDF Plugin',
                            filename: 'internal-pdf-viewer',
                            description: 'Portable Document Format'
                        },
                        {
                            name: 'Chrome PDF Viewer',
                            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                            description: ''
                        }
                    ]
                });
                
                // 覆盖 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
                
                // 覆盖 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // 添加 chrome 对象
                window.chrome = {
                    runtime: {}
                };
                
                // 伪装 headless
                Object.defineProperty(navigator, 'maxTouchPoints', {
                    get: () => 1
                });
            """)
            
            page = await context.new_page()
            print("✅ 页面创建成功")

            # 开启网络监听
            page.on("response", intercept_response)

            print(f"🌐 正在访问: {TARGET_URL}")
            print("⏳ 如果遇到 Cloudflare 验证，请手动点击验证...")
            
            # 访问页面 - 增加超时时间
            try:
                response = await page.goto(
                    TARGET_URL, 
                    wait_until="domcontentloaded",
                    timeout=60000  # 60秒超时
                )
                print(f"✅ 页面响应: HTTP {response.status}")
            except Exception as e:
                print(f"⚠️  页面加载异常: {e}")
            
            # 等待3秒让页面稳定
            await asyncio.sleep(3)
            
            # 检查当前 URL
            current_url = page.url
            print(f"📍 当前URL: {current_url}")
            
            # 保存截图用于调试
            screenshot_path = "gmgn_debug.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 已保存页面截图: {screenshot_path}")
            
            # 检查是否被 Cloudflare 拦截
            page_content = await page.content()
            if "cloudflare" in page_content.lower() or "challenge" in page_content.lower():
                print("🛡️  检测到 Cloudflare 验证，等待验证通过...")
                # 等待 Cloudflare 验证（最多30秒）
                await asyncio.sleep(30)
                current_url = page.url
                print(f"📍 验证后URL: {current_url}")
                await page.screenshot(path="gmgn_after_cf.png")
                print(f"📸 验证后截图: gmgn_after_cf.png")
            
            if "about:blank" in current_url:
                print("❌ 页面未正确加载！可能原因：")
                print("   1. 网络连接问题")
                print("   2. GMGN 服务器拒绝访问")
                print("   3. Cloudflare 防护拦截")
                print(f"   4. 请查看截图: {screenshot_path}")
                return
            
            print("⏳ 等待数据加载（15秒）...")
            await asyncio.sleep(15)
            
            print("✅ 监听完成，准备关闭浏览器")
            
        except asyncio.TimeoutError:
            print("⏰ 页面加载超时，但可能已捕获到数据")
            # 保存超时时的截图
            try:
                await page.screenshot(path="gmgn_timeout.png")
                print("📸 超时截图已保存: gmgn_timeout.png")
            except:
                pass
        except Exception as e:
            print(f"❌ 页面操作出错: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 关闭浏览器释放资源
            print("🔚 关闭浏览器...")
            await browser.close()

# 主程序入口：死循环执行
if __name__ == "__main__":
    print(">>> 启动 GMGN 聪明钱监控系统 (Playwright版)")
    print(">>> 提示：首次运行如遇到问题，确保系统已安装 Google Chrome 浏览器")
    
    while True:
        try:
            # 运行一次抓取任务
            asyncio.run(run_monitor())
            
            print(f"\n✅ 本轮抓取结束，休息 {LOOP_INTERVAL} 秒...")
            time.sleep(LOOP_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n程序已手动停止")
            break
        except Exception as e:
            print(f"⚠️  发生意外错误: {e}")
            print("10 秒后重试...")
            time.sleep(10) # 出错后短暂停顿重试
