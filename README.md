Target: Measure statistics of index return and oscillation for a given frequency. Apply short strangle strategy and earn premium in long terms.

TO DO
- Volatility Dynamic
  x: time, y: volatility

- Add a Parameter "Side Bias": Natural, Netural (Default)

- Modify Oscillation Projection
  spot line for price movement prediction
  is the calculation good for every frequency?
  
marketobserve.py

- class PriceDynamic(self, ticker, start_date=dt.date(2010,01,01)):
- "A DataFrame with Daily OHLC of a given ticker"

| Index | Open | High | Low | Close | Adj Close | Volume |
|-------|------|------|-----|-------|-----------|--------|
| Day1  | ...  | ...  | ... | ...   | ...       | ...     |
| Day2  | ...  | ...  | ... | ...   | ...       | ...     |
| ...   | ...  | ...  | ... | ...   | ...       | ...     |
| DayN  | ...  | ...  | ... | ...   | ...       | ...     |
  
  - ticker: necesary parameter when initialize the class.
  - start_date: the first date the record starts. 
  - frequency:  determine the frequency for sampling, 'D', 'W', 'ME', 'QE'. Default 'D'. 
  - osc: calculate the oscillation of price.
    - percentage unit. (High - Low) / Last Close * 100
  - ret: calculate the return of close price. 
    - percentage unit. (Close - Last Close) / Last Close * 100
  - dif: calculate the diff of close price. 
    - decimal unit. Close - Last Close
Example:
ticker = "^HSI"
pxdy_hsi = PriceDynamic(ticker)

 
