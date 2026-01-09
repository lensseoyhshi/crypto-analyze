"""
示例：如何使用 DexscreenerTokenBoost 的 links 映射功能

演示如何访问和解析 links 字段中的社交媒体链接
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_async_session
from app.repositories.dexscreener_repository import DexscreenerRepository


async def demo_links_mapping():
	"""演示 links 字段的映射和访问"""
	
	print("=" * 60)
	print("Dexscreener Token Boost Links 映射示例")
	print("=" * 60)
	
	async for session in get_async_session():
		repository = DexscreenerRepository(session)
		
		# 获取最新的 token boosts
		boosts = await repository.get_latest_boosts(limit=5)
		
		if not boosts:
			print("\n还没有数据，请等待系统采集数据后再试...")
			return
		
		print(f"\n找到 {len(boosts)} 条记录\n")
		
		for i, boost in enumerate(boosts, 1):
			print(f"\n{i}. Token Boost 信息")
			print(f"   链: {boost.chainId}")
			print(f"   代币地址: {boost.tokenAddress}")
			print(f"   描述: {boost.description}")
			print(f"   Boost 数量: {boost.totalAmount}")
			
			# 方法1: 使用 links_list 属性获取所有链接
			print(f"\n   方法1 - 获取所有链接 (links_list):")
			links = boost.links_list
			if links:
				for link in links:
					print(f"      - {link['type']}: {link['url']}")
			else:
				print(f"      无社交链接")
			
			# 方法2: 使用 get_link_by_type 方法获取特定类型的链接
			print(f"\n   方法2 - 获取特定类型链接 (get_link_by_type):")
			twitter = boost.get_link_by_type('twitter')
			telegram = boost.get_link_by_type('telegram')
			website = boost.get_link_by_type('website')
			
			if twitter:
				print(f"      Twitter: {twitter}")
			if telegram:
				print(f"      Telegram: {telegram}")
			if website:
				print(f"      Website: {website}")
			if not (twitter or telegram or website):
				print(f"      未找到常见社交链接")
			
			# 方法3: 使用便捷属性直接访问
			print(f"\n   方法3 - 使用便捷属性:")
			print(f"      Twitter: {boost.twitter_link or '无'}")
			print(f"      Telegram: {boost.telegram_link or '无'}")
			print(f"      Website: {boost.website_link or '无'}")
			
			print(f"\n   原始 links 字段内容:")
			print(f"      {boost.links}")
			print(f"\n" + "-" * 60)
		
		break  # 退出 async generator


async def demo_search_by_social():
	"""演示：查找有特定社交媒体链接的代币"""
	
	print("\n" + "=" * 60)
	print("查找有 Twitter 链接的代币")
	print("=" * 60)
	
	async for session in get_async_session():
		repository = DexscreenerRepository(session)
		
		# 获取所有最近的 boosts
		boosts = await repository.get_latest_boosts(limit=20)
		
		twitter_tokens = []
		for boost in boosts:
			if boost.twitter_link:
				twitter_tokens.append({
					'token': boost.tokenAddress,
					'chain': boost.chainId,
					'twitter': boost.twitter_link,
					'description': boost.description
				})
		
		if twitter_tokens:
			print(f"\n找到 {len(twitter_tokens)} 个有 Twitter 的代币:\n")
			for i, token in enumerate(twitter_tokens, 1):
				print(f"{i}. {token['token']} ({token['chain']})")
				print(f"   描述: {token['description']}")
				print(f"   Twitter: {token['twitter']}\n")
		else:
			print("\n未找到有 Twitter 链接的代币")
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: Links 映射功能
		await demo_links_mapping()
		
		# 演示2: 搜索功能
		await demo_search_by_social()
		
		print("\n" + "=" * 60)
		print("演示完成!")
		print("=" * 60)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

