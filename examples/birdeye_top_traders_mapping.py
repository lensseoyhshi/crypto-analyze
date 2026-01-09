"""
示例：如何使用 BirdeyeTopTrader 的映射功能

演示如何访问和解析 tags 字段，以及计算相关指标
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, desc
from app.db.session import get_async_session
from app.db.models import BirdeyeTopTrader


async def demo_top_traders_mapping():
	"""演示 Top Traders 数据的字段映射"""
	
	print("=" * 80)
	print("Birdeye Top Traders 映射示例")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取最新的 top traders
		query = select(BirdeyeTopTrader).order_by(
			desc(BirdeyeTopTrader.volume)
		).limit(10)
		
		result = await session.execute(query)
		traders = result.scalars().all()
		
		if not traders:
			print("\n还没有 Top Traders 数据，请等待系统采集数据后再试...")
			return
		
		print(f"\n找到 {len(traders)} 个 Top Traders (按交易量排序)\n")
		
		for i, trader in enumerate(traders, 1):
			print(f"\n{'=' * 80}")
			print(f"{i}. Top Trader 信息")
			print(f"{'=' * 80}")
			
			# 基本信息
			print(f"\n基本信息:")
			print(f"  代币地址: {trader.tokenAddress}")
			print(f"  钱包地址: {trader.owner}")
			print(f"  统计时间窗口: {trader.type}")
			
			# 交易统计
			print(f"\n交易统计:")
			print(f"  总交易量: ${trader.volume:,.2f}" if trader.volume else "  总交易量: N/A")
			print(f"  买入总额: ${trader.volumeBuy:,.2f}" if trader.volumeBuy else "  买入总额: N/A")
			print(f"  卖出总额: ${trader.volumeSell:,.2f}" if trader.volumeSell else "  卖出总额: N/A")
			print(f"  总交易次数: {trader.trade}" if trader.trade else "  总交易次数: N/A")
			print(f"  买入次数: {trader.tradeBuy}" if trader.tradeBuy else "  买入次数: N/A")
			print(f"  卖出次数: {trader.tradeSell}" if trader.tradeSell else "  卖出次数: N/A")
			
			# 方法1: 使用便捷属性计算指标
			print(f"\n方法1 - 使用便捷属性:")
			profit_ratio = trader.profit_ratio
			if profit_ratio:
				print(f"  盈利比率 (卖出/买入): {profit_ratio:.2f}x")
				if profit_ratio > 1:
					print(f"  → 盈利 {(profit_ratio - 1) * 100:.1f}%")
				else:
					print(f"  → 亏损 {(1 - profit_ratio) * 100:.1f}%")
			else:
				print(f"  盈利比率: N/A")
			
			net_volume = trader.net_volume
			if net_volume:
				print(f"  净交易额 (卖-买): ${net_volume:,.2f}")
				if net_volume > 0:
					print(f"  → 净盈利")
				else:
					print(f"  → 净亏损")
			else:
				print(f"  净交易额: N/A")
			
			# 方法2: 解析 tags
			print(f"\n方法2 - 标签识别:")
			print(f"  原始 tags 字段: {trader.tags or 'None'}")
			
			tags_list = trader.tags_list
			if tags_list:
				print(f"  解析后的标签: {tags_list}")
			else:
				print(f"  解析后的标签: []")
			
			# 方法3: 使用标签判断属性
			print(f"\n方法3 - 使用标签判断:")
			print(f"  是否为机器人: {'是 🤖' if trader.is_bot else '否'}")
			print(f"  是否为狙击手: {'是 🎯' if trader.is_sniper else '否'}")
			print(f"  是否为内部人士: {'是 👤' if trader.is_insider else '否'}")
			
			# 综合评价
			print(f"\n综合评价:")
			if trader.is_bot:
				print(f"  ⚠️  该交易者可能是机器人")
			if trader.is_sniper:
				print(f"  ⚠️  该交易者可能是狙击手（早期买入者）")
			if trader.is_insider:
				print(f"  ⚠️  该交易者可能是内部人士")
			if not (trader.is_bot or trader.is_sniper or trader.is_insider):
				print(f"  ✅ 普通交易者")
		
		break


async def demo_find_profitable_traders():
	"""演示查找盈利的交易者"""
	
	print("\n" + "=" * 80)
	print("查找盈利的交易者")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取所有交易者
		query = select(BirdeyeTopTrader).limit(100)
		result = await session.execute(query)
		traders = result.scalars().all()
		
		if not traders:
			print("\n暂无数据")
			return
		
		profitable_traders = []
		for trader in traders:
			profit_ratio = trader.profit_ratio
			if profit_ratio and profit_ratio > 1.5:  # 盈利超过 50%
				profitable_traders.append({
					'trader': trader,
					'profit_ratio': profit_ratio,
					'net_volume': trader.net_volume
				})
		
		if profitable_traders:
			# 按盈利比率排序
			profitable_traders.sort(key=lambda x: x['profit_ratio'], reverse=True)
			
			print(f"\n找到 {len(profitable_traders)} 个高盈利交易者 (盈利 > 50%):\n")
			for i, item in enumerate(profitable_traders[:10], 1):
				trader = item['trader']
				print(f"{i}. 钱包: {trader.owner}")
				print(f"   代币: {trader.tokenAddress}")
				print(f"   盈利比率: {item['profit_ratio']:.2f}x ({(item['profit_ratio'] - 1) * 100:.1f}%)")
				print(f"   净盈利: ${item['net_volume']:,.2f}")
				print(f"   买入: ${trader.volumeBuy:,.2f}, 卖出: ${trader.volumeSell:,.2f}")
				
				# 显示标签
				if trader.is_bot:
					print(f"   标签: 🤖 机器人")
				elif trader.is_sniper:
					print(f"   标签: 🎯 狙击手")
				elif trader.is_insider:
					print(f"   标签: 👤 内部人士")
				print()
		else:
			print("\n未找到高盈利交易者")
		
		break


async def demo_analyze_by_token():
	"""演示按代币分析 Top Traders"""
	
	print("\n" + "=" * 80)
	print("按代币分析 Top Traders")
	print("=" * 80)
	
	async for session in get_async_session():
		# 获取所有交易者
		query = select(BirdeyeTopTrader).limit(200)
		result = await session.execute(query)
		traders = result.scalars().all()
		
		if not traders:
			print("\n暂无数据")
			return
		
		# 按代币分组统计
		token_stats = {}
		for trader in traders:
			token = trader.tokenAddress
			if not token:
				continue
			
			if token not in token_stats:
				token_stats[token] = {
					'traders': 0,
					'total_volume': 0,
					'bots': 0,
					'snipers': 0,
					'insiders': 0,
					'profitable': 0
				}
			
			token_stats[token]['traders'] += 1
			if trader.volume:
				token_stats[token]['total_volume'] += trader.volume
			
			if trader.is_bot:
				token_stats[token]['bots'] += 1
			if trader.is_sniper:
				token_stats[token]['snipers'] += 1
			if trader.is_insider:
				token_stats[token]['insiders'] += 1
			
			profit_ratio = trader.profit_ratio
			if profit_ratio and profit_ratio > 1:
				token_stats[token]['profitable'] += 1
		
		# 按总交易量排序
		sorted_tokens = sorted(token_stats.items(), key=lambda x: x[1]['total_volume'], reverse=True)
		
		print(f"\n按代币统计 (Top 10):\n")
		for i, (token, stats) in enumerate(sorted_tokens[:10], 1):
			print(f"{i}. 代币: {token[:20]}...")
			print(f"   Top Traders 数量: {stats['traders']}")
			print(f"   总交易量: ${stats['total_volume']:,.2f}")
			print(f"   盈利者: {stats['profitable']}/{stats['traders']}")
			
			warnings = []
			if stats['bots'] > 0:
				warnings.append(f"🤖 {stats['bots']} 个机器人")
			if stats['snipers'] > 0:
				warnings.append(f"🎯 {stats['snipers']} 个狙击手")
			if stats['insiders'] > 0:
				warnings.append(f"👤 {stats['insiders']} 个内部人士")
			
			if warnings:
				print(f"   警告: {', '.join(warnings)}")
			print()
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: 字段映射
		await demo_top_traders_mapping()
		
		# 演示2: 查找盈利交易者
		await demo_find_profitable_traders()
		
		# 演示3: 按代币分析
		await demo_analyze_by_token()
		
		print("\n" + "=" * 80)
		print("演示完成!")
		print("=" * 80)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

