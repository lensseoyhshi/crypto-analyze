"""
示例：如何使用 BirdeyeNewListing 查询和分析新上币数据

演示如何查询新上币、按流动性排序、按来源统计等
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, desc, func
from app.db.session import get_async_session
from app.db.models import BirdeyeNewListing


async def demo_latest_listings():
	"""演示查看最新上币"""
	
	print("=" * 80)
	print("最新上币列表")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询最新上币（按添加流动性时间排序）
		query = select(BirdeyeNewListing).order_by(
			desc(BirdeyeNewListing.liquidity_added_at)
		).limit(10)
		
		result = await session.execute(query)
		listings = result.scalars().all()
		
		if not listings:
			print("\n还没有新上币数据，请等待系统采集...")
			return
		
		print(f"\n找到 {len(listings)} 个最新上币:\n")
		
		for i, listing in enumerate(listings, 1):
			print(f"{i}. {listing.symbol} - {listing.name}")
			print(f"   地址: {listing.address}")
			print(f"   来源: {listing.source or 'N/A'}")
			print(f"   初始流动性: ${listing.liquidity:,.2f}" if listing.liquidity else "   初始流动性: N/A")
			print(f"   添加时间: {listing.liquidity_added_at}")
			print(f"   精度: {listing.decimals}")
			if listing.logo_uri:
				print(f"   Logo: {listing.logo_uri[:60]}...")
			print()
		
		break


async def demo_high_liquidity_listings():
	"""演示查找高流动性新币"""
	
	print("=" * 80)
	print("高流动性新币 (流动性 > $10,000)")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询流动性大于 $10,000 的新币
		query = select(BirdeyeNewListing).where(
			BirdeyeNewListing.liquidity > 10000
		).order_by(desc(BirdeyeNewListing.liquidity)).limit(20)
		
		result = await session.execute(query)
		listings = result.scalars().all()
		
		if not listings:
			print("\n未找到高流动性新币")
			return
		
		print(f"\n找到 {len(listings)} 个高流动性新币:\n")
		
		for i, listing in enumerate(listings, 1):
			print(f"{i}. {listing.symbol} - {listing.name}")
			print(f"   地址: {listing.address}")
			print(f"   流动性: ${listing.liquidity:,.2f}")
			print(f"   来源: {listing.source or 'N/A'}")
			print(f"   上线时间: {listing.liquidity_added_at}")
			
			# 计算上线时长
			if listing.liquidity_added_at:
				age = datetime.utcnow() - listing.liquidity_added_at
				hours = age.total_seconds() / 3600
				if hours < 1:
					print(f"   上线时长: {int(age.total_seconds() / 60)} 分钟")
				elif hours < 24:
					print(f"   上线时长: {int(hours)} 小时")
				else:
					print(f"   上线时长: {int(hours / 24)} 天")
			print()
		
		break


async def demo_listings_by_source():
	"""演示按来源统计新币"""
	
	print("=" * 80)
	print("按 DEX 来源统计新币")
	print("=" * 80)
	
	async for session in get_async_session():
		# 统计每个来源的新币数量
		query = select(
			BirdeyeNewListing.source,
			func.count(BirdeyeNewListing.id).label('count'),
			func.avg(BirdeyeNewListing.liquidity).label('avg_liquidity'),
			func.sum(BirdeyeNewListing.liquidity).label('total_liquidity')
		).group_by(BirdeyeNewListing.source).order_by(desc('count'))
		
		result = await session.execute(query)
		stats = result.all()
		
		if not stats:
			print("\n暂无数据")
			return
		
		print(f"\n共 {len(stats)} 个来源:\n")
		
		for i, (source, count, avg_liq, total_liq) in enumerate(stats, 1):
			print(f"{i}. {source or 'Unknown'}")
			print(f"   代币数量: {count}")
			print(f"   平均流动性: ${avg_liq:,.2f}" if avg_liq else "   平均流动性: N/A")
			print(f"   总流动性: ${total_liq:,.2f}" if total_liq else "   总流动性: N/A")
			print()
		
		break


async def demo_recent_24h_listings():
	"""演示查看最近24小时新上币"""
	
	print("=" * 80)
	print("最近 24 小时新上币")
	print("=" * 80)
	
	async for session in get_async_session():
		# 计算24小时前的时间
		time_24h_ago = datetime.utcnow() - timedelta(hours=24)
		
		# 查询最近24小时的新币
		query = select(BirdeyeNewListing).where(
			BirdeyeNewListing.liquidity_added_at >= time_24h_ago
		).order_by(desc(BirdeyeNewListing.liquidity_added_at))
		
		result = await session.execute(query)
		listings = result.scalars().all()
		
		if not listings:
			print("\n最近 24 小时没有新币上线")
			return
		
		print(f"\n找到 {len(listings)} 个新币:\n")
		
		# 统计
		total_liquidity = sum(l.liquidity for l in listings if l.liquidity)
		avg_liquidity = total_liquidity / len(listings) if listings else 0
		
		# 按来源分组
		source_counts = {}
		for listing in listings:
			source = listing.source or 'Unknown'
			source_counts[source] = source_counts.get(source, 0) + 1
		
		print(f"统计信息:")
		print(f"  新币数量: {len(listings)}")
		print(f"  总流动性: ${total_liquidity:,.2f}")
		print(f"  平均流动性: ${avg_liquidity:,.2f}")
		print(f"\n按来源分布:")
		for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
			print(f"  {source}: {count} 个")
		
		print(f"\n详细列表:")
		for i, listing in enumerate(listings[:10], 1):
			print(f"\n{i}. {listing.symbol} - {listing.name}")
			print(f"   地址: {listing.address}")
			print(f"   来源: {listing.source or 'N/A'}")
			print(f"   流动性: ${listing.liquidity:,.2f}" if listing.liquidity else "   流动性: N/A")
			print(f"   上线时间: {listing.liquidity_added_at}")
		
		if len(listings) > 10:
			print(f"\n... 还有 {len(listings) - 10} 个新币")
		
		break


async def demo_search_by_symbol():
	"""演示按符号搜索代币"""
	
	print("\n" + "=" * 80)
	print("按符号搜索代币")
	print("=" * 80)
	
	search_symbol = "USDC"  # 可以修改为任意符号
	
	async for session in get_async_session():
		# 搜索包含指定符号的代币（不区分大小写）
		query = select(BirdeyeNewListing).where(
			BirdeyeNewListing.symbol.ilike(f"%{search_symbol}%")
		).order_by(desc(BirdeyeNewListing.liquidity_added_at))
		
		result = await session.execute(query)
		listings = result.scalars().all()
		
		if not listings:
			print(f"\n未找到包含 '{search_symbol}' 的代币")
			return
		
		print(f"\n找到 {len(listings)} 个包含 '{search_symbol}' 的代币:\n")
		
		for i, listing in enumerate(listings[:10], 1):
			print(f"{i}. {listing.symbol} - {listing.name}")
			print(f"   地址: {listing.address}")
			print(f"   流动性: ${listing.liquidity:,.2f}" if listing.liquidity else "   流动性: N/A")
			print(f"   上线时间: {listing.liquidity_added_at}")
			print()
		
		break


async def demo_low_liquidity_warning():
	"""演示识别低流动性代币（可能有风险）"""
	
	print("=" * 80)
	print("⚠️  低流动性代币预警 (流动性 < $1,000)")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询流动性小于 $1,000 的新币
		query = select(BirdeyeNewListing).where(
			BirdeyeNewListing.liquidity < 1000,
			BirdeyeNewListing.liquidity.isnot(None)
		).order_by(desc(BirdeyeNewListing.liquidity_added_at)).limit(20)
		
		result = await session.execute(query)
		listings = result.scalars().all()
		
		if not listings:
			print("\n未找到低流动性代币")
			return
		
		print(f"\n找到 {len(listings)} 个低流动性代币:\n")
		
		for i, listing in enumerate(listings, 1):
			print(f"{i}. {listing.symbol} - {listing.name}")
			print(f"   地址: {listing.address}")
			print(f"   ⚠️  流动性: ${listing.liquidity:,.2f}")
			print(f"   来源: {listing.source or 'N/A'}")
			print(f"   上线时间: {listing.liquidity_added_at}")
			print(f"   风险提示: 流动性较低，交易可能滑点大")
			print()
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: 最新上币
		await demo_latest_listings()
		
		# 演示2: 高流动性新币
		await demo_high_liquidity_listings()
		
		# 演示3: 按来源统计
		await demo_listings_by_source()
		
		# 演示4: 最近24小时
		await demo_recent_24h_listings()
		
		# 演示5: 按符号搜索
		await demo_search_by_symbol()
		
		# 演示6: 低流动性预警
		await demo_low_liquidity_warning()
		
		print("\n" + "=" * 80)
		print("演示完成!")
		print("=" * 80)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

