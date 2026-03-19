"""
futu-api 已验证函数库

由 Step 1-C 实机验证生成。
每个函数经 futu OpenD 实机运行验证，输出结构以实际运行结果为准。
"""
import logging
from contextlib import contextmanager

import futu

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# P1: 连接管理
# ---------------------------------------------------------------------------

@contextmanager
def create_quote_ctx(host: str = "127.0.0.1", port: int = 11111):
    """
    创建 futu OpenQuoteContext 上下文管理器，确保连接关闭。

    文档来源：futu-api 文档 > Quote Object > Create and Initialize the Connection
    实机验证日期：2026-03-19

    Args:
        host: futu OpenD 地址
        port: futu OpenD 端口

    Yields:
        futu.OpenQuoteContext 实例

    Usage::

        with create_quote_ctx() as ctx:
            ret, data = ctx.get_option_expiration_date(code='US.AAPL')
    """
    ctx = futu.OpenQuoteContext(host=host, port=port)
    try:
        yield ctx
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# P0-1: 期权到期日查询
# ---------------------------------------------------------------------------

def get_option_expiration_dates(
    ticker: str,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> list[str]:
    """
    获取指定标的的期权到期日列表。

    文档来源：futu-api 文档 > Get Option Expiration Date（L2511-L2556）
    GitHub 示例：futu/quote/open_quote_context.py docstring :example:
    实机验证日期：2026-03-19

    Args:
        ticker: futu 格式 Ticker，如 "US.AAPL"
        host: futu OpenD 地址
        port: futu OpenD 端口

    Returns:
        到期日字符串列表，格式 "YYYY-MM-DD"

    实机输出示例::

        ["2026-03-20", "2026-03-23", "2026-03-25", ...]

    返回 DataFrame 字段（实机验证）：
        - strike_time: str — 到期日，如 "2026-03-20"
        - option_expiry_date_distance: int64 — 距到期日天数，如 1
        - expiration_cycle: str — 到期周期，如 "MONTH"、"WEEK"
    """
    with create_quote_ctx(host=host, port=port) as ctx:
        ret, data = ctx.get_option_expiration_date(code=ticker)
        if ret != futu.RET_OK:
            raise RuntimeError(f"futu API error: {data}")
        return data["strike_time"].tolist()


# ---------------------------------------------------------------------------
# P0-2: 期权链查询
# ---------------------------------------------------------------------------

def get_option_chain(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    option_type: "futu.OptionType" = None,
    data_filter: "futu.OptionDataFilter | None" = None,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> "pd.DataFrame":
    """
    获取指定标的的期权链静态信息 DataFrame。

    文档来源：futu-api 文档 > Get Option Chain（L2557-L2700）
    GitHub 示例：futu/quote/open_quote_context.py docstring :example:
    实机验证日期：2026-03-19

    Args:
        ticker: futu 格式 Ticker，如 "US.AAPL"
        start: 起始到期日筛选，"YYYY-MM-DD"；None 则为今天
        end: 结束到期日筛选，"YYYY-MM-DD"；None 则为 start+30天
        option_type: 期权方向筛选（futu.OptionType.ALL/CALL/PUT）
        data_filter: OptionDataFilter 实例，按 Greeks/OI/Volume 过滤
        host: futu OpenD 地址
        port: futu OpenD 端口

    Returns:
        pd.DataFrame，每行一个期权合约

    实机输出示例（head 2）::

        code                  name              lot_size stock_type option_type stock_owner strike_time  strike_price suspension   stock_id
        US.AAPL260320C90000  AAPL 260320 90.00C      100       DRVT        CALL     US.AAPL  2026-03-20          90.0      False  501274783
        US.AAPL260320P90000  AAPL 260320 90.00P      100       DRVT         PUT     US.AAPL  2026-03-20          90.0      False  501274787

    返回 DataFrame 字段（实机验证，14列）：
        - code: str — 期权代码，如 "US.AAPL260320C90000"
        - name: str — 期权名称，如 "AAPL 260320 90.00C"
        - lot_size: int64 — 每手股数，如 100
        - stock_type: str — 证券类型，如 "DRVT"
        - option_type: str — 期权方向，"CALL" 或 "PUT"
        - stock_owner: str — 标的股票代码，如 "US.AAPL"
        - strike_time: str — 到期日，如 "2026-03-20"
        - strike_price: float64 — 行权价，如 90.0
        - suspension: bool — 是否停牌
        - stock_id: int64 — 内部股票 ID
        - index_option_type: str — 指数期权类型，普通股票为 "N/A"
        - expiration_cycle: str — 到期周期，如 "MONTH"
        - option_standard_type: str — 标准/非标准，如 "STANDARD"
        - option_settlement_mode: str — 结算模式，普通为 "N/A"

    频率限制：每 30 秒最多 10 次；时间跨度上限 30 天
    """
    import pandas as pd

    kwargs: dict = {"code": ticker}
    if start is not None:
        kwargs["start"] = start
    if end is not None:
        kwargs["end"] = end
    if option_type is not None:
        kwargs["option_type"] = option_type
    if data_filter is not None:
        kwargs["data_filter"] = data_filter

    with create_quote_ctx(host=host, port=port) as ctx:
        ret, data = ctx.get_option_chain(**kwargs)
        if ret != futu.RET_OK:
            raise RuntimeError(f"futu API error: {data}")
        assert isinstance(data, pd.DataFrame)
        return data


# ---------------------------------------------------------------------------
# P0-3: 现货价格查询
# ---------------------------------------------------------------------------

def get_spot_price(
    ticker: str,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> float:
    """
    获取指定标的的最新成交价（现货价格）。

    实现方式：subscribe(QUOTE) → get_stock_quote() → last_price。
    注意：get_market_snapshot() 在测试环境中超时，故改用 subscribe + get_stock_quote。

    文档来源：futu-api 文档 > Get Market Snapshot（L1714-L1790）/ Subscribe（L1144-L1235）
    实机验证日期：2026-03-19

    Args:
        ticker: futu 格式 Ticker，如 "HK.00700"、"US.AAPL"
        host: futu OpenD 地址
        port: futu OpenD 端口

    Returns:
        最新成交价 float 标量

    实机输出示例::

        513.0  （HK.00700 于 2026-03-19 16:07:59）

    get_stock_quote() 返回 DataFrame 关键字段（实机验证，共 62 列）：
        基础行情（对股票有值）：
        - code: str — 代码
        - last_price: float64 — 最新价 ← 本函数返回此字段
        - open_price: float64 — 开盘价
        - high_price: float64 — 最高价
        - low_price: float64 — 最低价
        - prev_close_price: float64 — 昨收价
        - volume: int64 — 成交量
        - turnover: float64 — 成交额

        期权专属字段（对期权合约有值，股票为 N/A）：
        - strike_price: float64 — 行权价
        - contract_size: float64 — 每张合约股数
        - open_interest: int64 — 未平仓合约数
        - implied_volatility: float64 — 隐含波动率
        - premium: float64 — 溢价
        - delta: float64 — Delta
        - gamma: float64 — Gamma
        - vega: float64 — Vega
        - theta: float64 — Theta
        - rho: float64 — Rho
        - expiry_date_distance: int64 — 距到期日天数
        - option_area_type: str — 行权类型（AMERICAN/EUROPEAN）
        - contract_multiplier: float64 — 合约乘数

    限制：
        - 需先调用 subscribe() 订阅 SubType.QUOTE
        - 美股非交易时段订阅可能失败（"拉取美股夜盘状态失败"）
    """
    with create_quote_ctx(host=host, port=port) as ctx:
        ret_sub, err = ctx.subscribe([ticker], [futu.SubType.QUOTE])
        if ret_sub != futu.RET_OK:
            raise RuntimeError(f"futu subscribe error: {err}")
        ret, data = ctx.get_stock_quote([ticker])
        if ret != futu.RET_OK:
            raise RuntimeError(f"futu API error: {data}")
        return float(data["last_price"].iloc[0])
