// Content Script - 注入脚本并接收消息
(function() {
  'use strict';
  
  console.log('🔍 GMGN 数据采集器 Content Script 已加载');
  
  // ============== 注入脚本到页面 ==============
  function injectScript() {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('inject.js');
    script.onload = function() {
      this.remove();
      console.log('✅ 注入脚本已加载');
    };
    (document.head || document.documentElement).appendChild(script);
  }
  
  // 立即注入
  injectScript();
  
  // ============== 接收来自注入脚本的消息 ==============
  window.addEventListener('message', function(event) {
    // 只接受来自同一窗口的消息
    if (event.source !== window) {
      return;
    }
    
    // 检查消息类型
    if (event.data.type === 'GMGN_WALLETS_DATA') {
      console.log('📨 收到来自注入脚本的数据');
      const { wallets, url, method, timestamp } = event.data.data;
      
      console.log(`📊 钱包数量: ${wallets.length}`);
      console.log(`🔗 来源: ${url}`);
      
      // 发送到 background script
      sendToBackground(wallets, url, timestamp);
    }
  });
  
  // ============== 发送到 background script ==============
  function sendToBackground(wallets, sourceUrl, timestamp) {
    console.log('📤 正在发送到 background script...');
    
    chrome.runtime.sendMessage({
      type: 'GMGN_DATA_CAPTURED',
      data: wallets,
      url: sourceUrl,
      timestamp: timestamp
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('❌ 发送失败:', chrome.runtime.lastError);
        showNotification('❌ 发送失败', '请检查扩展是否正常运行');
        return;
      }
      
      if (response && response.success) {
        console.log('✅ 数据已发送到服务器');
        showNotification('✅ 数据采集成功', `已捕获 ${wallets.length} 个钱包数据`);
      } else {
        console.warn('⚠️ 服务器响应异常:', response);
        showNotification('⚠️ 服务器未连接', '数据已保存到本地');
      }
    });
  }
  
  // ============== 显示通知 ==============
  function showNotification(title, message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4CAF50;
      color: white;
      padding: 15px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      max-width: 300px;
    `;
    notification.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 5px;">${title}</div>
      <div style="font-size: 12px; opacity: 0.9;">${message}</div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.transition = 'opacity 0.5s';
      notification.style.opacity = '0';
      setTimeout(() => notification.remove(), 500);
    }, 3000);
  }
  
  console.log('✅ Content Script 已就绪，等待数据...');
})();
