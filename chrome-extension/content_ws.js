// Content Script - WebSocket 拦截版本
(function() {
  'use strict';
  
  console.log('🔍 GMGN 数据采集器 Content Script 已加载（WebSocket 支持版）');
  
  // ============== 拦截 WebSocket ==============
  const originalWebSocket = window.WebSocket;
  window.WebSocket = function(...args) {
    console.log('🔌 WebSocket 连接创建:', args[0]);
    const ws = new originalWebSocket(...args);
    
    // 拦截接收到的消息
    const originalOnMessage = ws.onmessage;
    ws.addEventListener('message', function(event) {
      try {
        const data = JSON.parse(event.data);
        console.log('📨 WebSocket 消息:', data);
        
        // 检查是否是钱包数据
        if (data && typeof data === 'object') {
          // 尝试多种数据结构
          let wallets = null;
          
          if (data.type === 'rank' || data.topic === 'rank') {
            wallets = data.data?.rank || data.data || data.wallets;
          } else if (data.data?.rank) {
            wallets = data.data.rank;
          } else if (Array.isArray(data.data)) {
            wallets = data.data;
          } else if (Array.isArray(data)) {
            wallets = data;
          }
          
          if (wallets && Array.isArray(wallets) && wallets.length > 0) {
            // 检查是否包含钱包地址
            const firstItem = wallets[0];
            if (firstItem.address || firstItem.wallet_address) {
              console.log('🎯 ✅ 发现钱包数据（WebSocket）!');
              console.log(`📊 钱包数量: ${wallets.length}`);
              
              // 发送到 background script
              chrome.runtime.sendMessage({
                type: 'GMGN_DATA_CAPTURED',
                data: wallets,
                source: 'websocket',
                timestamp: new Date().toISOString()
              }, (response) => {
                if (response && response.success) {
                  console.log('✅ 数据已发送到服务器（WebSocket）');
                  showNotification('✅ 数据采集成功（WS）', `已捕获 ${wallets.length} 个钱包数据`);
                } else {
                  console.warn('⚠️ 数据发送失败:', response?.error);
                  showNotification('⚠️ 服务器未连接', '数据已保存到本地');
                }
              });
            }
          }
        }
      } catch (error) {
        // 不是 JSON 或解析失败，忽略
      }
      
      // 调用原始处理器
      if (originalOnMessage) {
        originalOnMessage.call(ws, event);
      }
    });
    
    return ws;
  };
  
  // ============== 拦截 fetch 请求（保留） ==============
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await originalFetch.apply(this, args);
    
    const url = args[0];
    const isTargetAPI = typeof url === 'string' && (
      url.includes('/rank/sol/wallets') ||
      url.includes('/rank/') && url.includes('/wallets/')
    );
    
    if (isTargetAPI) {
      console.log('🎯 ✅ 拦截到钱包排行榜 API（HTTP）!');
      console.log('📎 完整URL:', url);
      
      const clonedResponse = response.clone();
      
      try {
        const data = await clonedResponse.json();
        console.log('📦 获取到数据:', data);
        
        let wallets = [];
        if (data.code === 0 && data.data) {
          if (data.data.rank) {
            wallets = data.data.rank;
          } else if (Array.isArray(data.data)) {
            wallets = data.data;
          }
        }
        
        if (wallets.length > 0) {
          console.log(`✅ 成功解析 ${wallets.length} 个钱包（HTTP）`);
          
          chrome.runtime.sendMessage({
            type: 'GMGN_DATA_CAPTURED',
            data: wallets,
            url: url,
            source: 'http',
            timestamp: new Date().toISOString()
          }, (response) => {
            if (response && response.success) {
              console.log('✅ 数据已发送到服务器（HTTP）');
              showNotification('✅ 数据采集成功', `已捕获 ${wallets.length} 个钱包数据`);
            } else {
              console.warn('⚠️ 数据发送失败:', response?.error);
              showNotification('⚠️ 服务器未连接', '数据已保存到本地');
            }
          });
        }
      } catch (error) {
        console.error('解析数据失败:', error);
      }
    }
    
    return response;
  };
  
  // ============== 拦截 XMLHttpRequest（保留） ==============
  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._url = url;
    return originalOpen.apply(this, [method, url, ...rest]);
  };
  
  XMLHttpRequest.prototype.send = function(...args) {
    this.addEventListener('load', function() {
      const isTargetAPI = this._url && (
        this._url.includes('/rank/sol/wallets') ||
        this._url.includes('/rank/') && this._url.includes('/wallets/')
      );
      
      if (isTargetAPI) {
        console.log('🎯 ✅ XHR 拦截到钱包排行榜 API!');
        console.log('📎 完整URL:', this._url);
        
        try {
          const data = JSON.parse(this.responseText);
          console.log('📦 XHR 获取到数据:', data);
          
          let wallets = [];
          if (data.code === 0 && data.data) {
            if (data.data.rank) {
              wallets = data.data.rank;
            } else if (Array.isArray(data.data)) {
              wallets = data.data;
            }
          }
          
          if (wallets.length > 0) {
            console.log(`✅ XHR 成功解析 ${wallets.length} 个钱包`);
            
            chrome.runtime.sendMessage({
              type: 'GMGN_DATA_CAPTURED',
              data: wallets,
              url: this._url,
              source: 'xhr',
              timestamp: new Date().toISOString()
            });
          }
        } catch (error) {
          console.error('XHR 解析数据失败:', error);
        }
      }
    });
    
    return originalSend.apply(this, args);
  };
  
  // 在页面上显示通知
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
  
  console.log('✅ API 拦截器已就绪（HTTP + WebSocket）');
})();
