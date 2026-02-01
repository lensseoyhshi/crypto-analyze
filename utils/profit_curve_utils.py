"""
盈利曲线工具函数
处理 daily_profit_7d JSON 字段
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def parse_daily_profit(daily_profit_json: str) -> Optional[List[Dict[str, Any]]]:
    """
    解析每日盈利 JSON
    
    Args:
        daily_profit_json: JSON 字符串
    
    Returns:
        盈利数据列表，例如：
        [
            {"date": "2026-01-25", "profit": 1234.56},
            {"date": "2026-01-26", "profit": 2345.67},
            ...
        ]
    """
    if not daily_profit_json:
        return None
    
    try:
        data = json.loads(daily_profit_json)
        return data if isinstance(data, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def format_daily_profit(profit_list: List[Dict[str, Any]]) -> str:
    """
    格式化盈利数据为 JSON 字符串
    
    Args:
        profit_list: 盈利数据列表
    
    Returns:
        JSON 字符串
    """
    return json.dumps(profit_list, ensure_ascii=False)


def get_profit_trend(daily_profit_json: str) -> str:
    """
    分析盈利趋势
    
    Args:
        daily_profit_json: JSON 字符串
    
    Returns:
        趋势描述：'上升'、'下降'、'波动'、'稳定'
    """
    data = parse_daily_profit(daily_profit_json)
    if not data or len(data) < 2:
        return '数据不足'
    
    profits = [float(d.get('profit', 0)) for d in data]
    
    # 计算趋势
    increases = sum(1 for i in range(1, len(profits)) if profits[i] > profits[i-1])
    decreases = sum(1 for i in range(1, len(profits)) if profits[i] < profits[i-1])
    
    total_changes = len(profits) - 1
    
    if increases / total_changes > 0.7:
        return '上升'
    elif decreases / total_changes > 0.7:
        return '下降'
    elif abs(increases - decreases) <= 2:
        return '波动'
    else:
        return '稳定'


def calculate_volatility(daily_profit_json: str) -> float:
    """
    计算盈利波动率（标准差）
    
    Args:
        daily_profit_json: JSON 字符串
    
    Returns:
        波动率
    """
    data = parse_daily_profit(daily_profit_json)
    if not data or len(data) < 2:
        return 0.0
    
    profits = [float(d.get('profit', 0)) for d in data]
    
    mean = sum(profits) / len(profits)
    variance = sum((p - mean) ** 2 for p in profits) / len(profits)
    std_dev = variance ** 0.5
    
    return std_dev


def get_max_drawdown(daily_profit_json: str) -> float:
    """
    计算最大回撤
    
    Args:
        daily_profit_json: JSON 字符串
    
    Returns:
        最大回撤金额
    """
    data = parse_daily_profit(daily_profit_json)
    if not data or len(data) < 2:
        return 0.0
    
    profits = [float(d.get('profit', 0)) for d in data]
    
    max_drawdown = 0
    peak = profits[0]
    
    for profit in profits:
        if profit > peak:
            peak = profit
        drawdown = peak - profit
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown


def create_daily_profit_json(dates: List[str], profits: List[float]) -> str:
    """
    创建每日盈利 JSON
    
    Args:
        dates: 日期列表 ['2026-01-25', '2026-01-26', ...]
        profits: 盈利列表 [1234.56, 2345.67, ...]
    
    Returns:
        JSON 字符串
    """
    data = [
        {"date": date, "profit": profit}
        for date, profit in zip(dates, profits)
    ]
    return json.dumps(data, ensure_ascii=False)


def print_profit_chart(daily_profit_json: str, width: int = 50):
    """
    在终端打印盈利曲线图（简单版）
    
    Args:
        daily_profit_json: JSON 字符串
        width: 图表宽度
    """
    data = parse_daily_profit(daily_profit_json)
    if not data:
        print("无盈利数据")
        return
    
    profits = [float(d.get('profit', 0)) for d in data]
    dates = [d.get('date', '') for d in data]
    
    min_profit = min(profits)
    max_profit = max(profits)
    profit_range = max_profit - min_profit
    
    if profit_range == 0:
        profit_range = 1  # 避免除零
    
    print("\n📈 7日盈利曲线")
    print("=" * (width + 20))
    
    for i, (date, profit) in enumerate(zip(dates, profits)):
        # 计算条形图长度
        normalized = (profit - min_profit) / profit_range
        bar_length = int(normalized * width)
        bar = '█' * bar_length
        
        # 打印
        print(f"{date[-5:]} | {bar} ${profit:,.2f}")
    
    print("=" * (width + 20))
    print(f"最低: ${min_profit:,.2f} | 最高: ${max_profit:,.2f} | 趋势: {get_profit_trend(daily_profit_json)}")
    print()


# 示例用法
if __name__ == "__main__":
    # 示例数据
    example_json = create_daily_profit_json(
        dates=['2026-01-25', '2026-01-26', '2026-01-27', '2026-01-28', '2026-01-29', '2026-01-30', '2026-01-31'],
        profits=[1000, 1200, 1500, 1300, 1800, 2000, 2200]
    )
    
    print("示例 JSON:")
    print(example_json)
    print()
    
    # 解析
    data = parse_daily_profit(example_json)
    print("解析结果:")
    print(data)
    print()
    
    # 趋势分析
    print(f"盈利趋势: {get_profit_trend(example_json)}")
    print(f"波动率: ${calculate_volatility(example_json):,.2f}")
    print(f"最大回撤: ${get_max_drawdown(example_json):,.2f}")
    
    # 打印图表
    print_profit_chart(example_json)
