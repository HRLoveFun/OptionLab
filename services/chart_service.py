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