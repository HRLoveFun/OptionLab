from flask import Flask, request, render_template, jsonify
import atexit
import logging
import math
import os
import re
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
load_dotenv()


from services.form_service import FormService
from services.analysis_service import AnalysisService
from services.market_service import MarketService
from services.validation_service import ValidationService
from services.options_chain_service import OptionsChainService
from data_pipeline.data_service import DataService
from data_pipeline.scheduler import UpdateScheduler
from utils.utils import (
    DEFAULT_TICKER, DEFAULT_FREQUENCY, DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW, DEFAULT_SIDE_BIAS
)

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DB
DataService.initialize()
_scheduler = None
try:
    auto_update = os.environ.get("AUTO_UPDATE_TICKERS", "").strip()
    if auto_update:
        tickers = [t.strip().upper() for t in auto_update.split(",") if t.strip()]
        if tickers:
            _scheduler = UpdateScheduler()
            _scheduler.start_daily_update(tickers)
            _scheduler.start_monthly_correlation_update(tickers)
            logger.info(f"Auto-update scheduler started for: {tickers}")
            logger.info(f"Monthly correlation update scheduler started for: {tickers}")
except Exception as e:
    logger.warning(f"Scheduler init failed: {e}")

if _scheduler is not None:
    atexit.register(lambda: _scheduler.scheduler.shutdown(wait=False))

def parse_tickers(raw: str) -> list[str]:
    """Parse comma/newline separated tickers, deduplicate, max 6."""
    tickers = [t.strip().upper() for t in re.split(r'[,\n]+', raw) if t.strip()]
    seen = []
    for t in tickers:
        if t not in seen:
            seen.append(t)
    return seen[:6]


def _run_single_ticker_analysis(ticker: str, form_data: dict) -> dict:
    """Run full analysis pipeline for one ticker (designed for ThreadPoolExecutor)."""
    single_form = {**form_data, 'ticker': ticker}
    try:
        analysis_results = AnalysisService.generate_complete_analysis(single_form)
    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {e}", exc_info=True)
        analysis_results = {'error': str(e)}

    # Options chain analysis (non-blocking per ticker)
    try:
        oc_results = OptionsChainService.generate_options_chain_analysis(ticker)
        analysis_results.update(oc_results)
    except Exception as e:
        logger.warning(f"Options chain analysis failed for {ticker}: {e}")

    return analysis_results


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main dashboard route — supports multi-ticker analysis.
    GET: Render dashboard form.
    POST: Parse tickers, run analysis per ticker, render results.
    """
    try:
        if request.method == 'POST':
            # Extract and validate form data
            form_data = FormService.extract_form_data(request)
            validation_error = ValidationService.validate_input_data(form_data)

            if validation_error:
                return render_template('index.html', error=validation_error)

            # Parse multi-ticker input
            tickers_raw = form_data.get('ticker', '')
            tickers = parse_tickers(tickers_raw)
            if not tickers:
                return render_template('index.html', error='Please enter at least one ticker symbol.')

            # Concurrent analysis for each ticker
            results_by_ticker = {}
            max_workers = min(len(tickers), 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_run_single_ticker_analysis, ticker, form_data): ticker
                    for ticker in tickers
                }
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        results_by_ticker[ticker] = future.result()
                    except Exception as e:
                        logger.error(f"Ticker {ticker} analysis exception: {e}")
                        results_by_ticker[ticker] = {'error': str(e)}

            # Generate summary analysis (multi-ticker only)
            summary_data = None
            if len(tickers) > 1:
                try:
                    summary_data = AnalysisService.generate_summary_analysis(
                        tickers, results_by_ticker
                    )
                except Exception as e:
                    logger.warning(f"Summary analysis failed: {e}")

            # Use first ticker's form_data for template defaults
            first_ticker = tickers[0]
            first_result = results_by_ticker.get(first_ticker, {})
            template_data = {
                **form_data,
                **first_result,
                'ticker': first_ticker,
                'tickers': tickers,
                'tickers_raw': ', '.join(tickers),
                'results_by_ticker': results_by_ticker,
                'summary_data': summary_data,
            }

            return render_template('index.html', **template_data)

        return render_template('index.html',
            ticker=DEFAULT_TICKER,
            tickers=[DEFAULT_TICKER],
            tickers_raw=DEFAULT_TICKER,
            start_time=(
                lambda today: f"{today.year - 5}-{today.month:02d}"
            )(dt.date.today()),
            end_time='',
            frequency=DEFAULT_FREQUENCY,
            risk_threshold=DEFAULT_RISK_THRESHOLD,
            rolling_window=DEFAULT_ROLLING_WINDOW,
            side_bias=DEFAULT_SIDE_BIAS,
        )

    except Exception as e:
        logger.error(f"Unexpected error in main route: {e}", exc_info=True)
        return render_template('index.html',
            error=f"An unexpected error occurred: {str(e)}. Please try again.")

@app.route('/api/option_chain', methods=['GET'])
def option_chain():
    """
    API endpoint to fetch live option chain data from Yahoo Finance.
    Query params: ticker (required)
    Response: { expirations: [...], chain: { date: { calls: [...], puts: [...] } } }
    """
    import yfinance as yf

    ticker_sym = request.args.get('ticker', '').strip().upper()
    if not ticker_sym:
        return jsonify({'error': 'ticker is required'}), 400

    source = request.args.get('source', 'yfinance').strip().lower()
    if source == 'futu':
        try:
            from data_pipeline.futu_provider import get_option_chain_futu
            futu_host = os.environ.get('FUTU_HOST', '127.0.0.1')
            futu_port = int(os.environ.get('FUTU_PORT', '11111'))
            result = get_option_chain_futu(ticker_sym, host=futu_host, port=futu_port)
            return jsonify(result)
        except Exception as e:
            logger.error("Error fetching futu option chain for %s: %s", ticker_sym, e, exc_info=True)
            return jsonify({'error': str(e)}), 500

    def clean(v):
        """Convert NaN / inf to None for JSON serialisation."""
        try:
            if v is None:
                return None
            fv = float(v)
            return None if (math.isnan(fv) or math.isinf(fv)) else round(fv, 4)
        except Exception:
            return str(v) if v is not None else None

    try:
        tkr = yf.Ticker(ticker_sym)
        expirations = list(tkr.options)
        if not expirations:
            return jsonify({'error': f'No options available for {ticker_sym}'}), 404

        CALL_COLS = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest',
                     'impliedVolatility', 'inTheMoney']
        PUT_COLS  = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest',
                     'impliedVolatility', 'inTheMoney']

        # Current price for ATM highlighting and liquidity scoring
        try:
            fi = tkr.fast_info
            price = getattr(fi, 'last_price', None) or getattr(fi, 'regularMarketPrice', None)
            spot = clean(price)
        except Exception:
            spot = None

        def _liquidity_score(strike, bid, ask, last, oi, volume, spot_val):
            """Liquidity score: GOOD / FAIR / AVOID."""
            issues = []
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
                return 'GOOD', ''
            elif len(issues) == 1:
                return 'FAIR', issues[0]
            else:
                return 'AVOID', ' | '.join(issues[:2])

        chain_data = {}
        for exp in expirations:
            opt = tkr.option_chain(exp)
            calls_df = opt.calls[CALL_COLS].sort_values('strike') if hasattr(opt, 'calls') else None
            puts_df  = opt.puts[PUT_COLS].sort_values('strike')  if hasattr(opt, 'puts')  else None

            def df_to_records(df):
                if df is None or df.empty:
                    return []
                rows = []
                for _, r in df.iterrows():
                    strike = clean(r.get('strike'))
                    bid_   = clean(r.get('bid'))
                    ask_   = clean(r.get('ask'))
                    last_  = clean(r.get('lastPrice'))
                    oi_    = clean(r.get('openInterest'))
                    vol_   = clean(r.get('volume'))
                    score, reason = _liquidity_score(
                        strike or 0, bid_, ask_, last_, oi_, vol_, spot
                    )
                    rows.append({
                        'strike':        strike,
                        'lastPrice':     last_,
                        'bid':           bid_,
                        'ask':           ask_,
                        'volume':        vol_,
                        'openInterest':  oi_,
                        'iv':            clean((r.get('impliedVolatility') or 0) * 100),
                        'itm':           bool(r.get('inTheMoney', False)),
                        'liq_score':     score,
                        'liq_reason':    reason,
                    })
                return rows

            chain_data[exp] = {
                'calls': df_to_records(calls_df),
                'puts':  df_to_records(puts_df),
            }

        return jsonify({'expirations': expirations, 'chain': chain_data, 'spot': spot})

    except Exception as e:
        logger.error(f"Error fetching option chain for {ticker_sym}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate_ticker', methods=['POST'])
def validate_ticker():
    """
    API endpoint to validate ticker symbol.
    Request: JSON {"ticker": "AAPL"}
    Response: {"valid": true/false, "message": "..."}
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()

        if not ticker:
            return jsonify({'valid': False, 'message': 'Please enter a ticker symbol'})

        # Validate ticker using market service
        is_valid, message = MarketService.validate_ticker(ticker)

        return jsonify({
            'valid': is_valid,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error validating ticker: {e}")
        return jsonify({'valid': False, 'message': f'Error validating ticker: {str(e)}'})


# ── Module 0: Bulk ticker validation ──────────────────────────────
@app.route('/api/validate_tickers', methods=['POST'])
def validate_tickers_bulk():
    """Validate multiple tickers at once. Returns {status, results: {TICKER: {valid, price, message}}}."""
    data = request.get_json(silent=True) or {}
    tickers = data.get('tickers', [])
    results = {}
    for ticker in tickers[:10]:
        try:
            is_valid, message = MarketService.validate_ticker(ticker)
            price = None
            if is_valid:
                try:
                    import yfinance as yf
                    info = yf.Ticker(ticker).fast_info
                    price = float(info.get('lastPrice', 0) or info.get('regularMarketPrice', 0))
                except Exception:
                    pass
            results[ticker] = {"valid": is_valid, "price": price, "message": message}
        except Exception:
            results[ticker] = {"valid": False, "price": None, "message": "validation error"}
    return jsonify({"status": "ok", "results": results})


# ── Module 1: Option chain preload & cache ────────────────────────
_option_chain_cache: dict = {}
CACHE_TTL_MINUTES = 15


@app.route('/api/preload_option_chain', methods=['POST'])
def preload_option_chain():
    """Pre-load option chain for Position module dropdowns."""
    data = request.get_json(silent=True) or {}
    ticker = data.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify({"status": "error", "message": "No ticker provided"})

    cached = _option_chain_cache.get(ticker)
    if cached:
        age = (dt.datetime.now() - cached['ts']).total_seconds() / 60
        if age < CACHE_TTL_MINUTES:
            return jsonify({"status": "ok", **cached['data']})

    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer, _dte
        analyzer = OptionsChainAnalyzer(ticker)
        chain_out = {}
        for exp in analyzer.expiries:
            if exp not in analyzer.chain:
                continue
            calls_df = analyzer.chain[exp]['calls']
            puts_df = analyzer.chain[exp]['puts']

            def df_to_list(df):
                result = []
                for _, row in df.iterrows():
                    bid = float(row.get('bid', 0) or 0)
                    ask = float(row.get('ask', 0) or 0)
                    mid = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row.get('lastPrice', 0) or 0)
                    result.append({
                        "strike": float(row['strike']),
                        "bid": round(bid, 2),
                        "ask": round(ask, 2),
                        "mid": round(mid, 2),
                        "last": round(float(row.get('lastPrice', 0) or 0), 2),
                        "iv": round(float(row.get('impliedVolatility', 0) or 0), 4),
                        "iv_pct": round(float(row.get('impliedVolatility', 0) or 0) * 100, 1),
                        "oi": int(row.get('openInterest', 0) or 0),
                        "volume": int(row.get('volume', 0) or 0),
                        "dte": _dte(exp),
                    })
                return result

            chain_out[exp] = {
                "calls": df_to_list(calls_df),
                "puts": df_to_list(puts_df),
            }

        payload = {
            "ticker": analyzer.ticker,
            "spot": round(analyzer.spot, 2),
            "expiries": analyzer.expiries,
            "chain": chain_out,
        }
        _option_chain_cache[ticker] = {"ts": dt.datetime.now(), "data": payload}
        return jsonify({"status": "ok", **payload})

    except Exception as e:
        logger.error(f"preload_option_chain failed for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)})


# ── Module 3: Portfolio analysis  ─────────────────────────────────
@app.route('/api/portfolio_analysis', methods=['POST'])
def portfolio_analysis():
    """Analyse a multi-leg option portfolio."""
    data = request.get_json(silent=True) or {}
    positions = data.get('positions', [])
    account_size = data.get('account_size')
    max_risk_pct = data.get('max_risk_pct', 2.0)

    if not positions:
        return jsonify({"status": "error", "message": "No positions provided"})

    try:
        from services.portfolio_analysis_service import PortfolioAnalysisService
        result = PortfolioAnalysisService.run(positions, account_size, max_risk_pct)
        return jsonify(result)
    except Exception as e:
        logger.error(f"portfolio_analysis error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})


# ── Module 4A: Market Review time-series ──────────────────────────
@app.route('/api/market_review_ts', methods=['POST'])
def market_review_ts():
    """Return time-series data for interactive Market Review chart."""
    data = request.get_json(silent=True) or {}
    ticker = data.get('ticker', '').strip().upper()
    start_date = data.get('start_date')
    if not ticker:
        return jsonify({"status": "error", "message": "No ticker provided"})
    try:
        from core.market_review import market_review_timeseries
        result = market_review_timeseries(ticker, start_date=start_date)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"market_review_ts error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})


# ── Module 4B: Odds with vol context ─────────────────────────────
@app.route('/api/odds_with_vol', methods=['POST'])
def odds_with_vol():
    """Return odds data enriched with implied realized vol vs ATM IV."""
    data = request.get_json(silent=True) or {}
    ticker = data.get('ticker', '').strip().upper()
    target_pct = float(data.get('target_pct', 105))
    if not ticker:
        return jsonify({"status": "error", "message": "No ticker provided"})
    try:
        from core.options_chain_analyzer import OptionsChainAnalyzer, get_odds_with_vol_context
        analyzer = OptionsChainAnalyzer(ticker)
        result = get_odds_with_vol_context(
            spot=analyzer.spot, target_pct=target_pct,
            chain=analyzer.chain, expiries=analyzer.expiries,
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error(f"odds_with_vol error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
