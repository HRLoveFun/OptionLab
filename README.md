# Market Observation Dashboard

A comprehensive tool for market analysis and options strategy, providing statistics on index returns and oscillations across multiple frequencies.

## Features

- **Market Analysis**: Download/process stock data from Yahoo Finance; analyze daily, weekly, monthly, and quarterly frequencies.
- **Oscillation & Returns**: Calculate price oscillations (with/without overnight effect) and returns.
- **Statistical Analysis**: Tail statistics, distribution, and volatility dynamics with rolling windows.
- **Period Segmentation**: Analyze 1Y, 3Y, 5Y, or all data.
- **Risk Threshold & Bias**: Configurable percentile for projections; choose Natural or Neutral bias.
- **Visualization**: Scatter plots, cumulative distributions, volatility, and projection charts.
- **Options Strategy**: Analyze portfolios with multiple positions; visualize P&L, breakeven, and risk.
- **UI/UX**: Fixed parameter bar, responsive design, collapsible options, and form state persistence.

## Installation

```bash
git clone <repository-url>
cd market-observation
pip install -r requirements.txt
python app.py
```
Open `http://localhost:5000` in your browser.

## Usage

### Basic Analysis
1. Enter a ticker (e.g., AAPL, ^GSPC).
2. Set start date (YYYYMM).
3. Choose frequency.
4. Select periods.
5. Set risk threshold (0-100%).
6. Choose bias.
7. Click "Analyze".

### Options Strategy
1. Expand "Positions" section.
2. Add/edit option positions (type, strike, quantity, premium).
3. Submit to view P&L analysis.

## Parameters

- **Risk Threshold**: Percentile for oscillation projection (default 90%).
- **Side Bias**: 
  - *Natural*: Uses historical bias.
  - *Neutral*: Forces balanced projection.

## Key Classes

- **PriceDynamic**: Handles price data, oscillation, and returns.
- **MarketAnalyzer**: High-level analysis, statistics, and visualization.

## API

- `/` (GET/POST): Main dashboard.
- `/api/validate_ticker` (POST): Validate ticker.

## Technical Details

- Data from Yahoo Finance, resampled as needed.
- Rolling window volatility and tail statistics.
- Matplotlib/seaborn for charts, base64 for web display.
- Responsive, modern CSS and persistent form state.

## Error Handling

- Input validation for all fields.
- Graceful handling of data download/calculation errors.
- User-friendly error messages.

## Contributing

1. Fork and branch.
2. Make changes and add tests.
3. Submit a pull request.

## License

MIT License.

## Disclaimer

For educational/research use only. Not investment advice.
