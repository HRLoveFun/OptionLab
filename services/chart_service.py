import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import datetime as dt
import io
import base64
import logging

logger = logging.getLogger(__name__)

class ChartService:
    """Service for generating charts and visualizations"""
    
    @staticmethod
    def generate_correlation_matrix(correlation_data):
        """Generate correlation matrix chart"""
        try:
            # Calculate correlations for different periods
            periods = {
                '1M': 22,
                '1Q': 66,
                'YTD': None,
                'ETD': None
            }
            
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Market Correlation Matrix', fontsize=16, fontweight='bold')
            
            axes = axes.flatten()
            
            for idx, (period_name, days) in enumerate(periods.items()):
                try:
                    period_data = ChartService._prepare_correlation_data(correlation_data, period_name, days)
                    
                    if len(period_data) >= 2:
                        # Create correlation matrix
                        corr_df = pd.DataFrame(period_data).corr()
                        
                        # Plot heatmap
                        sns.heatmap(
                            corr_df,
                            annot=True,
                            cmap='RdYlBu_r',
                            center=0,
                            fmt='.2f',
                            square=True,
                            ax=axes[idx],
                            cbar_kws={'shrink': 0.8}
                        )
                        axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
                        axes[idx].tick_params(axis='x', rotation=45)
                        axes[idx].tick_params(axis='y', rotation=0)
                    else:
                        ChartService._add_no_data_text(axes[idx], f'Insufficient data for {period_name}')
                        axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
                    
                except Exception as e:
                    logger.warning(f"Error generating correlation for {period_name}: {e}")
                    ChartService._add_no_data_text(axes[idx], f'Error: {period_name}')
                    axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
            
            plt.tight_layout()
            
            # Convert to base64
            return ChartService._convert_plot_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error generating correlation matrix: {e}")
            return None
    
    @staticmethod
    def _prepare_correlation_data(correlation_data, period_name, days):
        """Prepare data for correlation calculation for a specific period"""
        period_data = {}
        
        for ticker, returns in correlation_data.items():
            if period_name == 'YTD':
                # Year to date
                year_start = dt.date(dt.date.today().year, 1, 1)
                period_returns = returns[returns.index.date >= year_start]
            elif period_name == 'ETD':
                # Entire time period
                period_returns = returns
            else:
                # Fixed period
                period_returns = returns.iloc[-days:] if len(returns) > days else returns
            
            if len(period_returns) > 10:  # Minimum data points
                period_data[ticker] = period_returns
        
        return period_data
    
    @staticmethod
    def _add_no_data_text(ax, text):
        """Add text to axis when no data is available"""
        ax.text(0.5, 0.5, text, ha='center', va='center', transform=ax.transAxes)
    
    @staticmethod
    def _convert_plot_to_base64(fig):
        """Convert matplotlib figure to base64 string"""
        try:
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close(fig)
            
            return base64.b64encode(plot_data).decode()
        except Exception as e:
            logger.error(f"Error converting plot to base64: {e}")
            plt.close(fig)
            return None