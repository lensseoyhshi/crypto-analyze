// Injected Script - 注入到页面主世界，拦截请求
(function() {
  'use strict';
  
  console.log('🔍 GMGN 拦截器已注入到页面');
  
  // 记录已处理的请求
  const processedUrls = new Set();
  
  // ============== 拦截 fetch ==============
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
    const response = await originalFetch.apply(this, args);
    
    // 检查是否是钱包API
    if (url && (url.includes('/rank/sol/wallets') || url.includes('/rank/') && url.includes('/wallets/'))) {
      console.log('🎯 ✅ Fetch 拦截到钱包API!', url);
      
      const clonedResponse = response.clone();
      try {
        const data = await clonedResponse.json();
        processWalletData(data, url, 'fetch');
      } catch (error) {
        console.error('❌ 解析失败:', error);
      }
    }
    
    return response;
  };
  
  // ============== 拦截 XMLHttpRequest ==============
  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._url = url;
    return originalOpen.apply(this, [method, url, ...rest]);
  };
  
  XMLHttpRequest.prototype.send = function(...args) {
    this.addEventListener('load', function() {
      const url = this._url;
      
      if (url && (url.includes('/rank/sol/wallets') || url.includes('/rank/') && url.includes('/wallets/'))) {
        console.log('🎯 ✅ XHR 拦截到钱包API!', url);
        
        try {
          const data = JSON.parse(this.responseText);
          processWalletData(data, url, 'xhr');
        } catch (error) {
          console.error('❌ XHR 解析失败:', error);
        }
      }
    });
    
    return originalSend.apply(this, args);
  };
  
  // 处理钱包数据
  function processWalletData(data, url, method) {
    let wallets = [];
    
    if (data && data.code === 0 && data.data) {
      if (data.data.rank) {
        wallets = data.data.rank;
      } else if (Array.isArray(data.data)) {
        wallets = data.data;
      }
    }
    
    if (wallets.length > 0) {
      const urlKey = url + '_' + wallets.length;
      
      // 避免重复（5秒内）
      if (processedUrls.has(urlKey)) {
        console.log('⏭️ 跳过重复数据');
        return;
      }
      processedUrls.add(urlKey);
      setTimeout(() => processedUrls.delete(urlKey), 5000);
      
      console.log(`✅ 成功解析 ${wallets.length} 个钱包 (${method})`);
      
      // 通过 postMessage 发送到 content script
      window.postMessage({
        type: 'GMGN_WALLETS_DATA',
        data: {
          wallets: wallets,
          url: url,
          method: method,
          timestamp: new Date().toISOString()
        }
      }, '*');
      
      console.log('📤 已发送到 content script');
    } else {
      console.warn('⚠️ 未找到钱包数据');
    }
  }
  
  console.log('✅ API 拦截器已就绪（注入脚本）');
})();
