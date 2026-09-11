# Exploration: futu-api as a Second Data Provider

**Date**: 2026-09-11, updated 2026-09-11 (Part F + mainstream-vs-plan pass) |
**Owner**: repo owner | **Status**: EXPLORATION — no futu code, no new ADR

> **Update**: the business-line reorg's batches **B1–B10 have since landed**
> (merged to `main`, see `business_line_reorg.md` §0/§10) — `providers/base.py`,
> `providers/_registry.py`, and `providers/yfinance_provider.py` are now real,
> shipped code, not the hypothetical target this doc originally sketched
> against. §3–§4 below are updated in place to point at the landed files. This
> document still does **not** propose implementing a futu provider — that
> remains a later, separate batch — but the seam it would plug into now exists.

> This document answers decision gate **Q5** of
> [`business_line_reorg.md`](business_line_reorg.md) §8 ("second-provider protocol
> shape … `providers/base.py` must be sketched against *both* yfinance and futu").
> Treat it as the field-and-deployment reference a future "add futu" batch would
> start from, now cross-checked against the **landed** seam (§3, §4) and against
> how futu-api is actually run in production elsewhere (§6, Part F).

Prior art: `archive/futu_integration/` holds a March-2026 integration attempt
(field map + tested-functions log + a `data_pipeline/futu_provider.py` that was
later archived). This doc supersedes and updates that material against the
current codebase and the now-landed ADR 0011 canonical schema.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Can we connect to futu data? | **Yes, mechanically** — SDK `futu-api 9.5.5508` is installed, `Futu_OpenD.app` is installed and was run as recently as 2026-08, port 11111 configured. Connectivity was live-verified in 2026-03 (AAPL: 26 expiries, 158 contracts). **But not right now**: OpenD is not running, and it needs an interactive Futu account login. |
| What does futu's option data contain? | Static chain (code/strike/expiry/type) from one call; dynamic quote (last/volume/OI/IV/**Greeks**) from a second subscribe-based call. **bid/ask are missing** from the quote path. IV is a **percent** (24.36), not a decimal. |
| How does it map to our format? | Two live shapes: the canonical `OptionChainSnapshot`/`OptionLeg` dataclasses (`providers/base.py`, landed but currently uncalled), and the legacy `{ticker, spot, expiries, chain{exp:{calls:DataFrame, puts:DataFrame}}}` dict every real consumer still uses. Mapping is 1:1 either way except: IV `/= 100`, `inTheMoney`/`in_the_money` computed from strike vs spot, `bid`/`ask` left empty. Ticker conversion already exists (`utils/ticker_utils.py`). A futu provider should target the canonical shape and migrate the consumers — see §3.1. |
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
| US **realtime** stock quotes | **gated by a separately-purchased "Nasdaq Basic" quote card** (行情卡; futu delisted free US realtime data, then reintroduced it as a paid add-on requiring OpenD ≥ 2.14.1000) — *not* an off-hours quirk. An account without the card gets `NN_ProtoRet_TimeOut` on `get_market_snapshot`/`subscribe` for US symbols **at any time of day**; the 2026-03 archived test's off-hours failure is consistent with this, not proof it's time-gated. | can't rely on futu for US spot without buying the card; option **metadata** (`get_option_chain`) has no such gate |
| Option-chain static call | **10 requests / 30 s**, 30-day expiry window per call | 26 expiries ≈ 26 calls ≈ **80 s+** just for the chain skeleton → **cannot run inline in a request** (breaks `constraints.md` §6) |
| Snapshot (`get_market_snapshot`) | 60 / 30 s, ≤ 400 codes/call; **timed out in every 2026-03 test** | prefer `subscribe` + `get_stock_quote` for dynamic data |
| Subscription quota | **1000 contracts total** per account | AAPL has 3400+ contracts — the tail gets no live quote (bid/ask/vol = `None`) |
| Min subscribe time | 60 s before you may `unsubscribe` | per-request unsubscribe is a no-op; quota frees only on `ctx.close()` |
| History klines | ~10 req/30 s + a small daily quota for non-subscribers | **keep OHLCV history on yfinance** — see §3.4 |

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
| `spot` | see §3.3 | **not** from futu for US without a Nasdaq Basic quote card |

---

## 3. Part C — Mapping to the project's data format

### 3.1 The internal contract — now two layers, since B1 landed

Two shapes coexist today (not hypothetical — this is the current tree):

**(a) The canonical seam** (landed, ADR 0011 B1) —
`data_pipeline/providers/base.py`:

```python
@dataclass(frozen=True)
class OptionLeg:
    strike: float
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    iv: float | None = None            # decimal — provider normalizes
    open_interest: float | None = None
    volume: float | None = None

@dataclass(frozen=True)
class OptionChainSnapshot:
    provider: str
    symbol: str
    spot: float | None
    expiries: tuple[str, ...] = ()
    chain: Mapping[str, Mapping[str, tuple[OptionLeg, ...]]] = field(default_factory=dict)
```

`MarketDataProvider.option_chain(symbol) -> OptionChainSnapshot` is the
protocol method; `YFinanceProvider.option_chain()` already implements it (by
wrapping the legacy fetch — see (b) below). Note this already **matches** the
design points this doc argued for before the seam landed: `bid`/`ask`/`iv` are
`Optional`, `iv` is fixed to decimal, and there is **no** `in_the_money` field —
exactly the "derive it, don't assume it" call in the original sketch. This
validates §4.2's pre-landing design reasoning; nothing to redo there.

**(b) The legacy dict-of-DataFrames shape** — still what every *live consumer*
actually calls, via the compat shim `data_pipeline/providers/yf_client.py`
(re-exporting `providers/yf_snapshot.py::fetch_option_chain`):

```python
{
  "ticker":  str,
  "spot":    float | None,            # None ⇒ OptionsChainAnalyzer raises RuntimeError
  "expiries": [ "YYYY-MM-DD", ... ],  # front-month first
  "chain": {
     "YYYY-MM-DD": {
        "calls": pd.DataFrame,   # strike/bid/ask/lastPrice/impliedVolatility/openInterest/volume/inTheMoney
        "puts":  pd.DataFrame,
     }, ...
  },
}
```

`services/options/chain.py`, `preload.py`, `builder.py`, and
`core/decision/candidate.py` all still `import fetch_option_chain` from the
shim and consume DataFrames directly — **none of them call
`get_provider().option_chain()` yet.** `grep -rn "get_provider(" services/
routes/` returns nothing. So (a) exists and is correct, but is currently a
seam with one implementation and zero callers on the option-chain path; (b) is
what the app actually runs today.

**Consequence for a futu provider**: implementing `FutuProvider.option_chain()`
against (a) alone does **not** make futu data reach any route — `_FACTORIES`
gaining a `"futu"` entry is necessary but not sufficient. Either (i) migrate
`services/options/*` + `core/decision/candidate.py` from the shim import to
`get_provider(name).option_chain()` and rewrite their DataFrame-column access
(`row["impliedVolatility"]`, `row["inTheMoney"]`, …) to `OptionLeg` attribute
access (`leg.iv`, `leg.strike`, …) plus a small `in_the_money(leg, spot)`
helper — the ADR-0011-correct direction, and now unavoidable once a second
provider actually exists — or (ii) add a thin adapter that turns a futu
`OptionChainSnapshot` back into the legacy dict-of-DataFrames shape so it can
flow through the existing shim untouched. (ii) is faster but re-creates the
exact vendor-shaped leakage ADR 0011 was written to close, on the one path
(options) that most needs the canonical schema. **(i) is the only path
consistent with the accepted ADR** — flag as a required scope item, not an
optional cleanup, in whichever batch adds futu.

### 3.2 Mapping function shape

```
FutuProvider.option_chain(yahoo_symbol) -> OptionChainSnapshot     # target: (a) above, not the legacy dict
  1. yahoo → futu code           utils.ticker_utils.yahoo_to_futu   (already exists, 27 tests)
  2. get_option_expiration_date  → expiries[]
  3. for each expiry (respect 10/30s): get_option_chain(start=exp,end=exp)
                                 → static rows (code, strike, type)
  4. subscribe(codes[:quota]) + get_stock_quote in batches of ~200
                                 → merge dynamic (last, vol, oi, iv, greeks)
  5. per row: iv/100; bid=ask=None (OptionLeg tolerates it)
  6. build OptionLeg tuples per expiry/side → OptionChainSnapshot
  7. ctx.close()  (frees the subscription quota)
```

`in_the_money` is deliberately not computed here — (a)'s schema has no such
field; whichever consumer needs it derives `strike < spot` (call) /
`strike > spot` (put) at read time, same as `liquidity_score` already does with
raw numbers today.

This is ~5–80 s of wall time. It **must** run off the request thread — it fits
ADR 0012's readiness-prefetch model (warm `services/options/preload` on a daemon
thread on submit) exactly, and the per-`(ticker, provider)` cache in
`services/options/preload.py` (15-min TTL) absorbs the cost after the first hit.

### 3.3 The `spot` problem

`OptionsChainAnalyzer._init_from_snapshot` raises `RuntimeError` if `spot is
None`. Futu US spot is gated behind the paid Nasdaq Basic quote card (§1.4) —
this fails the same way whether the market is open or closed, so "wait for
market hours" is not a fix. Resolution order for a futu provider:

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

This is now the real, landed `data_pipeline/providers/base.py` — see the exact
dataclasses in §3.1(a). It already encodes the yfinance/futu divergence points
this doc argued for pre-landing: `bid`/`ask`/`iv`/leg-level fields are
`Optional`; `iv` is fixed to decimal at the boundary; there is no
`in_the_money` (derive, don't assume). One gap remains, real and still open:

- **No `supports(symbol, dataset)` capability check.** The landed
  `MarketDataProvider` protocol is `name`, `history`, `close_panel`, `spot`,
  `option_chain` — nothing lets the registry ask "can you serve this symbol"
  and fall through. Fine with one provider (yfinance serves everything it's
  asked); breaks the moment futu joins, because futu has no equivalent for
  `^VIX`/`GC=F`/most indices, and §4.1's routing table needs some way to say
  "this dataset/symbol combination isn't yours" *before* calling the method
  and getting an exception. Adding `supports()` (or equivalent) to the
  protocol is a **prerequisite** for §4.1's routing, not a nice-to-have — and
  it's a `Protocol` change, so it touches the one existing implementation too.
- `option_chain` being allowed to be **slow** (§3.2: "call off the request
  thread") is a convention this doc is asserting, not something the protocol
  enforces — nothing in `base.py` stops a future implementation from being
  called inline. Worth a docstring `CONSTRAINT:` note when a second provider
  actually forces the point.

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

### 4.4 Storage — `provider` column is now a real discriminator (B2 landed)

- `raw_bars` (renamed from `raw_prices` in batch B2, which has since landed;
  the old name is kept as a shadow table for one release) carries `provider` +
  `symbol` as real key components — confirmed in the current
  `data_pipeline/store/db.py`. A futu OHLCV path would not silently collide
  with yfinance rows for the same ticker/date; the schema-level risk this
  section originally flagged is closed. Given §3.4 (keep OHLCV on yfinance
  anyway), it's moot in practice, but worth knowing the guard rail now exists
  for real.
- **Live option data is never persisted** (ADR 0004). The only shared state is
  the in-process cache, and this part is **still open, unimplemented, and
  still correct as a requirement**:
  - `services/options/preload.py::_option_chain_cache` is keyed by bare
    `ticker` today (`_option_chain_cache[ticker] = {...}`, confirmed in the
    current file) — a yfinance snapshot and a futu snapshot for the same
    ticker **would** clobber each other under this key. Must become
    `(ticker, provider)` before a second provider ships.
  - `services/options/chain.py` `_build_analyzer` takes no `source`/provider
    param today; it would need one, threaded to the cache key above.

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
| **F0 — env** | Add `futu-api` to an **optional** requirements group (like APScheduler — lazily imported, not a hard dep). Document OpenD as an external runtime dependency in `.env.example` (`FUTU_HOST`, `FUTU_PORT`, `FUTU_ENABLED`). Decide Python version story (base conda is 3.13 / unpinned; `requirements.txt` pins 3.12 — **pre-existing drift, flag separately**). Decide the connection-ownership model (§6.2 #2, Q-f) *before* F2, since it determines F2's shape. | `pip install` unaffected without the extra; app boots with `FUTU_ENABLED` unset |
| **F1 — protocol gap** | `providers/base.py` **already exists** (landed in B1) — the remaining protocol work is narrower than originally scoped: add `supports(symbol, dataset)` to `MarketDataProvider` (§4.2 gap) and retrofit `YFinanceProvider.supports()` to return `True` unconditionally (today's behaviour, made explicit). Write the field-map test fixture from `archive/futu_integration/field_mapping.md`. | `supports()` reviewed against both field maps; `YFinanceProvider` still passes existing tests unchanged |
| **F2 — futu provider** | `providers/futu_provider.py`, built against §6's ownership decision: if singleton-gateway (mainstream-aligned), a module-level connection created **lazily inside each worker process** (never at import time — fork safety, §6.1) guarded by a per-process lock; if per-call (this doc's original, simpler sketch), a context manager per `option_chain()` call. Either way: `option_chain()` returns `OptionChainSnapshot` (§3.1(a) target, not the legacy dict), `spot()` per §3.3, `supports()` per F1. Own throttle (§4.3). Copy/adapt logic from `archive/futu_integration/` (subscribe fault-tolerance, per-batch unsubscribe, 3.1 s spacing). | `pytest -m "not network"` green with a mocked `OpenQuoteContext`; one `network`-marked live test skipped by default; a `gunicorn --workers 2` smoke test doesn't double-subscribe |
| **F3 — wiring + consumer migration** | `_registry.py` selection (§4.1). **Migrate `services/options/chain.py`, `preload.py`, `builder.py`, `core/decision/candidate.py` off the legacy shim import onto `get_provider(name).option_chain()` + `OptionLeg` attribute access** (§3.1 — this is now the larger half of F3, not a footnote: today *zero* callers use the canonical path). `?source=futu` on `/api/option_chain` + preload cache key `(ticker, provider)`. Per-market auto-routing for `HK.`/`CN.`. Readiness prefetch (ADR 0012) warms the futu chain on submit for HK/CN tickers. | HK ticker → futu chain renders; US ticker unchanged; `source=yfinance` byte-identical to today; `grep -rn "from data_pipeline.providers.yf_client import fetch_option_chain" services/ core/` → empty |
| **F4 — ops** | OpenD supervision, aligned to §6.1's actual production pattern rather than the GUI app installed here: headless `FutuOpenD` binary (or the official `futuopen/futu-opend` Docker image) with `FutuOpenD.xml`/env creds, a **named volume for the login-session token** (avoids re-triggering SMS/2FA on every restart), a process supervisor + restart-on-crash hook (2026-08 local logs show crashes), and `auto_hold_quote_right` set deliberately if the same account also has a personal GUI OpenD running elsewhere (avoid "行情互踢" — §6.1). Health check: `/health/data` probes port 11111 when `FUTU_ENABLED`. | `FUTU_ENABLED=1` with OpenD down → graceful degrade to yfinance, one WARN, no 500s; a container restart doesn't require re-login |

### 5.1 Why F4 is the real cost

yfinance's whole appeal (ADR 0002) is "free, works out of the box, zero infra."
futu adds:

- a **second always-on process** (OpenD) that the Flask app can't start or
  supervise itself;
- an **authenticated session** that expires and needs re-login / device
  verification;
- **GUI-first tooling** on macOS (the headless build is Linux/Windows);
- **account-tier-dependent data** (US realtime needs the paid Nasdaq Basic
  quote card — see §1.4 — regardless of market hours).

This doesn't make futu "paid" — the reorg's scope lock still holds — but it is a
materially heavier operational dependency than yfinance, and the deployment plan
is mostly about containing that, not about the field mapping (which is easy).

---

## 6. Part F — Mainstream futu-api usage vs. this plan

Added 2026-09-11, after checking this plan against the official docs
(`openapi.futunn.com`), the `FutunnOpen/py-futu-api` repo, and public
OpenD-in-production write-ups. Some of §1–§5 above turns out to lean on
assumptions that don't match how futu-api is actually run in the wild — this
section is the delta, not a rewrite; §1.4 and §3.3 above are already corrected
in place.

### 6.1 What "mainstream" actually looks like

| Dimension | Mainstream pattern | Source |
|---|---|---|
| **Deployment** | Headless OpenD (CLI binary, no GUI) as an always-on background process — official `docker pull futuopen/futu-opend`, plus several community images (`pangliang/futuopend-docker`, `manhinhang/futu-opend-docker`). Credentials via `FUTU_ACCOUNT`/`FUTU_ACCOUNT_PWD_MD5` env vars (never plaintext). A **named volume persists the login session token** across container restarts — without it, every restart re-triggers SMS/device verification. | official docs + community Docker repos |
| **Connections** | One OpenD instance accepts up to **128 concurrent client connections**, and one account may run up to **10 OpenD terminals across different machines**. So "many processes each open their own `OpenQuoteContext`" is *supported* at the connection level. | `openapi.futunn.com` FAQ |
| **But quote tier is exclusive** | Only **one** logged-in terminal per account holds the highest-tier real-time quote at a time ("行情互踢" — quote-right kicking); logging in elsewhere can silently downgrade or evict another connection. `auto_hold_quote_right` controls whether OpenD fights to keep it. | same FAQ |
| **Subscription quota is account/instance-wide** | The 1000-contract subscription cap (§1.4) and the 60 s min-hold-before-unsubscribe are pooled across **all** connections to that OpenD, not per-connection. | official docs + archived 2026-03 test notes |
| **Data model** | Centre of gravity is **push/callback**: subclass `StockQuoteHandlerBase`, override `on_recv_rsp`, `subscribe()` once, `ctx.start()`, then consume an unbounded stream of async pushes into your own in-memory state. One-shot `get_stock_quote()` polling exists but is the secondary path in every tutorial. | `py-futu-api` docs/examples |
| **Snapshot vs. subscribe** | `get_market_snapshot()` is marketed as the subscription-free batch path (≤ 400 codes) — but for **US** symbols it fails with `NN_ProtoRet_TimeOut` unless the account holds the paid **Nasdaq Basic quote card**; this is a long-standing, still-open community complaint, not a bug that got fixed. HK/CN snapshots work without it. | `FutunnOpen/py-futu-api` issue #25 |
| **Primary use case** | Most public integrations use futu-api for **trading** (`OpenHKTradeContext`/`OpenUSTradeContext` placing real orders) as much as for quotes — "quotes" is the sensing half of a bot whose other half acts. Pure read-only research usage (what OptionLab wants) is a minority slice of the ecosystem's example code. | `py-futu-api` README, FutuQuant-style community projects |
| **Process model gotcha** | The SDK's internal push-handling threads do **not** survive `os.fork()` — a connection created before forking breaks silently in the child. Guidance is to use `multiprocessing`'s `spawn` start method, or (for a prefork web server) create the connection **inside** each already-forked worker, never at import time in the master process. | community Docker/deployment write-ups |
| **Adjacent, not mainstream yet** | A community "Futu MCP server" exists, wrapping futu-api as MCP tools for LLM agents. Noted for awareness only — orthogonal to this plan, not a deployment model to adopt now. | `glama.ai` MCP server listing |

### 6.2 Where §1–§5 of this plan diverge

| # | This plan (§ref) | Mainstream | Consequence |
|---|---|---|---|
| 1 | **Connection lifecycle** — §3.2 opens a context per fetch, subscribes a batch, unsubscribes, `ctx.close()`. | Long-lived context + push/callback; subscribe once, keep consuming. | Our design fits Flask's stateless-request model, but it fights the SDK's grain: repeated subscribe/unsubscribe cycles hit the 60 s min-hold wastefully, and we get none of the push-driven "always fresh" benefit the SDK is built for. Acceptable trade-off for a research dashboard (we don't need streaming ticks), but should be stated as a deliberate simplification, not an oversight. |
| 2 | **Connection ownership** — §4.3/§4.4 discuss a per-provider throttle and a `(ticker, provider)` cache key, but never say *which process* holds the OpenD connection. | One long-lived **singleton gateway process** owns the OpenD connection and all subscription state; other app code talks to *it*, never to OpenD directly. | OptionLab runs `gunicorn --workers 2 --threads 4` (prefork). If each worker independently opens `OpenQuoteContext`, they share one account's 1000-subscription pool and one quote-tier slot (§6.1) — uncoordinated, that's a race, not just a throttle problem. **New Q-f (§7)**: needs a decision before F2/F3, not just a rate limiter. |
| 3 | **Fork safety** | Connections must be created post-fork, per worker; SDK threads don't survive `fork()`. | Not mentioned anywhere in §5's F0–F4. Any `providers/futu_provider.py` singleton must be built lazily *inside* the worker process (e.g. on first use, guarded by a per-process lock), never at module import time — otherwise workers 2..N silently get a dead connection. |
| 4 | **US spot/quote failure cause** — originally attributed to "off-hours" (now corrected in §1.4/§3.3). | Root cause is the paid Nasdaq Basic quote card; time of day is irrelevant. | Already fixed in place above; flagged here so the correction isn't missed on a skim. |
| 5 | **Snapshot as the "free" path** — §3.2 step 4 leans on `subscribe`+`get_stock_quote`; §1.4 already flags `get_market_snapshot` as unreliable for US. | Confirmed by an open, years-old community issue — this isn't a transient bug to wait out. | Don't plan around `get_market_snapshot()` recovering for US; budget for the quote-card purchase (Q-e) or restrict futu quotes to HK/CN where it works today. |
| 6 | **Scope: quotes only, no trading contexts.** | Most tutorials/example code cover trading contexts too. | Deliberate and correct for a research tool (no execution) — called out so a future reader doesn't mistake the narrower scope for an oversight, and so community example code (mostly order-management-flavoured) is read with that filter on. |

---

## 7. Risks & open questions

| # | Question | Blocks |
|---|---|---|
| Q-a | Is the goal **HK/CN option coverage** (yfinance's real gap) or **US redundancy** (marginal)? Changes whether F3 auto-routing or `?source=` is the primary entry. | F3 |
| Q-b | Acceptable to ship US futu chains **without bid/ask**? Liquidity score degrades to "spread N/A"; strategy builder (`services/options/builder.py`) needs mid = `(bid+ask)/2` and falls back to `last` — usable but lower quality. Or invest in ORDER_BOOK subscription (quota-heavy)? | F2 |
| Q-c | Soften `OptionsChainAnalyzer` to tolerate `spot=None` (render "spot unavailable" instead of `RuntimeError`)? Needed for US futu without a quote card. Small, but touches a `core/` contract. | F2 |
| Q-d | Python/dep drift: base conda is 3.13 + numpy 2.x + yfinance 0.2.66, `requirements.txt` pins 3.12 + numpy 1.26 + yfinance 0.2.61, `.venv` is missing numpy entirely. Resolve **before** adding another dep. | F0 (and independent) |
| Q-e | Does the account here hold a Nasdaq Basic quote card (or equivalent HK pack)? Determines whether futu US spot/quotes work **at all**, independent of time of day. Needs the §1.3 smoke test — a card-less account will time out even during market hours. | F1 |
| Q-f | §6 below: is a per-request `OpenQuoteContext` (this doc's F2 sketch) acceptable, or does the shared subscription quota / quote-tier force a **singleton gateway process** owning the futu connection? | F2/F3 |

---

## 8. References

- Prior attempt: `archive/futu_integration/` — `field_mapping.md`,
  `api_syntax_notes.md`, `project_state.md`, `test_options_api_snapshot_filtering.py`
- **Landed seam** (post-B1/B2, current tree): `data_pipeline/providers/base.py`
  (`MarketDataProvider`, `OptionChainSnapshot`, `OptionLeg`, `CanonicalBar`),
  `providers/_registry.py` (`get_provider`, `MARKET_DATA_PROVIDER` env),
  `providers/yfinance_provider.py` (`YFinanceProvider`),
  `providers/yf_client.py` (one-release compat shim — still what every live
  consumer imports), `store/db.py` (`raw_bars`/`clean_bars`/`feature_bars`)
- Live option-chain consumers (still on the legacy shim, not yet migrated —
  §3.1): `core/options/chain/analyzer.py::OptionsChainAnalyzer`,
  `services/options/chain.py`, `services/options/preload.py`,
  `services/options/builder.py`, `core/decision/candidate.py`
- Ticker conversion: `utils/ticker_utils.py` (`normalize_ticker`, `yahoo_to_futu`)
- Seam target: [ADR 0011](../decisions/0011-pluggable-data-provider-seam.md),
  [ADR 0012](../decisions/0012-parameter-ownership-and-prefetch.md),
  [`business_line_reorg.md`](business_line_reorg.md) §5.2–§5.3, §8 Q5, §10 (deferred follow-ups)
- Constraints: [`constraints.md`](../constraints.md) §1 (yfinance-only, amended by 0011),
  §2 (throttle), §6 (one-request compute), [ADR 0002](../decisions/0002-yfinance-as-sole-data-source.md),
  [ADR 0004](../decisions/0004-no-iv-history-from-yfinance.md),
  [ADR 0005](../decisions/0005-token-bucket-throttle.md)
- futu SDK: `OpenQuoteContext.get_option_expiration_date` /
  `.get_option_chain` / `.subscribe` + `.get_stock_quote`; OpenD config
  `~/.com.futunn.FutuOpenD/UI/OpenD.xml`
- Mainstream-usage research (Part F, 2026-09-11): official docs —
  [OpenD 介绍](https://openapi.futunn.com/futu-api-doc/opend/opend-intro.html),
  [OpenD 相关 QA](https://openapi.futunn.com/futu-api-doc/qa/opend.html),
  [获取期权链](https://openapi.futunn.com/futu-api-doc/quote/get-option-chain.html);
  SDK — [FutunnOpen/py-futu-api](https://github.com/FutunnOpen/py-futu-api);
  community Docker deployments —
  [pangliang/futuopend-docker](https://github.com/pangliang/futuopend-docker),
  [manhinhang/futu-opend-docker](https://github.com/manhinhang/futu-opend-docker),
  [yanrongliang/futu-opend](https://github.com/yanrongliang/futu-opend);
  US-quote gating —
  [py-futu-api issue #25](https://github.com/FutunnOpen/py-futu-api/issues/25)
  (`get_market_snapshot` times out for US symbols without a paid Nasdaq Basic
  quote card — confirms and corrects §1.4/§3.3's original "off-hours"
  attribution)
