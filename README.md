# Market Observation Dashboard

A comprehensive market analysis tool for measuring statistics of index returns and oscillations across different frequencies, with integrated options strategy analysis.

## Features

### Market Analysis
- **Price Dynamics**: Download and process stock data from Yahoo Finance
- **Multiple Frequencies**: Support for Daily (D), Weekly (W), Monthly (ME), and Quarterly (QE) analysis
- **Oscillation Analysis**: Calculate price oscillations with optional overnight effect consideration
- **Statistical Analysis**: Comprehensive tail statistics and distribution analysis
- **Period Segmentation**: Analyze data across different time periods (1Y, 3Y, 5Y, All)
- **Volatility Dynamics**: Track volatility changes over time with multiple rolling windows

### Enhanced Parameters
- **Risk Threshold**: Configurable percentile threshold (0-100%) for projection analysis
- **Side Bias**: Choose between Natural (market-driven) or Neutral (balanced) bias for projections
- **Advanced Projections**: Oscillation projections with bias optimization and enhanced accuracy

### Visualization
- **Scatter Plots**: Feature vs Returns correlation analysis with marginal histograms
- **Cumulative Distribution**: Tail distribution analysis across different periods
- **Volatility Dynamics**: Time-series visualization of volatility patterns
- **Projection Charts**: Market oscillation projections with configurable bias and risk thresholds
- **Interactive Dashboard**: Modern, responsive web interface with fixed parameter bar

### Options Strategy
- **Portfolio Analysis**: Support for multiple option positions (Long/Short Calls/Puts)
- **P&L Visualization**: Comprehensive profit/loss analysis across price ranges
- **Breakeven Analysis**: Automatic calculation of breakeven points
- **Risk Assessment**: Maximum profit/loss calculations
- **Toggle Interface**: Collapsible options section for clean UI

### UI/UX Improvements
- **Fixed Parameter Bar**: Sticky top navigation with all key parameters
- **Top-Down Layout**: Vertical structure for better content flow
- **Toggle Sections**: Collapsible options interface
- **Responsive Design**: Optimized for all screen sizes
- **Form State Persistence**: Automatic saving/loading of user inputs

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
1. Enter a ticker symbol (e.g., AAPL, ^GSPC) in the fixed parameter bar
2. Set the start date in YYYYMM format
3. Choose analysis frequency (Daily, Weekly, Monthly, Quarterly)
4. Select time periods for analysis (1Y, 3Y, 5Y, All)
5. Configure risk threshold (0-100%, default 90%)
6. Choose side bias (Natural or Neutral)
7. Click "Analyze"

### Options Strategy Analysis
1. Click on "Options Strategy" to expand the toggle section
2. Add option positions using the "Add Position" button
3. Specify option type (SC/SP/LC/LP), strike, quantity, and premium
4. Submit the form to generate P&L analysis

### Parameter Explanations

#### Risk Threshold
- **Range**: 0-100%
- **Default**: 90%
- **Purpose**: Sets the percentile level for oscillation projection analysis
- **Impact**: Higher values create wider projection bands, lower values create tighter bands

#### Side Bias
- **Natural**: Uses historical market behavior to determine projection bias (target_bias=None)
- **Neutral**: Forces balanced projections with no directional bias (target_bias=0)
- **Impact**: Natural bias reflects market tendencies, Neutral bias provides symmetric projections

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
volatility_plot = analyzer.generate_volatility_dynamics()
projection = analyzer.generate_oscillation_projection(percentile=0.9, target_bias=None)
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

### Side Bias Options
- `Natural`: Market-driven bias based on historical performance
- `Neutral`: Balanced bias with no directional preference

## Technical Details

### Data Processing
- Automatic data download from Yahoo Finance
- Resampling for different frequencies
- Calculation of derived features (oscillation, returns, differences)
- Period segmentation for comparative analysis
- Enhanced volatility tracking with multiple rolling windows

### Statistical Analysis
- Tail statistics (mean, std, skewness, kurtosis, percentiles)
- Cumulative distribution analysis
- Gap statistics with Kolmogorov-Smirnov testing
- Projection modeling with advanced bias optimization
- Volatility dynamics analysis

### Visualization
- Matplotlib-based chart generation
- Base64 encoding for web display
- Responsive design with modern CSS
- Interactive form state management
- Fixed parameter bar for improved UX

### Enhanced Features
- **Natural Bias Calculation**: Analyzes historical performance to determine optimal projection weights
- **Volatility Dynamics**: Multi-timeframe volatility analysis with rolling windows
- **Improved Projections**: Enhanced oscillation projections with bias-aware calculations
- **Toggle Interface**: Collapsible sections for better space utilization

## Error Handling

The application includes comprehensive error handling:
- Input validation for all form fields including new parameters
- Data download error recovery
- Calculation error logging
- User-friendly error messages
- Graceful degradation for missing features

## Browser Compatibility

- Modern browsers with JavaScript enabled
- Responsive design for mobile and desktop
- Local storage for form state persistence
- Optimized for touch interfaces

## Recent Improvements

### UI/UX Enhancements
- Fixed parameter bar for always-accessible controls
- Top-down layout replacing left-right structure
- Toggle-based options section
- Improved responsive design
- Enhanced form state management

### Functional Enhancements
- Risk threshold parameter for projection control
- Side bias selection (Natural vs Neutral)
- Volatility dynamics visualization
- Enhanced bias calculation algorithms
- Improved projection accuracy

### Code Quality
- Better error handling and logging
- Enhanced parameter validation
- Improved code organization
- Comprehensive documentation

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