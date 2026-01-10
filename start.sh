#!/bin/bash

# 🚀 Crypto Analyze 快速启动脚本
# 作者: AI Assistant
# 用途: 一键启动加密货币分析系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "=========================================="
echo "🚀 Crypto Analyze 启动脚本"
echo "=========================================="
echo ""

# 1. 检查 Python 版本
print_info "检查 Python 版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 版本: $PYTHON_VERSION"
else
    print_error "Python3 未安装！请先安装 Python 3.11+"
    exit 1
fi

# 2. 检查虚拟环境
print_info "检查虚拟环境..."
if [ ! -d "venv" ]; then
    print_warning "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    print_success "虚拟环境创建成功"
fi

# 3. 激活虚拟环境
print_info "激活虚拟环境..."
source venv/bin/activate
print_success "虚拟环境已激活"

# 4. 安装依赖
print_info "检查并安装依赖..."
pip install -q -r requirements.txt
print_success "依赖安装完成"

# 5. 检查 MySQL 连接
print_info "检查 MySQL 连接..."
if command -v mysql &> /dev/null; then
    if mysql -u root -p12345678 -e "SELECT 1" &> /dev/null; then
        print_success "MySQL 连接正常"
    else
        print_warning "MySQL 连接失败，尝试使用 Docker MySQL..."
        # 检查 Docker MySQL
        if docker ps | grep -q crypto-mysql; then
            print_success "Docker MySQL 运行中"
        else
            print_warning "启动 Docker MySQL..."
            docker run --name crypto-mysql \
                -e MYSQL_ROOT_PASSWORD=12345678 \
                -e MYSQL_DATABASE=crypto_analyze \
                -p 3306:3306 \
                -d mysql:8.0
            sleep 10
            print_success "Docker MySQL 启动成功"
        fi
    fi
else
    print_warning "MySQL 命令不可用，假设 Docker MySQL 已运行"
fi

# 6. 创建数据库（如果不存在）
print_info "确保数据库存在..."
mysql -u root -p12345678 -e "CREATE DATABASE IF NOT EXISTS crypto_analyze CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || \
docker exec crypto-mysql mysql -uroot -p12345678 -e "CREATE DATABASE IF NOT EXISTS crypto_analyze CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || \
print_warning "无法创建数据库，可能已存在"

# 7. 检查 .env 文件
print_info "检查配置文件..."
if [ ! -f ".env" ]; then
    print_warning ".env 文件不存在，创建默认配置..."
    cat > .env << 'EOF'
APP_NAME=crypto-analyze
DEBUG=True
DATABASE_URL=mysql+aiomysql://root:12345678@localhost:3306/crypto_analyze
BIRDEYE_API_KEY=9c1c446225f246f69ec5ebd6103f1502
DEXSCREENER_FETCH_INTERVAL=6
BIRDEYE_NEW_LISTINGS_INTERVAL=60
BIRDEYE_TOKEN_OVERVIEW_INTERVAL=300
BIRDEYE_TOKEN_SECURITY_INTERVAL=3600
BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL=120
BIRDEYE_TOP_TRADERS_INTERVAL=300
BIRDEYE_WALLET_PORTFOLIO_INTERVAL=600
TRACKED_TOKENS=
TRACKED_WALLETS=
TRACK_NEW_LISTINGS_SECURITY=True
TRACK_NEW_LISTINGS_OVERVIEW=True
EOF
    print_success ".env 文件创建成功"
else
    print_success ".env 文件已存在"
fi

# 8. 运行数据库迁移
print_info "运行数据库迁移..."
alembic upgrade head
print_success "数据库迁移完成"

# 9. 启动应用
echo ""
echo "=========================================="
print_success "所有准备工作完成！"
echo "=========================================="
echo ""
print_info "启动应用服务器..."
print_info "访问 http://localhost:8000/docs 查看 API 文档"
print_info "按 Ctrl+C 停止服务器"
echo ""
echo "=========================================="
echo ""

# 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

