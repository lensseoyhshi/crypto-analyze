#!/usr/bin/env python3
"""
GMGN 数据接收服务器
接收 Chrome 扩展发送的数据并存储到数据库
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 统计信息
stats = {
    'total_received': 0,
    'last_receive_time': None,
    'server_start_time': datetime.now().isoformat()
}


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': '服务器运行中',
        'stats': stats
    })


@app.route('/api/wallets', methods=['POST'])
def receive_wallets():
    """接收钱包数据"""
    try:
        data = request.get_json()
        
        if not data or 'wallets' not in data:
            return jsonify({
                'success': False,
                'error': '无效的数据格式'
            }), 400
        
        wallets = data['wallets']
        timestamp = data.get('timestamp', datetime.now().isoformat())
        source = data.get('source', 'unknown')
        chain = data.get('chain', 'sol')
        
        print(f"\n{'='*70}")
        print(f"📡 收到数据 - {timestamp}")
        print(f"📊 来源: {source} | 链: {chain} | 钱包数: {len(wallets)}")
        print(f"{'='*70}")
        
        # 处理钱包数据
        process_wallets(wallets)
        
        # 更新统计
        stats['total_received'] += len(wallets)
        stats['last_receive_time'] = timestamp
        
        return jsonify({
            'success': True,
            'message': f'成功接收 {len(wallets)} 个钱包数据',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def process_wallets(wallets):
    """
    处理钱包数据
    TODO: 在这里添加数据库插入逻辑
    """
    print("\n" + "-" * 70)
    print("🔍 钱包详情（前5个）：")
    print("-" * 70)
    
    for index, wallet in enumerate(wallets[:5], 1):
        address = wallet.get('address') or wallet.get('wallet_address')
        pnl_7d = wallet.get('pnl_7d') or wallet.get('profit_7d') or 0
        win_rate = wallet.get('win_rate_7d') or wallet.get('winrate') or 0
        tags = wallet.get('tags', [])
        
        # 转换为数字类型
        try:
            pnl_7d = float(pnl_7d) if pnl_7d else 0
        except (ValueError, TypeError):
            pnl_7d = 0
        
        try:
            win_rate = float(win_rate) if win_rate else 0
        except (ValueError, TypeError):
            win_rate = 0
        
        print(f"\n排名 {index}: {address}")
        print(f"  💰 7日盈亏: ${pnl_7d:,.2f}")
        print(f"  📈 7日胜率: {win_rate*100:.1f}%")
        print(f"  🏷️  标签: {', '.join(tags) if tags else '无'}")
        
        # 显示可用字段（调试用）
        if index == 1:
            print(f"\n  📋 可用字段: {list(wallet.keys())[:15]}")
    
    print("\n" + "-" * 70)
    print(f"✅ 共处理 {len(wallets)} 个钱包")
    print("-" * 70)
    
    # TODO: 数据库插入逻辑
    # from dao.smart_wallet_dao import SmartWalletDAO
    # from config.database import get_session
    # 
    # session = get_session()
    # dao = SmartWalletDAO(session)
    # 
    # try:
    #     for wallet in wallets:
    #         address = wallet.get('address')
    #         tags = wallet.get('tags', [])
    #         
    #         dao.upsert_wallet(
    #             address=address,
    #             pnl_7d=wallet.get('pnl_7d'),
    #             win_rate_7d=wallet.get('win_rate_7d'),
    #             realized_profit_7d=wallet.get('realized_profit_7d'),
    #             unrealized_profit_7d=wallet.get('unrealized_profit_7d'),
    #             buy_7d=wallet.get('buy_7d'),
    #             sell_7d=wallet.get('sell_7d'),
    #             is_smart_money=1 if 'smart_degen' in tags else 0,
    #             is_kol=1 if 'kol' in tags else 0
    #         )
    #     
    #     session.commit()
    #     print("✅ 数据已保存到数据库")
    # except Exception as e:
    #     session.rollback()
    #     print(f"❌ 数据库保存失败: {e}")
    # finally:
    #     session.close()


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    return jsonify(stats)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 GMGN 数据接收服务器")
    print("=" * 70)
    print(f"📍 监听地址: http://localhost:8899")
    print(f"⏰ 启动时间: {stats['server_start_time']}")
    print("\n💡 使用说明：")
    print("   1. 在 Chrome 中安装扩展")
    print("   2. 访问 https://gmgn.ai")
    print("   3. 数据将自动发送到这里")
    print("\n" + "=" * 70 + "\n")
    
    # 启动服务器
    app.run(
        host='127.0.0.1',
        port=8899,
        debug=True,
        use_reloader=False  # 避免重复启动
    )
