#!/bin/bash

echo "======================================"
echo "Crypto Analyze 项目安装脚本"
echo "======================================"
echo ""

# 检查 Python 版本
echo "1. 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   当前 Python 版本: $python_version"

# 创建虚拟环境
echo ""
echo "2. 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "   虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "   ✓ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo ""
echo "3. 激活虚拟环境..."
source venv/bin/activate
echo "   ✓ 虚拟环境已激活"

# 安装依赖
echo ""
echo "4. 安装项目依赖..."
pip install -r requirements.txt
echo "   ✓ 依赖安装完成"

# 创建 .env 文件
echo ""
echo "5. 配置环境变量..."
if [ -f ".env" ]; then
    echo "   .env 文件已存在，跳过创建"
else
    cp .env.example .env
    echo "   ✓ 已创建 .env 文件"
    echo "   ⚠️  请编辑 .env 文件配置数据库连接信息"
fi

echo ""
echo "======================================"
echo "安装完成！"
echo "======================================"
echo ""
echo "下一步："
echo "  1. 编辑 .env 文件，配置数据库连接"
echo "  2. 使用提供的 SQL 创建数据库表"
echo "  3. 运行示例: python examples.py"
echo ""
echo "激活虚拟环境: source venv/bin/activate"
echo "退出虚拟环境: deactivate"
echo ""
