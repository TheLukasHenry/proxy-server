# Reporting Toolkit - Implementation Plan

> **For Claude:** Execute tasks in order. Mark each task complete before moving to next.

**Date:** January 21, 2026
**Estimated Time:** 4-5 hours total

---

## Task 1: Create Excel Creator Tool

**File:** `open-webui-functions/reporting/excel_creator.py`

### Step 1.1: Create the base function structure

```python
"""
title: Excel Creator
author: MCP Team
version: 0.1.0
description: Creates Excel files with working formulas, multiple sheets, and formatting
requirements: openpyxl
"""

import json
import base64
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    def create_excel(
        self,
        specification: str,
        __user__: dict = {},
        __event_emitter__=None
    ) -> str:
        """
        Create an Excel file with formulas and formatting.

        :param specification: JSON specification for the Excel file
        :return: Download link or error message
        """
        pass
```

### Step 1.2: Implement JSON parsing

Parse the LLM's JSON output into a workbook specification:
- Validate required fields (filename, sheets)
- Handle optional formatting settings
- Provide clear error messages for malformed JSON

### Step 1.3: Implement workbook creation with openpyxl

```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, PatternFill, Side
from openpyxl.utils import get_column_letter

def _create_workbook(self, spec: dict) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    for sheet_spec in spec.get("sheets", []):
        ws = wb.create_sheet(title=sheet_spec.get("name", "Sheet"))
        self._populate_sheet(ws, sheet_spec)

    return wb
```

### Step 1.4: Implement formula handling

Key: openpyxl stores formulas as strings, Excel evaluates them:
```python
# Formulas are stored as-is
cell.value = "=SUM(B2:B10)"      # Works!
cell.value = "=IF(A1>100,\"High\",\"Low\")"  # Works!
cell.value = "=VLOOKUP(A2,Data!A:B,2,FALSE)"  # Works!
```

### Step 1.5: Implement formatting

```python
def _apply_formatting(self, ws, format_spec: dict):
    # Bold headers
    if format_spec.get("bold_headers"):
        for cell in ws[1]:
            cell.font = Font(bold=True)

    # Currency format
    for col in format_spec.get("currency_columns", []):
        for cell in ws[col]:
            cell.number_format = '$#,##0.00'

    # Freeze panes
    if format_spec.get("freeze_row"):
        ws.freeze_panes = f"A{format_spec['freeze_row'] + 1}"

    # Auto-fit columns
    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = max_length + 2
```

### Step 1.6: Implement browser download

```python
import io
import base64

def _trigger_download(self, wb: Workbook, filename: str) -> str:
    # Save to bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Encode as base64
    b64 = base64.b64encode(buffer.read()).decode()

    # Return HTML that triggers download
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{filename}_{timestamp}.xlsx"

    return f'''
    <script>
    (function() {{
        const b64 = "{b64}";
        const blob = new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))],
                              {{type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "{safe_filename}";
        a.click();
        URL.revokeObjectURL(url);
    }})();
    </script>
    <p>Downloading {safe_filename}...</p>
    '''
```

### Step 1.7: Add comprehensive examples in docstring

Provide examples so the LLM knows how to use it:
```python
"""
Example usage:

User: "Create a sales report Excel with Q1 data"

Call with specification:
{
  "filename": "Q1_Sales",
  "sheets": [{
    "name": "Summary",
    "headers": ["Product", "Jan", "Feb", "Mar", "Total"],
    "data": [
      ["Widget", 100, 120, 140, "=SUM(B2:D2)"],
      ["Gadget", 150, 160, 170, "=SUM(B3:D3)"]
    ],
    "totals_row": ["TOTAL", "=SUM(B2:B3)", "=SUM(C2:C3)", "=SUM(D2:D3)", "=SUM(E2:E3)"],
    "format": {"bold_headers": true, "currency_columns": ["B","C","D","E"]}
  }]
}
"""
```

---

## Task 2: Create Executive Dashboard Tool

**File:** `open-webui-functions/reporting/executive_dashboard.py`

### Step 2.1: Create the base function structure

```python
"""
title: Executive Dashboard
author: MCP Team
version: 0.1.0
description: Creates multi-chart HTML dashboards with KPIs for executives
"""

class Tools:
    def __init__(self):
        self.plotly_cdn = "https://cdn.plot.ly/plotly-2.27.0.min.js"

    def create_dashboard(
        self,
        specification: str,
        __user__: dict = {},
        __event_emitter__=None
    ) -> str:
        """
        Create an executive dashboard with KPIs and charts.

        :param specification: JSON specification for the dashboard
        :return: HTML dashboard
        """
        pass
```

### Step 2.2: Implement KPI card generation

```python
def _generate_kpi_cards(self, kpis: list) -> str:
    cards_html = ""
    for kpi in kpis:
        trend_class = "positive" if kpi.get("trend") == "up" else "negative"
        trend_arrow = "▲" if kpi.get("trend") == "up" else "▼"

        cards_html += f'''
        <div class="kpi-card {trend_class}">
            <div class="kpi-label">{kpi["label"]}</div>
            <div class="kpi-value">{kpi["value"]}</div>
            <div class="kpi-change">{trend_arrow} {kpi["change"]}</div>
        </div>
        '''
    return cards_html
```

### Step 2.3: Implement chart generation with Plotly.js

```python
def _generate_chart(self, chart: dict, chart_id: str) -> tuple:
    """Returns (html_div, js_code)"""
    chart_type = chart.get("type", "bar")

    if chart_type == "bar":
        return self._generate_bar_chart(chart, chart_id)
    elif chart_type == "line":
        return self._generate_line_chart(chart, chart_id)
    elif chart_type == "pie":
        return self._generate_pie_chart(chart, chart_id)

def _generate_bar_chart(self, chart: dict, chart_id: str) -> tuple:
    traces = []
    for dataset in chart.get("datasets", []):
        traces.append({
            "x": chart["labels"],
            "y": dataset["data"],
            "name": dataset["label"],
            "type": "bar"
        })

    js = f'''
    Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {{
        title: "{chart['title']}",
        barmode: "group"
    }});
    '''
    return f'<div id="{chart_id}" class="chart"></div>', js
```

### Step 2.4: Implement CSS styling

```python
def _get_dashboard_css(self) -> str:
    return '''
    <style>
        .dashboard { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; background: #f5f5f5; }
        .dashboard-header { text-align: center; margin-bottom: 30px; }
        .dashboard-title { font-size: 28px; font-weight: 600; color: #333; }
        .dashboard-subtitle { font-size: 14px; color: #666; }

        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .kpi-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }
        .kpi-label { font-size: 14px; color: #666; margin-bottom: 8px; }
        .kpi-value { font-size: 32px; font-weight: 700; color: #333; }
        .kpi-change { font-size: 14px; margin-top: 8px; }
        .kpi-card.positive .kpi-change { color: #22c55e; }
        .kpi-card.negative .kpi-change { color: #ef4444; }

        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .chart { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-height: 300px; }

        .download-bar { text-align: center; margin-top: 30px; }
        .download-btn { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; margin: 0 10px; }
        .download-btn:hover { background: #2563eb; }
    </style>
    '''
```

### Step 2.5: Implement full HTML assembly

```python
def _assemble_dashboard(self, spec: dict) -> str:
    title = spec.get("title", "Executive Dashboard")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Generate components
    kpi_html = self._generate_kpi_cards(spec.get("kpis", []))

    charts_html = ""
    charts_js = ""
    for i, chart in enumerate(spec.get("charts", [])):
        div, js = self._generate_chart(chart, f"chart_{i}")
        charts_html += div
        charts_js += js

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <script src="{self.plotly_cdn}"></script>
        {self._get_dashboard_css()}
    </head>
    <body>
        <div class="dashboard">
            <div class="dashboard-header">
                <div class="dashboard-title">{title}</div>
                <div class="dashboard-subtitle">Generated: {timestamp}</div>
            </div>

            <div class="kpi-grid">{kpi_html}</div>
            <div class="chart-grid">{charts_html}</div>

            <div class="download-bar">
                <button class="download-btn" onclick="downloadHTML()">Download HTML</button>
                <button class="download-btn" onclick="downloadPNG()">Download PNG</button>
            </div>
        </div>

        <script>
            {charts_js}

            function downloadHTML() {{
                const html = document.documentElement.outerHTML;
                const blob = new Blob([html], {{type: "text/html"}});
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = "dashboard_{timestamp.replace(" ", "_")}.html";
                a.click();
            }}

            function downloadPNG() {{
                // Use html2canvas if available, or Plotly's toImage
                alert("PNG download - implement with html2canvas");
            }}
        </script>
    </body>
    </html>
    '''
```

---

## Task 3: Create Directory and __init__.py

**File:** `open-webui-functions/reporting/__init__.py`

```python
"""
Reporting Toolkit for Open WebUI

Tools for creating Excel files, dashboards, and visualizations.
"""

from .excel_creator import Tools as ExcelCreatorTools
from .executive_dashboard import Tools as ExecutiveDashboardTools

__all__ = ["ExcelCreatorTools", "ExecutiveDashboardTools"]
```

---

## Task 4: Create Installation Guide for Existing Tools

**File:** `docs/REPORTING-TOOLKIT-GUIDE.md`

Document how to:
1. Install Visualize Data R3 from community
2. Install Generate Presentations from community
3. Install our new Excel Creator tool
4. Install our new Executive Dashboard tool
5. Example prompts for each tool

---

## Task 5: Test All Tools

### Test Excel Creator
```
Prompt: "Create an Excel file with my monthly budget:
- Column A: Category (Rent, Food, Transport, Entertainment)
- Column B: Budget ($1500, $400, $200, $150)
- Column C: Actual ($1500, $380, $220, $180)
- Column D: Difference with formula =B-C
- Row 6: Totals with SUM formulas"

Expected: Downloads .xlsx with working formulas
```

### Test Executive Dashboard
```
Prompt: "Create an executive dashboard for Q1 with:
- KPIs: Revenue $1.2M (+15%), Users 45K (+8%), NPS 72 (+3)
- Line chart: Monthly revenue trend
- Pie chart: Revenue by region
- Bar chart: Actual vs Target"

Expected: Renders interactive HTML dashboard
```

### Test Visualize Data R3
```
Prompt: "Show me a bar chart of our team's productivity:
- Alice: 45 tasks
- Bob: 38 tasks
- Charlie: 52 tasks
- Diana: 41 tasks"

Expected: Renders interactive bar chart in chat
```

---

## Task 6: Commit and Document

```bash
git add open-webui-functions/reporting/
git add docs/REPORTING-TOOLKIT-GUIDE.md
git add docs/plans/2026-01-21-reporting-toolkit-*.md
git commit -m "feat: add Reporting Toolkit - Excel with formulas and Executive Dashboards"
```

---

## Summary Checklist

- [ ] Task 1: Excel Creator Tool (excel_creator.py)
- [ ] Task 2: Executive Dashboard Tool (executive_dashboard.py)
- [ ] Task 3: Create __init__.py
- [ ] Task 4: Installation guide
- [ ] Task 5: Test all tools
- [ ] Task 6: Commit

---

*Implementation plan created: January 21, 2026*
