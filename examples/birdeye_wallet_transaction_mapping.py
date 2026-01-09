"""
示例：如何使用 BirdeyeWalletTransaction 的 JSON 字段映射功能

演示如何访问和解析 balance_change、contract_label、token_transfers 这几个 JSON 字段
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, desc
from app.db.session import get_async_session
from app.db.models import BirdeyeWalletTransaction


async def demo_wallet_transaction_mapping():
	"""演示钱包交易数据的 JSON 字段映射"""
	
	print("=" * 80)
	print("Birdeye Wallet Transaction JSON 字段映射示例")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取最新的钱包交易记录
		query = select(BirdeyeWalletTransaction).order_by(
			desc(BirdeyeWalletTransaction.block_time)
		).limit(5)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		if not transactions:
			print("\n还没有钱包交易数据，请等待系统采集数据后再试...")
			return
		
		print(f"\n找到 {len(transactions)} 条钱包交易记录\n")
		
		for i, tx in enumerate(transactions, 1):
			print(f"\n{'=' * 80}")
			print(f"{i}. 钱包交易信息")
			print(f"{'=' * 80}")
			
			# 基本信息
			print(f"\n基本信息:")
			print(f"  交易哈希: {tx.tx_hash}")
			print(f"  区块高度: {tx.block_number}")
			print(f"  交易时间: {tx.block_time}")
			print(f"  交易状态: {'成功 ✅' if tx.status else '失败 ❌'}")
			print(f"  发起地址: {tx.from_address}")
			print(f"  目标地址: {tx.to_address}")
			print(f"  手续费: {tx.fee} Lamports" if tx.fee else "  手续费: N/A")
			print(f"  主要动作: {tx.main_action or 'N/A'}")
			
			# 方法1: 使用便捷属性
			print(f"\n方法1 - 使用便捷属性:")
			print(f"  合约名称: {tx.contract_name or 'N/A'}")
			print(f"  合约地址: {tx.contract_address or 'N/A'}")
			print(f"  SOL 余额变化: {tx.sol_balance_change or 0} SOL")
			print(f"  代币转账数量: {tx.total_token_transfers_count}")
			
			# 方法2: 访问完整的 contract_label JSON
			print(f"\n方法2 - 合约标签详细信息:")
			contract_info = tx.contract_label_info
			if contract_info:
				print(f"  地址: {contract_info.get('address')}")
				print(f"  名称: {contract_info.get('name')}")
				print(f"  元数据: {contract_info.get('metadata')}")
			else:
				print(f"  无合约标签信息")
			
			# 方法3: 访问 balance_change 列表
			print(f"\n方法3 - 余额变动详情:")
			balance_changes = tx.balance_change_list
			if balance_changes:
				print(f"  共 {len(balance_changes)} 个代币余额发生变化:")
				for j, change in enumerate(balance_changes, 1):
					amount = change.get('amount', 0)
					decimals = change.get('decimals', 0)
					ui_amount = amount / (10 ** decimals) if decimals > 0 else amount
					
					symbol = change.get('symbol', 'Unknown')
					name = change.get('name', 'Unknown')
					
					direction = "+" if amount > 0 else ""
					print(f"\n    {j}. {symbol} ({name})")
					print(f"       原始数量: {direction}{amount}")
					print(f"       UI数量: {direction}{ui_amount}")
					print(f"       小数位: {decimals}")
					print(f"       地址: {change.get('address', 'N/A')}")
			else:
				print(f"  无余额变动")
			
			# 方法4: 访问 token_transfers 列表
			print(f"\n方法4 - 代币流转明细:")
			transfers = tx.token_transfers_list
			if transfers:
				print(f"  共 {len(transfers)} 笔代币转账:")
				for j, transfer in enumerate(transfers, 1):
					print(f"\n    {j}. 代币转账")
					print(f"       从账户: {transfer.get('fromUserAccount', 'N/A')}")
					print(f"       到账户: {transfer.get('toUserAccount', 'N/A')}")
					print(f"       数量: {transfer.get('tokenAmount', 0)}")
					print(f"       代币: {transfer.get('mint', 'N/A')[:20]}...")
					print(f"       原生转账: {'是' if transfer.get('transferNative') else '否'}")
			else:
				print(f"  无代币转账")
			
			# 原始 JSON 字符串（截断显示）
			print(f"\n方法5 - 原始 JSON 字符串 (前80字符):")
			if tx.balance_change:
				print(f"  balance_change: {tx.balance_change[:80]}...")
			if tx.contract_label:
				print(f"  contract_label: {tx.contract_label[:80]}...")
			if tx.token_transfers:
				print(f"  token_transfers: {tx.token_transfers[:80]}...")
		
		break


async def demo_analyze_wallet_activity():
	"""演示分析钱包活动"""
	
	print("\n" + "=" * 80)
	print("钱包活动分析")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取最近的交易
		query = select(BirdeyeWalletTransaction).order_by(
			desc(BirdeyeWalletTransaction.block_time)
		).limit(100)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		if not transactions:
			print("\n暂无数据")
			return
		
		# 统计数据
		success_count = 0
		failed_count = 0
		total_fee = 0
		
		# 按合约统计
		contract_stats = {}
		
		# 按主要动作统计
		action_stats = {}
		
		for tx in transactions:
			# 成功失败统计
			if tx.status:
				success_count += 1
			else:
				failed_count += 1
			
			# 手续费统计
			if tx.fee:
				total_fee += tx.fee
			
			# 合约统计
			contract_name = tx.contract_name
			if contract_name:
				if contract_name not in contract_stats:
					contract_stats[contract_name] = 0
				contract_stats[contract_name] += 1
			
			# 动作统计
			action = tx.main_action or 'unknown'
			if action not in action_stats:
				action_stats[action] = 0
			action_stats[action] += 1
		
		print(f"\n总体统计 (最近 {len(transactions)} 笔交易):")
		print(f"  成功: {success_count} 笔 ({success_count/len(transactions)*100:.1f}%)")
		print(f"  失败: {failed_count} 笔 ({failed_count/len(transactions)*100:.1f}%)")
		print(f"  总手续费: {total_fee:,} Lamports ({total_fee/1e9:.6f} SOL)")
		print(f"  平均手续费: {total_fee/len(transactions):,.0f} Lamports")
		
		print(f"\n按合约统计 (Top 5):")
		sorted_contracts = sorted(contract_stats.items(), key=lambda x: x[1], reverse=True)[:5]
		for contract, count in sorted_contracts:
			print(f"  {contract}: {count} 笔")
		
		print(f"\n按动作统计 (Top 5):")
		sorted_actions = sorted(action_stats.items(), key=lambda x: x[1], reverse=True)[:5]
		for action, count in sorted_actions:
			print(f"  {action}: {count} 笔")
		
		break


async def demo_find_large_transfers():
	"""演示查找大额转账"""
	
	print("\n" + "=" * 80)
	print("查找大额 SOL 转账 (绝对值 > 0.1 SOL)")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取所有交易
		query = select(BirdeyeWalletTransaction).order_by(
			desc(BirdeyeWalletTransaction.block_time)
		).limit(200)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		large_transfers = []
		for tx in transactions:
			sol_change = tx.sol_balance_change
			if sol_change and abs(sol_change) > 0.1:
				large_transfers.append({
					'tx': tx,
					'sol_change': sol_change
				})
		
		if large_transfers:
			# 按金额排序
			large_transfers.sort(key=lambda x: abs(x['sol_change']), reverse=True)
			
			print(f"\n找到 {len(large_transfers)} 笔大额 SOL 转账:\n")
			for i, item in enumerate(large_transfers[:10], 1):
				tx = item['tx']
				sol_change = item['sol_change']
				
				direction = "流入 ⬆️" if sol_change > 0 else "流出 ⬇️"
				print(f"{i}. 交易哈希: {tx.tx_hash}")
				print(f"   SOL 变化: {sol_change:+.6f} SOL ({direction})")
				print(f"   发起地址: {tx.from_address}")
				print(f"   目标地址: {tx.to_address}")
				print(f"   合约: {tx.contract_name or 'N/A'}")
				print(f"   时间: {tx.block_time}")
				print(f"   动作: {tx.main_action or 'N/A'}")
				print()
		else:
			print("\n未找到大额 SOL 转账")
		
		break


async def demo_analyze_token_transfers():
	"""演示分析代币转账模式"""
	
	print("\n" + "=" * 80)
	print("代币转账模式分析")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取交易
		query = select(BirdeyeWalletTransaction).limit(100)
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		if not transactions:
			print("\n暂无数据")
			return
		
		# 统计代币转账
		total_transfers = 0
		native_transfers = 0
		token_mints = set()
		
		for tx in transactions:
			transfers = tx.token_transfers_list
			if transfers:
				total_transfers += len(transfers)
				for transfer in transfers:
					if transfer.get('transferNative'):
						native_transfers += 1
					mint = transfer.get('mint')
					if mint:
						token_mints.add(mint)
		
		print(f"\n代币转账统计:")
		print(f"  总转账次数: {total_transfers}")
		print(f"  原生转账: {native_transfers} ({native_transfers/total_transfers*100:.1f}%)" if total_transfers > 0 else "  原生转账: 0")
		print(f"  涉及代币数: {len(token_mints)}")
		print(f"  平均每笔交易转账: {total_transfers/len(transactions):.2f} 次")
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: JSON 字段映射
		await demo_wallet_transaction_mapping()
		
		# 演示2: 钱包活动分析
		await demo_analyze_wallet_activity()
		
		# 演示3: 大额转账查找
		await demo_find_large_transfers()
		
		# 演示4: 代币转账分析
		await demo_analyze_token_transfers()
		
		print("\n" + "=" * 80)
		print("演示完成!")
		print("=" * 80)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

