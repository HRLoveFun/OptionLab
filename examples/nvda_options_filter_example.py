"""
NVDA Options Filter Example
============================
使用 Futu API 获取 US.NVDA 期权链数据，并应用复杂多条件过滤。

过滤条件:
- 标的: US.NVDA
- 行权价范围: $160 - $190
- 到期日范围: 6天 - 30天
- 期权类型: CALL (看涨)
- 最小成交量: 50
- 最小持仓量: 500

使用方法:
1. 确保 Futu OpenD 已启动 (默认端口 11111)
2. 运行: python nvda_options_filter_example.py
"""

import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, '/Users/hrche/Documents/GitHub/OptionView')

from data_pipeline.futu_provider import get_option_chain_futu


def calculate_dte(expiration: str) -> int:
    """计算到期天数 (Days to Expiration)"""
    try:
        exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
        today = datetime.now().date()
        return max(0, (exp_date - today).days)
    except (ValueError, TypeError):
        return 0


def filter_options(
    df: pd.DataFrame,
    option_type: str = None,
    min_strike: float = None,
    max_strike: float = None,
    min_volume: int = None,
    min_oi: int = None,
    min_dte: int = None,
    max_dte: int = None,
) -> pd.DataFrame:
    """
    过滤期权数据框
    
    Args:
        df: 包含期权数据的 DataFrame
        option_type: 期权类型 "CALL" 或 "PUT"
        min_strike: 最小行权价
        max_strike: 最大行权价
        min_volume: 最小成交量
        min_oi: 最小持仓量
        min_dte: 最小到期天数
        max_dte: 最大到期天数
    
    Returns:
        过滤后的 DataFrame
    """
    if df.empty:
        return df

    filtered = df.copy()

    # 按期权类型过滤
    if option_type:
        filtered = filtered[filtered["option_type"] == option_type.upper()]

    # 按行权价范围过滤
    if min_strike is not None:
        filtered = filtered[filtered["strike"] >= min_strike]
    if max_strike is not None:
        filtered = filtered[filtered["strike"] <= max_strike]

    # 按成交量和持仓量过滤
    if min_volume is not None:
        filtered = filtered[filtered["volume"] >= min_volume]
    if min_oi is not None:
        filtered = filtered[filtered["openInterest"] >= min_oi]

    # 按到期天数范围过滤
    if min_dte is not None or max_dte is not None:
        if "dte" not in filtered.columns:
            filtered["dte"] = filtered["expiration"].apply(calculate_dte)

        if min_dte is not None:
            filtered = filtered[filtered["dte"] >= min_dte]
        if max_dte is not None:
            filtered = filtered[filtered["dte"] <= max_dte]

    return filtered.reset_index(drop=True)


def fetch_and_filter_nvda_options():
    """
    获取 NVDA 期权数据并应用复杂多条件过滤
    """
    print("=" * 70)
    print("NVDA 期权数据获取与过滤示例")
    print("=" * 70)

    # 参数设置
    TICKER = "US.NVDA"
    HOST = "127.0.0.1"
    PORT = 11111

    # 过滤条件
    FILTER_CONFIG = {
        "option_type": "CALL",
        "min_strike": 160.0,
        "max_strike": 190.0,
        "min_dte": 6,
        "max_dte": 30,
        "min_volume": 50,
        "min_oi": 500,
    }

    print(f"\n[1] 正在获取 {TICKER} 期权链数据...")
    print(f"    Futu OpenD: {HOST}:{PORT}")

    try:
        # 获取完整期权链数据
        result = get_option_chain_futu(TICKER, host=HOST, port=PORT)

        if not result or not result.get("expirations"):
            print("错误: 未获取到期权数据，请检查:")
            print("  - Futu OpenD 是否已启动")
            print("  - 是否正确连接 (host/port)")
            return None

        spot_price = result.get("spot", 0)
        print(f"\n[2] 数据获取成功!")
        print(f"    标的现价: ${spot_price:.2f}")
        print(f"    到期日数量: {len(result['expirations'])}")
        print(f"    到期日列表: {', '.join(result['expirations'][:5])}...")

        # 转换为 DataFrame
        print(f"\n[3] 正在转换数据格式...")
        all_records = []

        for expiry, data in result["chain"].items():
            for call in data.get("calls", []):
                if call.get("strike") is not None:  # 确保数据有效
                    record = {
                        "expiration": expiry,
                        "option_type": "CALL",
                        "spot_price": spot_price,
                        **call  # 展开 call 字典
                    }
                    all_records.append(record)

            for put in data.get("puts", []):
                if put.get("strike") is not None:
                    record = {
                        "expiration": expiry,
                        "option_type": "PUT",
                        "spot_price": spot_price,
                        **put
                    }
                    all_records.append(record)

        df = pd.DataFrame(all_records)

        if df.empty:
            print("错误: 未找到有效期权数据")
            return None

        print(f"    总记录数: {len(df)}")
        print(f"    CALL: {len(df[df['option_type'] == 'CALL'])}")
        print(f"    PUT: {len(df[df['option_type'] == 'PUT'])}")

        # 添加 DTE 列用于显示
        df["dte"] = df["expiration"].apply(calculate_dte)

        # 应用复杂多条件过滤
        print(f"\n[4] 应用过滤条件:")
        print(f"    期权类型: {FILTER_CONFIG['option_type']}")
        print(f"    行权价范围: ${FILTER_CONFIG['min_strike']} - ${FILTER_CONFIG['max_strike']}")
        print(f"    到期天数: {FILTER_CONFIG['min_dte']} - {FILTER_CONFIG['max_dte']} 天")
        print(f"    最小成交量: {FILTER_CONFIG['min_volume']}")
        print(f"    最小持仓量: {FILTER_CONFIG['min_oi']}")

        candidates = filter_options(df, **FILTER_CONFIG)

        # 显示结果
        print(f"\n[5] 过滤结果:")
        print(f"    匹配记录数: {len(candidates)}")

        if candidates.empty:
            print("\n    未找到符合条件的期权，请尝试放宽过滤条件")
            return candidates

        # 选择要显示的列
        display_cols = [
            "expiration", "dte", "strike", "option_type",
            "lastPrice", "volume", "openInterest", "iv"
        ]

        # 确保所有列都存在
        available_cols = [c for c in display_cols if c in candidates.columns]

        print(f"\n[6] 符合条件的期权列表:")
        print("-" * 70)

        # 按到期日和行权价排序
        candidates_sorted = candidates.sort_values(
            by=["dte", "strike"],
            ascending=[True, True]
        )

        # 打印表格
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', None)
        pd.set_option('display.float_format', '{:.2f}'.format)

        print(candidates_sorted[available_cols].to_string(index=False))

        # 统计信息
        print("\n" + "=" * 70)
        print("统计摘要:")
        print("=" * 70)
        print(f"  平均行权价: ${candidates['strike'].mean():.2f}")
        print(f"  平均隐含波动率: {candidates['iv'].mean():.1f}%" if 'iv' in candidates.columns else "  IV 数据不可用")
        print(f"  平均成交量: {candidates['volume'].mean():.0f}" if 'volume' in candidates.columns else "")
        print(f"  到期日分布:")
        for exp, count in candidates['expiration'].value_counts().sort_index().items():
            dte = calculate_dte(exp)
            print(f"    {exp} (DTE={dte}): {count} 个期权")

        return candidates

    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请检查:")
        print("  1. Futu OpenD 是否已启动")
        print("  2. 是否正确连接 (host/port)")
        print("  3. 是否有 API 访问权限")
        return None


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("Futu API NVDA 期权过滤示例")
    print("=" * 70)
    print("\n此脚本演示:")
    print("  1. 使用 Futu API 获取期权链数据")
    print("  2. 应用多条件过滤 (行权价、到期日、成交量等)")
    print("  3. 展示过滤结果")
    print("\n" + "-" * 70)

    result = fetch_and_filter_nvda_options()

    if result is not None and not result.empty:
        print("\n" + "=" * 70)
        print("✓ 成功!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ 未获取到数据")
        print("=" * 70)


if __name__ == "__main__":
    main()
