# Exploration: futu-api as a Second Data Provider

**Date**: 2026-09-11 | **Owner**: repo owner | **Status**: EXPLORATION — no code, no ADR yet

> This document answers decision gate **Q5** of
> [`business_line_reorg.md`](business_line_reorg.md) §8 ("second-provider protocol
> shape … `providers/base.py` must be sketched against *both* yfinance and futu").
> It does **not** propose implementing a futu provider now — ADR 0011 §Decision
> and the 2026-09-10 scope lock (`business_line_reorg.md` §1) both say the seam
> ships first with yfinance as the sole implementation. Treat this as the
> field-and-deployment reference a future "add futu" batch would start from.

Prior art: `archive/futu_integration/` holds a March-2026 integration attempt
(field map + tested-functions log + a `data_pipeline/futu_provider.py` that was
later archived). This doc supersedes and updates that material against the
current codebase and the ADR 0011 canonical-schema target.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Can we connect to futu data? | **Yes, mechanically** — SDK `futu-api 9.5.5508` is installed, `Futu_OpenD.app` is installed and was run as recently as 2026-08, port 11111 configured. Connectivity was live-verified in 2026-03 (AAPL: 26 expiries, 158 contracts). **But not right now**: OpenD is not running, and it needs an interactive Futu account login. |
| What does futu's option data contain? | Static chain (code/strike/expiry/type) from one call; dynamic quote (last/volume/OI/IV/**Greeks**) from a second subscribe-based call. **bid/ask are missing** from the quote path. IV is a **percent** (24.36), not a decimal. |
| How does it map to our format? | Our internal contract is `{ticker, spot, expiries, chain{exp:{calls:DataFrame, puts:DataFrame}}}` with columns `strike, bid, ask, lastPrice, impliedVolatility(decimal), openInterest, volume, inTheMoney`. Mapping is 1:1 except: `impliedVolatility /= 100`, `inTheMoney` computed from strike vs spot, `bid`/`ask` left `NaN`. Ticker conversion already exists (`utils/ticker_utils.py`). |
| How to avoid contention with yfinance? | Four seams: (1) `provider` column as a real DB discriminator; (2) a **separate** throttle — never share `yf_throttle()`; (3) explicit provider selection (env default + per-market routing), not "whoever answers first"; (4) live option data is not persisted (ADR 0004), so cache-key by `(ticker, provider)` and there is no row-level race. |
| Biggest blocker | **OpenD is a stateful, authenticated, GUI-oriented local daemon.** It breaks ADR 0002's "works out of the box / zero infra" property and cannot be dropped onto a headless VPS without the Linux headless build + a login ceremony + crash supervision. |

---

## 1. Part A — Connectivity

### 1.1 How futu-api works (this is not a REST API)

```
  Flask process ──TCP 127.0.0.1:11111──▶  OpenD (local daemon)  ──TLS──▶  Futu servers
   futu.OpenQuoteContext(host, port)          (Futu_OpenD.app)             (auth'd session)
```

- **OpenD** is a separate long-running process that holds the authenticated
  session. The Python SDK (`futu.OpenQuoteContext`) only speaks to OpenD over a
  local socket. There is no way to call Futu directly from Python.
- OpenD ships two ways: the **GUI app** (`Futu_OpenD.app`, what is installed
  here) and a **headless CLI build** (`FutuOpenD` binary + `FutuOpenD.xml` with
  `login_account` / `login_pwd_md5`), the latter being what a server would use.
- Login requires a Futu/moomoo account. The GUI remembers the session; the
  headless build reads credentials from XML and still triggers **device
  verification / 2FA** on first login from a new machine.

### 1.2 State on this machine (2026-09-11)

| Check | Result |
|---|---|
| `futu-api` SDK | ✅ installed, `9.5.5508`, in the base conda env (`/opt/miniconda3`, Python 3.13) — **not** in `.venv` |
| `Futu_OpenD.app` | ✅ `/Applications/Futu_OpenD.app`, config `~/.com.futunn.FutuOpenD/UI/OpenD.xml` → `api_port 11111`, `ip 127.0.0.1`, `lang chs` |
| OpenD running | ❌ port 11111 closed; last logs 2026-07/08, with `FTCrash` entries |
| Live probe from here | ❌ blocked — OpenD down; also SDK not in the project venv |
| Prior live verification | ✅ `archive/futu_integration/project_state.md` — 2026-03-19/20: `get_option_expiration_date('US.AAPL')` → 26 dates; `get_option_chain` → 158 contracts; `get_spot_price('HK.00700')` → 513.0; 10× calls, no FD/thread leak |

**Conclusion**: connectivity is a solved problem *when OpenD is up and logged in*.
Re-verification is an operational step (start OpenD, log in, run the smoke
script), not an engineering unknown.

### 1.3 Re-verification steps (for the user to run)

```bash
# 1. Start OpenD and log in (GUI)
open -a Futu_OpenD          # then complete login + 2FA in the window

# 2. Confirm the gateway is listening
nc -z 127.0.0.1 11111 && echo "OpenD up"

# 3. Smoke test from the env that has futu-api (base conda here)
python - <<'PY'
from futu import OpenQuoteContext, RET_OK
ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
print("expiry:", ctx.get_option_expiration_date(code="US.AAPL")[0] == RET_OK)
ret, chain = ctx.get_option_chain(code="US.AAPL", start="2026-09-19", end="2026-09-19")
print("chain rows:", len(chain) if ret == RET_OK else chain)
ctx.close()
PY
```

### 1.4 Permission & quota caveats (these shape the design)

| Constraint | Value | Consequence for OptionLab |
|---|---|---|
| US **realtime** stock quotes | needs a paid LV1+ market-data pack; **off-hours `subscribe` fails** ("拉取美股夜盘状态失败") | can't rely on futu for US spot; option **metadata** has no such gate |
| Option-chain static call | **10 requests / 30 s**, 30-day expiry window per call | 26 expiries ≈ 26 calls ≈ **80 s+** just for the chain skeleton → **cannot run inline in a request** (breaks `constraints.md` §6) |
| Snapshot (`get_market_snapshot`) | 60 / 30 s, ≤ 400 codes/call; **timed out in every 2026-03 test** | prefer `subscribe` + `get_stock_quote` for dynamic data |
| Subscription quota | **1000 contracts total** per account | AAPL has 3400+ contracts — the tail gets no live quote (bid/ask/vol = `None`) |
| Min subscribe time | 60 s before you may `unsubscribe` | per-request unsubscribe is a no-op; quota frees only on `ctx.close()` |
| History klines | ~10 req/30 s + a small daily quota for non-subscribers | **keep OHLCV history on yfinance** — see §4 |

---

## 2. Part B — What fields futu options data contains

Futu splits an option chain across **three** calls (yfinance does it in one
`option_chain(expiry)`):

### 2.1 `get_option_expiration_date(code)` → expiry list

| futu field | type | example | maps to |
|---|---|---|---|
| `strike_time` | str | `"2026-03-20"` | an element of our `expiries` list |
| `option_expiry_date_distance` | int | `1` | (derive our own `dte`) |
| `expiration_cycle` | str | `"MONTH"` / `"WEEK"` | — (not used) |

### 2.2 `get_option_chain(code, start, end)` → **static** contract metadata

Returns ~14 columns, **no live quote**. The useful ones:

| futu field | type | example | maps to |
|---|---|---|---|
| `code` | str | `"US.AAPL260320C90000"` | `contractSymbol` (optional; not consumed today) |
| `option_type` | str | `"CALL"` / `"PUT"` | selects the `calls` vs `puts` DataFrame |
| `strike_price` | float | `90.0` | `strike` |
| `strike_time` | str | `"2026-03-20"` | the `chain` dict key |
| `stock_owner` | str | `"US.AAPL"` | underlying cross-check |
| `option_area_type` | str | `"AMERICAN"` | — (informational) |

`get_option_chain` also accepts a server-side **`OptionDataFilter`**
(`delta_min/max`, `implied_volatility_min/max`, `open_interest_min/max`,
`vol_min/max`, …) and `option_cond_type` (`WITHIN`/`OUTSIDE` the money) — a
capability yfinance does **not** have, useful for cutting the fetch down before
it hits the subscription quota.

### 2.3 `subscribe([codes], SubType.QUOTE)` + `get_stock_quote` → **dynamic** quote

This is where last price / volume / OI / IV / Greeks come from. Per option
contract:

| futu field | type | example | maps to | note |
|---|---|---|---|---|
| `last_price` | float | `2.25` | `lastPrice` | direct |
| `volume` | int | `3847` | `volume` | direct |
| `open_interest` | int | `227` | `openInterest` | direct; updates pre-market (US) / post-close (HK) |
| `implied_volatility` | float | `24.359` | `impliedVolatility` | **÷ 100** — futu is percent, yfinance/our code is decimal |
| `strike_price` | float | `255.0` | `strike` | direct |
| `delta` `gamma` `vega` `theta` `rho` | float | `0.3366` … | **bonus** — yfinance has none; we compute our own | optional |
| `premium` | float | `3.014` | — | not used |
| `expiry_date_distance` | int | `11` | (derive `dte`) | |
| `contract_multiplier` / `contract_size` | float | `100` | — | assume 100 |
| **`bid` / `ask`** | — | — | ❌ **absent** from `get_stock_quote` | needs `SubType.ORDER_BOOK` + `get_order_book()` per contract — expensive, likely infeasible at chain scale |
| `inTheMoney` | — | — | ❌ **absent** | compute: call ITM ⇔ `strike < spot`, put ITM ⇔ `strike > spot`; `False` when spot unknown |

### 2.4 Field-gap summary

| Our column | Futu source | Action |
|---|---|---|
| `strike` | `strike_price` | direct |
| `lastPrice` | `last_price` | direct |
| `volume` | `volume` | direct (`fillna(0)`) |
| `openInterest` | `open_interest` | direct (`fillna(0)`) |
| `impliedVolatility` | `implied_volatility` | **`/ 100`**, then clamp to the plausibility window `[0.01, 5.0]` (`services/options/chain.py::_iv_ok`) |
| `bid` | — | `NaN` (or ORDER_BOOK later) → liquidity score degrades to "spread N/A" |
| `ask` | — | `NaN` |
| `inTheMoney` | — | computed from `strike` vs `spot` |
| `contractSymbol` | `code` | optional, only if a consumer starts needing it |
| `spot` | see §3.3 | **not** from futu for US off-hours |

---

## 3. Part C — Mapping to the project's data format

### 3.1 The internal contract (de-facto, today)

`data_pipeline/yf_client.py::fetch_option_chain` returns, and every options
consumer expects:

```python
{
  "ticker":  str,
  "spot":    float | None,            # None ⇒ OptionsChainAnalyzer raises RuntimeError
  "expiries": [ "YYYY-MM-DD", ... ],  # front-month first
  "chain": {
     "YYYY-MM-DD": {
        "calls": pd.DataFrame,   # columns below
        "puts":  pd.DataFrame,
     }, ...
  },
}
```

Required DataFrame columns (union across `core/options/**`, `services/options/**`,
`core/decision/candidate.py`):

`strike`, `bid`, `ask`, `lastPrice`, `impliedVolatility` (decimal),
`openInterest`, `volume`, `inTheMoney`.
Numeric coercion + `openInterest`/`volume` `fillna(0)` is done by the fetcher.

ADR 0011's canonical target names this `OptionChainSnapshot` with canonical leg
columns `strike, bid, ask, last, iv, open_interest, volume` — a futu provider
maps into **that**, and the yfinance provider is refactored to do the same, so
`impliedVolatility`-vs-`iv` naming churn happens once, in the seam batch, not in
the futu batch.

### 3.2 Mapping function shape

```
futu_provider.option_chain(yahoo_ticker) -> OptionChainSnapshot
  1. yahoo → futu code           utils.ticker_utils.yahoo_to_futu   (already exists, 27 tests)
  2. get_option_expiration_date  → expiries[]
  3. for each expiry (respect 10/30s): get_option_chain(start=exp,end=exp)
                                 → static rows (code, strike, type)
  4. subscribe(codes[:quota]) + get_stock_quote in batches of ~200
                                 → merge dynamic (last, vol, oi, iv, greeks)
  5. per row: iv/100; itm = f(strike, spot); bid=ask=NaN
  6. build calls/puts DataFrames per expiry
  7. ctx.close()  (frees the subscription quota)
```

This is ~5–80 s of wall time. It **must** run off the request thread — it fits
ADR 0012's readiness-prefetch model (warm `services/options/preload` on a daemon
thread on submit) exactly, and the per-`(ticker, provider)` cache in
`services/options/preload.py` (15-min TTL) absorbs the cost after the first hit.

### 3.3 The `spot` problem

`OptionsChainAnalyzer._init_from_snapshot` raises `RuntimeError` if `spot is
None`. Futu US spot is gated / fails off-hours. Resolution order for a futu
provider:

1. `get_market_snapshot([underlying]).last_price` (if it responds),
2. else `prev_close_price` from the same snapshot,
3. else **fall back to `yfinance` spot** (`yf_client.fetch_spot`) — a deliberate
   cross-provider call, cheap, one request,
4. else return `spot=None` and let the analyzer surface "spot unavailable"
   instead of crashing (the archived code chose this; the analyzer contract
   would need a small softening — a follow-up, not blocking).

### 3.4 OHLCV mapping (recommendation: don't)

Futu history (`request_history_kline`) is heavily quota-limited for non-paying
accounts. yfinance is strictly better for bulk OHLCV. **Keep OHLCV on
yfinance.** If a futu OHLCV path is ever wanted (e.g. HK tickers yfinance covers
poorly), the canonical `raw_bars` row is `provider, symbol, date, open, high,
low, close, adj_close, volume` and futu klines map 1:1 (`time_key`→`date`,
`k_open`→`open`, …, `turnover` dropped); futu has **no `adj_close`** → store
`close` in both, mark it.

### 3.5 Ticker format — already handled

`utils/ticker_utils.py` is done and tested: `normalize_ticker("AAPL")` →
`("AAPL", "US.AAPL")`, `normalize_ticker("0700.HK")` → `("0700.HK",
"HK.00700")`, `^SPX` ↔ `US..SPX`. Routes already call `normalize_ticker` and
keep the yahoo form. A futu provider consumes the futu form from the same tuple.
Futures (`GC=F`) and most `^`-indices have **no** futu equivalent — the provider
must declare which symbols it can serve (see §4.2).

---

## 4. Part D — Preventing contention with yfinance

"Contention" here means four distinct things. Each has its own seam.

### 4.1 Which provider serves a request — *explicit selection, never a race*

Anti-pattern: "fire both, take whoever answers." That doubles upstream load,
doubles rate-limit exposure, and makes results non-deterministic.

Model (per ADR 0011 `providers/_registry.py`):

```
MARKET_DATA_PROVIDER = "yfinance"        # env, default; the only value until futu ships

# When futu ships, selection is layered:
#   1. explicit override:  ?source=futu  (interim) or job param
#   2. per-market routing:  HK./CN. symbols → futu   (yfinance HK option coverage is poor/none)
#   3. capability check:    provider.supports(symbol, dataset) → else fall through
#   4. default:             yfinance
```

Routing table (proposed):

| Dataset | US equity/ETF | US index (`^`) | HK / CN | Futures |
|---|---|---|---|---|
| OHLCV history | yfinance | yfinance | yfinance | yfinance |
| Spot | yfinance | yfinance | futu → yfinance | yfinance |
| **Option chain** | yfinance (futu = manual `?source=futu`) | yfinance | **futu** (yfinance has ~none) | n/a |

The value futu actually adds is **HK/CN options** and **Greeks** — not competing
with yfinance on US equities.

### 4.2 `MarketDataProvider` protocol must not be yfinance-shaped

Sketch for `providers/base.py` (the Q5 deliverable), checked against both:

```python
class MarketDataProvider(Protocol):
    name: str

    def supports(self, symbol: str, dataset: Literal["ohlcv", "spot", "option_chain"]) -> bool: ...

    def history(self, symbol: str, start: date, end: date) -> list[CanonicalBar]: ...
    def spot(self, symbol: str) -> float | None: ...
    def option_chain(self, symbol: str) -> OptionChainSnapshot | None: ...


@dataclass(frozen=True)
class CanonicalOptionQuote:
    strike: float
    last: float | None
    bid: float | None  # yfinance: yes | futu: None  → Optional, not assumed present
    ask: float | None
    iv: float | None  # ALWAYS decimal — provider normalizes (futu ÷100)
    open_interest: float
    volume: float
    in_the_money: bool | None  # yfinance: given | futu: derived | None if spot unknown
    # greeks intentionally NOT here — computed by core/options/greeks from (S,K,T,r,iv)
    #   so the number is identical regardless of provider
```

Design rules the protocol encodes (all points where yfinance and futu differ):

- `bid`/`ask`/`in_the_money`/`iv` are **Optional**; no consumer may assume presence.
- `iv` unit is **fixed to decimal** at the provider boundary.
- `option_chain` is allowed to be **slow** (contract says "call off the request
  thread"); it is never called from a Flask handler directly.
- `supports()` lets the registry fall through instead of erroring on
  `^VIX`/`GC=F` that futu can't serve.

### 4.3 Throttling — a **separate** limiter, never `yf_throttle()`

`yf_throttle()` (token bucket, 5 req/s) is tuned for Yahoo's per-IP limit.
Futu's limits are different in kind: **10 / 30 s** for option chains, **60 / 30
s** for snapshots, **1000** concurrent subscriptions. Sharing one bucket would
either strangle yfinance or blow the futu chain limit.

- New `providers/_futu_throttle.py` (or `utils/network.py::futu_throttle`) with
  its own bucket sized to 10/30 s for the chain call, plus a subscription-quota
  accountant.
- `doc_guard` rule `single-yf-exit` is rescoped to `providers/` (ADR 0011 B1);
  a parallel `single-futu-exit` (only `providers/futu_provider.py` may
  `import futu`) is added.
- The two providers' upstream traffic is fully independent → no cross-poisoning.

### 4.4 Storage — `provider` column becomes a real discriminator

- `raw_prices.provider` **already exists** (defaults `'yfinance'`) but is written
  blindly and never read as a key. ADR 0011 B2 makes `(provider, symbol, date)`
  meaningful in `raw_bars`.
- Until then: if a futu OHLCV path is added, it must **not** upsert into the same
  `(ticker, date)` PK as yfinance — pick one provider per ticker for history, or
  wait for B2. Given §3.4 (keep OHLCV on yfinance), this contention simply
  doesn't arise.
- **Live option data is never persisted** (ADR 0004). The only shared state is
  the in-process caches:
  - `services/options/preload.py::_option_chain_cache` — key must become
    `(ticker, provider)` so a yfinance snapshot and a futu snapshot for the same
    ticker don't clobber each other.
  - `services/options/chain.py` `_build_analyzer` — takes `source` param,
    threads it to the cache key.
- No DB row race, no schema fork, because the canonical tables are provider-
  tagged and the live path has no tables.

### 4.5 Recommended coexistence model (one line)

> yfinance stays the default and the sole OHLCV source; futu is an **opt-in,
> per-market** option-chain provider (HK/CN automatic, US manual), behind the
> ADR 0011 seam, with its own throttle and its own `import` chokepoint, feeding
> the same canonical `OptionChainSnapshot` so nothing downstream changes.

---

## 5. Part E — Deployment plan (if/when this is greenlit)

Ordered; each phase independently revertible. Phases 1–2 depend on ADR 0011 B1
(the seam) having landed.

| Phase | Work | Exit criteria |
|---|---|---|
| **F0 — env** | Add `futu-api` to an **optional** requirements group (like APScheduler — lazily imported, not a hard dep). Document OpenD as an external runtime dependency in `.env.example` (`FUTU_HOST`, `FUTU_PORT`, `FUTU_ENABLED`). Decide Python version story (base conda is 3.13 / unpinned; `requirements.txt` pins 3.12 — **pre-existing drift, flag separately**). | `pip install` unaffected without the extra; app boots with `FUTU_ENABLED` unset |
| **F1 — protocol** | Land `providers/base.py` per §4.2 (this is Q5; can land inside B1). Write the field-map test fixture from `archive/futu_integration/field_mapping.md`. | `MarketDataProvider` protocol reviewed against both field maps; no yfinance-ism in the dataclasses |
| **F2 — futu provider** | `providers/futu_provider.py`: connection context manager (`set_all_thread_daemon` so it doesn't block exit), `option_chain()` per §3.2, `spot()` per §3.3, `supports()` per §4.2. Own throttle (§4.3). Copy/adapt logic from `archive/futu_integration/` (subscribe fault-tolerance, per-batch unsubscribe, 3.1 s spacing). | `pytest -m "not network"` green with a mocked `OpenQuoteContext`; one `network`-marked live test skipped by default |
| **F3 — wiring** | `_registry.py` selection (§4.1). `?source=futu` on `/api/option_chain` + preload cache key `(ticker, provider)`. Per-market auto-routing for `HK.`/`CN.`. Readiness prefetch (ADR 0012) warms the futu chain on submit for HK/CN tickers. | HK ticker → futu chain renders; US ticker unchanged; `source=yfinance` byte-identical to today |
| **F4 — ops** | OpenD supervision: document that OpenD must run beside Flask; it is **not** in the container image; on a VPS use the headless `FutuOpenD` build with `FutuOpenD.xml` creds + a process supervisor + a restart-on-crash hook (2026-08 logs show crashes). Health check: `/health/data` probes port 11111 when `FUTU_ENABLED`. | `FUTU_ENABLED=1` with OpenD down → graceful degrade to yfinance, one WARN, no 500s |

### 5.1 Why F4 is the real cost

yfinance's whole appeal (ADR 0002) is "free, works out of the box, zero infra."
futu adds:

- a **second always-on process** (OpenD) that the Flask app can't start or
  supervise itself;
- an **authenticated session** that expires and needs re-login / device
  verification;
- **GUI-first tooling** on macOS (the headless build is Linux/Windows);
- **account-tier-dependent data** (US realtime needs a paid pack; off-hours US
  quotes fail regardless).

This doesn't make futu "paid" — the reorg's scope lock still holds — but it is a
materially heavier operational dependency than yfinance, and the deployment plan
is mostly about containing that, not about the field mapping (which is easy).

---

## 6. Risks & open questions

| # | Question | Blocks |
|---|---|---|
| Q-a | Is the goal **HK/CN option coverage** (yfinance's real gap) or **US redundancy** (marginal)? Changes whether F3 auto-routing or `?source=` is the primary entry. | F3 |
| Q-b | Acceptable to ship US futu chains **without bid/ask**? Liquidity score degrades to "spread N/A"; strategy builder (`services/options/builder.py`) needs mid = `(bid+ask)/2` and falls back to `last` — usable but lower quality. Or invest in ORDER_BOOK subscription (quota-heavy)? | F2 |
| Q-c | Soften `OptionsChainAnalyzer` to tolerate `spot=None` (render "spot unavailable" instead of `RuntimeError`)? Needed for US off-hours futu. Small, but touches a `core/` contract. | F2 |
| Q-d | Python/dep drift: base conda is 3.13 + numpy 2.x + yfinance 0.2.66, `requirements.txt` pins 3.12 + numpy 1.26 + yfinance 0.2.61, `.venv` is missing numpy entirely. Resolve **before** adding another dep. | F0 (and independent) |
| Q-e | Does the account here have the market-data packs to make US futu quotes useful at all? Needs the §1.3 smoke test during US market hours. | F1 |

---

## 7. References

- Prior attempt: `archive/futu_integration/` — `field_mapping.md`,
  `api_syntax_notes.md`, `project_state.md`, `test_options_api_snapshot_filtering.py`
- Internal contract: `data_pipeline/yf_client.py::fetch_option_chain`,
  `core/options/chain/analyzer.py::OptionsChainAnalyzer`,
  `services/options/chain.py`, `services/options/preload.py`,
  `services/options/builder.py`, `core/decision/candidate.py`
- Ticker conversion: `utils/ticker_utils.py` (`normalize_ticker`, `yahoo_to_futu`)
- Seam target: [ADR 0011](../decisions/0011-pluggable-data-provider-seam.md),
  [ADR 0012](../decisions/0012-parameter-ownership-and-prefetch.md),
  [`business_line_reorg.md`](business_line_reorg.md) §5.2–§5.3, §8 Q5
- Constraints: [`constraints.md`](../constraints.md) §1 (yfinance-only, amended by 0011),
  §2 (throttle), §6 (one-request compute), [ADR 0002](../decisions/0002-yfinance-as-sole-data-source.md),
  [ADR 0004](../decisions/0004-no-iv-history-from-yfinance.md),
  [ADR 0005](../decisions/0005-token-bucket-throttle.md)
- futu SDK: `OpenQuoteContext.get_option_expiration_date` /
  `.get_option_chain` / `.subscribe` + `.get_stock_quote`; OpenD config
  `~/.com.futunn.FutuOpenD/UI/OpenD.xml`
