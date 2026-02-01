// GMGN 聪明钱数据采集器 - 后台脚本
console.log('🚀 GMGN 数据采集插件已启动');

// 配置区
const CONFIG = {
  API_PATTERN: 'rank/sol/wallets/7d',  // 要拦截的 API 特征
  SERVER_URL: 'http://localhost:5000/api/wallets',  // 你的本地服务器地址
  AUTO_SAVE: true,  // 是否自动保存到服务器
  DEBUG: true  // 调试模式
};

// 监听网络请求
chrome.webRequest.onCompleted.addListener(
  async (details) => {
    // 检查是否是我们要拦截的 API
    if (details.url.includes(CONFIG.API_PATTERN) && details.statusCode === 200) {
      console.log('🎯 捕获到目标 API:', details.url);
      
      try {
        // 获取响应内容（注意：webRequest API 无法直接获取响应体）
        // 我们需要重新发起请求来获取数据
        const response = await fetch(details.url, {
          credentials: 'include',  // 包含 Cookie
          headers: {
            'Accept': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ 数据获取成功');
          
          // 处理数据
          await processWalletData(data, details.url);
        } else {
          console.error('❌ 请求失败:', response.status);
        }
      } catch (error) {
        console.error('❌ 处理出错:', error);
      }
    }
  },
  { urls: ["https://gmgn.ai/*"] }
);

// 处理钱包数据
async function processWalletData(data, sourceUrl) {
  try {
    // 解析 GMGN 数据结构
    let wallets = [];
    
    if (data.code === 0 && data.data) {
      if (data.data.rank) {
        wallets = data.data.rank;
      } else if (Array.isArray(data.data)) {
        wallets = data.data;
      }
    }
    
    if (wallets.length === 0) {
      console.warn('⚠️ 未找到钱包数据');
      return;
    }
    
    console.log(`📊 解析到 ${wallets.length} 个钱包`);
    
    // 保存到本地存储
    const timestamp = new Date().toISOString();
    const savedData = {
      timestamp,
      source_url: sourceUrl,
      wallet_count: wallets.length,
      wallets: wallets.slice(0, 10)  // 只保存前10个到存储（节省空间）
    };
    
    await chrome.storage.local.set({
      'latest_data': savedData,
      'last_update': timestamp
    });
    
    console.log('💾 数据已保存到本地存储');
    
    // 显示前5个钱包（调试用）
    if (CONFIG.DEBUG) {
      console.log('\n🏆 聪明钱排行榜 TOP 5:');
      wallets.slice(0, 5).forEach((w, i) => {
        console.log(`${i + 1}. ${w.address}`);
        console.log(`   💰 7日盈亏: $${w.pnl_7d?.toLocaleString() || 'N/A'}`);
        console.log(`   📈 7日胜率: ${(w.win_rate_7d * 100).toFixed(1)}%`);
        console.log(`   🏷️ 标签: ${w.tags?.join(', ') || 'N/A'}`);
      });
    }
    
    // 发送到本地服务器
    if (CONFIG.AUTO_SAVE) {
      await sendToServer(wallets);
    }
    
    // 更新插件图标徽章
    chrome.action.setBadgeText({ text: wallets.length.toString() });
    chrome.action.setBadgeBackgroundColor({ color: '#00AA00' });
    
  } catch (error) {
    console.error('❌ 数据处理失败:', error);
  }
}

// 发送数据到本地服务器
async function sendToServer(wallets) {
  try {
    console.log('📤 正在发送数据到服务器...');
    
    const response = await fetch(CONFIG.SERVER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        timestamp: new Date().toISOString(),
        wallets: wallets
      })
    });
    
    if (response.ok) {
      console.log('✅ 数据已发送到服务器');
    } else {
      console.error('⚠️ 服务器返回错误:', response.status);
    }
  } catch (error) {
    console.error('⚠️ 无法连接到本地服务器:', error.message);
    console.log('💡 提示：请先启动本地 API 服务器');
  }
}

// 监听来自 popup 的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getLatestData') {
    chrome.storage.local.get(['latest_data', 'last_update'], (result) => {
      sendResponse(result);
    });
    return true;  // 保持消息通道开启
  }
  
  if (request.action === 'updateConfig') {
    Object.assign(CONFIG, request.config);
    console.log('⚙️ 配置已更新:', CONFIG);
    sendResponse({ success: true });
  }
});

console.log('👀 正在监听 GMGN API 请求...');
