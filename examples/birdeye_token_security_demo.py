"""
示例：如何使用 BirdeyeTokenSecurity 进行代币安全检测和风险评估

演示如何查询代币安全信息、识别风险因素、评估风险等级等
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, desc
from app.db.session import get_async_session
from app.db.models import BirdeyeTokenSecurity


async def demo_token_security_info():
	"""演示查看代币安全信息"""
	
	print("=" * 80)
	print("代币安全检测报告")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询最近检测的代币
		query = select(BirdeyeTokenSecurity).order_by(
			desc(BirdeyeTokenSecurity.create_time)
		).limit(5)
		
		result = await session.execute(query)
		securities = result.scalars().all()
		
		if not securities:
			print("\n还没有代币安全检测数据，请等待系统采集...")
			return
		
		print(f"\n找到 {len(securities)} 个代币安全报告:\n")
		
		for i, sec in enumerate(securities, 1):
			print(f"\n{'=' * 80}")
			print(f"{i}. 代币安全报告")
			print(f"{'=' * 80}")
			
			# 基本信息
			print(f"\n基本信息:")
			print(f"  代币地址: {sec.token_address}")
			print(f"  创建者地址: {sec.creator_address or 'N/A'}")
			print(f"  当前所有者: {sec.owner_address or 'N/A'}")
			
			# 创建信息
			if sec.creation_time:
				creation_dt = datetime.fromtimestamp(sec.creation_time)
				print(f"  创建时间: {creation_dt}")
			print(f"  创建交易: {sec.creation_tx or 'N/A'}")
			
			# 持仓分析
			print(f"\n持仓分析:")
			if sec.creator_percentage:
				print(f"  创建者持仓: {sec.creator_percentage:.2f}%")
				if sec.creator_percentage > 50:
					print(f"    ⚠️  创建者持仓过高（>50%）")
			else:
				print(f"  创建者持仓: N/A")
			
			if sec.top10_holder_percent:
				print(f"  前10持有者占比: {sec.top10_holder_percent:.2f}%")
				if sec.top10_holder_percent > 80:
					print(f"    🚨 极度集中（>80%）")
				elif sec.top10_holder_percent > 50:
					print(f"    ⚠️  高度集中（>50%）")
			else:
				print(f"  前10持有者占比: N/A")
			
			if sec.total_supply:
				print(f"  总供应量: {sec.total_supply:,.0f}")
			
			# 安全特性
			print(f"\n安全特性:")
			print(f"  元数据可变: {'是 ⚠️' if sec.mutable_metadata else '否 ✅'}")
			print(f"  可冻结: {'是 ⚠️' if sec.freezeable else '否 ✅'}")
			print(f"  不可转账: {'是 🚨' if sec.non_transferable else '否 ✅'}")
			print(f"  开启转账费: {'是' if sec.transfer_fee_enable else '否'}")
			print(f"  Token2022标准: {'是' if sec.is_token_2022 else '否'}")
			
			# 风险评估
			print(f"\n风险评估:")
			print(f"  是否存在风险: {'是 🚨' if sec.is_risky else '否 ✅'}")
			
			risk_level = sec.risk_level
			risk_emoji = {
				'high': '🚨',
				'medium': '⚠️',
				'low': '⚡',
				'safe': '✅'
			}
			print(f"  风险等级: {risk_level.upper()} {risk_emoji.get(risk_level, '')}")
			
			# JSON 字段
			pre_market = sec.pre_market_holder_list
			if pre_market:
				print(f"\n盘前持仓: 共 {len(pre_market)} 个地址")
			
			lock_info = sec.lock_info_dict
			if lock_info:
				print(f"\n锁仓信息:")
				print(f"  {lock_info}")
			
			transfer_fee = sec.transfer_fee_data_dict
			if transfer_fee:
				print(f"\n转账费详情:")
				print(f"  {transfer_fee}")
		
		break


async def demo_find_risky_tokens():
	"""演示查找高风险代币"""
	
	print("\n" + "=" * 80)
	print("🚨 高风险代币识别")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询所有代币
		query = select(BirdeyeTokenSecurity).limit(100)
		result = await session.execute(query)
		securities = result.scalars().all()
		
		if not securities:
			print("\n暂无数据")
			return
		
		# 筛选高风险代币
		high_risk_tokens = []
		for sec in securities:
			if sec.risk_level == 'high':
				high_risk_tokens.append(sec)
		
		if not high_risk_tokens:
			print("\n未找到高风险代币 ✅")
			return
		
		print(f"\n找到 {len(high_risk_tokens)} 个高风险代币:\n")
		
		for i, sec in enumerate(high_risk_tokens, 1):
			print(f"{i}. 代币地址: {sec.token_address}")
			
			# 列出风险因素
			risk_factors = []
			if sec.non_transferable:
				risk_factors.append("🚨 不可转账")
			if sec.freezeable:
				risk_factors.append("⚠️  可冻结")
			if sec.mutable_metadata:
				risk_factors.append("⚠️  元数据可变")
			if sec.top10_holder_percent and sec.top10_holder_percent > 50:
				risk_factors.append(f"⚠️  前10持有者占比{sec.top10_holder_percent:.1f}%")
			if sec.creator_percentage and sec.creator_percentage > 50:
				risk_factors.append(f"⚠️  创建者持仓{sec.creator_percentage:.1f}%")
			
			print(f"   风险因素:")
			for factor in risk_factors:
				print(f"     - {factor}")
			print()
		
		break


async def demo_safe_tokens():
	"""演示查找安全代币"""
	
	print("\n" + "=" * 80)
	print("✅ 安全代币识别")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询所有代币
		query = select(BirdeyeTokenSecurity).limit(100)
		result = await session.execute(query)
		securities = result.scalars().all()
		
		if not securities:
			print("\n暂无数据")
			return
		
		# 筛选安全代币
		safe_tokens = []
		for sec in securities:
			if sec.risk_level == 'safe' and not sec.is_risky:
				safe_tokens.append(sec)
		
		if not safe_tokens:
			print("\n未找到完全安全的代币")
			return
		
		print(f"\n找到 {len(safe_tokens)} 个安全代币:\n")
		
		for i, sec in enumerate(safe_tokens[:10], 1):
			print(f"{i}. 代币地址: {sec.token_address}")
			print(f"   创建者: {sec.creator_address or 'N/A'}")
			
			# 列出安全特性
			safe_features = []
			if not sec.mutable_metadata:
				safe_features.append("✅ 元数据不可变")
			if not sec.freezeable:
				safe_features.append("✅ 不可冻结")
			if not sec.non_transferable:
				safe_features.append("✅ 可正常转账")
			if sec.top10_holder_percent and sec.top10_holder_percent < 30:
				safe_features.append(f"✅ 持仓分散（前10占{sec.top10_holder_percent:.1f}%）")
			
			if safe_features:
				print(f"   安全特性:")
				for feature in safe_features:
					print(f"     - {feature}")
			print()
		
		break


async def demo_concentration_analysis():
	"""演示持仓集中度分析"""
	
	print("\n" + "=" * 80)
	print("持仓集中度分析")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询所有代币
		query = select(BirdeyeTokenSecurity).limit(100)
		result = await session.execute(query)
		securities = result.scalars().all()
		
		if not securities:
			print("\n暂无数据")
			return
		
		# 按集中度分类
		highly_concentrated = []  # >80%
		concentrated = []  # 50-80%
		moderate = []  # 30-50%
		dispersed = []  # <30%
		
		for sec in securities:
			if not sec.top10_holder_percent:
				continue
			
			percent = sec.top10_holder_percent
			if percent > 80:
				highly_concentrated.append(sec)
			elif percent > 50:
				concentrated.append(sec)
			elif percent > 30:
				moderate.append(sec)
			else:
				dispersed.append(sec)
		
		print(f"\n持仓集中度分布:")
		print(f"  极度集中 (>80%): {len(highly_concentrated)} 个 🚨")
		print(f"  高度集中 (50-80%): {len(concentrated)} 个 ⚠️")
		print(f"  中度集中 (30-50%): {len(moderate)} 个 ⚡")
		print(f"  分散持有 (<30%): {len(dispersed)} 个 ✅")
		
		if highly_concentrated:
			print(f"\n极度集中代币 (Top 5):")
			for i, sec in enumerate(sorted(highly_concentrated, key=lambda x: x.top10_holder_percent, reverse=True)[:5], 1):
				print(f"  {i}. {sec.token_address[:20]}... - {sec.top10_holder_percent:.2f}%")
		
		break


async def demo_creator_ownership():
	"""演示创建者持仓分析"""
	
	print("\n" + "=" * 80)
	print("创建者持仓分析")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询所有代币
		query = select(BirdeyeTokenSecurity).limit(100)
		result = await session.execute(query)
		securities = result.scalars().all()
		
		if not securities:
			print("\n暂无数据")
			return
		
		# 筛选创建者持仓高的代币
		high_creator_ownership = []
		for sec in securities:
			if sec.creator_percentage and sec.creator_percentage > 20:
				high_creator_ownership.append(sec)
		
		if not high_creator_ownership:
			print("\n未找到创建者高持仓代币")
			return
		
		# 按持仓占比排序
		high_creator_ownership.sort(key=lambda x: x.creator_percentage, reverse=True)
		
		print(f"\n创建者持仓 > 20% 的代币 (共 {len(high_creator_ownership)} 个):\n")
		
		for i, sec in enumerate(high_creator_ownership[:10], 1):
			print(f"{i}. 代币地址: {sec.token_address}")
			print(f"   创建者地址: {sec.creator_address or 'N/A'}")
			print(f"   创建者持仓: {sec.creator_percentage:.2f}%")
			
			if sec.creator_percentage > 50:
				print(f"   ⚠️  风险: 创建者持仓过半，存在抛售风险")
			elif sec.creator_percentage > 30:
				print(f"   ⚡ 注意: 创建者持仓较高")
			
			# 创建时间
			if sec.creation_time:
				creation_dt = datetime.fromtimestamp(sec.creation_time)
				age = datetime.utcnow() - creation_dt
				days = age.days
				print(f"   创建时间: {creation_dt} ({days} 天前)")
			print()
		
		break


async def demo_token2022_tokens():
	"""演示 Token2022 代币统计"""
	
	print("\n" + "=" * 80)
	print("Token2022 代币统计")
	print("=" * 80)
	
	async for session in get_async_session():
		# 查询 Token2022 代币
		query = select(BirdeyeTokenSecurity).where(
			BirdeyeTokenSecurity.is_token_2022 == True
		)
		
		result = await session.execute(query)
		token2022_list = result.scalars().all()
		
		if not token2022_list:
			print("\n未找到 Token2022 代币")
			return
		
		print(f"\n找到 {len(token2022_list)} 个 Token2022 代币:\n")
		
		# 统计转账费开启情况
		transfer_fee_enabled = sum(1 for t in token2022_list if t.transfer_fee_enable)
		freezeable_count = sum(1 for t in token2022_list if t.freezeable)
		
		print(f"统计信息:")
		print(f"  总数: {len(token2022_list)}")
		print(f"  开启转账费: {transfer_fee_enabled} 个")
		print(f"  可冻结: {freezeable_count} 个")
		
		print(f"\n详细列表 (Top 10):")
		for i, sec in enumerate(token2022_list[:10], 1):
			print(f"\n{i}. 代币地址: {sec.token_address}")
			print(f"   转账费: {'开启 ⚠️' if sec.transfer_fee_enable else '关闭 ✅'}")
			print(f"   可冻结: {'是 ⚠️' if sec.freezeable else '否 ✅'}")
			print(f"   风险等级: {sec.risk_level.upper()}")
		
		break


async def main():
	"""主函数"""
	try:
		# 演示1: 代币安全信息
		await demo_token_security_info()
		
		# 演示2: 高风险代币
		await demo_find_risky_tokens()
		
		# 演示3: 安全代币
		await demo_safe_tokens()
		
		# 演示4: 持仓集中度
		await demo_concentration_analysis()
		
		# 演示5: 创建者持仓
		await demo_creator_ownership()
		
		# 演示6: Token2022
		await demo_token2022_tokens()
		
		print("\n" + "=" * 80)
		print("演示完成!")
		print("=" * 80)
		
	except Exception as e:
		print(f"\n错误: {str(e)}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(main())

