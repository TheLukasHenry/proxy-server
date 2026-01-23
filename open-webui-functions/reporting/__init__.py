"""
Reporting Toolkit for Open WebUI

A collection of tools for creating professional reports:
- Excel Creator: Spreadsheets with working formulas
- Executive Dashboard: KPI cards and interactive charts

Usage:
    Import these tools into Open WebUI via Admin > Functions/Tools
"""

from .excel_creator import Tools as ExcelCreatorTools
from .executive_dashboard import Tools as ExecutiveDashboardTools

__all__ = ["ExcelCreatorTools", "ExecutiveDashboardTools"]
__version__ = "0.1.0"
