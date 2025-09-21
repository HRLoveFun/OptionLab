# Market Observation Dashboard

A comprehensive Flask-based web application for market analysis and options strategy evaluation, providing statistical analysis on index returns and oscillations across multiple time frequencies.

## Features

### Core Analysis
- **Market Data Processing**: Download and process stock data from Yahoo Finance
- **Multi-Frequency Analysis**: Analyze daily, weekly, monthly, and quarterly data
- **Oscillation Analysis**: Calculate price oscillations with/without overnight effects
- **Statistical Analysis**: Comprehensive tail statistics, distribution analysis, and volatility dynamics
- **Period Segmentation**: Analyze data across 1Y, 3Y, 5Y, or entire available history

### Advanced Features
- **Risk Assessment**: Configurable percentile thresholds for risk projections
- **Bias Analysis**: Natural vs Neutral bias selection for market projections
- **Options Strategy**: Multi-position portfolio analysis with P&L visualization
- **Market Review**: Multi-asset comparative analysis with correlation matrices

### User Experience
- **Responsive Design**: Mobile-first responsive interface
- **Real-time Validation**: Asynchronous ticker symbol validation
- **Form Persistence**: Automatic saving/loading of form state
- **Interactive Charts**: High-quality matplotlib visualizations
- **Collapsible Sections**: Clean, organized interface with expandable options

## Technology Stack

- **Backend**: Flask 3.1.1, Python 3.8+
- **Data Processing**: pandas, numpy, scipy
- **Visualization**: matplotlib, seaborn
- **Market Data**: yfinance
- **Frontend**: Vanilla JavaScript, CSS Grid/Flexbox
- **Deployment**: Gunicorn WSGI server

## Project Structure

```
OptionStrategy/
├── app.py                    # Flask application entry point
├── requirements.txt          # Python dependencies
├── README.md                # Project documentation
├── .env.example             # Environment variables template
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── market_analyzer.py   # Main analysis engine
│   ├── market_review.py     # Multi-asset review functionality
│   └── price_dynamic.py     # Data processing and calculations
├── services/                # Service layer
│   ├── __init__.py
│   ├── analysis_service.py  # Analysis orchestration
│   ├── chart_service.py     # Chart generation utilities
│   ├── form_service.py      # Form data processing
│   ├── market_service.py    # Market data operations
│   └── validation_service.py # Input validation
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── data_utils.py        # Data processing utilities
│   └── utils.py             # Common helpers and formatters
├── templates/               # Jinja2 templates
│   └── index.html
└── static/                  # Static assets
    ├── styles.css
    └── main.js
```

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd OptionStrategy
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser to `http://localhost:5000`

## API Endpoints

### Main Dashboard
- **GET/POST** `/`
  - GET: Renders the main dashboard interface
  - POST: Processes analysis request and returns results
  - **Parameters**:
    - `ticker` (str): Stock symbol (e.g., "AAPL", "^GSPC")
    - `start_time` (str): Analysis start date in YYYYMM format
    - `frequency` (str): Data frequency - D/W/ME/QE
   - (removed) `periods`: The app now uses the Horizon months to drive the analysis window.
    - `risk_threshold` (int): Risk percentile threshold (0-100)
    - `side_bias` (str): "Natural" or "Neutral" bias
    - `option_position` (JSON): Optional options positions

### Ticker Validation
- **POST** `/api/validate_ticker`
  - **Request**: `{"ticker": "AAPL"}`
  - **Response**: `{"valid": true/false, "message": "..."}`

## Key Components

### Core Classes

#### PriceDynamic
- Handles data download from Yahoo Finance
- Frequency conversion and resampling
- Oscillation and return calculations
- Volatility analysis

#### MarketAnalyzer
- High-level analysis orchestration
- Statistical calculations and projections
- Chart generation and visualization
- Options portfolio analysis

#### Service Layer
- **AnalysisService**: Coordinates complete analysis workflow
- **MarketService**: Market data validation and review generation
- **FormService**: Form data extraction and processing
- **ValidationService**: Input validation and error handling

### Frontend Features

#### Form Management
- Automatic state persistence using localStorage
- Real-time ticker validation with visual feedback
- Dynamic options position management
- Responsive parameter controls

#### Visualization
- Interactive scatter plots with marginal histograms
- Cumulative distribution analysis
- Volatility dynamics with bull/bear market identification
- Options P&L analysis with breakeven calculations

## Configuration

### Environment Variables
```bash
# Flask settings
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key
PORT=5000

# Logging
LOG_LEVEL=INFO

# Analysis defaults
DEFAULT_FREQUENCY=W
DEFAULT_RISK_THRESHOLD=90
```

### Analysis Parameters
- **Frequencies**: Daily (D), Weekly (W), Monthly (ME), Quarterly (QE)
   (The Periods controls have been removed; analysis follows the Horizon window.)
- **Risk Thresholds**: 0-100% percentile for volatility projections
- **Bias Types**: Natural (data-driven) vs Neutral (symmetric)

## Usage Examples

### Basic Market Analysis
1. Enter ticker symbol (e.g., "AAPL")
2. Set analysis horizon (e.g., "202001" for Jan 2020)
3. Select frequency (Weekly recommended)
4. Set Horizon start/end months (optional end)
5. Set risk threshold (90% default)
6. Click "Analyze"

### Options Strategy Analysis
1. Complete basic analysis setup
2. Expand "Positions (Optional)" section
3. Add option positions:
   - Type: Short Call, Short Put, Long Call, Long Put
   - Strike price, quantity, premium
4. Submit analysis for combined market + options view

### Market Review
The system automatically generates comparative analysis including:
- US Dollar Index, 10-Year Treasury, Gold, S&P 500
- CSI 300, STOXX Europe 600, Hang Seng, Nikkei 225
- Returns, volatility, and correlation analysis

## Performance Optimizations

- **Efficient Data Processing**: Vectorized pandas operations
- **Caching**: Form state persistence and data caching
- **Lazy Loading**: On-demand chart generation
- **Optimized Dependencies**: Minimal required packages
- **Memory Management**: Proper matplotlib figure cleanup

## Deployment

### Production Deployment
```bash
# Using Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 app:application

# Using Docker (create Dockerfile)
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:application"]
```

### Environment Setup
- Set `FLASK_ENV=production`
- Configure proper logging levels
- Set secure `SECRET_KEY`
- Configure reverse proxy (nginx recommended)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.

---

**Market Observation Dashboard** - Advanced analytics for informed trading decisions.