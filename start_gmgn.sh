#!/bin/bash
# GMGN 数据采集系统 - 快速启动脚本

echo "🚀 GMGN 数据采集系统"
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source .venv/bin/activate

# 检查依赖
echo "✅ 检查依赖..."
pip show flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "📦 安装依赖..."
    pip install flask flask-cors requests
fi

# 启动服务器
echo ""
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
echo "🎯 启动 Python 服务器..."
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
echo ""
echo "💡 下一步："
echo "   1. 保持此窗口运行"
echo "   2. 在 Chrome 中打开 chrome://extensions/"
echo "   3. 开启'开发者模式'"
echo "   4. 点击'加载已解压的扩展程序'"
echo "   5. 选择: $(pwd)/chrome-extension"
echo "   6. 访问 https://gmgn.ai"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

python gmgn_server.py
