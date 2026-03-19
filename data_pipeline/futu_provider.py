"""
futu 期权链数据提供器

封装 futu API 调用，返回与 app.py yfinance 路径相同格式的期权链数据。
底层调用全部来自 futu_tested_functions.py 已验证函数。
"""
import logging
import math
import time
from datetime import datetime, timedelta

import futu
import pandas as pd

from futu_tested_functions import create_quote_ctx, get_option_expiration_dates

logger = logging.getLogger(__name__)

_CHAIN_BATCH_DAYS = 29   # get_option_chain 跨度上限 30 天
_QUOTE_BATCH_SIZE = 200   # 每批 subscribe / get_stock_quote 的合约数


# ---------------------------------------------------------------------------
# 工具函数（与 app.py option_chain() 内同名函数逻辑一致）
# ---------------------------------------------------------------------------

def _clean(v):
    """Convert NaN / inf / N/A to None for JSON serialisation."""
    try:
        if v is None:
            return None
        if isinstance(v, str) and v.strip().upper() == "N/A":
            return None
        fv = float(v)
        return None if (math.isnan(fv) or math.isinf(fv)) else round(fv, 4)
    except Exception:
        return str(v) if v is not None else None


def _liquidity_score(strike, bid, ask, last, oi, volume, spot_val):
    """Liquidity score: GOOD / FAIR / AVOID."""
    issues: list[str] = []
    bid_ = bid if (bid and bid > 0) else None
    ask_ = ask if (ask and ask > 0) else None
    if bid_ is not None and ask_ is not None:
        mid = (bid_ + ask_) / 2
        spread_pct = (ask_ - bid_) / mid if mid > 0 else 1.0
        if spread_pct > 0.20:
            issues.append(f"spread {spread_pct:.0%}")
    else:
        issues.append("spread N/A")
    oi_ = int(oi) if oi else 0
    if oi_ < 100:
        issues.append(f"OI={oi_}")
    vol_ = int(volume) if volume else 0
    if vol_ < 10:
        issues.append(f"Vol={vol_}")
    if spot_val and spot_val > 0 and strike:
        m = strike / spot_val
        if m < 0.75 or m > 1.35:
            issues.append("deep OTM")
    if len(issues) == 0:
        return "GOOD", ""
    elif len(issues) == 1:
        return "FAIR", issues[0]
    else:
        return "AVOID", " | ".join(issues[:2])


# ---------------------------------------------------------------------------
# 内部批量获取
# ---------------------------------------------------------------------------

def _fetch_all_chains(ctx, ticker: str, expirations: list[str]) -> pd.DataFrame:
    """批量获取期权链静态数据，按 30 天窗口分批调用以遵守频率限制。"""
    all_dfs: list[pd.DataFrame] = []
    i = 0
    while i < len(expirations):
        batch_start = expirations[i]
        start_dt = datetime.strptime(batch_start, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=_CHAIN_BATCH_DAYS)

        j = i + 1
        while j < len(expirations):
            if datetime.strptime(expirations[j], "%Y-%m-%d") > end_dt:
                break
            j += 1
        batch_end = expirations[j - 1]

        ret, df = ctx.get_option_chain(code=ticker, start=batch_start, end=batch_end)
        if ret == futu.RET_OK and isinstance(df, pd.DataFrame) and not df.empty:
            all_dfs.append(df)
        else:
            logger.warning("get_option_chain failed for %s~%s: %s",
                           batch_start, batch_end,
                           df if ret != futu.RET_OK else "empty")
        i = j
        if i < len(expirations):
            time.sleep(3.1)  # rate limit: max 10 per 30s

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


def _fetch_quotes(ctx, codes: list[str]) -> pd.DataFrame:
    """批量 subscribe + get_stock_quote 获取期权动态行情。"""
    if not codes:
        return pd.DataFrame()

    all_dfs: list[pd.DataFrame] = []
    for start in range(0, len(codes), _QUOTE_BATCH_SIZE):
        batch = codes[start : start + _QUOTE_BATCH_SIZE]
        ret_sub, err = ctx.subscribe(batch, [futu.SubType.QUOTE])
        if ret_sub != futu.RET_OK:
            logger.warning("subscribe failed (offset %d): %s", start, err)
            continue
        ret, df = ctx.get_stock_quote(batch)
        if ret == futu.RET_OK and isinstance(df, pd.DataFrame) and not df.empty:
            all_dfs.append(df)
        else:
            logger.warning("get_stock_quote failed (offset %d): %s",
                           start, df if ret != futu.RET_OK else "empty")
        # Release subscription quota immediately
        ctx.unsubscribe(batch, [futu.SubType.QUOTE])
        time.sleep(0.1)  # give SDK time to process unsubscribe

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


# ---------------------------------------------------------------------------
# 字段映射 + 记录构建
# ---------------------------------------------------------------------------

def _build_records(
    static_df: pd.DataFrame,
    quotes_df: pd.DataFrame,
    option_type: str,
    spot: float,
) -> list[dict]:
    """
    合并静态链数据与动态行情，输出与 app.py df_to_records() 相同格式的记录列表。

    字段映射依据 docs/field_mapping.md。
    """
    if static_df.empty:
        return []
    filtered = static_df[static_df["option_type"] == option_type]
    if filtered.empty:
        return []

    # 索引动态行情以 O(1) 查找
    quotes_map: dict[str, pd.Series] = {}
    if not quotes_df.empty:
        for _, qr in quotes_df.iterrows():
            quotes_map[qr["code"]] = qr

    spot_clean = _clean(spot)
    records: list[dict] = []
    for _, row in filtered.iterrows():
        code = row["code"]
        strike = _clean(row["strike_price"])

        # 动态字段（来自 subscribe + get_stock_quote）
        last_price = None
        bid = None          # get_stock_quote 不返回 bid/ask（见 field_mapping.md）
        ask = None
        volume = None
        open_interest = None
        iv = None

        qr = quotes_map.get(code)
        if qr is not None:
            last_price = _clean(qr.get("last_price"))
            volume = _clean(qr.get("volume"))
            open_interest = _clean(qr.get("open_interest"))
            # futu implied_volatility 已为百分比（24.359 = 24.359%），无需再 *100
            iv = _clean(qr.get("implied_volatility"))

        # inTheMoney：CALL ITM = spot > strike，PUT ITM = spot < strike
        itm = False
        if spot and strike:
            itm = (spot > strike) if option_type == "CALL" else (spot < strike)

        score, reason = _liquidity_score(
            strike or 0, bid, ask, last_price, open_interest, volume, spot_clean,
        )

        records.append({
            "strike":       strike,
            "lastPrice":    last_price,
            "bid":          bid,
            "ask":          ask,
            "volume":       volume,
            "openInterest": open_interest,
            "iv":           iv,
            "itm":          itm,
            "liq_score":    score,
            "liq_reason":   reason,
        })

    records.sort(key=lambda r: r["strike"] or 0)
    return records


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def get_option_chain_futu(
    ticker: str,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> dict:
    """
    返回与 yfinance 路径相同格式的期权链数据。

    Args:
        ticker: futu 格式 Ticker，如 ``"US.AAPL"``
        host: futu OpenD 地址
        port: futu OpenD 端口

    Returns:
        ``{"expirations": [...], "chain": {"YYYY-MM-DD": {"calls": [...], "puts": [...]}}, "spot": float}``
    """
    # Step 1: 获取到期日（使用已验证函数，独立连接）
    expirations = get_option_expiration_dates(ticker, host=host, port=port)
    if not expirations:
        return {"expirations": [], "chain": {}, "spot": None}

    # Step 2-4: 共享连接获取 spot + 静态链 + 动态行情
    with create_quote_ctx(host=host, port=port) as ctx:
        # 2. 现货价格（复用 get_spot_price 的 subscribe + get_stock_quote 模式）
        spot = None
        ret_sub, err = ctx.subscribe([ticker], [futu.SubType.QUOTE])
        if ret_sub == futu.RET_OK:
            ret, spot_df = ctx.get_stock_quote([ticker])
            if ret == futu.RET_OK and not spot_df.empty:
                spot = float(spot_df["last_price"].iloc[0])
            else:
                logger.warning("get_stock_quote failed for spot %s: %s", ticker,
                               spot_df if ret != futu.RET_OK else "empty")
            ctx.unsubscribe([ticker], [futu.SubType.QUOTE])
        else:
            logger.warning("subscribe failed for spot %s: %s", ticker, err)

        # 3. 批量获取全部到期日的期权链静态数据
        all_options = _fetch_all_chains(ctx, ticker, expirations)

        # 4. 批量获取全部期权合约的动态行情
        all_codes = all_options["code"].tolist() if not all_options.empty else []
        quotes_df = _fetch_quotes(ctx, all_codes)

        # 5. Release all subscriptions before closing connection
        ret_unsub, err_unsub = ctx.unsubscribe_all()
        if ret_unsub != futu.RET_OK:
            logger.warning("unsubscribe_all failed: %s", err_unsub)
        time.sleep(2)  # allow SDK to process unsubscribe before close

    # 5. 按到期日拆分并构建记录
    chain_data: dict[str, dict] = {}
    for exp in expirations:
        if not all_options.empty:
            exp_options = all_options[all_options["strike_time"] == exp]
        else:
            exp_options = pd.DataFrame()

        chain_data[exp] = {
            "calls": _build_records(exp_options, quotes_df, "CALL", spot),
            "puts":  _build_records(exp_options, quotes_df, "PUT", spot),
        }

    return {
        "expirations": expirations,
        "chain": chain_data,
        "spot": _clean(spot),
    }
