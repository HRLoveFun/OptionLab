# Market Observation Dashboard

A comprehensive market analysis tool for measuring statistics of index returns and oscillations across different frequencies, with integrated options strategy analysis.

## Features

### Market Analysis
- **Price Dynamics**: Download and process stock data from Yahoo Finance
- **Multiple Frequencies**: Support for Daily (D), Weekly (W), Monthly (ME), and Quarterly (QE) analysis
- **Oscillation Analysis**: Calculate price oscillations with optional overnight effect consideration
- **Statistical Analysis**: Comprehensive tail statistics and distribution analysis
- **Period Segmentation**: Analyze data across different time periods (1Y, 3Y, 5Y, All)

### Visualization
- **Scatter Plots**: Feature vs Returns correlation analysis with marginal histograms
- **Cumulative Distribution**: Tail distribution analysis across different periods
- **Projection Charts**: Market oscillation projections with configurable bias
- **Interactive Dashboard**: Modern, responsive web interface

### Options Strategy
- **Portfolio Analysis**: Support for multiple option positions (Long/Short Calls/Puts)
- **P&L Visualization**: Comprehensive profit/loss analysis across price ranges
- **Breakeven Analysis**: Automatic calculation of breakeven points
- **Risk Assessment**: Maximum profit/loss calculations

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd market-observation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

### Basic Analysis
1. Enter a ticker symbol (e.g., AAPL, ^GSPC)
2. Set the start date in YYYYMM format
3. Choose analysis frequency (Weekly, Monthly, Quarterly)
4. Select time periods for analysis
5. Click "Run Analysis"

### Options Strategy Analysis
1. Add option positions using the options table
2. Specify option type (SC/SP/LC/LP), strike, quantity, and premium
3. Submit the form to generate P&L analysis

### Key Classes

#### PriceDynamic
Core class for handling price data:
```python
pxdy = PriceDynamic(ticker="AAPL", start_date=dt.date(2020, 1, 1), frequency='W')
oscillation = pxdy.osc(on_effect=True)  # Calculate oscillation
returns = pxdy.ret()  # Calculate returns
```

#### MarketAnalyzer
High-level analysis class:
```python
analyzer = MarketAnalyzer("AAPL", dt.date(2020, 1, 1), 'W')
scatter_plot = analyzer.generate_scatter_plot('Oscillation')
tail_stats = analyzer.calculate_tail_statistics('Oscillation')
```

## API Endpoints

- `GET/POST /`: Main dashboard interface
- `POST /api/validate_ticker`: Ticker symbol validation

## Configuration

### Supported Frequencies
- `D`: Daily
- `W`: Weekly  
- `ME`: Monthly
- `QE`: Quarterly

### Option Types
- `SC`: Short Call
- `SP`: Short Put
- `LC`: Long Call
- `LP`: Long Put

## Technical Details

### Data Processing
- Automatic data download from Yahoo Finance
- Resampling for different frequencies
- Calculation of derived features (oscillation, returns, differences)
- Period segmentation for comparative analysis

### Statistical Analysis
- Tail statistics (mean, std, skewness, kurtosis, percentiles)
- Cumulative distribution analysis
- Gap statistics with Kolmogorov-Smirnov testing
- Projection modeling with bias optimization

### Visualization
- Matplotlib-based chart generation
- Base64 encoding for web display
- Responsive design with modern CSS
- Interactive form state management

## Error Handling

The application includes comprehensive error handling:
- Input validation for all form fields
- Data download error recovery
- Calculation error logging
- User-friendly error messages

## Browser Compatibility

- Modern browsers with JavaScript enabled
- Responsive design for mobile and desktop
- Local storage for form state persistence

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Disclaimer

This tool is for educational and research purposes only. It should not be used as the sole basis for investment decisions. Always consult with qualified financial professionals before making investment decisions.