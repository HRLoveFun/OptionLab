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
from matplotlib.ticker import PercentFormatter
from scipy.stats import ks_2samp, percentileofscore


yf.enable_debug_mode()

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


# 从雅虎财经下载股票数据
def yf_download(ticker, start_date, end_date, interval='1d', progress=True, auto_adjust=False):
    try:
        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=progress,
            auto_adjust=auto_adjust,
        )
        df.columns = df.columns.droplevel(1)
        df.set_index(pd.DatetimeIndex(df.index), inplace=True)
        df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        return df
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None


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
        return {}  # 修复此处

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
    data["Oscillation"] = data["High"] - data["Low"]
    data["OscillationPct"] = (data["Oscillation"] / data['LastClose'])
    data = data.dropna()
    return data


# 计算百分位数统计信息
def percentile_stats(df, feature, percentile, frequency, periods: list = [12, 36, 60, "ALL"], all_period_start: str = None,
                     interpolation: str = "linear"):
    if not isinstance(periods, list):
        raise TypeError("periods must be a list")
    if not all(isinstance(p, (int, str)) for p in periods):
        raise ValueError("periods must contain integers or strings")

    data_sources = create_data_sources(df, periods, all_period_start, frequency)

    last_three_index_list = df.index[-3:].strftime('%b%d').tolist()
    stats_index = pd.Index(
        ["mean", "std", "skew", "kurt", "max", "75th", "25th", "prob_next_per"]
    )
    stats_df = pd.DataFrame(index=stats_index)

    if frequency == "ME":
        bin_range = list(np.arange(0, 21, 1))
    elif frequency == "W":
        bin_range = list(np.arange(1, 101, 10))
    else:
        raise ValueError(f"Unsupported frequency: {frequency}. Supported frequencies are 'ME' and 'W'.")

    interval_freq_dict = {}
    for period_name, data in data_sources.items():
        data["percentile"] = data[feature].apply(lambda x: percentileofscore(data[feature], x))
        data["sequence"] = range(len(data))
        mask_percentile = data["percentile"] >= percentile
        mask_first_last = (data.index == data.index[0]) | (data.index == data.index[-1])
        data = data[mask_percentile | mask_first_last].copy()
        data["interval"] = data["sequence"].diff()
        data = data.dropna()

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

        n, bins = np.histogram(data[col], bins=bin_range, density=True)
        if n.sum() == 0:
            cumulative_n = np.zeros_like(n)
        else:
            cumulative_n = np.cumsum(n * np.diff(bins))
        n_diff = np.insert(np.diff(cumulative_n), 0, cumulative_n[0])

        bin_intervals = [(bins[i], bins[i + 1]) for i in range(len(bins) - 1)]
        bin_info = {}
        for i in range(len(bin_intervals)):
            bin_info[f"{bin_intervals[i]}"] = n_diff[i]

        interval_freq_dict[period_name] = bin_info

    interval_freq_df = pd.DataFrame(interval_freq_dict)
    combined_df = pd.concat([stats_df, interval_freq_df])
    combined_df.index.names = [f"{percentile=}"]
    return combined_df


# 计算尾部统计信息
def tail_stats(df, feature, frequency, periods: list = [12, 36, 60, "ALL"], all_period_start: str = None,
               interpolation: str = "linear"):
    if not isinstance(periods, list):
        raise TypeError("periods must be a list")
    if not all(isinstance(p, (int, str)) for p in periods):
        raise ValueError("periods must contain integers or strings")

    data_sources = create_data_sources(df, periods, all_period_start, frequency)

    last_three_index_list = df.index[-3:].strftime('%b%d').tolist()
    stats_index = pd.Index(
        ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th"] +
        [f'{last_three_index}_val' for last_three_index in last_three_index_list] +
        [f'{last_three_index}_%th' for last_three_index in last_three_index_list]
    )
    stats_df = pd.DataFrame(index=stats_index)

    if frequency == "ME":
        bin_range = list(np.arange(0, 0.35, 0.05))
    elif frequency == "W":
        bin_range = list(np.arange(0, 0.18, 0.03))
    else:
        raise ValueError(f"Unsupported frequency: {frequency}. Supported frequencies are 'ME' and 'W'.")

    interval_freq_dict = {}
    for period_name, data in data_sources.items():
        stats_df[period_name] = [
            data[feature].mean(),
            data[feature].std(),
            data[feature].skew(),
            data[feature].kurtosis(),
            data[feature].max(),
            data[feature].quantile(0.99, interpolation=interpolation),
            data[feature].quantile(0.95, interpolation=interpolation),
            data[feature].quantile(0.90, interpolation=interpolation),
            data[feature].iloc[-3],
            data[feature].iloc[-2],
            data[feature].iloc[-1],
            percentileofscore(data[feature], data[feature].iloc[-3]),
            percentileofscore(data[feature], data[feature].iloc[-2]),
            percentileofscore(data[feature], data[feature].iloc[-1])
        ]

        n, bins = np.histogram(data[feature], bins=bin_range, density=True)
        cumulative_n = np.cumsum(n * np.diff(bins))
        n_diff = np.insert(np.diff(cumulative_n), 0, cumulative_n[0])

        bin_intervals = [(bins[i], bins[i + 1]) for i in range(len(bins) - 1)]
        bin_info = {}
        for i in range(len(bin_intervals)):
            bin_info[f"{bin_intervals[i]}"] = n_diff[i]

        interval_freq_dict[period_name] = bin_info

    interval_freq_df = pd.DataFrame(interval_freq_dict)
    combined_df = pd.concat([stats_df, interval_freq_df])
    return combined_df


# 绘制尾部特征值分布
def tail_plot(df, feature, frequency, periods: list = [12, 36, 60, "ALL"], all_period_start: str = None,
              interpolation: str = "linear"):
    data_sources = create_data_sources(df, periods, all_period_start, frequency)

    if frequency == "ME":
        bin_range = list(np.arange(0, 0.35, 0.05))
    elif frequency == "W":
        bin_range = list(np.arange(0, 0.18, 0.03))
    else:
        bin_range = list(np.arange(0, 0.25, 0.04))  # Default range for other frequencies

    # Create a single figure with subplots for each period
    num_periods = len(data_sources)
    fig, axes = plt.subplots(num_periods, 1, figsize=(10, 6 * num_periods))
    
    # Handle case with only one period
    if num_periods == 1:
        axes = [axes]
    
    sns.set_style("darkgrid")
    
    for i, (period_name, data) in enumerate(data_sources.items()):
        ax = axes[i]
        n, bins, patches = ax.hist(data[feature], bins=bin_range, alpha=0.5, color='skyblue', density=True,
                                cumulative=True)

        n_diff = np.insert(np.diff(n), 0, n[0])
        for rect, h_diff, h in zip(patches, n_diff, n):
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, height, f'{h_diff:.0%}/{h:.0%}', ha='center', va='bottom',
                     size=12)

        percentiles = [data[feature].quantile(p, interpolation=interpolation) for p in [0.90, 0.95, 0.99]]
        for p, val in zip([90, 95, 99], percentiles):
            ax.axvline(val, color='red', linestyle=':', alpha=0.3, label=f'{p}th: {val:.1%}')

        last_three = data[feature].iloc[-3:]
        last_three_dates = last_three.index.strftime('%b%d')
        for val, date, grayscale in zip(last_three, last_three_dates, np.arange(0.7, 0, -0.3)):
            ax.scatter(val, 0, color=str(grayscale), s=100, zorder=5, label=f'{date}: {val:.1%}')

        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.set_title(f"Distribution of {feature} - {period_name}")
        ax.set_xlabel(f"{feature} (%)")
        ax.set_ylabel("Density")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Save the combined figure
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    plot_url = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()
    
    return plot_url

# 计算波动率预测
def calculate_projections(data, feature, percentile, interpolation, bias_weight):
    data["ProjectHigh"] = data["LastClose"] + data["LastClose"] * data[feature].quantile(percentile,
                                                                                        interpolation=interpolation) / 100 * bias_weight
    data["ProjectLow"] = data["LastClose"] - data["LastClose"] * data[feature].quantile(percentile,
                                                                                        interpolation=interpolation) / 100 * (
                                                         1 - bias_weight)
    data["ActualClosingStatus"] = np.where(data["Close"] > data["ProjectHigh"], 1,
                                           np.where(data["Close"] < data["ProjectLow"], -1, 0))
    realized_bias = ((data["ActualClosingStatus"] == 1).sum() - ((data["ActualClosingStatus"] == -1).sum())) / len(data)
    return realized_bias


def volatility_projection(df, feature, frequency: str = 'ME', percentile: float = 0.90, prefer_bias: float = None,
                          periods: list = [12, 36, 60, "ALL"], all_period_start: str = None,
                          interpolation: str = "linear"):
    if not isinstance(periods, list):
        raise TypeError("periods must be a list")
    if not all(isinstance(p, (int, str)) for p in periods):
        raise ValueError("periods must contain integers or strings")

    if feature == "OscillationPct":
        refrequency_data = refrequency(df, frequency=frequency)
        refrequency_feature = oscillation(refrequency_data)

        data_sources = create_data_sources(refrequency_feature, periods, all_period_start, frequency)

        volatility_projection_index = pd.Index(
            [
                f"Last: {refrequency_feature.index[-2].strftime('%y%b%d')}",
                f"{percentile}th {feature}",
                "RealizedBias%",
                "ProjectedHighWeight%",
                "ProjHigh",
                "ProjLow",
                f"Today: {df.index[-1].strftime('%y%b%d')}"
            ]
        )
        volatility_projection_df = pd.DataFrame(index=volatility_projection_index)

        for period_name, data in data_sources.items():
            period_end_close = data["Close"].iloc[-1]
            assumed_volatility = data[feature].quantile(percentile, interpolation=interpolation)

            if prefer_bias is not None:
                proj_high_weights = np.linspace(0.1, 0.9, 90)
                min_error = float('inf')
                best_proj_high_weight = 0
                for proj_high_weight in proj_high_weights:
                    realized_bias = calculate_projections(data.copy(), feature, percentile, interpolation,
                                                          proj_high_weight)
                    error = abs(realized_bias - prefer_bias)
                    if error < min_error:
                        min_error = error
                        best_proj_high_weight = proj_high_weight
                proj_high_weight = best_proj_high_weight
            else:
                proj_high_weight = 0.5

            realized_bias = calculate_projections(data, feature, percentile, interpolation, proj_high_weight)

            proj_high = period_end_close + period_end_close * assumed_volatility * proj_high_weight
            proj_low = period_end_close - period_end_close * assumed_volatility * (1 - proj_high_weight)

            last_close = df["Close"].iloc[-1]

            volatility_projection_df[period_name] = [
                period_end_close,
                assumed_volatility,
                realized_bias * 100,
                proj_high_weight * 100,
                proj_high,
                proj_low,
                last_close
            ]
        return volatility_projection_df
    else:
        raise ValueError("Invalid feature value")


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


# 计算期权矩阵
def option_matrix(ticker, option_position):
    close = yf.download(ticker, start=dt.datetime.now().date())[["Close"]].iloc[-1, -1]
    change_range = np.linspace(0.9, 1.1, 20)
    option_matrix_df = pd.DataFrame(index=change_range)
    option_matrix_df['price'] = (close * change_range).astype(int)
    option_matrix_df['SC'] = 0.0
    option_matrix_df['SP'] = 0.0
    option_matrix_df['LC'] = 0.0
    option_matrix_df['LP'] = 0.0

    for _, row in option_position.iterrows():
        option_type = row["option_type"]
        strike = row["strike"]
        quantity = row["quantity"]
        premium = row["premium"]

        if option_type == 'SC':
            option_matrix_df.loc[option_matrix_df['price'] < strike, 'SC'] = premium
            option_matrix_df.loc[option_matrix_df['price'] >= strike, 'SC'] = premium + (
                    strike - option_matrix_df.loc[option_matrix_df['price'] >= strike, 'price'])
            option_matrix_df['SC'] *= quantity
        elif option_type == 'SP':
            option_matrix_df.loc[option_matrix_df['price'] > strike, 'SP'] = premium
            option_matrix_df.loc[option_matrix_df['price'] <= strike, 'SP'] = premium - (
                    strike - option_matrix_df.loc[option_matrix_df['price'] <= strike, 'price'])
            option_matrix_df['SP'] *= quantity
        elif option_type == 'LC':
            option_matrix_df.loc[option_matrix_df['price'] > strike, 'LC'] = option_matrix_df.loc[
                                                                                 option_matrix_df['price'] > strike,
                                                                                 'price'] - strike - premium
            option_matrix_df.loc[option_matrix_df['price'] <= strike, 'LC'] = - premium
            option_matrix_df['LC'] *= quantity
        elif option_type == 'LP':
            option_matrix_df.loc[option_matrix_df['price'] > strike, 'LP'] = - premium
            option_matrix_df.loc[option_matrix_df['price'] <= strike, 'LP'] = - option_matrix_df.loc[
                                                                                 option_matrix_df['price'] <= strike,
                                                                                 'price'] + strike - premium
            option_matrix_df['LP'] *= quantity
        else:
            raise ValueError("Invalid option type")

    option_matrix_df['PnL'] = option_matrix_df[['SC', 'SP', 'LC', 'LP']].sum(axis=1)
    return option_matrix_df
