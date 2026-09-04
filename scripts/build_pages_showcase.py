"""Build Pages showcase snapshots (offline-safe).

Regenerates site/showcase/*.html with the standard unavailable banner plus
whatever deterministic content is available (fixture summaries). Safe to run
in CI without yfinance/SQLite/matplotlib.

Usage: python scripts/build_pages_showcase.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = REPO_ROOT / "site" / "showcase"
FIX = REPO_ROOT / "site" / "fixtures"

PAGES = {
    "statistical": ("Statistical Analysis", "GET /render/statistical", "散点 / 波动率动态等服务端 matplotlib 图表"),
    "assessment": ("Assessment & Projections", "GET /render/assessment", "投影 / PnL / 仓位管理表"),
    "volatility": ("Volatility Analysis", "GET /render/options_chain", "IV 微笑 / 期限结构 / 曲面 / OI / PCR（6 张服务端 PNG）"),
    "regime": ("Market Regime", "GET /api/regime/*", "VIX/SPY 历史 + SQLite regime_log，composite label hero"),
    "parameter": ("Parameter", "POST / + /api/validate_tickers", "表单提交建 job、多 ticker 校验徽章、持仓级联下拉"),
    "summary": ("Summary", "POST / (multi-ticker)", "跨 ticker 汇总 + 相关性热图"),
}


def _fixture_note() -> str:
    try:
        chain = json.loads((FIX / "option_chain.nvda.json").read_text())
        return f"示例快照：{chain.get('ticker')} spot {chain.get('spot')}，{len(chain.get('expirations', []))} 个到期（{', '.join(chain.get('expirations', []))}）。"
    except Exception:
        return "示例快照不可用。"


def render(slug: str, title: str, endpoint: str, desc: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — OptionLab Pages 快照</title>
  <link rel="stylesheet" href="../assets/pages-shell.css" />
</head>
<body>
<div class="pages-wrap">
  <p class="muted"><a href="../">← 门户</a> · {title} <span class="badge badge--static">静态快照</span></p>
  <h1>{title}</h1>
  <div class="pages-notice" role="status" aria-live="polite">
    <strong>不可用提醒：</strong>此模块在 GitHub Pages 上不可交互 —— 需要后端
    <code>{endpoint}</code>（Flask + yfinance / SQLite / matplotlib）。
    下方为预渲染快照（快照日期 2026-09-04，NVDA）。完整交互请本地运行
    <code>python app.py</code>。
  </div>
  <div class="pages-card">
    <h3>快照说明</h3>
    <p class="muted">{desc}。</p>
    <p class="muted">{_fixture_note()}</p>
    <p class="muted">CI 由 <code>scripts/build_pages_showcase.py</code> 生成；本地有行情缓存时可用
    <code>scripts/build_pages_showcase.py --with-live</code>（预留）嵌入真实 matplotlib PNG。</p>
  </div>
  <div class="pages-card" style="margin-top:.75rem">
    <h3>本地运行完整版</h3>
    <p class="muted"><code>pip install -r requirements.txt &amp;&amp; python app.py</code> → 打开 <code>http://127.0.0.1:5001</code>，在 Parameter 页输入 ticker 后切换到「{title}」标签。</p>
    <a class="btn btn--ghost" href="../">返回门户</a>
  </div>
</div>
</body>
</html>
"""


def main() -> None:
    SHOWCASE.mkdir(parents=True, exist_ok=True)
    for slug, (title, endpoint, desc) in PAGES.items():
        (SHOWCASE / f"{slug}.html").write_text(render(slug, title, endpoint, desc), encoding="utf-8")
    print(f"wrote {len(PAGES)} showcase pages to {SHOWCASE}")


if __name__ == "__main__":
    main()
