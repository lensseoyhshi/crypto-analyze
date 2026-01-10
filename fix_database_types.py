"""手动执行SQL来修复字段类型溢出问题"""

import asyncio
from app.db.session import get_async_session


async def fix_database_types():
    """修改数据库字段类型从 DECIMAL 或 FLOAT 改为 DOUBLE"""
    
    sqls = [
        # 1. birdeye_token_transactions 表
        "ALTER TABLE birdeye_token_transactions MODIFY COLUMN basePrice DOUBLE COMMENT '目标币单价 (USD)'",
        "ALTER TABLE birdeye_token_transactions MODIFY COLUMN quotePrice DOUBLE COMMENT '计价币单价 (USD)'",
        "ALTER TABLE birdeye_token_transactions MODIFY COLUMN pricePair DOUBLE COMMENT '兑换比率'",
        "ALTER TABLE birdeye_token_transactions MODIFY COLUMN tokenPrice DOUBLE COMMENT 'Quote Token 的价格'",
        
        # 2. birdeye_token_trending 表
        "ALTER TABLE birdeye_token_trending MODIFY COLUMN marketcap DOUBLE COMMENT '流通市值'",
        "ALTER TABLE birdeye_token_trending MODIFY COLUMN fdv DOUBLE COMMENT '完全稀释估值'",
        "ALTER TABLE birdeye_token_trending MODIFY COLUMN liquidity DOUBLE COMMENT '池子流动性'",
        "ALTER TABLE birdeye_token_trending MODIFY COLUMN volume_24h_usd DOUBLE COMMENT '24小时交易量(USD)'",
        
        # 3. birdeye_new_listings 表
        "ALTER TABLE birdeye_new_listings MODIFY COLUMN liquidity DOUBLE COMMENT '初始流动性USD'",
        
        # 4. birdeye_token_overview 表
        "ALTER TABLE birdeye_token_overview MODIFY COLUMN market_cap DOUBLE COMMENT 'Market cap'",
        "ALTER TABLE birdeye_token_overview MODIFY COLUMN fdv DOUBLE COMMENT 'Fully diluted valuation'",
        "ALTER TABLE birdeye_token_overview MODIFY COLUMN liquidity DOUBLE COMMENT 'Total liquidity'",
        "ALTER TABLE birdeye_token_overview MODIFY COLUMN v24h DOUBLE COMMENT '24h volume'",
        "ALTER TABLE birdeye_token_overview MODIFY COLUMN v24h_usd DOUBLE COMMENT '24h volume USD'",
    ]
    
    async for session in get_async_session():
        try:
            for sql in sqls:
                print(f"执行: {sql[:80]}...")
                await session.execute(sql)
                await session.commit()
                print("✓ 完成")
            
            print("\n" + "=" * 60)
            print("所有字段类型已成功修改为 DOUBLE！")
            print("=" * 60)
            
            # 验证修改
            print("\n验证修改结果...")
            result = await session.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'birdeye_token_transactions' 
                AND COLUMN_NAME IN ('basePrice', 'quotePrice', 'pricePair', 'tokenPrice')
            """)
            
            rows = result.fetchall()
            for row in rows:
                print(f"  {row[0]}: {row[2]}")
            
            break
            
        except Exception as e:
            print(f"错误: {str(e)}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("开始修复数据库字段类型...")
    print("=" * 60)
    asyncio.run(fix_database_types())
    print("\n修复完成！现在可以重启应用程序。")

