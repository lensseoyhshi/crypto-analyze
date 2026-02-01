// Popup script
document.addEventListener('DOMContentLoaded', function() {
  const statusDiv = document.getElementById('status');
  const lastCaptureSpan = document.getElementById('lastCapture');
  const pendingCountSpan = document.getElementById('pendingCount');
  const testServerBtn = document.getElementById('testServer');
  const openGmgnBtn = document.getElementById('openGmgn');
  const clearCacheBtn = document.getElementById('clearCache');
  
  // 加载状态
  loadStatus();
  
  // 测试服务器连接
  testServerBtn.addEventListener('click', async () => {
    testServerBtn.disabled = true;
    testServerBtn.textContent = '测试中...';
    
    try {
      const response = await fetch('http://localhost:8899/api/health', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        statusDiv.className = 'status active';
        statusDiv.textContent = '✅ 服务器已连接 - ' + (data.message || 'OK');
      } else {
        throw new Error('服务器响应异常');
      }
    } catch (error) {
      statusDiv.className = 'status inactive';
      statusDiv.textContent = '⚠️ 无法连接到服务器 (localhost:8899)';
    } finally {
      testServerBtn.disabled = false;
      testServerBtn.textContent = '测试服务器连接';
    }
  });
  
  // 打开 GMGN 网站
  openGmgnBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://gmgn.ai/?chain=sol&tab=smart_degen' });
  });
  
  // 清除本地缓存
  clearCacheBtn.addEventListener('click', async () => {
    if (confirm('确定要清除所有本地缓存的数据吗？')) {
      await chrome.storage.local.clear();
      alert('✅ 本地缓存已清除');
      loadStatus();
    }
  });
  
  // 加载状态信息
  async function loadStatus() {
    const data = await chrome.storage.local.get(['lastCaptureTime', 'pendingData']);
    
    if (data.lastCaptureTime) {
      const date = new Date(data.lastCaptureTime);
      lastCaptureSpan.textContent = date.toLocaleString('zh-CN');
    } else {
      lastCaptureSpan.textContent = '未捕获';
    }
    
    const pendingCount = (data.pendingData || []).length;
    pendingCountSpan.textContent = pendingCount + ' 条';
    
    if (pendingCount > 0) {
      pendingCountSpan.style.color = '#f44336';
      pendingCountSpan.style.fontWeight = 'bold';
    }
  }
  
  // 自动测试服务器
  testServerBtn.click();
});
