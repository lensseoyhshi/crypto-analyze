// Background Service Worker - 拦截网络请求
console.log('GMGN 数据采集器已启动');

// 监听网络请求
chrome.webRequest.onCompleted.addListener(
  async (details) => {
    // 只处理 GMGN 的聪明钱 API
    if (details.url.includes('rank/sol/wallets/7d') && details.statusCode === 200) {
      console.log('🎯 捕获到聪明钱 API 请求:', details.url);
      
      try {
        // 获取响应数据（注意：webRequest API 无法直接获取响应体）
        // 我们需要在 content script 中处理
        chrome.storage.local.set({
          lastCaptureTime: new Date().toISOString(),
          lastApiUrl: details.url
        });
        
        // 发送通知
        chrome.action.setBadgeText({ text: '✓' });
        chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
        
        setTimeout(() => {
          chrome.action.setBadgeText({ text: '' });
        }, 3000);
        
      } catch (error) {
        console.error('处理请求失败:', error);
      }
    }
  },
  { urls: ["https://gmgn.ai/*"] }
);

// 监听来自 content script 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GMGN_DATA_CAPTURED') {
    console.log('📊 收到钱包数据:', message.data.length, '个钱包');
    
    // 发送到本地 Python 服务器
    sendToLocalServer(message.data)
      .then(() => {
        console.log('✅ 数据已发送到本地服务器');
        sendResponse({ success: true });
      })
      .catch((error) => {
        console.error('❌ 发送失败:', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // 保持消息通道开启
  }
});

// 发送数据到本地 Python 服务器
async function sendToLocalServer(data) {
  const SERVER_URL = 'http://localhost:8899/api/wallets';
  
  try {
    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        timestamp: new Date().toISOString(),
        source: 'gmgn.ai',
        chain: 'sol',
        wallets: data
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('服务器响应:', result);
    return result;
    
  } catch (error) {
    console.error('连接本地服务器失败:', error);
    // 如果服务器连接失败，保存到本地存储
    const saved = await chrome.storage.local.get('pendingData') || { pendingData: [] };
    saved.pendingData = saved.pendingData || [];
    saved.pendingData.push({
      timestamp: new Date().toISOString(),
      data: data
    });
    await chrome.storage.local.set(saved);
    console.log('💾 数据已保存到本地，待服务器恢复后重试');
    throw error;
  }
}
