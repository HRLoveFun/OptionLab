from flask import Flask, render_template, request
import pandas as pd
import logging
import datetime as dt
import matplotlib.pyplot as plt
import io
import base64
import json

from marketobserve import *

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)


@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        if request.method == 'POST':
            # Handle Return Profile
            ticker = request.form.get('ticker')
            feature = request.form.get('feature')
            frequency = request.form.get('frequency', 'W')
            periods = request.form.getlist('period')
            if not periods:
                periods = [12, 36, 60, "ALL"]

            # Get stock data
            start_date = dt.date(2016, 12, 1)
            end_date = dt.date.today()
            data = yf_download(ticker, start_date, end_date)
            if data is None or data.empty:
                app.logger.error(f"Failed to download data for {ticker}")
                return render_template('index.html', error=f"Failed to download data for {ticker}. Please check the ticker symbol.")

            refreq_data = refrequency(data, frequency=frequency)
            if refreq_data is None or refreq_data.empty:
                app.logger.error(f"Failed to refrequency data for {ticker}")
                return render_template('index.html', error=f"Failed to process data for {ticker} with frequency {frequency}.")

            # Initialize PriceDynamic instance
            pxdy = PriceDynamic(ticker, start_date, frequency)
            osc = pxdy.osc().dropna()
            ret = pxdy.ret().dropna()

            # Initialize variables
            tail_stats_result = None
            tail_plot_url = None
            oscillation_projection = None
            gap_stats_result = None
            option_matrix_result = None
            plot_url = None
            osc_ret_scatter_hist_url = None

            # Handle feature-specific calculations
            if feature == 'Oscillation':
                feat_data = oscillation(refreq_data)
                if feat_data is None or feat_data.empty:
                    app.logger.error(f"Failed to calculate oscillation for {ticker}")
                    return render_template('index.html', error=f"Failed to calculate oscillation for {ticker}.")

                # Create scatter plot
                fig, ax = scatter_hist(osc, ret)
                # Save the plot to a buffer
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format='png')
                img_buffer.seek(0)
                osc_ret_scatter_hist_url = base64.b64encode(img_buffer.getvalue()).decode()
                plt.close(fig)

                osc_period_segment = period_segment(osc)
                tail_stats_result = tail_stats(osc_period_segment)
                tail_plot_url = tail_plot(osc_period_segment)

                volatility_proj_pb0 = osc_projection(data, target_bias=0)

                if "LastClose" in feat_data.columns and "PeriodGap" not in feat_data.columns:
                    # Calculate PeriodGap if it doesn't exist
                    feat_data["PeriodGap"] = feat_data["Open"] / feat_data["LastClose"] - 1

                if "PeriodGap" in feat_data.columns:
                    gap_stats_result = period_gap_stats(feat_data, "PeriodGap", frequency=frequency)
                    if gap_stats_result is not None:
                        gap_stats_result = gap_stats_result.apply(
                            lambda row: row.apply(
                                lambda x: '{:.2%}'.format(x) if isinstance(x, (int, float)) and row.name not in [
                                    "skew", "kurt", "p-value"] else '{:.2f}'.format(x)
                            ), axis=1
                        )
            elif feature == 'Returns':
                # Placeholder for future implementation of Returns feature
                app.logger.warning("Returns feature not fully implemented yet")
                return render_template('index.html', error="The Returns feature is not fully implemented yet.")
            else:
                app.logger.error(f"Invalid feature: {feature}")
                return render_template('index.html', error=f"Invalid feature selected: {feature}")

            # Handle option matrix
            option_position_str = request.form.get('option_position')
            option_data = []
            if option_position_str:
                try:
                    option_rows = json.loads(option_position_str)
                    for row in option_rows:
                        option_type = row['optionType']
                        strike = float(row['strike'])
                        quantity = int(row['quantity'])
                        premium = float(row['premium'])
                        option_data.append({
                            'option_type': option_type,
                            'strike': strike,
                            'quantity': quantity,
                            'premium': premium
                        })

                    option_position = pd.DataFrame(option_data)
                    if not option_position.empty:
                        option_matrix_result = option_matrix(ticker, option_position)

                        # Generate PnL Chart
                        plt.figure(figsize=(10, 6))
                        plt.plot(option_matrix_result.index, option_matrix_result['PnL'])
                        plt.xlabel('Price')
                        plt.ylabel('PnL')
                        plt.title('Option PnL Chart')
                        plt.grid(True)

                        # Save the plot
                        with io.BytesIO() as img:
                            plt.savefig(img, format='png')
                            img.seek(0)
                            plot_url = base64.b64encode(img.getvalue()).decode()
                        plt.close()
                except Exception as e:
                    app.logger.error(f"Error processing option data: {e}", exc_info=True)
                    return render_template('index.html', error=f"Error processing option data: {str(e)}")

            return render_template('index.html',
                                   ticker=ticker,
                                   feature=feature,
                                   frequency=frequency,
                                   refreq_data=refreq_data.to_html() if refreq_data is not None else None,
                                   osc_ret_scatter_hist_url=osc_ret_scatter_hist_url,
                                   tail_stats_result=tail_stats_result.to_html() if tail_stats_result is not None else None,
                                   volatility_proj_pb0=volatility_proj_pb0.to_html() if volatility_proj_pb0 is not None else None,
                                   gap_stats_result=gap_stats_result.to_html() if gap_stats_result is not None else None,
                                   option_matrix_result=option_matrix_result.to_html() if option_matrix_result is not None else None,
                                   plot_url=plot_url,
                                   tail_plot_url=tail_plot_url)

        return render_template('index.html')

    except KeyError as ke:
        app.logger.error(f"Key error occurred: {ke}", exc_info=True)
        return render_template('index.html', error=f"Key error occurred: {str(ke)}. Please check your input.")
    except ValueError as ve:
        app.logger.error(f"Value error occurred: {ve}", exc_info=True)
        return render_template('index.html', error=f"Value error occurred: {str(ve)}. Please check your input.")
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return render_template('index.html', error=f"An unexpected error occurred: {str(e)}. Please try again.")


if __name__ == '__main__':
    app.run(debug=True)
