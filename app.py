import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import base64
import numpy as np
import seaborn as sns
import datetime as dt
from flask import Flask, request, render_template
import json


from marketobserve import * 

app = Flask(__name__)


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

            # Get start time from user input
            start_time_str = request.form.get('start_time')
            try:
                start_date = dt.datetime.strptime(start_time_str, '%Y%m').date()
            except ValueError:
                app.logger.error(f"Invalid start time format: {start_time_str}. Please use YYYYMM.")
                return render_template('index.html', error=f"Invalid start time format: {start_time_str}. Please use YYYYMM.")

            # Initialize PriceDynamic instance
            pxdy = PriceDynamic(ticker, start_date, frequency)
            data = pxdy._data
            if data is None or data.empty:
                app.logger.error(f"Failed to download data for {ticker}")
                return render_template('index.html', error=f"Failed to download data for {ticker}. Please check the ticker symbol.")

            refreq_data = data
            if refreq_data is None or refreq_data.empty:
                app.logger.error(f"Failed to refrequency data for {ticker}")
                return render_template('index.html', error=f"Failed to process data for {ticker} with frequency {frequency}.")

            # Calculate osc and ret using PriceDynamic methods
            osc = pxdy.osc(on_effect=True).dropna()
            ret = pxdy.ret().dropna()
            dif = pxdy.dif().dropna()
            df_features = pd.DataFrame({
                'Oscillation': osc,
                'Returns': ret,
                'Diff': dif
            })
            
            data = pd.concat([data,df_features],axis=1)

            # Initialize variables
            tail_stats_result = None
            tail_plot_url = None
            oscillation_projection_url = None
            gap_stats_result = None
            option_matrix_result = None
            plot_url = None
            osc_ret_scatter_hist_url = None

            # Handle feature-specific calculations
            if feature == 'Oscillation':
                feat_df= oscillation(refreq_data)
                feat_data = osc

            # elif feature == '':

            else:
                app.logger.error(f"Invalid feature: {feature}")
                return render_template('index.html', error=f"Invalid feature selected: {feature}")

            if feat_df is None or feat_df.empty:
                app.logger.error(f"Failed to calculate oscillation for {ticker}")
                return render_template('index.html', error=f"Failed to calculate oscillation for {ticker}.")

            # Create scatter plot
            fig, _ = scatter_hist(feat_data, ret)
            # Save the plot to a buffer
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png')
            img_buffer.seek(0)
            feat_ret_scatter_hist_url = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)

            feat_period_segment = period_segment(feat_data)
            tail_stats_result = tail_stats(feat_period_segment)
            tail_plot_url = tail_plot(feat_period_segment)

            if feature == 'Oscillation':
                feat_projection_url = osc_projection(data, target_bias=0)

            # elif feature == '':

            else:
                pass

            if "LastClose" in feat_df.columns and "PeriodGap" not in feat_df.columns:
                # Calculate PeriodGap if it doesn't exist
                feat_df["PeriodGap"] = feat_df["Open"] / feat_df["LastClose"] - 1

            if "PeriodGap" in feat_df.columns:
                gap_stats_result = period_gap_stats(feat_df, "PeriodGap", frequency=frequency)
                if gap_stats_result is not None:
                    gap_stats_result = gap_stats_result.apply(
                        lambda row: row.apply(
                            lambda x: '{:.2%}'.format(x) if isinstance(x, (int, float)) and row.name not in [
                                "skew", "kurt", "p-value"] else '{:.2f}'.format(x)
                            ), axis=1
                        )

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
                                   feat_ret_scatter_hist_url=feat_ret_scatter_hist_url,
                                   tail_stats_result=tail_stats_result.to_html() if tail_stats_result is not None else None,
                                   feat_projection_url=feat_projection_url,
                                   gap_stats_result=gap_stats_result.to_html() if gap_stats_result is not None else None,
                                #    option_matrix_result=option_matrix_result.to_html() if option_matrix_result is not None else None,
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
