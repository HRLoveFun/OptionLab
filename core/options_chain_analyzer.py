"""
Options Chain Analyzer - Real-time IV surface, skew, OI profile, and expected move.

Fetches live option chain data via yfinance and generates matplotlib charts
(returned as base64 PNG strings) and HTML tables for the Options Chain Analysis tab.
"""

import io
import base64
import logging
import datetime as dt
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (needed for 3D projection)
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    result = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)
    return result


def _atm_strike(strikes, spot: float) -> float:
    return min(strikes, key=lambda x: abs(x - spot))


def _calc_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    strikes = sorted(set(calls['strike']) | set(puts['strike']))
    losses = []
    for s in strikes:
        call_loss = ((calls['strike'] - s).clip(lower=0) * calls['openInterest']).sum()
        put_loss  = ((s - puts['strike']).clip(lower=0) * puts['openInterest']).sum()
        losses.append(call_loss + put_loss)
    return strikes[losses.index(min(losses))]


def _calc_expected_move(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> Optional[float]:
    atm = _atm_strike(calls['strike'].tolist(), spot)
    c_ask = calls.loc[calls['strike'] == atm, 'ask'].values
    p_ask = puts.loc[puts['strike']  == atm, 'ask'].values
    if len(c_ask) > 0 and len(p_ask) > 0:
        return float(c_ask[0]) + float(p_ask[0])
    return None


def _calc_25d_skew(puts: pd.DataFrame, calls: pd.DataFrame, spot: float) -> Optional[float]:
    try:
        put_iv  = puts.loc[(puts['strike'] / spot - 0.97).abs().idxmin(), 'impliedVolatility']
        call_iv = calls.loc[(calls['strike'] / spot - 1.03).abs().idxmin(), 'impliedVolatility']
        return float(put_iv - call_iv)
    except Exception:
        return None


def _dte(expiry_str: str) -> int:
    """Days to expiry from today."""
    today = dt.date.today()
    exp  = dt.datetime.strptime(expiry_str, '%Y-%m-%d').date()
    return max(0, (exp - today).days)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class OptionsChainAnalyzer:
    """Fetches and analyses an option chain snapshot via yfinance."""

    def __init__(self, ticker: str = "^SPX"):
        self.ticker = ticker
        tk = yf.Ticker(ticker)

        # Spot price
        fi = tk.fast_info
        self.spot: float = float(
            getattr(fi, 'last_price', None)
            or getattr(fi, 'regularMarketPrice', None)
            or tk.history(period='1d')['Close'].iloc[-1]
        )

        # Expiries
        self.expiries: list = list(tk.options)

        # Chain: {expiry_str: {"calls": DataFrame, "puts": DataFrame}}
        self.chain: dict = {}
        for exp in self.expiries:
            try:
                opt = tk.option_chain(exp)
                calls = opt.calls.copy()
                puts  = opt.puts.copy()
                # Ensure numeric columns
                for col in ['strike', 'bid', 'ask', 'impliedVolatility',
                            'openInterest', 'volume', 'lastPrice']:
                    if col in calls.columns:
                        calls[col] = pd.to_numeric(calls[col], errors='coerce')
                    if col in puts.columns:
                        puts[col]  = pd.to_numeric(puts[col],  errors='coerce')
                # Fill NaN openInterest / volume with 0
                for col in ['openInterest', 'volume']:
                    calls[col] = calls[col].fillna(0)
                    puts[col]  = puts[col].fillna(0)
                self.chain[exp] = {'calls': calls, 'puts': puts}
            except Exception as e:
                logger.warning(f"Could not load chain for {exp}: {e}")

    # ------------------------------------------------------------------
    # 1.1  Snapshot summary
    # ------------------------------------------------------------------

    def get_snapshot_summary(self) -> dict:
        nearest = self.expiries[0] if self.expiries else None
        if nearest and nearest in self.chain:
            calls = self.chain[nearest]['calls']
            atm   = _atm_strike(calls['strike'].tolist(), self.spot)
        else:
            atm = None
        return {
            'spot':           round(self.spot, 2),
            'expiries':       self.expiries,
            'nearest_expiry': nearest,
            'atm_strike':     atm,
            'timestamp':      dt.datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
        }

    # ------------------------------------------------------------------
    # 1.2  IV Smile
    # ------------------------------------------------------------------

    def plot_iv_smile(self, expiry: str) -> Optional[str]:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]['calls'].dropna(subset=['impliedVolatility'])
            puts  = self.chain[expiry]['puts'].dropna(subset=['impliedVolatility'])

            atm = _atm_strike(calls['strike'].tolist(), self.spot)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(calls['strike'], calls['impliedVolatility'] * 100,
                    color='tab:blue', linestyle='--', linewidth=1.8, label='Calls IV')
            ax.plot(puts['strike'],  puts['impliedVolatility']  * 100,
                    color='tab:orange', linestyle='-', linewidth=1.8, label='Puts IV')
            ax.axvline(atm,         color='grey', linestyle=':', linewidth=1.2,
                       label=f'ATM ~{atm:.0f}')
            ax.axvline(self.spot,   color='black', linestyle='-', linewidth=1,
                       alpha=0.5, label=f'Spot {self.spot:.2f}')

            ax.set_xlabel('Strike')
            ax.set_ylabel('Implied Volatility (%)')
            ax.set_title(f'IV Smile — {expiry}  |  Spot: {self.spot:.2f}')
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f%%'))
            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_iv_smile failed for {expiry}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.3  IV Term Structure
    # ------------------------------------------------------------------

    def plot_iv_term_structure(self) -> Optional[str]:
        try:
            dates, atm_ivs = [], []
            for exp in self.expiries:
                if exp not in self.chain:
                    continue
                puts = self.chain[exp]['puts'].dropna(subset=['impliedVolatility'])
                if puts.empty:
                    continue
                idx = (puts['strike'] - self.spot).abs().idxmin()
                atm_ivs.append(float(puts.loc[idx, 'impliedVolatility']) * 100)
                dates.append(exp)

            if len(dates) < 2:
                return None

            fig, ax = plt.subplots(figsize=(10, 5))
            x = range(len(dates))
            # Colour each segment: contango=green, backwardation=red
            for i in range(len(dates) - 1):
                color = 'green' if atm_ivs[i + 1] >= atm_ivs[i] else 'red'
                ax.plot([i, i + 1], [atm_ivs[i], atm_ivs[i + 1]],
                        color=color, linewidth=2)
            ax.scatter(x, atm_ivs, color='tab:blue', zorder=5, s=40)
            for xi, iv in zip(x, atm_ivs):
                ax.annotate(f'{iv:.1f}%', (xi, iv), textcoords='offset points',
                            xytext=(0, 6), ha='center', fontsize=7)

            ax.set_xticks(list(x))
            ax.set_xticklabels(dates, rotation=45, ha='right', fontsize=7)
            ax.set_ylabel('ATM Put IV (%)')
            ax.set_title(f'IV Term Structure  |  Spot: {self.spot:.2f}')
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f%%'))
            ax.grid(alpha=0.3)

            # Annotate contango / backwardation
            slope = atm_ivs[-1] - atm_ivs[0]
            label = 'Contango (Normal)' if slope >= 0 else 'Backwardation (Inverted)'
            color = 'green' if slope >= 0 else 'red'
            ax.text(0.98, 0.95, label, transform=ax.transAxes,
                    ha='right', va='top', color=color, fontsize=9, fontweight='bold')
            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_iv_term_structure failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.4  IV Surface (3D)
    # ------------------------------------------------------------------

    def plot_iv_surface(self) -> Optional[str]:
        try:
            records = []
            for exp in self.expiries:
                if exp not in self.chain:
                    continue
                dte = _dte(exp)
                puts = self.chain[exp]['puts'].dropna(subset=['impliedVolatility'])
                for _, row in puts.iterrows():
                    moneyness = float(row['strike']) / self.spot
                    iv        = float(row['impliedVolatility']) * 100
                    if 0.7 <= moneyness <= 1.3 and iv > 0:
                        records.append({'moneyness': moneyness, 'dte': dte, 'iv': iv})

            if len(records) < 6:
                return None

            df = pd.DataFrame(records)
            X  = df['moneyness'].values
            Y  = df['dte'].values
            Z  = df['iv'].values

            fig = plt.figure(figsize=(12, 7))
            ax  = fig.add_subplot(111, projection='3d')
            sc  = ax.scatter(X, Y, Z, c=Z, cmap='RdYlGn_r', s=15, alpha=0.8)
            fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.1, label='IV (%)')

            ax.set_xlabel('Moneyness\n(Strike / Spot)', labelpad=10)
            ax.set_ylabel('DTE (days)',                 labelpad=10)
            ax.set_zlabel('Put IV (%)',                 labelpad=10)
            ax.set_title(f'IV Surface — {self.ticker}  |  Spot: {self.spot:.2f}')
            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_iv_surface failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.5  Skew Analysis
    # ------------------------------------------------------------------

    def plot_skew_analysis(self, expiry: str) -> Optional[str]:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]['calls'].dropna(subset=['impliedVolatility'])
            puts  = self.chain[expiry]['puts'].dropna(subset=['impliedVolatility'])

            atm_iv = float(
                puts.loc[(puts['strike'] - self.spot).abs().idxmin(), 'impliedVolatility']
            ) * 100

            puts2  = puts.copy()
            puts2['moneyness']  = puts2['strike'] / self.spot
            puts2['put_skew']   = puts2['impliedVolatility'] * 100 - atm_iv
            puts2 = puts2[puts2['moneyness'] <= 1.0].sort_values('moneyness')

            # Risk Reversal per row (align by moneyness)
            merged = pd.merge_asof(
                puts2.sort_values('strike')[['strike', 'moneyness', 'impliedVolatility']],
                calls.sort_values('strike')[['strike', 'impliedVolatility']],
                on='strike', suffixes=('_put', '_call'), direction='nearest'
            )
            merged['rr'] = (merged['impliedVolatility_put'] - merged['impliedVolatility_call']) * 100

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=False)

            # Sub-plot 1: Put Skew
            ax1.plot(puts2['moneyness'], puts2['put_skew'],
                     color='tab:orange', linewidth=1.8)
            ax1.axhline(0, color='grey', linestyle='--', linewidth=1)
            ax1.axvline(1.0, color='black', linestyle=':', linewidth=1, alpha=0.5)
            ax1.set_ylabel('Put Skew (OTM Put IV − ATM IV) %')
            ax1.set_title(f'Skew Analysis — {expiry}')
            ax1.grid(alpha=0.3)

            # Sub-plot 2: Risk Reversal
            ax2.bar(merged['moneyness'], merged['rr'],
                    color=['red' if v > 0 else 'green' for v in merged['rr']],
                    width=0.005, alpha=0.8)
            ax2.axhline(0, color='grey', linestyle='--', linewidth=1)
            ax2.set_xlabel('Moneyness (Strike / Spot)')
            ax2.set_ylabel('Risk Reversal (Put IV − Call IV) %')
            ax2.grid(alpha=0.3)

            # Annotate 25Δ skew
            skew_25 = _calc_25d_skew(puts, calls, self.spot)
            if skew_25 is not None:
                ax2.text(0.02, 0.95, f'25Δ Skew: {skew_25 * 100:.2f}%',
                         transform=ax2.transAxes, fontsize=9, va='top',
                         color='darkred', fontweight='bold')

            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_skew_analysis failed for {expiry}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.6  OI / Volume Profile
    # ------------------------------------------------------------------

    def plot_oi_volume_profile(self, expiry: str) -> Optional[str]:
        try:
            if expiry not in self.chain:
                return None
            calls = self.chain[expiry]['calls']
            puts  = self.chain[expiry]['puts']

            max_pain = _calc_max_pain(calls, puts)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

            # ----- OI -----
            ax1.barh(calls['strike'], calls['openInterest'],
                     color='green', alpha=0.7, label='Call OI', height=2)
            ax1.barh(puts['strike'],  -puts['openInterest'],
                     color='red',   alpha=0.7, label='Put OI', height=2)
            ax1.axhline(self.spot,    color='black',   linestyle='--', linewidth=1.5,
                        label=f'Spot {self.spot:.0f}')
            ax1.axhline(max_pain,     color='purple',  linestyle=':',  linewidth=1.5,
                        label=f'Max Pain {max_pain:.0f}')
            ax1.set_xlabel('Open Interest  (Call +ve / Put −ve)')
            ax1.set_ylabel('Strike')
            ax1.set_title('OI Distribution')
            ax1.legend(fontsize=8)
            ax1.grid(axis='x', alpha=0.3)

            # ----- Volume -----
            ax2.barh(calls['strike'], calls['volume'],
                     color='green', alpha=0.7, label='Call Volume', height=2)
            ax2.barh(puts['strike'],  -puts['volume'],
                     color='red',   alpha=0.7, label='Put Volume', height=2)
            ax2.axhline(self.spot,    color='black',   linestyle='--', linewidth=1.5,
                        label=f'Spot {self.spot:.0f}')
            ax2.axhline(max_pain,     color='purple',  linestyle=':',  linewidth=1.5,
                        label=f'Max Pain {max_pain:.0f}')
            ax2.set_xlabel('Volume  (Call +ve / Put −ve)')
            ax2.set_title('Volume Distribution')
            ax2.legend(fontsize=8)
            ax2.grid(axis='x', alpha=0.3)

            fig.suptitle(f'OI / Volume Profile — {expiry}  |  Spot: {self.spot:.2f}',
                         fontsize=12)
            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_oi_volume_profile failed for {expiry}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.7  PCR Summary
    # ------------------------------------------------------------------

    def plot_pcr_summary(self) -> Optional[str]:
        try:
            rows = []
            for exp in self.expiries[:12]:   # limit to 12 expiries for readability
                if exp not in self.chain:
                    continue
                calls = self.chain[exp]['calls']
                puts  = self.chain[exp]['puts']
                c_vol = calls['volume'].sum()
                p_vol = puts['volume'].sum()
                c_oi  = calls['openInterest'].sum()
                p_oi  = puts['openInterest'].sum()
                vol_pcr = (p_vol / c_vol) if c_vol > 0 else np.nan
                oi_pcr  = (p_oi  / c_oi)  if c_oi  > 0 else np.nan
                rows.append({'expiry': exp, 'vol_pcr': vol_pcr, 'oi_pcr': oi_pcr})

            if not rows:
                return None

            df = pd.DataFrame(rows).dropna(subset=['vol_pcr', 'oi_pcr'])

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, max(4, len(df) * 0.6 + 1)))

            for ax, col, title in [
                (ax1, 'vol_pcr', 'Volume PCR'),
                (ax2, 'oi_pcr',  'OI PCR'),
            ]:
                colors = ['red' if v > 1.3 else ('green' if v < 0.7 else 'tab:blue')
                          for v in df[col]]
                ax.barh(df['expiry'], df[col], color=colors, alpha=0.8)
                ax.axvline(1.0, color='grey',   linestyle='--', linewidth=1.2, label='PCR=1 (Neutral)')
                ax.axvline(0.7, color='green',  linestyle=':',  linewidth=1.0, label='PCR=0.7 (Bullish)')
                ax.axvline(1.3, color='red',    linestyle=':',  linewidth=1.0, label='PCR=1.3 (Bearish)')
                ax.set_xlabel('PCR')
                ax.set_title(title)
                ax.legend(fontsize=7)
                ax.grid(axis='x', alpha=0.3)

            fig.suptitle(f'Put/Call Ratio by Expiry — {self.ticker}', fontsize=12)
            fig.tight_layout()
            return _fig_to_base64(fig)
        except Exception as e:
            logger.error(f"plot_pcr_summary failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.8  Expected Move Table (HTML)
    # ------------------------------------------------------------------

    def get_expected_move_table(self) -> Optional[str]:
        try:
            rows = []
            for exp in self.expiries:
                if exp not in self.chain:
                    continue
                calls = self.chain[exp]['calls']
                puts  = self.chain[exp]['puts']
                dte   = _dte(exp)
                em    = _calc_expected_move(calls, puts, self.spot)
                if em is None:
                    continue
                em_pct     = em / self.spot * 100
                upper      = self.spot + em
                lower      = self.spot - em
                rows.append({
                    'Expiry':         exp,
                    'DTE':            dte,
                    'ATM Straddle':   f'${em:.2f}',
                    'Exp Move':       f'${em:.2f}',
                    'Exp Move %':     f'{em_pct:.2f}%',
                    'Upper Bound':    f'{upper:.2f}',
                    'Lower Bound':    f'{lower:.2f}',
                })

            if not rows:
                return '<p>No expected move data available.</p>'

            df = pd.DataFrame(rows)
            return df.to_html(index=False, classes='table table-striped',
                              border=0, justify='center')
        except Exception as e:
            logger.error(f"get_expected_move_table failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 1.9  Key Metrics Table (HTML)
    # ------------------------------------------------------------------

    def get_key_metrics_table(self) -> Optional[str]:
        try:
            nearest = self.expiries[0] if self.expiries else None
            second  = self.expiries[1] if len(self.expiries) > 1 else None

            # Nearest expiry ATM IV
            near_atm_iv = None
            if nearest and nearest in self.chain:
                puts = self.chain[nearest]['puts'].dropna(subset=['impliedVolatility'])
                if not puts.empty:
                    idx = (puts['strike'] - self.spot).abs().idxmin()
                    near_atm_iv = float(puts.loc[idx, 'impliedVolatility']) * 100

            # 25Δ Skew
            skew_25 = None
            if nearest and nearest in self.chain:
                c = self.chain[nearest]['calls']
                p = self.chain[nearest]['puts']
                s = _calc_25d_skew(p, c, self.spot)
                skew_25 = s * 100 if s is not None else None

            # Term structure slope (near IV - second IV)
            ts_slope = None
            second_iv = None
            if second and second in self.chain:
                puts = self.chain[second]['puts'].dropna(subset=['impliedVolatility'])
                if not puts.empty:
                    idx = (puts['strike'] - self.spot).abs().idxmin()
                    second_iv = float(puts.loc[idx, 'impliedVolatility']) * 100
            if near_atm_iv is not None and second_iv is not None:
                ts_slope = near_atm_iv - second_iv

            # PCR near month
            near_pcr = None
            if nearest and nearest in self.chain:
                calls = self.chain[nearest]['calls']
                puts  = self.chain[nearest]['puts']
                c_vol = calls['volume'].sum()
                p_vol = puts['volume'].sum()
                near_pcr = p_vol / c_vol if c_vol > 0 else None

            # Expected move near month
            near_em = None
            if nearest and nearest in self.chain:
                calls = self.chain[nearest]['calls']
                puts  = self.chain[nearest]['puts']
                near_em = _calc_expected_move(calls, puts, self.spot)

            # Max Pain near month
            max_pain_val = None
            if nearest and nearest in self.chain:
                calls = self.chain[nearest]['calls']
                puts  = self.chain[nearest]['puts']
                try:
                    max_pain_val = _calc_max_pain(calls, puts)
                except Exception:
                    pass

            def _fmt(v, fmt='.2f', suffix=''):
                return f'{v:{fmt}}{suffix}' if v is not None else 'N/A'

            rows = [
                ('Spot Price',               _fmt(self.spot,    '.2f')),
                ('Nearest Expiry',           nearest or 'N/A'),
                ('Nearest ATM IV',           _fmt(near_atm_iv,  '.2f', '%')),
                ('25Δ Put Skew (near)',       _fmt(skew_25,      '.2f', '%')),
                ('Term Structure Slope',      _fmt(ts_slope,     '.2f', '%')),
                ('PCR — near month (Vol)',    _fmt(near_pcr,     '.3f')),
                ('Expected Move (near)',      _fmt(near_em,      '.2f', ' pts') if near_em else 'N/A'),
                ('Max Pain (near)',           _fmt(max_pain_val, '.0f')),
            ]

            df = pd.DataFrame(rows, columns=['Metric', 'Value'])
            return df.to_html(index=False, classes='table table-striped',
                              border=0, justify='center')
        except Exception as e:
            logger.error(f"get_key_metrics_table failed: {e}", exc_info=True)
            return None
