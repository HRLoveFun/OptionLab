import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 设置非 GUI 后端
import matplotlib.pyplot as plt
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
import numpy as np
import seaborn as sns
import datetime as dt
from matplotlib.ticker import PercentFormatter, LogFormatter
from scipy.stats import ks_2samp, percentileofscore

yf.enable_debug_mode()

PERIODS = [12, 36, 60, "ALL"]

class PriceDynamic:

    def __init__(self, ticker: str, start_date = dt.date(2016, 12, 1), frequency='D'):
        """
        Initialize the PriceDynamic class.

        :param ticker: Stock ticker symbol, a necessary parameter when initializing the class.
        :param start_date: The first date the record starts.
        :param frequency: Determine the frequency for sampling, allowed values are 'D', 'W', 'ME', 'QE'. Default is 'D'.
        """

        assert isinstance(start_date, dt.date)
        assert frequency in ['D', 'W', 'ME', 'QE']

        self.ticker = ticker
        self.start_date = start_date
        self.frequency = frequency

        data = self._download_data()
        self._data = self._refrequency(data)

    def __getattr__(self, attr):
        # 当访问实例属性时，若属性不存在，尝试从 _data 中获取
        if self._data is not None:
            return getattr(self._data, attr)
        return None

    def __getitem__(self, item):
        # 支持索引操作，将操作转发给 _data
        if self._data is not None:
            return self._data[item]
        return None

    def _download_data(self):
        """
        Download stock data from Local, Yahoo Finance, BBG, Futu, etc.

        :return: DataFrame containing stock data with columns 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'.
        """

        # try:
        #     local_data = pd.read_excel(f"PriceDynamic.xlsx", sheet_name=self.ticker, index_col=0)
        #     local_data = local_data[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        #     print("Data loaded from local database.")
        #     return local_data
        # except FileNotFoundError:
        #     print("Local data file not found.")
        # except KeyError as e:
        #     print(f"Missing column {e} in local data.")
        # except Exception as e:
        #     print(f"Unexpected error loading local data: {e}")

        try:
            df = yf.download(
                self.ticker,
                start=self.start_date,
                interval='1d',
                progress=True,
                auto_adjust=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.set_index(pd.DatetimeIndex(df.index), inplace=True)
            df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]

            return df
        except Exception as e:
            print(f"Unexpected error downloading data: {e}")
        return None

    def _refrequency(self, df):
        """
        Resample the data to the specified frequency.

        :param df: DataFrame to be resampled.
        :return: Resampled DataFrame.
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")
        if not {'Open', 'High', 'Low', 'Close'}.issubset(df.columns):
            raise ValueError("DataFrame must contain OHLC columns")

        if self.frequency == 'D':
            df['LastClose'] = df["Close"].shift(1)
            return df
        else:
            try:
                refrequency_df = df.resample(self.frequency).agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Adj Close': 'last',
                    'Volume': 'sum',
                    # 'OpenDate': lambda x: x['Open'].index[0],
                    # 'HighDate': lambda x: x['High'].index[x['High'].argmax()],
                    # 'LowDate': lambda x: x['Low'].index[x['Low'].argmin()],
                    # 'CloseDate': lambda x: x['Close'].index[-1]
                }).dropna()
                refrequency_df['LastClose'] = refrequency_df["Close"].shift(1)
                refrequency_df['OpenDate'] = df.resample(self.frequency).agg({'Open': lambda x: x.index[0]})
                refrequency_df['HighDate'] = df.resample(self.frequency).agg({'High': lambda x: x.index[x.argmax()]})
                refrequency_df['LowDate'] = df.resample(self.frequency).agg({'Low': lambda x: x.index[x.argmin()]})
                refrequency_df['CloseDate'] = df.resample(self.frequency).agg({'Close': lambda x: x.index[-1]})       

                return refrequency_df
            except KeyError as e:
                print(f"Missing column {e} in DataFrame")
                return None
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                return None

    def osc(self, on_effect=False):
        """
        Calculate the oscillation of price.
        parameters:
            on_effect: the overnight effect, i.e. price gap between open and last close.   
        return: DataFrame containing oscillation data.
        """
        if self._data is None:
            return None
        if on_effect:
            osc_data = ( 
                (
                    self._data["High"] + self._data["LastClose"] + abs(self._data["High"] - self._data["LastClose"]) 
                    )/2 
                - 
                (
                    self._data["Low"] + self._data["LastClose"] - abs(self._data["Low"] - self._data["LastClose"]) 
                    )/2 
                ) / self._data['LastClose'] * 100
        else:
            osc_data = (self._data["High"] - self._data["Low"]) / self._data['LastClose'] * 100

        osc_data.name = 'oscillation'

        return osc_data

    # def tr(self):
    #     """
    #     Calculate the true range of price.

    #     :return: DataFrame containing oscillation data.
    #     """
    #     if self._data is None:
    #         return None
    #     tr_data = np.max(
    #         (self._data["High"] - self._data["Low"]) / self._data['LastClose'] * 100,
    #         abs((self._data["LastClose"] - self._data["Low"]) / self._data['LastClose'] * 100),
    #         abs((self._data["High"] - self._data["LastClose"]) / self._data['LastClose'] * 100),
    #         )
    #     tr_data.name = 'truerange'
    #     return tr_data

    def ret(self):
        """
        Calculate the return of close price.

        :return: DataFrame containing return data.
        """
        if self._data is None:
            return None
        ret_data = ((self._data["Close"] - self._data['LastClose']) / self._data['LastClose']) * 100
        ret_data.name = 'returns'

        return ret_data

    def dif(self):
        """
        Calculate the diff of close price.

        :return: DataFrame containing diff data.
        """
        if self._data is None:
            return None
        dif_data = self._data["Close"] - self._data['LastClose']
        dif_data.name = 'difference'

        return dif_data

def period_segment(df, periods = PERIODS):
    """
    Create data sources for different periods based on the frequency.
    Param:
        df/series:
        periods: list of integers and string, the integer represent the number of latest months.

    return: Dictionary of data sources.
    """
    if df is None:
        return {}

    last_date = df.index[-1]

    dict_period_segment = {}
    for period in periods:
        if isinstance(period, int):
            start_date = last_date - pd.DateOffset(months=period)
            # 将 start_date 转换为 datetime64[ns] 类型
            start_date = pd.Timestamp(start_date)
            col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
            dict_period_segment[col_name] = df.loc[df.index >= start_date]
        elif period == "ALL":
            start_date = df.index[0]
            col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
            dict_period_segment[col_name] = df.loc[df.index >= start_date]
        else:
            raise ValueError("Invalid period value")

    return dict_period_segment

# 辅助函数：解析时间窗口
def parse_time_window(window, latest_date):
    if isinstance(window, str):
        if window[-1] not in ['W', 'M', 'Q', 'Y']:
            raise ValueError("Invalid time window string format. Expected 'number+[W,M,Q,Y]'.")
        unit = window[-1]
        num = int(window[:-1])
        if unit == 'W':
            start_time = latest_date - pd.DateOffset(weeks=num)
        elif unit == 'M':
            start_time = latest_date - pd.DateOffset(months=num)
        elif unit == 'Q':
            start_time = latest_date - pd.DateOffset(months=3 * num)
        elif unit == 'Y':
            start_time = latest_date - pd.DateOffset(years=num)
        return start_time, latest_date
    elif isinstance(window, tuple):
        start_date = pd.to_datetime(window[0])
        end_date = pd.to_datetime(window[1])
        return start_date, end_date
    else:
        raise ValueError("Invalid time window format. Expected string or tuple.")

# 绘制牛市熊市趋势图
def BullBearPlot(data, time_window):
    if not isinstance(time_window, (list, tuple)):
        raise ValueError("time_window must be a list or a tuple.")
    if not isinstance(data, pd.Series):
        raise ValueError("data must be a pandas Series.")

    n = len(time_window)
    fig = make_subplots(rows=n, cols=1, subplot_titles=[f"Plot {i + 1}" for i in range(n)])

    df = pd.DataFrame(data)
    df.columns = ["Close"]
    df["CumMax"] = df["Close"].cummax()
    df["IsBull"] = (df["Close"] - df["CumMax"] * 0.8).apply(np.sign)
    df.index = pd.to_datetime(df.index)

    for i, time_window_element in enumerate(time_window):
        start_date, end_date = parse_time_window(time_window_element, df.index[-1])
        if isinstance(time_window_element, str):
            time_unit = time_window_element[-1]
            num = int(time_window_element[:-1])
            if time_unit == 'W':
                offset = pd.DateOffset(weeks=num)
            elif time_unit == 'M':
                offset = pd.DateOffset(months=num)
            elif time_unit == 'Q':
                offset = pd.DateOffset(months=3 * num)
            elif time_unit == 'Y':
                offset = pd.DateOffset(years=num)
            else:
                raise ValueError("Invalid time unit. Allowed units are [W, M, Q, Y].")
            end_date = df.index[-1]
            start_date = end_date - offset
            selected_df = df[(df.index >= start_date) & (df.index <= end_date)]
            title_time_window = f"Recent {time_window_element}"
        elif isinstance(time_window_element, tuple) and len(time_window_element) == 2:
            start_date = pd.to_datetime(time_window_element[0], format="%Y%m%d")
            end_date = pd.to_datetime(time_window_element[1], format="%Y%m%d")
            selected_df = df[(df.index >= start_date) & (df.index <= end_date)]
            title_time_window = f"{time_window_element[0]}-{time_window_element[1]}"
        else:
            raise ValueError("Invalid time_window format.")

        for j in range(len(selected_df) - 1):
            x_vals = [selected_df.index[j], selected_df.index[j + 1]]
            y_vals = [selected_df["Close"].iloc[j], selected_df["Close"].iloc[j + 1]]
            color = 'red' if selected_df['IsBull'].iloc[j] < 0 else 'green'

            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                line=dict(color=color),
                showlegend=False
            ), row=i + 1, col=1)

        fig.update_yaxes(type="log", row=i + 1, col=1)
        fig.update_xaxes(title_text="Date", row=i + 1, col=1)
        fig.update_yaxes(title_text="Price", row=i + 1, col=1)
        fig.layout.annotations[i].update(text=f"Bull and Bear Trend: {title_time_window}")

    fig.update_layout(height=400 * n)
    fig.show()

# 获取期权链数据
def options_chain(symbol):
    tk = yf.Ticker(symbol)
    print(tk.info)
    exps = tk.options
    options_list = []
    for e in exps:
        opt = tk.option_chain(e)
        calls_puts = pd.concat([opt.calls, opt.puts])
        calls_puts['expirationDate'] = e
        options_list.append(calls_puts)

    options = pd.concat(options_list, ignore_index=True)
    options['expirationDate'] = pd.to_datetime(options['expirationDate']) + dt.timedelta(days=1)
    options['dte'] = (options['expirationDate'] - dt.datetime.today()).dt.days / 365
    options['CALL'] = options['contractSymbol'].str[4:].apply(lambda x: "C" in x)
    options[['bid', 'ask', 'strike']] = options[['bid', 'ask', 'strike']].apply(pd.to_numeric)
    options['mark'] = (options['bid'] + options['ask']) / 2
    options = options.drop(columns=['contractSize', 'currency', 'change', 'percentChange', 'lastTradeDate', 'lastPrice'])
    return options

# 绘制价格变化分布图表
def ChangeDistPlot(data, time_windows=[1], frequencies=['W', 'M', 'Q', 'Y']):
    if data.empty:
        raise ValueError("Input data is empty.")
    data.index = pd.to_datetime(data.index)
    latest_date = data.index.max()

    num_freq = len(frequencies)
    num_windows = len(time_windows)

    sub_figsize_width = 8
    if num_windows == 1 and num_freq == 1:
        fig, axes = plt.subplots(figsize=(sub_figsize_width, sub_figsize_width))
        axes = np.array([[axes]])
    elif num_windows == 1:
        fig, axes = plt.subplots(1, num_freq, figsize=(sub_figsize_width * num_freq, sub_figsize_width))
        axes = axes.reshape(1, -1)
    elif num_freq == 1:
        fig, axes = plt.subplots(num_windows, 1, figsize=(sub_figsize_width, sub_figsize_width * num_windows))
        axes = axes.reshape(-1, 1)
    else:
        fig, axes = plt.subplots(num_windows, num_freq, figsize=(sub_figsize_width * num_freq, sub_figsize_width * num_windows))

    bin_widths = {'W': 0.01, 'M': 0.025, 'Q': 0.05, 'Y': 0.1}

    for i, window in enumerate(time_windows):
        start_date, end_date = parse_time_window(window, latest_date)
        subset = data[start_date:end_date].copy()
        time_span = (subset.index.max() - subset.index.min()).days

        for j, freq in enumerate(frequencies):
            if freq not in ['W', 'M', 'Q', 'Y']:
                raise ValueError(f"Invalid frequency: {freq}. Allowed frequencies are ['W', 'M', 'Q', 'Y'].")
            if (freq == 'W' and time_span < 7) or (freq == 'M' and time_span < 30) or (freq == 'Q' and time_span < 90) or (freq == 'Y' and time_span < 365):
                ax = axes[i, j]
                ax.set_title(f"{freq}-ly change in {window}")
                ax.set_xlabel("Change")
                ax.set_ylabel("Frequency")
                continue

            log_returns = np.log(subset / subset.shift(1))
            resample_freq = freq if freq == "W" else freq + "E"
            change = log_returns.resample(resample_freq).sum()
            change = change.dropna()
            change = np.exp(change) - 1
            change_max = np.max(change)
            change_min = np.min(change)
            bin_width = bin_widths[freq]
            bins = np.arange(np.floor(change_min / bin_width) * bin_width - 0.5 * bin_width,
                             np.ceil(change_max / bin_width) * bin_width + 0.5 * bin_width, bin_width)

            ax = axes[i, j]
            sns.histplot(change, kde=True, ax=ax, bins=bins, legend=False)
            ax.set_title(f"{freq}-ly change in {window}")
            ax.xaxis.set_major_formatter(PercentFormatter(1))
            yticks = ax.get_yticks().astype(int)
            ax.set_yticks(yticks)
            ax.set_xlabel("Change")
            ax.set_ylabel("Frequency")

            current_values = change.tail(4)
            current_values_lables = [f'{idx.date()}: {val.iloc[0]:.2%}' for idx, val in current_values.iterrows()]
            for k, label in enumerate(current_values_lables):
                ax.text(0.05, 0.9 - k * 0.05, label, transform=ax.transAxes, fontsize=12)

            count = len(change)
            for rect in ax.patches:
                height = rect.get_height()
                if height > 0:
                    change_freq = height / count
                    ax.text(rect.get_x() + rect.get_width() / 2, height, f'{height}, {change_freq * 100:.0f}%',
                            ha='center', va='bottom', fontsize=12)

            expectation = 0
            for rect in ax.patches:
                mid_point = rect.get_x() + rect.get_width() / 2
                height = rect.get_height()
                change_freq = height / count
                expectation += mid_point * change_freq
            if expectation > 0:
                text_color = 'green'
            elif expectation < 0:
                text_color = 'red'
            else:
                text_color = 'black'

            deviation = np.std(change.values)
            text_weight = 'bold'
            ax.text(0.05, 0.95, f'Expectation: {expectation * 100:.2f}%', transform=ax.transAxes, fontsize=12,
                    color=text_color, weight=text_weight)
            ax.text(0.05, 0.99, f'Deviation: {deviation * 100:.2f}%', transform=ax.transAxes, fontsize=12,
                    weight=text_weight)

    plt.tight_layout()
    plt.show()

# 创建不同时间周期的数据来源
def create_data_sources(df, periods, all_period_start, frequency):
    current_date = pd.Timestamp.now()
    if frequency == 'ME':
        end_date = current_date.replace(day=1)
    elif frequency == 'W':
        end_date = current_date - pd.DateOffset(days=current_date.weekday())
    elif frequency == 'QE':
        end_date = current_date - pd.tseries.offsets.QuarterBegin()
    else:
        raise ValueError("Invalid frequency value. Allowed values are 'ME', 'W', 'QE'.")

    df = df[df.index < end_date]
    if df.empty:
        print("DataFrame is empty. Cannot get the last date.")
        return {}

    last_date = df.index[-1]

    if all_period_start is None:
        all_period_start = "2010-01-01"

    data_sources = {}
    for period in periods:
        if isinstance(period, int):
            if frequency in ['ME', 'W']:
                start_date = last_date - pd.DateOffset(months=period - 1)
            elif frequency == 'QE':
                start_date = last_date - pd.DateOffset(quarters=period - 1)
            col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
            data_sources[col_name] = df.loc[df.index >= start_date]
        elif period == "ALL":
            col_name = f"{pd.to_datetime(all_period_start).strftime('%y%b')}-{last_date.strftime('%y%b')}"
            data_sources[col_name] = df.loc[df.index >= all_period_start]
        else:
            raise ValueError("Invalid period value")

    return data_sources

# 对数据进行重采样
def refrequency(df, frequency: str):
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex")
    if not {'Open', 'High', 'Low', 'Close'}.issubset(df.columns):
        raise ValueError("DataFrame must contain OHLC columns")

    try:
        refrequency_df = df.resample(frequency).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Adj Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return refrequency_df
    except KeyError as e:
        print(f"Missing column {e} in DataFrame")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


# 计算震荡指标
def oscillation(df):
    data = df[['Open', 'High', 'Low', 'Close']].copy()
    data['LastClose'] = data["Close"].shift(1)
    # data["Oscillation"] = data["High"] - data["Low"]
    data["Oscillation"] = (data["High"] - data["Low"] / data['LastClose'])
    data = data.dropna()
    return data


# 计算百分位数统计信息
def percentile_stats(dict, percentile, interpolation: str = "linear"):

    stats_index = pd.Index(
        ["mean", "std", "skew", "kurt", "max", "75th", "25th", "prob_next_per"]
    )
    stats_df = pd.DataFrame(index=stats_index)

    interval_freq_dict = {}
    for period_name, data in dict.items():
        # 明确创建 DataFrame 的副本
        data = data.copy()
        data["percentile"] = data.apply(lambda x: percentileofscore(data, x))
        data["sequence"] = range(len(data))

        # 确保布尔掩码长度和 data 一致
        if len(data) == 0:
            continue

        mask_percentile = data["percentile"] >= percentile
        mask_first_last = (data.index == data.index[0]) | (data.index == data.index[-1])

        # 检查布尔掩码长度
        if len(mask_percentile) != len(data) or len(mask_first_last) != len(data):
            raise ValueError("布尔掩码的长度和 DataFrame 的长度不匹配，请检查数据处理逻辑。")

        data = data[mask_percentile | mask_first_last].copy()
        data["interval"] = data["sequence"].diff()
        data = data.dropna()

        if len(data) == 0:
            continue

        latest_interval = data["interval"].iloc[-1]
        mask_beyond_latest_interval = data["interval"] > latest_interval
        mask_latest_interval_plus = data["interval"] == latest_interval + 1

        if len(data[mask_latest_interval_plus]) == 0:
            prob_next_per = None
        else:
            prob_next_per = len(data[mask_latest_interval_plus]) / len(data[mask_beyond_latest_interval])

        col = "interval"
        stats_df[period_name] = [
            data[col].mean(),
            data[col].std(),
            data[col].skew(),
            data[col].kurtosis(),
            data[col].max(),
            data[col].quantile(0.75, interpolation=interpolation),
            data[col].quantile(0.25, interpolation=interpolation),
            prob_next_per
        ]

    return stats_df
    
#绘制带直方图的散点图
def scatter_hist(x, y):
    """
    绘制一个带有 x 和 y 数据直方图的散点图。

    参数:
    x (array-like): 散点图中各点的 x 坐标数据。
    y (array-like): 散点图中各点的 y 坐标数据。

    返回:
    fig (matplotlib.figure.Figure): 包含图形的 Figure 对象。
    ax (matplotlib.axes.Axes): 包含散点图的 Axes 对象。
    """
    # 检查输入数据长度是否一致
    if len(x) != len(y):
        raise ValueError("输入的 x 和 y 数据长度必须一致。")

    # 创建画布和子图布局
    fig = plt.figure(figsize=(8, 8))
    gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                          left=0.1, right=0.9, bottom=0.1, top=0.9,
                          wspace=0.05, hspace=0.05)
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)

    # 不显示直方图的标签
    ax_histx.tick_params(axis="x", labelbottom=False)
    ax_histy.tick_params(axis="y", labelleft=False)

    # 绘制散点图
    ax.scatter(x, y)

    # 绘制辅助线
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.plot(xlim, xlim, 'k--', label='y = x')
    ax.plot(xlim, [-i for i in xlim], 'k--', label='y = -x')
    ax.axhline(y=0, color='k', linestyle='--', label='y = 0')

    # 当 x 为 pandas.Series 且索引为时间格式时，高亮显示最后一个点
    if isinstance(x, pd.Series) and pd.api.types.is_datetime64_any_dtype(x.index):
        ax.scatter(x.iloc[-1], y.iloc[-1], color='red', s=100, zorder=5)

    # 根据 x 和 y 的取值范围自动调整坐标轴范围
    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    ax.set_xlim(x_min - 1, x_max + 1)
    ax.set_ylim(y_min - 1, y_max + 1)

    # 绘制5的倍数的垂直和水平辅助线
    for x_val in np.arange(round(x_min / 5) * 5, x_max + 1, 5):
        ax.axvline(x=x_val, color='green', linestyle='--', alpha=0.5)
    for y_val in np.arange(round(y_min / 5) * 5, y_max + 1, 5):
        ax.axhline(y=y_val, color='green', linestyle='--', alpha=0.5)

    # 增加坐标轴标签
    ax.set_xlabel(x.name)
    ax.set_ylabel(y.name)

    # 找出分位数超过mark_percentile的散点并标注索引
    mark_percentile = 0.90
    mark_x = np.quantile(x, mark_percentile)
    for (x_val, y_val) in zip(x, y):
        if x_val > mark_x:
            if isinstance(x, pd.Series):
                index_time = x[x == x_val].index[0].strftime('%y%b')
                ax.annotate(index_time, (x_val, y_val), textcoords="offset points",
                            xytext=(0, 10), ha='center')
            else:
                ax.annotate(str(x.tolist().index(x_val)), (x_val, y_val), textcoords="offset points",
                            xytext=(0, 0), ha='center')

    # 绘制直方图
    ax_histx.hist(x, bins='auto')
    ax_histy.hist(y, bins='auto', orientation='horizontal')

    return fig, ax


# 计算尾部统计信息
def tail_stats(data_sources, interpolation: str = "linear"):


    stats_index = pd.Index(
        ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th"]
    )

    stats_df = pd.DataFrame(index=stats_index)

    interval_freq_dict = {}
    for period_name, data in data_sources.items():
        # check data if pd.Series
        tail_values = [
            data.mean(),
            data.std(),
            data.skew(),
            data.kurtosis(),
            data.max(),
            data.quantile(0.99, interpolation=interpolation),
            data.quantile(0.95, interpolation=interpolation),
            data.quantile(0.90, interpolation=interpolation),
        ]

        stats_df[period_name] = tail_values
    
    return stats_df


# 绘制尾部特征值分布
def tail_plot(data_sources, interpolation: str = "linear"):

    # Create a single figure
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.set_style("darkgrid")

    for period_name, data in data_sources.items():
        # 绘制累积密度曲线
        sns.ecdfplot(data, ax=ax, label=period_name)

    # 绘制 y=0.9, 0.95, 0.99 的横线
    for y_val in [0.9, 0.95, 0.99]:
        ax.axhline(y=y_val, color='gray', linestyle='--', alpha=0.7)
        # 添加文本标注
        ax.text(ax.get_xlim()[-1], y_val, f'{y_val * 100:.0f}th', ha='left', va='center', color='gray')

    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_title(f"Cumulative Density")
    # ax.set_xlabel(f"{feature} (%)")
    ax.set_ylabel("Cumulative Frequency")
    ax.grid(True, alpha=0.3)

    # 设置对数y轴
    ax.set_yscale('log')
    # 设置y轴范围
    ax.set_ylim(bottom=0.8)
 
    plt.tight_layout()

    # Save the combined figure
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    plot_url = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()

    return plot_url



# 计算波动率
def calculate_oscillation(df, proj_volatility, interpolation, proj_high_weight):
    df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * proj_high_weight
    df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - proj_high_weight)
    df["ActualClosingStatus"] = np.where(df["Close"] > df["ProjHigh"], 1,
                                         np.where(df["Close"] < df["ProjLow"], -1, 0))
    realized_bias = ((df["ActualClosingStatus"] == 1).sum() - ((df["ActualClosingStatus"] == -1).sum())) / len(df)
    return realized_bias

def osc_projection(data, percentile: float = 0.90, target_bias: float = None, interpolation: str = "linear"):
    """
    波动率预测函数
    
    参数:
    data: 包含必要价格数据的DataFrame
    percentile: 用于计算预测波动率的百分位数，默认0.90
    target_bias: 目标偏差值，如指定将优化权重以接近此值
    interpolation: 百分位数计算的插值方法
    
    返回:
    包含预测结果的散点图的Base64编码字符串
    """
    # 检查数据是否包含所需的列
    required_columns = ['High', 'Low', 'LastClose', 'Oscillation', 'Close', 'HighDate', 'LowDate', 'CloseDate']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"数据中缺少列: {col}")

    # 准备数据
    df = data[required_columns].copy().iloc[:-1]
    proj_volatility = data["Oscillation"].quantile(percentile, interpolation=interpolation)

    # 确定最佳的高点权重
    proj_high_weight = 0.5  # 默认值
    
    if target_bias is not None:
        proj_high_weights = np.linspace(0.4, 0.6, 21)
        min_error = float('inf')
        best_proj_high_weight = 0.5

        for weight in proj_high_weights:
            realized_bias = calculate_oscillation(df, proj_volatility, interpolation, weight)
            error = abs(realized_bias - target_bias)

            if error < min_error:
                min_error = error
                best_proj_high_weight = weight

        proj_high_weight = best_proj_high_weight

    # 计算实际偏差
    realized_bias = calculate_oscillation(df, proj_volatility, interpolation, proj_high_weight).round(2)

    # 获取价格和日期数据
    px_lastClose = data["LastClose"].iloc[-1]
    px_high = data["High"].iloc[-1]
    px_low = data["Low"].iloc[-1]
    px_last = data["Close"].iloc[-1]

    date_lastClose = data["CloseDate"].iloc[-2]
    date_high = data["HighDate"].iloc[-1]
    date_low = data["LowDate"].iloc[-1]
    date_last = data["CloseDate"].iloc[-1]

    # 计算预测高点和低点
    proj_highCurPrd = px_lastClose + px_lastClose * proj_volatility / 100 * proj_high_weight
    proj_lowCurPrd = px_lastClose - px_lastClose * proj_volatility / 100 * (1 - proj_high_weight)
    proj_highNextPrd = px_last + px_last * proj_volatility / 100 * proj_high_weight
    proj_lowNextPrd = px_last - px_last * proj_volatility / 100 * (1 - proj_high_weight)

    # 生成预测数据框
    end_date = date_lastClose + pd.DateOffset(months=2)
    all_weekdays = pd.date_range(start=date_lastClose, end=end_date, freq='B')
    df_proj = pd.DataFrame(index=all_weekdays, columns=["Close", "High", "Low", "iHigh", "iLow"])

    # 填充已知数据
    df_proj.loc[date_lastClose, "Close"] = px_lastClose
    df_proj.loc[date_high, "High"] = px_high
    df_proj.loc[date_low, "Low"] = px_low
    df_proj.loc[date_last, "Close"] = px_last

    # 获取当前月份的工作日
    today = dt.datetime.now()
    if today.month < 12:
        date_NextMonthEnd = dt.datetime(today.year, today.month + 1, 1) - pd.Timedelta(days=1)
    else:
        date_NextMonthEnd = dt.datetime(today.year + 1, 1, 1) - pd.Timedelta(days=1)
    
    weekdays_this_month = pd.date_range(start=date_lastClose, end=date_NextMonthEnd, freq='B')
    last_weekday_this_month = weekdays_this_month[-1]                           
    current_month_dates = pd.date_range(start=date_lastClose, end=last_weekday_this_month, freq='B')[1:]
    
    # 填充预测数据
    for i, date in enumerate(current_month_dates):
        progress = (i+1) / len(current_month_dates)
    
        df_proj.loc[date, "iHigh"] = np.sqrt(progress) * (proj_highCurPrd - px_lastClose) + px_lastClose
        df_proj.loc[date, "iLow"] = np.sqrt(progress) * (proj_lowCurPrd - px_lastClose) + px_lastClose

    # 绘制图表
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # 创建连续的索引用于绘图
    x_values = np.arange(len(df_proj.index))
    
    # 绘制历史数据（实心点）
    ax.scatter(x_values, df_proj["Close"], label="Close", color='black', s=60, zorder=3)
    ax.scatter(x_values, df_proj["High"], label="High", color='purple', s=60, zorder=3)
    ax.scatter(x_values, df_proj["Low"], label="Low", color='purple', s=60, zorder=3)

    # 绘制预测数据（空心点）
    ax.scatter(x_values, df_proj["iHigh"], label="Projection High", color='red', facecolors='none', edgecolors='red', s=60, zorder=3)
    ax.scatter(x_values, df_proj["iLow"], label="Projection Low", color='red', facecolors='none', edgecolors='red', s=60, zorder=3)
    

    # 显示 High, Low, LastClose, Close 的具体值，位置在对应数据点的下方
    for i, date in enumerate(df_proj.index):
        if not np.isnan(df_proj.loc[date, "Close"]):
            ax.annotate(f"{df_proj.loc[date, 'Close']:.0f}",
                        (i, df_proj.loc[date, "Close"]),
                        xytext=(0, -15),
                        textcoords="offset points",
                        ha='center', va='top',
                        fontsize=9, color='black')

        if not np.isnan(df_proj.loc[date, "High"]):
            ax.annotate(f"{df_proj.loc[date, 'High']:.0f}",
                        (i, df_proj.loc[date, "High"]),
                        xytext=(0, -15),
                        textcoords="offset points",
                        ha='center', va='top',
                        fontsize=9, color='purple')

        if not np.isnan(df_proj.loc[date, "Low"]):
            ax.annotate(f"{df_proj.loc[date, 'Low']:.0f}",
                        (i, df_proj.loc[date, "Low"]),
                        xytext=(0, -15),
                        textcoords="offset points",
                        ha='center', va='top',
                        fontsize=9, color='purple')

    # 只显示最后三个日期的 iHigh 和 iLow 的具体值，位置在对应数据点的下方
    last_three_dates = df_proj[["iHigh","iLow"]].dropna().index[-3:]
    for i, date in enumerate(df_proj.index):
        if date in last_three_dates:
            if not np.isnan(df_proj.loc[date, "iHigh"]):
                ax.annotate(f"{df_proj.loc[date, 'iHigh']:.0f}",
                            (i, df_proj.loc[date, "iHigh"]),
                            xytext=(0, -15),
                            textcoords="offset points",
                            ha='center', va='top',
                            fontsize=9, color='red')

            if not np.isnan(df_proj.loc[date, "iLow"]):
                ax.annotate(f"{df_proj.loc[date, 'iLow']:.0f}",
                            (i, df_proj.loc[date, "iLow"]),
                            xytext=(0, -15),
                            textcoords="offset points",
                            ha='center', va='top',
                            fontsize=9, color='red')

    # 设置 x 轴标签为日期
    ax.set_xticks(x_values[::1])  # 每 3 天显示一个标签，可根据需要调整
    ax.set_xticklabels([date.strftime('%b%d') for date in df_proj.index], rotation=90)

    # 图表格式优化
    ax.set_title(f"Oscillation Projection (Percentile: {percentile}, Bias: {realized_bias})", fontsize=14)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Price", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6, zorder=0)
    ax.legend(fontsize=11, loc='best')
    plt.tight_layout()

    # 保存图表
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plot_url = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close(fig)

    return plot_url

# 计算每个频率对应的天数
def days_of_frequency(frequency):
    if frequency == "W":
        days = 5
    elif frequency == "ME":
        days = 21
    elif frequency == "QE":
        days = 63
    else:
        raise ValueError("Invalid frequency, input one of ['W', 'ME', 'QE']")
    return days


# 计算不同时间周期的频率缺口统计
def period_gap_stats(df, feature, frequency, periods: list = [12, 36, 60, "ALL"], all_period_start: str = None,
                     interpolation: str = "linear"):
    if not isinstance(periods, list):
        raise TypeError("periods must be a list")
    if not all(isinstance(p, (int, str)) for p in periods):
        raise ValueError("periods must contain integers or strings")

    data_sources = create_data_sources(df, periods, all_period_start, frequency)

    stats_index = pd.Index(
        ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th", "10th", "05th", "01st", "min", "p-value"]
    )
    gap_return_stats_df = pd.DataFrame(index=stats_index)

    if feature == "PeriodGap":
        for period_name, data in data_sources.items():
            if len(data) > 0:
                gap_return = (data["Open"] / data["LastClose"] - 1)
                period_return = (data["Close"] / data["LastClose"] - 1)
                days_of_period = days_of_frequency(frequency)
                compounded_gap_return = (1 + gap_return) ** days_of_period - 1
                _, p_value = ks_2samp(compounded_gap_return, period_return)

                gap_return_stats_df[period_name] = [
                    gap_return.mean(),
                    gap_return.std(),
                    gap_return.skew(),
                    gap_return.kurtosis(),
                    gap_return.max(),
                    gap_return.quantile(0.99, interpolation=interpolation),
                    gap_return.quantile(0.95, interpolation=interpolation),
                    gap_return.quantile(0.90, interpolation=interpolation),
                    gap_return.quantile(0.10, interpolation=interpolation),
                    gap_return.quantile(0.05, interpolation=interpolation),
                    gap_return.quantile(0.01, interpolation=interpolation),
                    gap_return.min(),
                    p_value
                ]

    return gap_return_stats_df


# Calculate options matrix
def option_matrix(ticker, option_position):
    """
    Calculate the profit and loss matrix for an options portfolio under different stock price movements
    
    Parameters:
    ticker (str): Stock ticker symbol
    option_position (pd.DataFrame): Options position data with columns: option_type, strike, quantity, premium
    
    Returns:
    pd.DataFrame: Matrix showing P&L for different price scenarios
    """
    # Fetch latest closing price
    try:
        px_last = yf.download(ticker, start=dt.date.today() - dt.timedelta(days=7))[["Close"]].iloc[-1, -1]
    except Exception as e:
        print(f"Failed to retrieve stock data: {e}")
        return None
    
    change_range = np.linspace(-15, 15, 301)
    
    # Calculate price step (using percentage instead of fixed value)
    px_step = px_last * 0.01  # 1% price change
    
    # Initialize matrix framework
    option_matrix_df = pd.DataFrame(index=change_range)
    option_matrix_df['price'] = px_last * (1 + change_range / 100)
    option_matrix_df['SC'] = 0.0  # Short Call
    option_matrix_df['SP'] = 0.0  # Short Put
    option_matrix_df['LC'] = 0.0  # Long Call
    option_matrix_df['LP'] = 0.0  # Long Put
    
    # Calculate P&L for each option
    for _, row in option_position.iterrows():
        option_type = row["option_type"]
        strike = row["strike"]
        quantity = row["quantity"]
        premium = row["premium"]
        
        # Short Call
        if option_type == 'SC':
            in_the_money = option_matrix_df['price'] >= strike
            option_matrix_df['SC'] += np.where(
                in_the_money,
                (premium + (strike - option_matrix_df['price'])) * quantity,
                premium * quantity
            )
        
        # Short Put
        elif option_type == 'SP':
            in_the_money = option_matrix_df['price'] <= strike
            option_matrix_df['SP'] += np.where(
                in_the_money,
                (premium - (strike - option_matrix_df['price'])) * quantity,
                premium * quantity
            )
        
        # Long Call
        elif option_type == 'LC':
            in_the_money = option_matrix_df['price'] > strike
            option_matrix_df['LC'] += np.where(
                in_the_money,
                (option_matrix_df['price'] - strike - premium) * quantity,
                -premium * quantity
            )
        
        # Long Put
        elif option_type == 'LP':
            in_the_money = option_matrix_df['price'] <= strike
            option_matrix_df['LP'] += np.where(
                in_the_money,
                (-option_matrix_df['price'] + strike - premium) * quantity,
                -premium * quantity
            )
        
        else:
            raise ValueError(f"Invalid option type: {option_type}")
    
    # Calculate total P&L
    option_matrix_df['PnL'] = option_matrix_df[['SC', 'SP', 'LC', 'LP']].sum(axis=1)
    
    return option_matrix_df
