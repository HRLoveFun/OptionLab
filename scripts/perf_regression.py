"""Performance regression benchmark.

Goal
----
End-to-end time for analysing **4 tickers concurrently** must stay under 8 s.
Baseline (pre-streaming, monolithic POST `/`) was ~24 s for 4 tickers.

Methodology
-----------
1. POST `/` with 4 tickers — should return a skeleton in well under 1 s.
2. Fan out `/render/<kind>?job=…&ticker=…` for every (kind, ticker) pair in
   parallel using a thread pool, mirroring what HTMX does in the browser.
3. Wait for all fragments and report wall-clock time.

The benchmark uses Flask's `test_client` (no real HTTP stack) so the result is
a *lower bound* on infrastructure cost. Network/yfinance latency is included
when the DB cache is cold.

Run
---
    python scripts/perf_regression.py
    python scripts/perf_regression.py --tickers AAPL,NVDA,SPY,^VIX

Exit code 0 if total time < TARGET_SECONDS, else 1.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Allow running this script directly from the repo root or via `python -m`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("perf_regression")

DEFAULT_TICKERS = ["AAPL", "NVDA", "SPY", "^VIX"]
RENDER_KINDS = ["market_review", "statistical", "assessment", "options_chain"]
TARGET_SECONDS = 8.0


def _form_payload(tickers_csv: str) -> dict:
    return {
        "ticker": tickers_csv,
        "start_time": "202301",
        "frequency": "D",
        "risk_threshold": "50",
        "side_bias": "Natural",
        "rolling_window": "20",
    }


def run_benchmark(tickers: list[str]) -> float:
    import threading
    from urllib.request import urlopen, Request, build_opener, ProxyHandler, install_opener
    from urllib.parse import urlencode
    from werkzeug.serving import make_server

    # Ensure localhost bypasses any HTTP_PROXY set by init_yf_proxy().
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    install_opener(build_opener(ProxyHandler({})))

    from app import app

    # Boot a real WSGI server in a background thread so concurrent
    # /render/<kind> requests don't share Flask request-contexts.
    server = make_server("127.0.0.1", 0, app, threaded=True)
    base = f"http://{server.server_address[0]}:{server.server_address[1]}"
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        t0 = time.perf_counter()

        # Step 1 — POST `/` (skeleton)
        from urllib.request import Request

        post_body = urlencode(_form_payload(",".join(tickers))).encode("utf-8")
        req = Request(
            base + "/",
            data=post_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            resp = urlopen(req, timeout=30)
        except Exception as e:
            from urllib.error import HTTPError
            if isinstance(e, HTTPError):
                logger.error("POST / -> %s body=%s", e.code, e.read()[:500])
            raise
        with resp:
            if resp.status != 200:
                raise RuntimeError(f"POST / returned {resp.status}")
            body = resp.read().decode("utf-8", errors="replace")
        # Pull job id out of the rendered template.
        marker = 'name="job_id" value="'
        idx = body.find(marker)
        if idx < 0:
            marker = "?job="
            idx = body.find(marker)
            if idx < 0:
                raise RuntimeError("Could not locate job_id in skeleton response")
            start = idx + len(marker)
            end = start
            while end < len(body) and body[end] not in ('&', '"', "'", " "):
                end += 1
            job_id = body[start:end]
        else:
            start = idx + len(marker)
            end = body.find('"', start)
            job_id = body[start:end]
        skeleton_elapsed = time.perf_counter() - t0
        logger.info("skeleton ready in %.2fs (job=%s)", skeleton_elapsed, job_id[:8])

        # Step 2 — fan-out /render/<kind> for every (kind, ticker) combo.
        def fetch(kind: str, ticker: str) -> tuple[str, str, float, int]:
            local_t0 = time.perf_counter()
            url = f"{base}/render/{kind}?job={job_id}&ticker={ticker}"
            with urlopen(url, timeout=60) as r:
                _ = r.read()
                return kind, ticker, time.perf_counter() - local_t0, r.status

        max_workers = len(tickers) * len(RENDER_KINDS)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(fetch, k, t) for t in tickers for k in RENDER_KINDS]
            for fut in as_completed(futures):
                kind, ticker, dt, status = fut.result()
                logger.info("  %s/%s -> %s in %.2fs", ticker, kind, status, dt)

        total = time.perf_counter() - t0
        return total
    finally:
        server.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                        help="Comma-separated tickers (default: %(default)s)")
    parser.add_argument("--target", type=float, default=TARGET_SECONDS,
                        help="Pass/fail wall-clock threshold in seconds (default: %(default).1f)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("perf_regression").setLevel(logging.INFO)

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    print(f"Benchmarking {len(tickers)} tickers: {tickers}")
    elapsed = run_benchmark(tickers)
    status = "PASS" if elapsed < args.target else "FAIL"
    print(f"\n[{status}] total={elapsed:.2f}s  target<{args.target:.1f}s  "
          f"({len(tickers)} tickers x {len(RENDER_KINDS)} kinds = "
          f"{len(tickers) * len(RENDER_KINDS)} fragments)")
    return 0 if elapsed < args.target else 1


if __name__ == "__main__":
    sys.exit(main())
