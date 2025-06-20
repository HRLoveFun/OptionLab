"""
Market Analyzer - Core business logic for market analysis
"""
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the existing MarketAnalyzer from marketobserve.py
from marketobserve import MarketAnalyzer

# Re-export for clean imports
__all__ = ['MarketAnalyzer']