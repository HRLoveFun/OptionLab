# 主入口文件，仅保留接口和兼容函数
from core.price_dynamic import PriceDynamic
from core.market_analyzer import MarketAnalyzer
from utils.data_utils import calculate_recent_extreme_change, market_review

# 兼容性遗留函数

def period_segment(df, periods=None):
    """Legacy function - use MarketAnalyzer instead"""
    if periods is None:
        from core.price_dynamic import PERIODS
        periods = PERIODS
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    return analyzer._create_period_segments(df, periods)

def oscillation(df):
    """Legacy function - use PriceDynamic.osc() instead"""
    data = df[['Open', 'High', 'Low', 'Close']].copy()
    data['LastClose'] = data["Close"].shift(1)
    data["Oscillation"] = (data["High"] - data["Low"]) / data['LastClose'] * 100
    return data.dropna()

def scatter_hist(x, y):
    """Legacy function - use MarketAnalyzer.generate_scatter_plot() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    return analyzer._create_scatter_hist_plot(x, y), None

def tail_stats(data_sources):
    """Legacy function - use MarketAnalyzer.calculate_tail_statistics() instead"""
    import pandas as pd
    stats_index = ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th"]
    stats_df = pd.DataFrame(index=stats_index)
    for period_name, data in data_sources.items():
        if len(data) > 0:
            stats_df[period_name] = [
                data.mean(), data.std(), data.skew(), data.kurtosis(),
                data.max(), data.quantile(0.99), data.quantile(0.95), data.quantile(0.90)
            ]
    return stats_df

def tail_plot(data_sources):
    """Legacy function - use MarketAnalyzer.generate_tail_plot() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    import matplotlib.pyplot as plt
    import numpy as np
    fig, ax = plt.subplots(figsize=(10, 6))
    for period_name, data in data_sources.items():
        if len(data) > 0:
            sorted_data = np.sort(data)
            y_vals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            ax.plot(sorted_data, y_vals, label=period_name, linewidth=2)
    for percentile in [0.9, 0.95, 0.99]:
        ax.axhline(y=percentile, color='gray', linestyle='--', alpha=0.7)
    ax.legend()
    ax.set_title("Cumulative Density")
    ax.grid(True, alpha=0.3)
    return analyzer._fig_to_base64(fig)

def osc_projection(data, target_bias=0):
    """Legacy function - use MarketAnalyzer.generate_oscillation_projection() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    analyzer.price_dynamic = type('MockPriceDynamic', (), {'_data': data, 'is_valid': lambda: True})()
    return analyzer.generate_oscillation_projection(target_bias=target_bias)

def period_gap_stats(df, feature, frequency):
    """Legacy function - use MarketAnalyzer.calculate_gap_statistics() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    analyzer.price_dynamic = type('MockPriceDynamic', (), {'_data': df, 'is_valid': lambda: True})()
    return analyzer._calculate_period_gap_stats(df, frequency)

def option_matrix(ticker, option_position):
    """Legacy function - use MarketAnalyzer.analyze_options() instead"""
    try:
        analyzer = MarketAnalyzer(ticker)
        option_data = []
        for _, row in option_position.iterrows():
            option_data.append({
                'option_type': row['option_type'],
                'strike': row['strike'],
                'quantity': row['quantity'],
                'premium': row['premium']
            })
        # 兼容旧接口
        # option_data.to_excel('option_data.xlsx', index=False)
        return analyzer.analyze_options(option_data)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in legacy option_matrix function: {e}")
        return None