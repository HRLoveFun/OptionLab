# Market Dashboard 优化执行手册

> **目标读者**：Claude Opus 4.6  
> **执行范围**：基于现有 Flask + 原生 JS 架构进行功能扩展与改造  
> **优先级标注**：🔴 核心依赖（先执行）/ 🟡 功能改造 / 🟢 增量新增

---

## 0. 总体依赖关系图

```
[0] 多 Ticker 输入架构  ←──────────────────────────────────────┐
         │                                                       │
         ▼                                                       │
[1] 期权链预加载 API                                            │
         │                                                       │
         ▼                                                       │
[2] Position 模块重构（引用预加载数据）                          │
         │                                                       │
         ▼                                                       │
[3] 投资组合分析按钮（消费 Position 数据）                       │
         │                                                       │
         └──────────────────────→ [5] 综合标签页（汇总多 Ticker）┘
                                                                 
[4A] Market Review 时序图（独立改造，使用多 Ticker 数据）
[4B] Expiry Odds 实现波动率标注（独立改造）
```

**执行顺序**：[0] → [1] → [2] → [3] → [4A] → [4B] → [5]  
每个模块完成后独立可测试。

---

## 模块 0：多 Ticker 输入架构 🔴

### 0.1 需求描述

- 参数面板支持输入多个 ticker（逗号或换行分隔）
- 点击"分析"后，为每个 ticker 生成独立标签页，另加"综合"标签页
- 所有现有分析（Market Review、Statistical Analysis、Assessment、Volatility 等）均需在各 ticker 标签页内分别展示

### 0.2 前端改造：`templates/index.html` + `static/main.js`

#### 0.2.1 输入组件改造

```html
<!-- 替换原有单行 ticker input -->
<div class="form-group">
  <label for="tickers">Ticker Symbols（多个用逗号分隔，如 AAPL, SPY, ^SPX）</label>
  <input type="text" id="tickers" name="tickers"
         placeholder="AAPL, SPY, ^SPX"
         value="{{ tickers_raw or '' }}">
  <div id="ticker-validation-container"></div>
  <!-- 验证状态容器：每个 ticker 一个 badge -->
</div>
```

#### 0.2.2 动态标签页渲染逻辑（伪代码）

```javascript
// static/main.js — 新增函数 renderTickerTabs()

function parseTickers(rawInput) {
    /*
     * 输入: "AAPL, SPY, ^SPX"
     * 输出: ["AAPL", "SPY", "^SPX"]
     */
    return rawInput
        .split(/[,\n]+/)
        .map(t => t.trim().toUpperCase())
        .filter(t => t.length > 0)
        .filter((t, i, arr) => arr.indexOf(t) === i);  // 去重
}

function renderTickerTabs(tickers, activeTab = null) {
    /*
     * 在 #ticker-tabs-nav 中渲染标签导航
     * 在 #ticker-tabs-content 中渲染内容容器
     */
    const nav = document.getElementById('ticker-tabs-nav');
    const content = document.getElementById('ticker-tabs-content');
    nav.innerHTML = '';
    content.innerHTML = '';

    // 若多于1个ticker，生成"综合"标签
    if (tickers.length > 1) {
        nav.appendChild(createTabButton('综合', 'tab-综合'));
        content.appendChild(createTabPanel('tab-综合'));
    }

    for (const ticker of tickers) {
        nav.appendChild(createTabButton(ticker, `tab-${ticker}`));
        content.appendChild(createTabPanel(`tab-${ticker}`, ticker));
    }

    // 激活第一个标签（或指定标签）
    const firstTab = activeTab || (tickers.length > 1 ? 'tab-综合' : `tab-${tickers[0]}`);
    switchTab(firstTab);
}

function switchTab(tabId) {
    document.querySelectorAll('.ticker-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.ticker-tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === tabId);
    });
}
```

#### 0.2.3 多 ticker 验证（伪代码）

```javascript
async function validateAllTickers(tickers) {
    /*
     * 并发验证所有 ticker，显示逐个验证状态
     * 返回: { valid: ["AAPL","SPY"], invalid: ["XXX"] }
     */
    const container = document.getElementById('ticker-validation-container');
    container.innerHTML = '';

    const results = await Promise.all(
        tickers.map(async ticker => {
            const badge = createValidationBadge(ticker, 'pending');
            container.appendChild(badge);
            try {
                const resp = await fetch('/api/validate_ticker', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ticker })
                });
                const data = await resp.json();
                updateBadge(badge, data.valid ? 'valid' : 'invalid', data.price);
                return { ticker, valid: data.valid, price: data.price };
            } catch {
                updateBadge(badge, 'error');
                return { ticker, valid: false, price: null };
            }
        })
    );

    return {
        valid: results.filter(r => r.valid).map(r => r.ticker),
        prices: Object.fromEntries(results.map(r => [r.ticker, r.price]))
    };
}
```

### 0.3 后端改造：`services/analysis_service.py` + `app.py`

#### 0.3.1 `app.py` 路由改造（伪代码）

```python
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 解析多 ticker 输入
        tickers_raw = request.form.get('tickers', '').strip()
        tickers = parse_tickers(tickers_raw)  # ["AAPL", "SPY", "^SPX"]

        # 并发执行各 ticker 分析
        results_by_ticker = {}
        with ThreadPoolExecutor(max_workers=min(len(tickers), 4)) as executor:
            futures = {
                executor.submit(run_single_ticker_analysis, ticker, form_data): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                results_by_ticker[ticker] = future.result()

        # 生成综合分析（仅多 ticker 时）
        if len(tickers) > 1:
            results_by_ticker['__综合__'] = generate_综合_analysis(
                tickers, results_by_ticker
            )

        return render_template('index.html',
                               tickers=tickers,
                               results=results_by_ticker,
                               ...)
    return render_template('index.html')


def parse_tickers(raw: str) -> list[str]:
    """解析并去重，最多支持 6 个 ticker"""
    tickers = [t.strip().upper() for t in re.split(r'[,\n]+', raw) if t.strip()]
    seen = []
    for t in tickers:
        if t not in seen:
            seen.append(t)
    return seen[:6]  # 限制最大数量防止超时
```

#### 0.3.2 `validation_service.py` 保持兼容

```python
# 无需大改，但要支持批量验证接口
@app.route('/api/validate_tickers', methods=['POST'])
def validate_tickers_bulk():
    """
    新增批量验证端点
    请求体: { "tickers": ["AAPL", "SPY", "XXX"] }
    响应: { "results": [{"ticker":"AAPL","valid":true,"price":213.5}, ...] }
    """
    tickers = request.json.get('tickers', [])
    results = []
    for ticker in tickers[:10]:  # 安全上限
        try:
            valid, price = ValidationService.validate_ticker(ticker)
            results.append({"ticker": ticker, "valid": valid, "price": price})
        except Exception:
            results.append({"ticker": ticker, "valid": False, "price": None})
    return jsonify({"results": results})
```

---

## 模块 1：期权链后台预加载 🔴

### 1.1 需求描述

- 用户输入 ticker 并完成验证后，**自动触发**期权链后台加载
- 加载内容：全部 expiry × strike 的 call/put 数据，含 bid/ask/IV/OI/volume
- 数据缓存于内存（按 ticker + 时间戳），供 Position 模块的下拉菜单使用
- 加载状态以非阻塞方式告知用户（loading spinner）

### 1.2 新增后端端点：`app.py`

```python
# 内存缓存结构
_option_chain_cache: dict = {}
# 格式: { "AAPL": { "ts": datetime, "data": {...} } }
CACHE_TTL_MINUTES = 15


@app.route('/api/preload_option_chain', methods=['POST'])
def preload_option_chain():
    """
    异步预加载期权链，供 Position 模块使用。
    请求体: { "ticker": "AAPL" }
    响应: {
        "status": "ok" | "error",
        "ticker": "AAPL",
        "spot": 213.5,
        "expiries": ["2025-03-21", "2025-04-18", ...],
        "chain": {
            "2025-03-21": {
                "calls": [
                    { "strike": 210, "bid": 3.5, "ask": 3.7,
                      "iv": 0.22, "oi": 1200, "volume": 340,
                      "last": 3.6, "mid": 3.6 },
                    ...
                ],
                "puts": [ ... ]
            },
            ...
        }
    }
    """
    ticker = request.json.get('ticker', '').upper()
    if not ticker:
        return jsonify({"status": "error", "message": "No ticker provided"})

    # 检查缓存
    cached = _option_chain_cache.get(ticker)
    if cached:
        age = (datetime.now() - cached['ts']).total_seconds() / 60
        if age < CACHE_TTL_MINUTES:
            return jsonify({"status": "ok", **cached['data']})

    try:
        # 使用现有 OptionsChainAnalyzer 加载
        analyzer = OptionsChainAnalyzer(ticker)
        chain_data = build_chain_payload(analyzer)  # 见下方

        _option_chain_cache[ticker] = {
            "ts": datetime.now(),
            "data": chain_data
        }
        return jsonify({"status": "ok", **chain_data})

    except Exception as e:
        logger.error(f"preload_option_chain failed for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)})


def build_chain_payload(analyzer: OptionsChainAnalyzer) -> dict:
    """
    将 OptionsChainAnalyzer 的数据整理为前端友好的 JSON 格式。
    仅返回流动性 ≥ FAIR 的合约，减少数据量。
    """
    chain_out = {}
    for exp in analyzer.expiries:
        if exp not in analyzer.chain:
            continue
        calls_df = analyzer.chain[exp]['calls']
        puts_df  = analyzer.chain[exp]['puts']

        def df_to_list(df):
            result = []
            for _, row in df.iterrows():
                bid = float(row.get('bid', 0) or 0)
                ask = float(row.get('ask', 0) or 0)
                mid = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row.get('lastPrice', 0) or 0)
                result.append({
                    "strike":   float(row['strike']),
                    "bid":      round(bid, 2),
                    "ask":      round(ask, 2),
                    "mid":      round(mid, 2),
                    "last":     round(float(row.get('lastPrice', 0) or 0), 2),
                    "iv":       round(float(row.get('impliedVolatility', 0) or 0), 4),
                    "iv_pct":   round(float(row.get('impliedVolatility', 0) or 0) * 100, 1),
                    "oi":       int(row.get('openInterest', 0) or 0),
                    "volume":   int(row.get('volume', 0) or 0),
                    "dte":      _dte(exp)
                })
            return result

        chain_out[exp] = {
            "calls": df_to_list(calls_df),
            "puts":  df_to_list(puts_df)
        }

    return {
        "ticker":   analyzer.ticker,
        "spot":     round(analyzer.spot, 2),
        "expiries": analyzer.expiries,
        "chain":    chain_out
    }
```

### 1.3 前端：触发预加载的时机

```javascript
// static/main.js — 在 validateAllTickers() 验证成功后自动触发

async function preloadOptionChains(validTickers) {
    /*
     * 验证成功后立即后台预加载，不阻塞用户操作
     * 结果存入全局缓存 window._chainCache[ticker]
     */
    window._chainCache = window._chainCache || {};

    for (const ticker of validTickers) {
        // 非阻塞：fire and forget，不等待完成
        fetch('/api/preload_option_chain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                window._chainCache[ticker] = data;
                // 通知 Position 模块数据已就绪
                document.dispatchEvent(
                    new CustomEvent('chainLoaded', { detail: { ticker } })
                );
            }
        })
        .catch(err => console.warn(`Chain preload failed for ${ticker}:`, err));
    }
}

// 在验证完成后调用
document.getElementById('tickers').addEventListener('blur', async () => {
    const tickers = parseTickers(document.getElementById('tickers').value);
    if (tickers.length > 0) {
        const { valid } = await validateAllTickers(tickers);
        if (valid.length > 0) {
            preloadOptionChains(valid);  // 异步，不 await
        }
    }
});
```

---

## 模块 2：Position 模块重构 🔴

### 2.1 需求描述

- 新表格列：`ticker | type | expiry | strike | side | price | quantity`
- `expiry` 和 `strike` 为下拉选择，数据来自模块 1 的预加载缓存
- `price` 字段：选中 strike 后自动回填对应 mid price，支持手动覆盖
- `type` 列区分 call/put；`side` 列区分 long/short

### 2.2 前端表格结构（伪代码）

```javascript
// 新版 createPositionRow() 替换原有 createOptionRow()

function createPositionRow(defaultTicker = '') {
    /*
     * 生成一行持仓输入行，包含联动下拉菜单
     */
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>
            <!-- ticker 下拉：来自当前已验证的 ticker 列表 -->
            <select name="pos_ticker" class="pos-select"
                    onchange="onPositionTickerChange(this)">
                <option value="">-- ticker --</option>
                ${getValidTickers().map(t =>
                    `<option value="${t}" ${t===defaultTicker?'selected':''}>${t}</option>`
                ).join('')}
            </select>
        </td>
        <td>
            <!-- type: call / put -->
            <select name="pos_type" class="pos-select"
                    onchange="onPositionTypeChange(this)">
                <option value="call">Call</option>
                <option value="put">Put</option>
            </select>
        </td>
        <td>
            <!-- expiry: 从缓存中动态填充 -->
            <select name="pos_expiry" class="pos-select"
                    onchange="onPositionExpiryChange(this)">
                <option value="">-- expiry --</option>
            </select>
        </td>
        <td>
            <!-- strike: 从缓存中动态填充 -->
            <select name="pos_strike" class="pos-select"
                    onchange="onPositionStrikeChange(this)">
                <option value="">-- strike --</option>
            </select>
        </td>
        <td>
            <!-- side: long / short -->
            <select name="pos_side" class="pos-select">
                <option value="long">Long</option>
                <option value="short">Short</option>
            </select>
        </td>
        <td>
            <!-- price: 自动回填 mid，可手动修改 -->
            <input type="number" name="pos_price" step="0.01"
                   class="pos-price-input" placeholder="Mid">
        </td>
        <td>
            <input type="number" name="pos_qty" step="1"
                   min="1" placeholder="1" class="pos-qty-input">
        </td>
        <td>
            <button type="button" class="btn-delete"
                    onclick="this.closest('tr').remove()">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    return row;
}


function onPositionTickerChange(selectEl) {
    /*
     * ticker 变化时：
     * 1. 清空并重填 expiry 下拉
     * 2. 清空 strike 下拉
     * 3. 清空 price
     */
    const row = selectEl.closest('tr');
    const ticker = selectEl.value;
    const expirySelect = row.querySelector('[name="pos_expiry"]');
    const strikeSelect = row.querySelector('[name="pos_strike"]');

    expirySelect.innerHTML = '<option value="">-- expiry --</option>';
    strikeSelect.innerHTML = '<option value="">-- strike --</option>';
    row.querySelector('[name="pos_price"]').value = '';

    const cache = window._chainCache?.[ticker];
    if (!cache) {
        // 数据尚未就绪，等待 chainLoaded 事件
        document.addEventListener('chainLoaded', function handler(e) {
            if (e.detail.ticker === ticker) {
                populateExpiryDropdown(expirySelect, ticker);
                document.removeEventListener('chainLoaded', handler);
            }
        });
        expirySelect.innerHTML = '<option value="">Loading...</option>';
        return;
    }

    populateExpiryDropdown(expirySelect, ticker);
}


function populateExpiryDropdown(expirySelect, ticker) {
    /*
     * 从缓存中读取 expiry 列表，填入下拉框
     */
    const cache = window._chainCache[ticker];
    const expiries = cache.expiries || [];
    expirySelect.innerHTML = '<option value="">-- expiry --</option>';
    expiries.forEach(exp => {
        const opt = document.createElement('option');
        opt.value = exp;
        const dte = Math.max(0, Math.round(
            (new Date(exp) - new Date()) / (1000 * 60 * 60 * 24)
        ));
        opt.textContent = `${exp} (${dte}d)`;
        expirySelect.appendChild(opt);
    });
}


function onPositionExpiryChange(selectEl) {
    /*
     * expiry 变化时：重填 strike 下拉（按当前 type call/put 过滤）
     */
    const row = selectEl.closest('tr');
    const ticker  = row.querySelector('[name="pos_ticker"]').value;
    const type    = row.querySelector('[name="pos_type"]').value;   // 'call' | 'put'
    const expiry  = selectEl.value;
    const strikeSelect = row.querySelector('[name="pos_strike"]');

    strikeSelect.innerHTML = '<option value="">-- strike --</option>';
    row.querySelector('[name="pos_price"]').value = '';

    if (!ticker || !expiry) return;
    const chain = window._chainCache?.[ticker]?.chain?.[expiry];
    if (!chain) return;

    const contracts = type === 'call' ? chain.calls : chain.puts;
    const spot = window._chainCache[ticker].spot;

    // 排序：从 ITM 到 OTM
    contracts
        .sort((a, b) => a.strike - b.strike)
        .forEach(contract => {
            const opt = document.createElement('option');
            opt.value = contract.strike;
            const moneyLabel = getMoneyLabel(contract.strike, spot, type);
            opt.textContent = `${contract.strike} | IV:${contract.iv_pct}% | Mid:${contract.mid} ${moneyLabel}`;
            opt.dataset.iv  = contract.iv;
            opt.dataset.mid = contract.mid;
            opt.dataset.dte = contract.dte;
            strikeSelect.appendChild(opt);
        });
}


function onPositionStrikeChange(selectEl) {
    /*
     * strike 变化时：自动回填 mid price
     */
    const row = selectEl.closest('tr');
    const selectedOpt = selectEl.options[selectEl.selectedIndex];
    const priceInput = row.querySelector('[name="pos_price"]');
    if (selectedOpt && selectedOpt.dataset.mid) {
        priceInput.value = selectedOpt.dataset.mid;
        priceInput.dataset.autoFilled = 'true';
    }
}


function getMoneyLabel(strike, spot, type) {
    const ratio = strike / spot;
    if (type === 'call') {
        if (ratio < 0.99) return '(ITM)';
        if (ratio > 1.01) return '(OTM)';
        return '(ATM)';
    } else {
        if (ratio > 1.01) return '(ITM)';
        if (ratio < 0.99) return '(OTM)';
        return '(ATM)';
    }
}
```

### 2.3 序列化为后端格式（伪代码）

```javascript
function getPositionsData() {
    /*
     * 从表格读取所有行，序列化为后端期望的 JSON 格式
     * 输出格式需兼容现有 options_greeks.portfolio_greeks_table()
     */
    const rows = document.querySelectorAll('#positions-table tbody tr');
    const positions = [];
    rows.forEach(row => {
        const ticker  = row.querySelector('[name="pos_ticker"]').value;
        const type    = row.querySelector('[name="pos_type"]').value;    // call/put
        const expiry  = row.querySelector('[name="pos_expiry"]').value;
        const strike  = parseFloat(row.querySelector('[name="pos_strike"]').value);
        const side    = row.querySelector('[name="pos_side"]').value;    // long/short
        const price   = parseFloat(row.querySelector('[name="pos_price"]').value);
        const qty     = parseInt(row.querySelector('[name="pos_qty"]').value);

        if (!ticker || !expiry || !strike || !price || !qty) return;

        // 还原为现有后端格式的 option_type 字段
        const optionType = `${side === 'long' ? 'L' : 'S'}${type === 'call' ? 'C' : 'P'}`;
        // optionType ∈ { LC, SC, LP, SP }

        // 从预加载缓存取 IV 和 DTE（用于 Greeks 计算）
        const strikeOpt = row.querySelector('[name="pos_strike"]')
                             .options[row.querySelector('[name="pos_strike"]').selectedIndex];
        const iv  = parseFloat(strikeOpt?.dataset?.iv  || 0);
        const dte = parseInt(strikeOpt?.dataset?.dte || 0);

        positions.push({
            ticker,
            option_type: optionType,
            expiry,
            strike,
            side,
            price,
            quantity: qty,
            iv,
            dte
        });
    });
    return positions;
}
```

---

## 模块 3：投资组合综合分析按钮 🟡

### 3.1 分析维度设计

点击"组合分析"后，系统对整个持仓组合（可含多 ticker）执行以下分析：

| 维度 | 说明 | 依赖数据 |
|---|---|---|
| **到期损益图** | 多腿组合 P&L payoff，当前已有，需扩展至多 ticker | 现有 `market_analyzer.py` |
| **净希腊字母汇总** | 组合级 Delta/Gamma/Theta/Vega，当前已有，需扩展 | 现有 `options_greeks.py` |
| **Theta Decay 路径** | 组合 Theta 随时间衰减曲线（DTE → 0） | 现有 `theta_decay_path()` |
| **风险敞口分解** | 按 ticker、按 expiry、按 side 分组的 Delta 和 Vega 占比饼/柱图 | 从 Greeks 计算结果聚合 |
| **相关性调整后组合 VaR** | 考虑持仓间相关性的组合风险估计 | 现有 `correlation_validator.py` |
| **盈亏平衡分析** | 组合到期盈亏平衡价格区间 | P&L 矩阵 |
| **仓位集中度** | 各 ticker 的名义 Delta 占比 | Greeks 聚合 |

### 3.2 新增后端端点：`app.py`

```python
@app.route('/api/portfolio_analysis', methods=['POST'])
def portfolio_analysis():
    """
    请求体:
    {
        "positions": [
            {
                "ticker": "AAPL",
                "option_type": "LC",   # LC/SC/LP/SP
                "expiry": "2025-04-18",
                "strike": 210,
                "price": 3.6,          # premium paid/received
                "quantity": 2,
                "iv": 0.22,
                "dte": 31
            },
            ...
        ],
        "account_size": 100000,        # 可选
        "max_risk_pct": 2.0            # 可选
    }

    响应: {
        "status": "ok",
        "pnl_chart":        "<base64 PNG>",
        "greeks_summary":   { delta, gamma, theta, vega, net_premium },
        "greeks_detail":    [ {Leg, Strike, DTE, IV, Qty, Delta, ...} ],
        "theta_decay_chart":"<base64 PNG>",
        "risk_breakdown":   { by_ticker: {...}, by_side: {...}, by_expiry: {...} },
        "breakevens":       [price1, price2],
        "position_sizing":  { max_contracts, max_loss_per_contract, ... },
        "portfolio_var_1d": float,
        "warnings":         [...]
    }
    """
    data = request.json
    positions = data.get('positions', [])
    account_size = data.get('account_size')
    max_risk_pct = data.get('max_risk_pct', 2.0)

    if not positions:
        return jsonify({"status": "error", "message": "No positions provided"})

    result = PortfolioAnalysisService.run(positions, account_size, max_risk_pct)
    return jsonify(result)
```

### 3.3 新增服务类：`services/portfolio_analysis_service.py`（伪代码）

```python
class PortfolioAnalysisService:

    @staticmethod
    def run(positions: list, account_size=None, max_risk_pct=2.0) -> dict:
        """
        主入口：协调所有子分析
        """
        result = {"status": "ok", "warnings": []}

        # 1. 获取各 ticker 当前现货价格
        spots = PortfolioAnalysisService._get_spots(positions)

        # 2. Greeks 计算（使用现有 portfolio_greeks_table）
        greeks_totals, greeks_detail_df = portfolio_greeks_table(
            positions=[{
                "type":    pos["option_type"],
                "strike":  pos["strike"],
                "dte":     pos["dte"],
                "iv":      pos["iv"],
                "qty":     pos["quantity"],
                "premium": pos["price"]
            } for pos in positions],
            spot=spots.get(positions[0]["ticker"], 100),  # 主标的
            r=0.05
        )
        result["greeks_summary"] = greeks_totals
        result["greeks_detail"]  = greeks_detail_df.to_dict(orient='records')

        # 3. 到期 P&L 图（需支持多 ticker：按 ticker 分组分别绘制，或归一化为同一横轴）
        pnl_fig = PortfolioAnalysisService._plot_pnl(positions, spots)
        result["pnl_chart"] = _fig_to_base64(pnl_fig)

        # 4. Theta Decay 路径图
        theta_fig = PortfolioAnalysisService._plot_theta_decay(positions, spots)
        result["theta_decay_chart"] = _fig_to_base64(theta_fig)

        # 5. 风险敞口分解
        result["risk_breakdown"] = PortfolioAnalysisService._risk_breakdown(
            positions, spots, greeks_detail_df
        )

        # 6. 盈亏平衡点（单标的时精确计算，多标的时近似）
        result["breakevens"] = PortfolioAnalysisService._find_breakevens(
            positions, spots
        )

        # 7. 仓位管理（仅当提供账户规模时）
        if account_size:
            result["position_sizing"] = PortfolioAnalysisService._position_sizing(
                positions, spots, account_size, max_risk_pct
            )

        # 8. 组合 Delta-VaR（95%，1日）
        result["portfolio_var_1d"] = PortfolioAnalysisService._calc_var(
            positions, spots, greeks_totals
        )

        return result


    @staticmethod
    def _risk_breakdown(positions, spots, greeks_df) -> dict:
        """
        按维度汇总 Delta 暴露，生成饼图数据
        """
        breakdown = {"by_ticker": {}, "by_side": {"long": 0, "short": 0}}

        for pos in positions:
            ticker = pos["ticker"]
            sign   = 1 if pos["side"] == "long" else -1
            delta_contrib = 0  # 从 greeks_df 中匹配

            # 按 ticker 聚合
            if ticker not in breakdown["by_ticker"]:
                breakdown["by_ticker"][ticker] = {"delta": 0, "vega": 0}
            # ... 聚合逻辑

        return breakdown


    @staticmethod
    def _calc_var(positions, spots, greeks_totals, confidence=0.95) -> float:
        """
        Delta-近似 VaR:
        VaR_1d = |Delta_portfolio| × S × σ_1d × z(confidence)
        其中 σ_1d = ATM_IV / sqrt(252)，z(0.95) ≈ 1.645
        """
        from scipy.stats import norm
        import numpy as np

        # 加权平均隐波（按 Vega 加权）
        total_vega = abs(greeks_totals.get('vega', 0)) + 1e-10
        weighted_iv = sum(
            pos['iv'] * abs(pos.get('vega_contrib', 0)) / total_vega
            for pos in positions
        ) or 0.25  # 默认25%

        main_ticker = positions[0]['ticker']
        S = spots.get(main_ticker, 100)
        delta = greeks_totals.get('delta', 0)
        sigma_1d = weighted_iv / np.sqrt(252)
        z = norm.ppf(confidence)

        var_1d = abs(delta) * S * sigma_1d * z * 100  # 乘以合约乘数100
        return round(var_1d, 2)
```

### 3.4 前端触发与展示（伪代码）

```javascript
// static/main.js

async function runPortfolioAnalysis() {
    const positions = getPositionsData();
    if (positions.length === 0) {
        showAlert('请至少添加一个持仓');
        return;
    }

    const btn = document.getElementById('portfolio-analysis-btn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 分析中...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/portfolio_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                positions,
                account_size: parseFloat(document.getElementById('account_size').value) || null,
                max_risk_pct: parseFloat(document.getElementById('max_risk_pct').value) || 2.0
            })
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            renderPortfolioAnalysisResults(data);
            // 自动切换到"组合分析"结果面板
            document.getElementById('portfolio-results-panel').style.display = 'block';
            document.getElementById('portfolio-results-panel').scrollIntoView({ behavior: 'smooth' });
        } else {
            showAlert(`分析失败：${data.message}`);
        }
    } finally {
        btn.innerHTML = '<i class="fas fa-chart-pie"></i> 组合分析';
        btn.disabled = false;
    }
}

function renderPortfolioAnalysisResults(data) {
    /*
     * 渲染以下面板：
     * 1. Greeks 汇总卡片（Delta/Gamma/Theta/Vega/VaR）
     * 2. 到期 P&L 图
     * 3. Theta Decay 路径图
     * 4. 风险分解图（Chart.js 饼图）
     * 5. 盈亏平衡点表格
     * 6. 仓位管理建议（若有）
     */
    renderGreeksSummaryCard(data.greeks_summary, data.portfolio_var_1d);
    renderChartImage('pnl-chart-container',          data.pnl_chart);
    renderChartImage('theta-decay-chart-container',  data.theta_decay_chart);
    renderRiskBreakdownChart(data.risk_breakdown);
    renderBreakevenTable(data.breakevens);
    if (data.position_sizing) {
        renderPositionSizingCard(data.position_sizing);
    }
}
```

---

## 模块 4A：Market Review 动态时序图 🟡

### 4A.1 需求描述

- 将现有静态 DataFrame HTML 表格替换为交互式时序图
- 核心展示：Return / Volatility / Correlation 三组时间序列
- 支持时间段切换（1M / 1Q / YTD / ETD）
- 支持资产切换（主标的 vs 各基准），可叠加对比
- 保留原有数值信息（hover tooltip 显示具体数字）

### 4A.2 后端改造：`core/market_review.py`

```python
def market_review_timeseries(instrument, start_date=None, end_date=None) -> dict:
    """
    新增函数：返回时序数据而非汇总表格，供前端 Chart.js 渲染。
    
    返回格式:
    {
        "dates": ["2024-01-02", "2024-01-03", ...],
        "assets": {
            "AAPL": {
                "prices":        [185.2, 186.1, ...],
                "cum_returns":   [0.0, 0.5, ...],      # % from period start
                "rolling_vol":   [18.2, 18.5, ...],    # 20-day annualized HV %
                "rolling_corr":  [null, null, ..., 0.65, ...]  # vs instrument，前N个为null
            },
            "SPX": { ... },
            "USD": { ... },
            ...
        },
        "instrument": "AAPL",
        "periods": {
            "1M":  "2025-02-17",
            "1Q":  "2024-12-17",
            "YTD": "2025-01-01",
            "ETD": "2024-01-02"
        },
        "summary_table": "<html string>"  # 保留原表格作为 fallback
    }
    """
    # 复用现有数据下载逻辑（参考 market_review() 函数）
    benchmarks = { 'USD':'DX-Y.NYB', 'US10Y':'^TNX', 'Gold':'GC=F',
                   'SPX':'^SPX', 'CSI300':'000300.SS',
                   'HSI':'^HSI', 'NKY':'^N225', 'STOXX':'^STOXX' }
    
    all_tickers    = [instrument] + list(benchmarks.values())
    display_names  = [instrument] + list(benchmarks.keys())
    
    data = yf.download(all_tickers, start=start_date, period="400d",
                       auto_adjust=False, progress=False)["Close"]
    data = data.ffill().dropna()
    data.columns = display_names
    
    returns = data.pct_change().dropna()
    dates   = data.index.strftime('%Y-%m-%d').tolist()
    
    assets_out = {}
    for asset in display_names:
        if asset not in data.columns:
            continue
        
        # 累计收益（相对起始日）
        cum_ret = ((data[asset] / data[asset].iloc[0]) - 1) * 100
        
        # 滚动20日历史波动率（年化 %）
        roll_vol = returns[asset].rolling(20).std() * np.sqrt(252) * 100
        
        # 滚动20日相关性（vs 主标的）
        if asset != instrument:
            roll_corr = returns[instrument].rolling(20).corr(returns[asset])
        else:
            roll_corr = pd.Series(1.0, index=returns.index)
        
        assets_out[asset] = {
            "prices":       [round(x, 2) if pd.notna(x) else None for x in data[asset]],
            "cum_returns":  [round(x, 2) if pd.notna(x) else None for x in cum_ret],
            "rolling_vol":  [round(x, 2) if pd.notna(x) else None for x in roll_vol],
            "rolling_corr": [round(x, 3) if pd.notna(x) else None for x in roll_corr]
        }
    
    # 时间段标记点
    today = data.index[-1]
    periods = {
        "1M":  (today - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
        "1Q":  (today - pd.Timedelta(days=90)).strftime('%Y-%m-%d'),
        "YTD": f"{today.year}-01-01",
        "ETD": data.index[0].strftime('%Y-%m-%d')
    }
    
    return {
        "dates":         dates,
        "assets":        assets_out,
        "instrument":    instrument,
        "periods":       periods,
        "summary_table": market_review(instrument, start_date, end_date).to_html(...)
    }
```

#### 新增 API 端点

```python
@app.route('/api/market_review_ts', methods=['POST'])
def market_review_ts():
    """
    请求体: { "ticker": "AAPL", "start_date": "2024-01-01" }
    响应:   market_review_timeseries() 的返回值
    """
    ticker     = request.json.get('ticker', '').upper()
    start_date = request.json.get('start_date')
    try:
        data = market_review_timeseries(ticker, start_date=start_date)
        return jsonify({"status": "ok", **data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
```

### 4A.3 前端 Chart.js 渲染（伪代码）

```javascript
// static/market_review_chart.js — 新文件

const MR_CHART_CONFIG = {
    COLORS: {
        instrument: '#FF6B35',   // 橙色：主标的
        SPX:  '#2196F3',
        USD:  '#4CAF50',
        Gold: '#FFD700',
        US10Y:'#9C27B0',
        CSI300:'#F44336',
        HSI:  '#00BCD4',
        NKY:  '#FF9800',
        STOXX:'#795548'
    },
    ROLLING_VOL_WINDOW: 20,
    ROLLING_CORR_WINDOW: 20
};

let mrChart = null;      // Chart.js 实例
let mrData  = null;      // 后端返回的原始数据
let mrMode  = 'return';  // 当前显示模式：'return' | 'vol' | 'corr'
let mrPeriod = 'ETD';    // 当前时间段
let mrVisibleAssets = new Set();  // 当前显示的资产


async function loadMarketReviewChart(ticker, startDate) {
    /*
     * 加载时序数据并初始化图表
     * 在 Market Review 标签页激活时调用
     */
    const container = document.getElementById('market-review-chart-container');
    container.innerHTML = '<div class="loading">Loading...</div>';

    const resp = await fetch('/api/market_review_ts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, start_date: startDate })
    });
    mrData = await resp.json();

    if (mrData.status !== 'ok') {
        container.innerHTML = `<div class="error">${mrData.message}</div>`;
        return;
    }

    // 初始化所有资产可见
    mrVisibleAssets = new Set(Object.keys(mrData.assets));

    renderMarketReviewChart();
    renderAssetToggleButtons();
    renderPeriodButtons();
}


function renderMarketReviewChart() {
    /*
     * 根据 mrMode（return|vol|corr）和 mrPeriod（1M|1Q|YTD|ETD）
     * 重新渲染 Chart.js 时序图
     */
    if (!mrData) return;

    // 根据 mrPeriod 筛选日期范围
    const startDate = mrData.periods[mrPeriod];
    const startIdx  = mrData.dates.findIndex(d => d >= startDate);
    const filteredDates = mrData.dates.slice(startIdx);

    // 构建 datasets
    const datasets = [];
    for (const [asset, series] of Object.entries(mrData.assets)) {
        if (!mrVisibleAssets.has(asset)) continue;

        let yData;
        if (mrMode === 'return') {
            // 重新基准化：从 startIdx 开始的累计收益
            const prices = series.prices.slice(startIdx);
            const basePrice = prices[0];
            yData = prices.map(p => p ? ((p / basePrice) - 1) * 100 : null);
        } else if (mrMode === 'vol') {
            yData = series.rolling_vol.slice(startIdx);
        } else {
            // corr: 与主标的的滚动相关性
            yData = series.rolling_corr.slice(startIdx);
        }

        datasets.push({
            label:           asset,
            data:            filteredDates.map((d, i) => ({ x: d, y: yData[i] })),
            borderColor:     MR_CHART_CONFIG.COLORS[asset] || '#999',
            backgroundColor: 'transparent',
            borderWidth:     asset === mrData.instrument ? 2.5 : 1.5,
            pointRadius:     0,
            tension:         0.3
        });
    }

    // 更新或创建图表
    const ctx = document.getElementById('market-review-chart').getContext('2d');
    if (mrChart) mrChart.destroy();
    mrChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend:  { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const v = ctx.parsed.y;
                            if (v === null) return null;
                            if (mrMode === 'return') return `${ctx.dataset.label}: ${v.toFixed(2)}%`;
                            if (mrMode === 'vol')    return `${ctx.dataset.label}: ${v.toFixed(1)}%`;
                            return `${ctx.dataset.label}: ${v.toFixed(3)}`;
                        }
                    }
                }
            },
            scales: {
                x: { type: 'time', time: { unit: 'month' }, grid: { display: false } },
                y: {
                    title: {
                        display: true,
                        text: mrMode === 'return' ? 'Cumulative Return (%)' :
                              mrMode === 'vol'    ? 'Rolling 20d Vol (%)' :
                              'Rolling 20d Correlation'
                    },
                    grid: { color: 'rgba(200,200,200,0.2)' }
                }
            }
        }
    });
}
```

#### HTML 控件（Market Review 标签页内）

```html
<!-- 在 tab-market-review 内，替换原有 table 区域 -->
<div class="content-card">
    <!-- 模式切换 -->
    <div class="mr-toolbar">
        <div class="btn-group" id="mr-mode-btns">
            <button class="btn-toggle active" onclick="setMrMode('return')">Return</button>
            <button class="btn-toggle"         onclick="setMrMode('vol')">Volatility</button>
            <button class="btn-toggle"         onclick="setMrMode('corr')">Correlation</button>
        </div>
        <!-- 时间段切换 -->
        <div class="btn-group" id="mr-period-btns">
            <button class="btn-toggle"         onclick="setMrPeriod('1M')">1M</button>
            <button class="btn-toggle"         onclick="setMrPeriod('1Q')">1Q</button>
            <button class="btn-toggle"         onclick="setMrPeriod('YTD')">YTD</button>
            <button class="btn-toggle active"  onclick="setMrPeriod('ETD')">ETD</button>
        </div>
        <!-- 资产显隐切换 -->
        <div id="asset-toggle-container"></div>
        <!-- 原始数据表格折叠按钮 -->
        <button class="btn-secondary" onclick="toggleSummaryTable()">
            <i class="fas fa-table"></i> 数据表格
        </button>
    </div>

    <!-- Chart.js 时序图 -->
    <div id="market-review-chart-container" style="height: 420px;">
        <canvas id="market-review-chart"></canvas>
    </div>

    <!-- 可折叠的原始数据表格（兼容保留） -->
    <div id="market-review-table-wrapper" style="display:none">
        <div class="table-wrapper">{{ market_review_table | safe }}</div>
    </div>
</div>
```

---

## 模块 4B：Expiry Odds 实现波动率标注 🟡

### 4B.1 需求描述

- 在现有 Odds 图中，输入指定变动幅度后，基于该幅度反推对应的**实现波动率**
- 将该预计实现波动率（Realized Vol Implied by Move）标注在图表上
- 同时叠加显示市场当前 ATM IV，便于判断赔率与概率的关系（IV高估/低估）

### 4B.2 核心计算逻辑

```
设:
  S     = 当前现货价格
  T     = 到期日对应的 DTE / 365（年化时间）
  Move% = 用户输入的预计变动幅度（如 5% = 0.05）

对应的隐含实现波动率（Implied Realized Vol）:
  σ_implied = |Move%| / sqrt(T)

例：30日到期（T=30/365≈0.082），预计上涨5%
  σ_implied = 0.05 / sqrt(0.082) = 0.05 / 0.287 ≈ 17.4%

此 σ_implied 可与市场 ATM IV 直接对比：
  - 若 σ_implied < ATM IV：市场认为此幅度move"便宜"，买权赔率合理
  - 若 σ_implied > ATM IV：市场认为此幅度move"昂贵"，卖权赔率可能更优
```

### 4B.3 后端增强：新增计算函数 `core/options_chain_analyzer.py`

```python
def calc_implied_realized_vol(move_pct: float, dte: int) -> float:
    """
    反推用户预期变动幅度对应的年化实现波动率。
    
    参数:
        move_pct: 预期变动幅度，绝对值，如 0.05 表示 5%
        dte:      距到期日天数
    返回:
        年化实现波动率（小数形式，如 0.174 = 17.4%）
    """
    import numpy as np
    if dte <= 0:
        return 0.0
    T = dte / 365.0
    return abs(move_pct) / np.sqrt(T)


def get_odds_with_vol_context(
    spot: float,
    target_pct: float,
    chain: dict,
    expiries: list
) -> dict:
    """
    增强版 Odds 计算，附加每个到期日的波动率上下文。
    
    参数:
        spot:       现货价格
        target_pct: 用户输入的目标价格（相对现货的百分比，如 105 = 5% up）
        chain:      { expiry: { "calls": df, "puts": df } }
        expiries:   到期日列表
    
    返回: {
        "expiries_data": [
            {
                "expiry":             "2025-04-18",
                "dte":                31,
                "target_price":       223.2,
                "implied_rv":         0.174,    # 反推的实现波动率
                "implied_rv_pct":     17.4,     # 同上，百分比
                "atm_iv":             0.22,     # 市场 ATM IV
                "atm_iv_pct":         22.0,
                "vol_ratio":          0.79,     # implied_rv / atm_iv，< 1 说明 IV 高估此次 move
                "call_odds": [ { "strike": K, "odd": float }, ... ],
                "put_odds":  [ { "strike": K, "odd": float }, ... ]
            },
            ...
        ]
    }
    """
    import numpy as np
    
    target_price = spot * (target_pct / 100.0)
    move_pct = abs(target_price - spot) / spot
    
    results = []
    for exp in expiries:
        if exp not in chain:
            continue
        dte = _dte(exp)
        if dte <= 0:
            continue
        
        calls_df = chain[exp]['calls']
        puts_df  = chain[exp]['puts']
        
        # 反推实现波动率
        impl_rv = calc_implied_realized_vol(move_pct, dte)
        
        # ATM IV（使用 put IV，更准确）
        atm_iv = None
        atm_idx = (puts_df['strike'] - spot).abs().idxmin()
        if atm_idx is not None:
            atm_iv = float(puts_df.loc[atm_idx, 'impliedVolatility'])
        
        vol_ratio = (impl_rv / atm_iv) if atm_iv and atm_iv > 0 else None
        
        # 计算每个行权价的赔率（保留现有逻辑）
        def calc_odds(df, option_type):
            odds = []
            for _, row in df.iterrows():
                K   = float(row['strike'])
                mid = (float(row.get('bid',0) or 0) + float(row.get('ask',0) or 0)) / 2
                if mid <= 0:
                    mid = float(row.get('lastPrice', 0) or 0)
                if mid <= 0:
                    continue
                if option_type == 'call':
                    payoff = max(target_price - K, 0)
                else:
                    payoff = max(K - target_price, 0)
                odd = (payoff - mid) / mid
                odds.append({ "strike": K, "odd": round(odd, 3) })
            return odds
        
        results.append({
            "expiry":         exp,
            "dte":            dte,
            "target_price":   round(target_price, 2),
            "implied_rv":     round(impl_rv, 4),
            "implied_rv_pct": round(impl_rv * 100, 1),
            "atm_iv":         round(atm_iv, 4) if atm_iv else None,
            "atm_iv_pct":     round(atm_iv * 100, 1) if atm_iv else None,
            "vol_ratio":      round(vol_ratio, 3) if vol_ratio else None,
            "call_odds":      calc_odds(calls_df, 'call'),
            "put_odds":       calc_odds(puts_df,  'put')
        })
    
    return { "expiries_data": results, "spot": spot, "target_pct": target_pct }
```

### 4B.4 前端：Odds 图增强（伪代码）

```javascript
// static/main.js — 增强 loadOddsData() 和 renderOddsChart()

async function loadOddsDataEnhanced() {
    const ticker    = document.getElementById('ticker').value.trim().toUpperCase();
    const targetPct = parseFloat(document.getElementById('odds-target').value) || 105;

    const btn = document.getElementById('odds-load-btn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

    try {
        const resp = await fetch('/api/odds_with_vol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, target_pct: targetPct })
        });
        const data = await resp.json();

        if (data.status === 'ok') {
            renderOddsChartEnhanced(data);
            renderVolContextTable(data.expiries_data);
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-download"></i> Load Chain';
    }
}


function renderOddsChartEnhanced(data) {
    /*
     * 在原有赔率折线图上叠加：
     * 1. 每个到期日的"implied RV"垂直标注线（在 x 轴为 strike 时，转换为等效 strike 范围）
     * 2. ATM IV 标注
     * 3. Vol ratio 颜色编码（绿：IV高估此move/卖方有利，红：IV低估/买方有利）
     */
    const ctx  = document.getElementById('odds-chart').getContext('2d');
    const spot = data.spot;

    // 为每个到期日构建 dataset（保留现有逻辑）
    const callDatasets = [];
    const annotationPlugins = [];

    for (const expData of data.expiries_data) {
        const { expiry, dte, implied_rv_pct, atm_iv_pct, vol_ratio } = expData;

        // 标注：implied RV 对应的价格区间
        const impliedMoveAbs = spot * (implied_rv_pct / 100) * Math.sqrt(dte / 365);
        const upperBound = spot + impliedMoveAbs;
        const lowerBound = spot - impliedMoveAbs;

        // 颜色编码：vol_ratio < 0.8 → IV高估此move（绿，对卖方有利）
        //            vol_ratio > 1.2 → IV低估此move（红，对买方有利）
        const bandColor = vol_ratio === null ? 'rgba(128,128,128,0.1)' :
                          vol_ratio < 0.8   ? 'rgba(76,175,80,0.15)' :
                          vol_ratio > 1.2   ? 'rgba(244,67,54,0.15)' :
                                              'rgba(33,150,243,0.1)';

        // 在图表注解中添加：
        // - 竖线：implied RV 对应的 strike 上下界
        // - 文字标注：Impl.RV: 17.4% vs ATM IV: 22.0%
        annotationPlugins.push({
            type: 'box',
            xMin: lowerBound,
            xMax: upperBound,
            backgroundColor: bandColor,
            borderWidth: 0,
            label: {
                display:  true,
                content:  `${expiry.slice(5)}: ${implied_rv_pct}% RV / ${atm_iv_pct}% IV`,
                position: 'start',
                font:     { size: 9 }
            }
        });
    }

    // 重绘图表（Chart.js annotation plugin）
    // ... 保留现有赔率折线 + 叠加注解
}


function renderVolContextTable(expiriesData) {
    /*
     * 在图表下方渲染波动率对比表：
     * | Expiry | DTE | Move Needed | Implied RV | ATM IV | Ratio | Signal |
     */
    const table = document.getElementById('vol-context-table');
    if (!table) return;

    const rows = expiriesData.map(d => {
        const signal = d.vol_ratio === null ? '—' :
                       d.vol_ratio < 0.8   ? '🟢 IV Rich (Seller)' :
                       d.vol_ratio > 1.2   ? '🔴 IV Cheap (Buyer)' :
                                             '🔵 Neutral';
        return `
            <tr>
                <td>${d.expiry}</td>
                <td>${d.dte}</td>
                <td>${((d.target_price / /* spot */ 1) - 1 * 100).toFixed(1)}%</td>
                <td><strong>${d.implied_rv_pct}%</strong></td>
                <td>${d.atm_iv_pct ?? '—'}%</td>
                <td>${d.vol_ratio ?? '—'}</td>
                <td>${signal}</td>
            </tr>
        `;
    }).join('');

    table.querySelector('tbody').innerHTML = rows;
}
```

#### 新增后端端点

```python
@app.route('/api/odds_with_vol', methods=['POST'])
def odds_with_vol():
    """
    请求体: { "ticker": "AAPL", "target_pct": 105 }
    响应:   get_odds_with_vol_context() 的完整返回
    """
    ticker     = request.json.get('ticker', '').upper()
    target_pct = float(request.json.get('target_pct', 105))

    try:
        analyzer = OptionsChainAnalyzer(ticker)
        result   = get_odds_with_vol_context(
            spot       = analyzer.spot,
            target_pct = target_pct,
            chain      = analyzer.chain,
            expiries   = analyzer.expiries
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
```

---

## 模块 5：综合标签页（多 Ticker 汇总） 🟢

### 5.1 综合标签页展示内容

仅当 ticker 数量 ≥ 2 时显示，包含以下子面板：

| 子面板 | 内容 | 数据来源 |
|---|---|---|
| **相关性热力图** | 多 ticker 价格相关性矩阵（滚动30日） | `correlation_validator.py` |
| **波动率对比** | 各 ticker ATM IV、HV20、Vol Premium 对比表 | `options_chain_service.py` |
| **组合 Greeks 汇总** | 若有跨 ticker 持仓，显示组合级 Greeks | `portfolio_analysis_service.py` |
| **Market Review 叠加图** | 多 ticker 累计收益时序叠加（重用模块4A的图表）| `market_review_timeseries()` |
| **Info 摘要卡片** | 各 ticker 的当前价格、1日涨跌幅、ATM IV | 缓存数据 |

### 5.2 后端：`services/analysis_service.py`

```python
def generate_综合_analysis(tickers: list, results_by_ticker: dict) -> dict:
    """
    从各 ticker 的独立分析结果中提取并汇总，生成综合视图数据。
    避免重复下载，复用 results_by_ticker 中已有数据。
    """
    综合 = {}

    # 1. 各 ticker 快照摘要
    综合['summaries'] = {}
    for ticker in tickers:
        res = results_by_ticker.get(ticker, {})
        综合['summaries'][ticker] = {
            'price':       res.get('current_price'),
            'change_1d':   res.get('change_1d'),
            'atm_iv':      res.get('oc_vol_premium', {}).get('atm_iv'),
            'vol_signal':  res.get('oc_vol_premium', {}).get('signal'),
            'hv_20d':      res.get('oc_vol_premium', {}).get('hv_20d')
        }

    # 2. 相关性矩阵（直接计算）
    try:
        import yfinance as yf
        import pandas as pd
        data = yf.download(tickers, period='90d', auto_adjust=False,
                           progress=False)['Close'].ffill().dropna()
        corr = data.pct_change().dropna().corr().round(3)
        综合['correlation_matrix'] = {
            'labels': tickers,
            'values': corr.values.tolist()
        }
    except Exception as e:
        logger.warning(f"Correlation matrix failed: {e}")
        综合['correlation_matrix'] = None

    # 3. Vol Premium 对比
    综合['vol_comparison'] = [
        {
            'ticker':      t,
            'atm_iv':      results_by_ticker.get(t, {}).get('oc_vol_premium', {}).get('atm_iv'),
            'hv_20d':      results_by_ticker.get(t, {}).get('oc_vol_premium', {}).get('hv_20d'),
            'vol_premium': results_by_ticker.get(t, {}).get('oc_vol_premium', {}).get('vol_premium'),
            'signal':      results_by_ticker.get(t, {}).get('oc_vol_premium', {}).get('signal')
        }
        for t in tickers
    ]

    return 综合
```

### 5.3 前端：相关性热力图渲染（伪代码）

```javascript
function renderCorrelationHeatmap(corrData) {
    /*
     * 使用 Chart.js（matrix 类型）或 SVG 渲染 N×N 相关性热力图
     * 颜色: 1.0 → 深蓝, 0 → 白, -1.0 → 深红
     */
    const { labels, values } = corrData;
    const n = labels.length;

    // 生成 SVG 热力图（无需额外插件）
    const cellSize = 60;
    const margin   = 80;
    const totalSize = cellSize * n + margin;

    let svgCells = '';
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const corr  = values[i][j];
            const color = corrToColor(corr);  // 颜色映射函数
            const x = margin + j * cellSize;
            const y = margin + i * cellSize;
            svgCells += `
                <rect x="${x}" y="${y}" width="${cellSize}" height="${cellSize}"
                      fill="${color}" stroke="white" stroke-width="1"/>
                <text x="${x + cellSize/2}" y="${y + cellSize/2 + 5}"
                      text-anchor="middle" font-size="12"
                      fill="${Math.abs(corr) > 0.5 ? 'white' : 'black'}">
                    ${corr.toFixed(2)}
                </text>
            `;
        }
    }

    // 轴标签
    let axisLabels = labels.map((label, i) => `
        <text x="${margin + i * cellSize + cellSize/2}" y="${margin - 10}"
              text-anchor="middle" font-size="11" transform="rotate(-30,${margin + i*cellSize+cellSize/2},${margin-10})">${label}</text>
        <text x="${margin - 10}" y="${margin + i * cellSize + cellSize/2 + 5}"
              text-anchor="end" font-size="11">${label}</text>
    `).join('');

    const svg = `
        <svg viewBox="0 0 ${totalSize} ${totalSize}"
             xmlns="http://www.w3.org/2000/svg">
            ${axisLabels}
            ${svgCells}
        </svg>
    `;

    document.getElementById('correlation-heatmap-container').innerHTML = svg;
}


function corrToColor(corr) {
    // 线性插值：-1→红，0→白，+1→蓝
    if (corr > 0) {
        const r = Math.round(255 * (1 - corr));
        const g = Math.round(255 * (1 - corr));
        return `rgb(${r},${g},255)`;
    } else {
        const intensity = Math.abs(corr);
        const g = Math.round(255 * (1 - intensity));
        const b = Math.round(255 * (1 - intensity));
        return `rgb(255,${g},${b})`;
    }
}
```

---

## 附录 A：文件改动清单

| 文件 | 改动类型 | 所属模块 |
|---|---|---|
| `app.py` | 修改路由 + 新增端点 | 0, 1, 4B, 5 |
| `templates/index.html` | 重构输入区 + 新增标签页结构 | 0, 2, 3, 4A |
| `static/main.js` | 多 ticker 逻辑 + Position 联动 | 0, 1, 2, 3 |
| `static/market_review_chart.js` | **新建**：Chart.js 时序图逻辑 | 4A |
| `core/market_review.py` | 新增 `market_review_timeseries()` | 4A |
| `core/options_chain_analyzer.py` | 新增 `get_odds_with_vol_context()` | 4B |
| `services/analysis_service.py` | 新增 `generate_综合_analysis()` | 5 |
| `services/portfolio_analysis_service.py` | **新建**：组合分析服务 | 3 |

---

## 附录 B：关键数据流说明

### B1. 期权数据流（模块 1 → 2 → 3）

```
用户输入 ticker
    │
    ▼
/api/validate_ticker（现有）
    │ 验证成功
    ▼
/api/preload_option_chain（新建）
    │ 后台异步
    ▼
window._chainCache[ticker] = { expiries, chain, spot }
    │
    ├─→ Position 模块 expiry 下拉填充
    ├─→ Position 模块 strike 下拉填充（含 IV/mid 自动回填）
    └─→ /api/portfolio_analysis（用户点击组合分析时触发）
```

### B2. Market Review 数据流（模块 4A）

```
用户切换到 Market Review 标签
    │
    ▼
loadMarketReviewChart(ticker, startDate)
    │
    ▼
/api/market_review_ts（新增）
    │ 返回时序 JSON
    ▼
Chart.js 渲染（Return / Vol / Corr 三模式）
    │
    ├─→ 时间段切换（1M/1Q/YTD/ETD）：纯前端切片，无需重新请求
    └─→ 资产显隐切换：纯前端 dataset 过滤
```

### B3. Odds + Vol 数据流（模块 4B）

```
用户在 Odds 页输入目标涨幅（如 +5%）
    │
    ▼
/api/odds_with_vol（新增）
    │ 返回每个到期日的: odds + implied_rv + atm_iv + vol_ratio
    ▼
renderOddsChartEnhanced()
    ├─→ 赔率折线图（保留现有）
    ├─→ IV 对比带状区域（新增 annotation）
    └─→ renderVolContextTable()：Vol 对比汇总表
```

---

## 附录 C：期权交易理论依据（参考 Euan Sinclair）

以下设计决策直接引用 *Volatility Trading* 和 *Positional Option Trading* 的核心框架：

### C1. 模块 4B 设计依据
> **Odds vs Probability**：赔率只告诉你"盈利多少"，不告诉你"多大概率实现"。  
> 实现 σ > IV 时，市场高估了此次 move 的概率，卖方有统计优势；  
> 实现 σ < IV 时，市场低估了此次 move，买方有优势。  
> 系统通过展示 `implied_rv / atm_iv` 的比值，帮助交易者在赔率图旁直接看到概率分布的倾斜方向。

### C2. 模块 3 Greeks 设计依据
> 组合管理的核心是**净敞口管理**，而非单腿管理。  
> Delta 中性（Delta ≈ 0）+ Vega 暴露（Vega ≠ 0）是波动率交易的标准形态。  
> 系统新增 Delta-VaR 指标用于量化组合的方向性风险，防止因隐性 Delta 暴露导致不预期的方向亏损。

### C3. 模块 2 IV 自动回填设计依据
> 构建持仓时，"以成交价估算未来成本"是常见错误。  
> 使用 mid price 作为建仓成本基准，配合 bid-ask spread 的流动性评分（现有 GOOD/FAIR/AVOID），  
> 帮助交易者在构建组合时直观感知实际成本 vs 理论定价的偏差。

---

## 附录 D：执行注意事项

1. **测试顺序**：先在单 ticker 场景下验证每个模块，再测试多 ticker 并发场景。
2. **性能考量**：`preload_option_chain` 对每个 ticker 调用一次 yfinance，建议设 15 分钟缓存 TTL（已在模块 1 中设计）。
3. **多 ticker 并发**：`ThreadPoolExecutor(max_workers=4)` 限制并发数，防止 yfinance rate limit。
4. **localStorage 兼容**：新版 Position 模块的持仓数据（含新增字段）需更新 `FormManager.saveState()` 和 `loadState()` 的序列化逻辑。
5. **向后兼容**：`market_review_timeseries()` 的返回值包含 `summary_table` 字段（原有 HTML 表格），作为 fallback。
6. **`__综合__` 键名**：后端字典中使用 `__综合__` 作为综合分析的键，前端模板用 `results.__综合__` 访问，注意 Jinja2 的属性访问语法。
