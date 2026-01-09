"""
示例：如何使用 BirdeyeTokenTransaction 的 JSON 字段映射功能

演示如何访问和解析 quote、base、from、to 这几个 JSON 字段
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, desc
from app.db.session import get_async_session
from app.db.models import BirdeyeTokenTransaction


async def demo_transaction_mapping():
	"""演示交易数据的 JSON 字段映射"""
	
	print("=" * 80)
	print("Birdeye Token Transaction JSON 字段映射示例")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取最新的交易记录
		query = select(BirdeyeTokenTransaction).order_by(
			desc(BirdeyeTokenTransaction.blockUnixTime)
		).limit(5)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		if not transactions:
			print("\n还没有交易数据，请等待系统采集数据后再试...")
			return
		
		print(f"\n找到 {len(transactions)} 条交易记录\n")
		
		for i, tx in enumerate(transactions, 1):
			print(f"\n{'=' * 80}")
			print(f"{i}. 交易信息")
			print(f"{'=' * 80}")
			
			# 基本信息
			print(f"\n基本信息:")
			print(f"  交易哈希: {tx.txHash}")
			print(f"  交易类型: {tx.txType}")
			print(f"  交易方向: {tx.side}")
			print(f"  交易来源: {tx.source}")
			print(f"  交易时间: {tx.block_time}")
			print(f"  钱包地址: {tx.owner}")
			print(f"  流动性池: {tx.poolId}")
			
			# 价格信息
			print(f"\n价格信息:")
			print(f"  目标币价格 (basePrice): ${tx.basePrice:.10f}" if tx.basePrice else "  目标币价格: N/A")
			print(f"  计价币价格 (quotePrice): ${tx.quotePrice:.10f}" if tx.quotePrice else "  计价币价格: N/A")
			print(f"  代币价格 (tokenPrice): ${tx.tokenPrice:.10f}" if tx.tokenPrice else "  代币价格: N/A")
			print(f"  兑换比率 (pricePair): {tx.pricePair:.15f}" if tx.pricePair else "  兑换比率: N/A")
			
			# 方法1: 使用便捷属性快速访问
			print(f"\n方法1 - 使用便捷属性:")
			print(f"  计价币符号: {tx.quote_symbol or 'N/A'}")
			print(f"  目标币符号: {tx.base_symbol or 'N/A'}")
			print(f"  计价币数量: {tx.quote_ui_amount or 'N/A'}")
			print(f"  目标币数量: {tx.base_ui_amount or 'N/A'}")
			
			# 方法2: 使用完整的 JSON 对象
			print(f"\n方法2 - 访问完整的 JSON 对象:")
			
			quote_info = tx.quote_info
			if quote_info:
				print(f"\n  计价币 (Quote) 详细信息:")
				print(f"    符号: {quote_info.get('symbol')}")
				print(f"    地址: {quote_info.get('address')}")
				print(f"    小数位: {quote_info.get('decimals')}")
				print(f"    原始数量: {quote_info.get('amount')}")
				print(f"    UI数量: {quote_info.get('uiAmount')}")
				print(f"    价格: ${quote_info.get('price')}")
				print(f"    最近价格: ${quote_info.get('nearestPrice')}")
			
			base_info = tx.base_info
			if base_info:
				print(f"\n  目标币 (Base) 详细信息:")
				print(f"    符号: {base_info.get('symbol')}")
				print(f"    地址: {base_info.get('address')}")
				print(f"    小数位: {base_info.get('decimals')}")
				print(f"    原始数量: {base_info.get('amount')}")
				print(f"    UI数量: {base_info.get('uiAmount')}")
				print(f"    价格: ${base_info.get('price')}")
			
			from_info = tx.from_info
			if from_info:
				print(f"\n  从 (From) 代币:")
				print(f"    符号: {from_info.get('symbol')}")
				print(f"    数量: {from_info.get('uiAmount')}")
			
			to_info = tx.to_info
			if to_info:
				print(f"\n  到 (To) 代币:")
				print(f"    符号: {to_info.get('symbol')}")
				print(f"    数量: {to_info.get('uiAmount')}")
			
			# 原始 JSON 字符串
			print(f"\n方法3 - 原始 JSON 字符串 (前100字符):")
			if tx.quote:
				print(f"  Quote: {tx.quote[:100]}...")
			if tx.base:
				print(f"  Base: {tx.base[:100]}...")
		
		break


async def demo_transaction_analysis():
	"""演示交易分析 - 统计买卖情况"""
	
	print("\n" + "=" * 80)
	print("交易分析 - 最近交易的买卖统计")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取最近100笔交易
		query = select(BirdeyeTokenTransaction).order_by(
			desc(BirdeyeTokenTransaction.blockUnixTime)
		).limit(100)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		if not transactions:
			print("\n暂无交易数据")
			return
		
		# 统计买卖情况
		buy_count = 0
		sell_count = 0
		total_buy_volume = 0
		total_sell_volume = 0
		
		# 按代币分组统计
		token_stats = {}
		
		for tx in transactions:
			# 买卖统计
			if tx.side == 'buy':
				buy_count += 1
				if tx.quote_ui_amount:
					total_buy_volume += tx.quote_ui_amount
			elif tx.side == 'sell':
				sell_count += 1
				if tx.quote_ui_amount:
					total_sell_volume += tx.quote_ui_amount
			
			# 按代币统计
			base_symbol = tx.base_symbol
			if base_symbol:
				if base_symbol not in token_stats:
					token_stats[base_symbol] = {'buy': 0, 'sell': 0, 'total': 0}
				token_stats[base_symbol]['total'] += 1
				if tx.side == 'buy':
					token_stats[base_symbol]['buy'] += 1
				elif tx.side == 'sell':
					token_stats[base_symbol]['sell'] += 1
		
		print(f"\n总体统计 (最近 {len(transactions)} 笔交易):")
		print(f"  买入: {buy_count} 笔 (总量: {total_buy_volume:.4f})")
		print(f"  卖出: {sell_count} 笔 (总量: {total_sell_volume:.4f})")
		print(f"  买卖比: {buy_count/sell_count:.2f}" if sell_count > 0 else "  买卖比: N/A")
		
		print(f"\n按代币统计 (Top 10):")
		sorted_tokens = sorted(token_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
		for symbol, stats in sorted_tokens:
			buy_pct = (stats['buy'] / stats['total'] * 100) if stats['total'] > 0 else 0
			print(f"  {symbol}: {stats['total']}笔 (买: {stats['buy']}, 卖: {stats['sell']}, 买入率: {buy_pct:.1f}%)")
		
		break


async def demo_find_large_transactions():
	"""演示查找大额交易"""
	
	print("\n" + "=" * 80)
	print("查找大额交易 (价值超过 $100)")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取所有交易
		query = select(BirdeyeTokenTransaction).order_by(
			desc(BirdeyeTokenTransaction.blockUnixTime)
		).limit(200)
		
		result = await session.execute(query)
		transactions = result.scalars().all()
		
		large_txs = []
		for tx in transactions:
			quote_info = tx.quote_info
			if quote_info:
				# 计算交易价值 = 数量 * 价格
				value = quote_info.get('uiAmount', 0) * quote_info.get('price', 0)
				if value > 100:  # 超过 $100
					large_txs.append({
						'tx': tx,
						'value': value,
						'quote_symbol': quote_info.get('symbol'),
						'base_symbol': tx.base_symbol
					})
		
		if large_txs:
			# 按价值排序
			large_txs.sort(key=lambda x: x['value'], reverse=True)
			
			print(f"\n找到 {len(large_txs)} 笔大额交易:\n")
			for i, item in enumerate(large_txs[:10], 1):
				tx = item['tx']
				print(f"{i}. 交易哈希: {tx.txHash}")
				print(f"   交易价值: ${item['value']:.2f}")
				print(f"   方向: {tx.side}")
				print(f"   代币: {item['base_symbol']}")
				print(f"   计价币: {item['quote_symbol']}")
				print(f"   钱包: {tx.owner}")
				print(f"   时间: {tx.block_time}\n")
		else:
			print("\n未找到大额交易")
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: JSON 字段映射
		await demo_transaction_mapping()
		
		# 演示2: 交易分析
		await demo_transaction_analysis()
		
		# 演示3: 大额交易查找
		await demo_find_large_transactions()
		
		print("\n" + "=" * 80)
		print("演示完成!")
		print("=" * 80)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

