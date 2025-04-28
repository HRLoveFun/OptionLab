Target: Measure statistics of index return and oscillation for a given frequency. Apply short strangle strategy and earn premium in long terms.

marketobserve.py

 - class PriceDynamic(self, ticker, start_date=dt.date(2010,01,01)):
 - "A DataFrame with Daily OHLC of a given ticker"
 - |     | Open | High | Low | Close | Adj Close | Volume |
 - |Index|                          ...                   |
 - |Day1 |                          ...                   |
 - |Day2 |                          ...                   |
 - |...  |                          ...                   |
 - |DayN |                          ...                   |
   
   - ticker: necesary parameter when initialize the class.
   - start_date: the first date the record starts. 
   - frequency:  determine the frequency for sampling, 'D', 'W', 'ME', 'QE'.
   - oscillation: calculate the oscillation of price for given frequency.
     - percentage unit. (High - Low) / Last Close * 100
   - return: calculate the return of price for given frequency. 
     - percentage unit. (Close - Last Close) / Last Close * 100
   - diff
     - decimal unit. Close - Last Close

 
