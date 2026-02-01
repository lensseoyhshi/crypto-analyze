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
    处理钱包数据并存入数据库
    同时写入两个表：
    1. smart_wallets - 实时最新数据
    2. smart_wallets_snapshot - 每日快照
    """
    from datetime import date
    from dao.smart_wallet_dao import SmartWalletDAO
    from dao.smart_wallet_snapshot_dao import SmartWalletSnapshotDAO
    from config.database import get_session
    
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
    print(f"💾 开始存入数据库...")
    print("-" * 70)
    
    # 数据库操作
    snapshot_date = date.today()
    session = None
    
    try:
        session = get_session()
        wallet_dao = SmartWalletDAO(session)
        snapshot_dao = SmartWalletSnapshotDAO(session)
        
        # 统计计数器
        wallet_upsert_count = 0  # 实时表：插入或更新的数量
        snapshot_insert_count = 0  # 快照表：新插入的数量
        snapshot_skip_count = 0  # 快照表：跳过的数量（已存在）
        
        for wallet in wallets:
            address = wallet.get('address') or wallet.get('wallet_address')
            if not address:
                continue
            
            tags = wallet.get('tags', [])
            
            # 处理盈利曲线（如果有的话）
            daily_profit_7d = wallet.get('daily_profit_7d')
            if daily_profit_7d and isinstance(daily_profit_7d, (list, dict)):
                import json
                daily_profit_7d_json = json.dumps(daily_profit_7d)
            else:
                daily_profit_7d_json = None
            
            # 准备数据
            wallet_data = {
                'address': address,
                'wallet_address': wallet.get('wallet_address', address),
                'name': wallet.get('name'),
                'last_active': safe_int(wallet.get('last_active', 0)),
                'chain': 'SOL',
                'balance': safe_float(wallet.get('balance', 0)),
                'sol_balance': safe_float(wallet.get('sol_balance', 0)),
                
                # 标签识别 - 根据GMGN API返回的tags字段映射到数据库
                'is_smart_money': 1 if 'smart_degen' in tags or 'smart_money' in tags else 0,
                'is_kol': 1 if 'kol' in tags or 'renowned' in tags else 0,  # renowned = KOL
                'is_whale': 1 if 'whale' in tags else 0,
                'is_sniper': 1 if 'sniper' in tags else 0,
                'is_hot_followed': 1 if 'hot_followed' in tags or 'top_followed' in tags else 0,
                'is_hot_remarked': 1 if 'hot_remarked' in tags or 'top_renamed' in tags else 0,
                'twitter_handle': wallet.get('twitter_username'),
                'twitter_name': wallet.get('twitter_name'),
                'twitter_description': wallet.get('twitter_bio'),
                
                # 工具标签识别
                'uses_trojan': 1 if 'trojan' in tags else 0,
                'uses_bullx': 1 if 'bullx' in tags else 0,
                'uses_photon': 1 if 'photon' in tags else 0,
                'uses_axiom': 1 if 'axiom' in tags else 0,
                'uses_bot': 1 if 'bot' in tags else 0,
                
                # 盈利曲线
                'daily_profit_7d': daily_profit_7d_json,
                
                # 1天数据
                'pnl_1d': safe_float(wallet.get('pnl_1d', 0)),
                'pnl_1d_roi': safe_float(wallet.get('pnl_1d_roi', 0)),
                'win_rate_1d': safe_float(wallet.get('win_rate_1d', 0)) * 100,
                'tx_count_1d': safe_int(wallet.get('tx_count_1d', 0)),
                'buy_count_1d': safe_int(wallet.get('buy_1d', 0)),
                'sell_count_1d': safe_int(wallet.get('sell_1d', 0)),
                'volume_1d': safe_float(wallet.get('volume_1d', 0)),
                'net_inflow_1d': safe_float(wallet.get('net_inflow_1d', 0)),
                'avg_hold_time_1d': safe_int(wallet.get('avg_hold_time_1d', 0)),
                
                # 7天数据（主要数据）
                'pnl_7d': safe_float(wallet.get('pnl_7d', 0)),
                'pnl_7d_roi': safe_float(wallet.get('pnl_7d_roi', 0)),
                'win_rate_7d': safe_float(wallet.get('win_rate_7d', 0)) * 100,  # 转换为百分比
                'pnl_lt_minus_dot5_num_7d': safe_int(wallet.get('pnl_lt_minus_dot5_num_7d', 0)),
                'pnl_minus_dot5_0x_num_7d': safe_int(wallet.get('pnl_minus_dot5_0x_num_7d', 0)),
                'pnl_lt_2x_num_7d': safe_int(wallet.get('pnl_lt_2x_num_7d', 0)),
                'pnl_2x_5x_num_7d': safe_int(wallet.get('pnl_2x_5x_num_7d', 0)),
                'pnl_gt_5x_num_7d': safe_int(wallet.get('pnl_gt_5x_num_7d', 0)),
                'tx_count_7d': safe_int(wallet.get('buy_7d', 0)) + safe_int(wallet.get('sell_7d', 0)),
                'buy_count_7d': safe_int(wallet.get('buy_7d', 0)),
                'sell_count_7d': safe_int(wallet.get('sell_7d', 0)),
                'volume_7d': safe_float(wallet.get('volume_7d', 0)),
                'net_inflow_7d': safe_float(wallet.get('net_inflow_7d', 0)),
                'avg_hold_time_7d': safe_int(wallet.get('avg_hold_time_7d', 0)),
                
                # 30天数据
                'pnl_30d': safe_float(wallet.get('pnl_30d', 0)),
                'realized_profit_30d': safe_float(wallet.get('realized_profit_30d', 0)),
                'pnl_30d_roi': safe_float(wallet.get('pnl_30d_roi', 0)),
                'win_rate_30d': safe_float(wallet.get('win_rate_30d', 0)) * 100,
                'tx_count_30d': safe_int(wallet.get('tx_count_30d', 0)),
                'buy_count_30d': safe_int(wallet.get('buy_30d', 0)),
                'sell_count_30d': safe_int(wallet.get('sell_30d', 0)),
                'tx_count_total': safe_int(wallet.get('total_tx_count', 0)),
                'volume_30d': safe_float(wallet.get('volume_30d', 0)),
                'net_inflow_30d': safe_float(wallet.get('net_inflow_30d', 0)),
                'avg_hold_time_30d': safe_int(wallet.get('avg_hold_time_30d', 0)),
                
                # 社交指标
                'followed_count': safe_int(wallet.get('followed_count', 0)),
                'remark_count': safe_int(wallet.get('remark_count', 0)),
            }
            
            try:
                # 1. 写入实时表（smart_wallets）- 存在则更新，不存在则插入
                wallet_dao.upsert_wallet(wallet_data)
                wallet_upsert_count += 1
                
                # 2. 写入快照表（smart_wallets_snapshot）- 存在则跳过，不存在则插入
                result = snapshot_dao.upsert_snapshot(wallet_data, snapshot_date)
                if result is not None:
                    snapshot_insert_count += 1
                else:
                    snapshot_skip_count += 1
                
            except Exception as e:
                print(f"⚠️  插入钱包 {address[:8]}... 失败: {e}")
                continue
        
        session.commit()
        print(f"\n✅ 实时表 (smart_wallets): 成功处理 {wallet_upsert_count}/{len(wallets)} 个钱包（存在则更新，不存在则插入）")
        print(f"✅ 快照表 (smart_wallets_snapshot): 新插入 {snapshot_insert_count} 个，跳过 {snapshot_skip_count} 个（已存在）")
        print(f"📅 快照日期: {snapshot_date}")
        
    except Exception as e:
        if session:
            session.rollback()
        print(f"\n❌ 数据库操作失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if session:
            session.close()
    
    print("-" * 70)


def safe_float(value, default=0.0):
    """安全转换为 float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """安全转换为 int"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default
    
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
