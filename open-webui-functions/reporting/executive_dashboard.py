"""
title: Executive Dashboard
author: MCP Team
author_url: https://github.com/your-org
funding_url: https://github.com/sponsors/your-org
version: 0.1.0
description: Creates professional executive dashboards with KPI cards and interactive charts using Plotly.js
"""

import json
import base64
from datetime import datetime
from typing import Optional, Any, List, Dict


class Tools:
    """
    Executive Dashboard Tool for Open WebUI

    Creates professional HTML dashboards with:
    - KPI cards with trend indicators
    - Interactive charts (bar, line, pie, scatter)
    - Responsive layout for any screen
    - Download as HTML file
    - Professional styling

    Example prompt:
        "Create an executive dashboard for Q1 2026 with:
         - KPIs: Revenue $1.2M up 15%, Users 45K up 8%, NPS 72 up 3 points
         - Line chart showing monthly revenue trend
         - Pie chart showing sales by region
         - Bar chart comparing actual vs target"
    """

    def __init__(self):
        self.valves = self.Valves()
        self.plotly_cdn = "https://cdn.plot.ly/plotly-2.27.0.min.js"

    class Valves:
        """Configuration options for the Executive Dashboard tool."""
        pass

    def create_dashboard(
        self,
        specification: str,
        __user__: dict = {},
        __event_emitter__: Any = None
    ) -> str:
        """
        Create an executive dashboard with KPIs and charts.

        :param specification: JSON specification for the dashboard. Format:
            {
                "title": "Q1 2026 Executive Dashboard",
                "subtitle": "Performance Overview",
                "kpis": [
                    {"label": "Revenue", "value": "$1.2M", "change": "+15%", "trend": "up"},
                    {"label": "Users", "value": "45,000", "change": "+8%", "trend": "up"},
                    {"label": "NPS", "value": "72", "change": "+3 pts", "trend": "up"}
                ],
                "charts": [
                    {
                        "type": "line",
                        "title": "Revenue Trend",
                        "labels": ["Jan", "Feb", "Mar", "Apr"],
                        "datasets": [
                            {"label": "2026", "data": [350000, 420000, 480000, 520000]},
                            {"label": "2025", "data": [300000, 350000, 400000, 430000]}
                        ]
                    },
                    {
                        "type": "pie",
                        "title": "Sales by Region",
                        "labels": ["North", "South", "East", "West"],
                        "data": [35, 25, 22, 18]
                    },
                    {
                        "type": "bar",
                        "title": "Actual vs Target",
                        "labels": ["Q1", "Q2", "Q3", "Q4"],
                        "datasets": [
                            {"label": "Actual", "data": [105, 98, 112, 108]},
                            {"label": "Target", "data": [100, 100, 100, 100]}
                        ]
                    }
                ],
                "theme": "light"
            }
        :return: HTML dashboard
        """
        try:
            # Parse specification
            if isinstance(specification, str):
                try:
                    spec = json.loads(specification)
                except json.JSONDecodeError as e:
                    return f"Error: Invalid JSON specification. {str(e)}"
            else:
                spec = specification

            # Extract components
            title = spec.get("title", "Executive Dashboard")
            subtitle = spec.get("subtitle", "")
            kpis = spec.get("kpis", [])
            charts = spec.get("charts", [])
            theme = spec.get("theme", "light")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Generate KPI cards HTML
            kpi_html = self._generate_kpi_cards(kpis)

            # Generate charts HTML and JS
            charts_html = ""
            charts_js = ""
            for i, chart in enumerate(charts):
                chart_id = f"chart_{i}"
                div_html, js_code = self._generate_chart(chart, chart_id)
                charts_html += div_html
                charts_js += js_code

            # Get CSS
            css = self._get_dashboard_css(theme)

            # Assemble full HTML
            html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="{self.plotly_cdn}"></script>
    {css}
</head>
<body>
    <div class="dashboard">
        <div class="dashboard-header">
            <div class="dashboard-title">{title}</div>
            {f'<div class="dashboard-subtitle">{subtitle}</div>' if subtitle else ''}
            <div class="dashboard-timestamp">Generated: {timestamp}</div>
        </div>

        {f'<div class="kpi-grid">{kpi_html}</div>' if kpis else ''}

        {f'<div class="chart-grid">{charts_html}</div>' if charts else ''}

        <div class="download-bar">
            <button class="download-btn" onclick="downloadHTML()">
                <span class="btn-icon">&#128190;</span> Download HTML
            </button>
        </div>

        <div class="footer">
            Generated by Open WebUI Reporting Toolkit
        </div>
    </div>

    <script>
        // Initialize charts
        document.addEventListener('DOMContentLoaded', function() {{
            {charts_js}
        }});

        // Download function
        function downloadHTML() {{
            const html = document.documentElement.outerHTML;
            const blob = new Blob([html], {{type: "text/html"}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>'''

            return html

        except Exception as e:
            return f"Error creating dashboard: {str(e)}"

    def _generate_kpi_cards(self, kpis: List[Dict]) -> str:
        """Generate HTML for KPI cards."""
        cards_html = ""

        for kpi in kpis:
            label = kpi.get("label", "KPI")
            value = kpi.get("value", "0")
            change = kpi.get("change", "")
            trend = kpi.get("trend", "neutral")

            # Determine trend class and arrow
            if trend == "up":
                trend_class = "positive"
                trend_arrow = "&#9650;"  # ▲
            elif trend == "down":
                trend_class = "negative"
                trend_arrow = "&#9660;"  # ▼
            else:
                trend_class = "neutral"
                trend_arrow = "&#9644;"  # ▬

            cards_html += f'''
            <div class="kpi-card {trend_class}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                {f'<div class="kpi-change"><span class="trend-arrow">{trend_arrow}</span> {change}</div>' if change else ''}
            </div>'''

        return cards_html

    def _generate_chart(self, chart: Dict, chart_id: str) -> tuple:
        """Generate HTML div and Plotly.js code for a chart."""
        chart_type = chart.get("type", "bar")
        title = chart.get("title", "Chart")

        div_html = f'''
        <div class="chart-container">
            <div class="chart-title">{title}</div>
            <div id="{chart_id}" class="chart"></div>
        </div>'''

        # Generate Plotly.js code based on chart type
        if chart_type == "bar":
            js_code = self._generate_bar_chart_js(chart, chart_id)
        elif chart_type == "line":
            js_code = self._generate_line_chart_js(chart, chart_id)
        elif chart_type == "pie":
            js_code = self._generate_pie_chart_js(chart, chart_id)
        elif chart_type == "scatter":
            js_code = self._generate_scatter_chart_js(chart, chart_id)
        else:
            js_code = self._generate_bar_chart_js(chart, chart_id)

        return div_html, js_code

    def _generate_bar_chart_js(self, chart: Dict, chart_id: str) -> str:
        """Generate Plotly.js code for a bar chart."""
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])

        traces = []
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

        for i, dataset in enumerate(datasets):
            trace = {
                "x": labels,
                "y": dataset.get("data", []),
                "name": dataset.get("label", f"Series {i+1}"),
                "type": "bar",
                "marker": {"color": colors[i % len(colors)]}
            }
            traces.append(trace)

        layout = {
            "barmode": "group",
            "margin": {"t": 20, "r": 20, "b": 40, "l": 50},
            "legend": {"orientation": "h", "y": -0.15},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)"
        }

        config = {"responsive": True, "displayModeBar": False}

        return f'''
            Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {json.dumps(layout)}, {json.dumps(config)});
        '''

    def _generate_line_chart_js(self, chart: Dict, chart_id: str) -> str:
        """Generate Plotly.js code for a line chart."""
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])

        traces = []
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

        for i, dataset in enumerate(datasets):
            trace = {
                "x": labels,
                "y": dataset.get("data", []),
                "name": dataset.get("label", f"Series {i+1}"),
                "type": "scatter",
                "mode": "lines+markers",
                "line": {"color": colors[i % len(colors)], "width": 3},
                "marker": {"size": 8}
            }
            traces.append(trace)

        layout = {
            "margin": {"t": 20, "r": 20, "b": 40, "l": 50},
            "legend": {"orientation": "h", "y": -0.15},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "xaxis": {"showgrid": True, "gridcolor": "#e5e7eb"},
            "yaxis": {"showgrid": True, "gridcolor": "#e5e7eb"}
        }

        config = {"responsive": True, "displayModeBar": False}

        return f'''
            Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {json.dumps(layout)}, {json.dumps(config)});
        '''

    def _generate_pie_chart_js(self, chart: Dict, chart_id: str) -> str:
        """Generate Plotly.js code for a pie chart."""
        labels = chart.get("labels", [])
        data = chart.get("data", [])

        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

        trace = {
            "labels": labels,
            "values": data,
            "type": "pie",
            "hole": 0.4,  # Donut style
            "marker": {"colors": colors[:len(labels)]},
            "textinfo": "label+percent",
            "textposition": "outside"
        }

        layout = {
            "margin": {"t": 20, "r": 20, "b": 20, "l": 20},
            "showlegend": True,
            "legend": {"orientation": "h", "y": -0.1},
            "paper_bgcolor": "rgba(0,0,0,0)"
        }

        config = {"responsive": True, "displayModeBar": False}

        return f'''
            Plotly.newPlot("{chart_id}", [{json.dumps(trace)}], {json.dumps(layout)}, {json.dumps(config)});
        '''

    def _generate_scatter_chart_js(self, chart: Dict, chart_id: str) -> str:
        """Generate Plotly.js code for a scatter chart."""
        datasets = chart.get("datasets", [])
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']

        traces = []
        for i, dataset in enumerate(datasets):
            trace = {
                "x": dataset.get("x", []),
                "y": dataset.get("y", []),
                "name": dataset.get("label", f"Series {i+1}"),
                "type": "scatter",
                "mode": "markers",
                "marker": {"color": colors[i % len(colors)], "size": 10}
            }
            traces.append(trace)

        layout = {
            "margin": {"t": 20, "r": 20, "b": 40, "l": 50},
            "legend": {"orientation": "h", "y": -0.15},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)"
        }

        config = {"responsive": True, "displayModeBar": False}

        return f'''
            Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {json.dumps(layout)}, {json.dumps(config)});
        '''

    def _get_dashboard_css(self, theme: str = "light") -> str:
        """Get CSS for the dashboard."""
        if theme == "dark":
            bg_color = "#1f2937"
            text_color = "#f9fafb"
            card_bg = "#374151"
            border_color = "#4b5563"
        else:
            bg_color = "#f3f4f6"
            text_color = "#111827"
            card_bg = "#ffffff"
            border_color = "#e5e7eb"

        return f'''
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: {bg_color};
            color: {text_color};
            line-height: 1.6;
        }}

        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }}

        .dashboard-header {{
            text-align: center;
            margin-bottom: 40px;
        }}

        .dashboard-title {{
            font-size: 32px;
            font-weight: 700;
            color: {text_color};
            margin-bottom: 8px;
        }}

        .dashboard-subtitle {{
            font-size: 18px;
            color: #6b7280;
            margin-bottom: 8px;
        }}

        .dashboard-timestamp {{
            font-size: 14px;
            color: #9ca3af;
        }}

        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}

        .kpi-card {{
            background: {card_bg};
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}

        .kpi-label {{
            font-size: 14px;
            font-weight: 500;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 36px;
            font-weight: 700;
            color: {text_color};
            margin-bottom: 8px;
        }}

        .kpi-change {{
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }}

        .kpi-card.positive .kpi-change {{
            color: #10b981;
        }}

        .kpi-card.negative .kpi-change {{
            color: #ef4444;
        }}

        .kpi-card.neutral .kpi-change {{
            color: #6b7280;
        }}

        .trend-arrow {{
            font-size: 12px;
        }}

        /* Charts */
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}

        .chart-container {{
            background: {card_bg};
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}

        .chart-title {{
            font-size: 18px;
            font-weight: 600;
            color: {text_color};
            margin-bottom: 16px;
            text-align: center;
        }}

        .chart {{
            min-height: 300px;
            width: 100%;
        }}

        /* Download Bar */
        .download-bar {{
            text-align: center;
            margin: 40px 0;
        }}

        .download-btn {{
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .download-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
        }}

        .btn-icon {{
            font-size: 18px;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #9ca3af;
            font-size: 12px;
            border-top: 1px solid {border_color};
            margin-top: 40px;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .dashboard {{
                padding: 16px;
            }}

            .dashboard-title {{
                font-size: 24px;
            }}

            .kpi-value {{
                font-size: 28px;
            }}

            .chart-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>'''

    def create_simple_dashboard(
        self,
        title: str,
        kpis: str,
        chart_type: str = "bar",
        chart_title: str = "Chart",
        chart_labels: str = "",
        chart_data: str = "",
        __user__: dict = {},
        __event_emitter__: Any = None
    ) -> str:
        """
        Create a simple dashboard from basic inputs (easier for LLM to use).

        :param title: Dashboard title
        :param kpis: KPIs in format "Label:Value:Change:trend|..." (e.g., "Revenue:$1.2M:+15%:up|Users:45K:+8%:up")
        :param chart_type: Type of chart (bar, line, pie)
        :param chart_title: Title for the chart
        :param chart_labels: Comma-separated labels (e.g., "Jan,Feb,Mar,Apr")
        :param chart_data: Comma-separated data values (e.g., "100,120,140,160")
        :return: HTML dashboard
        """
        try:
            # Parse KPIs
            kpi_list = []
            if kpis:
                for kpi_str in kpis.split("|"):
                    parts = kpi_str.split(":")
                    if len(parts) >= 2:
                        kpi_list.append({
                            "label": parts[0].strip(),
                            "value": parts[1].strip(),
                            "change": parts[2].strip() if len(parts) > 2 else "",
                            "trend": parts[3].strip() if len(parts) > 3 else "neutral"
                        })

            # Parse chart
            labels = [l.strip() for l in chart_labels.split(",")] if chart_labels else []
            data = []
            if chart_data:
                for val in chart_data.split(","):
                    try:
                        data.append(float(val.strip()))
                    except ValueError:
                        data.append(0)

            # Build specification
            spec = {
                "title": title,
                "kpis": kpi_list,
                "charts": []
            }

            if labels and data:
                if chart_type == "pie":
                    spec["charts"].append({
                        "type": "pie",
                        "title": chart_title,
                        "labels": labels,
                        "data": data
                    })
                else:
                    spec["charts"].append({
                        "type": chart_type,
                        "title": chart_title,
                        "labels": labels,
                        "datasets": [{"label": "Value", "data": data}]
                    })

            return self.create_dashboard(json.dumps(spec), __user__, __event_emitter__)

        except Exception as e:
            return f"Error creating simple dashboard: {str(e)}"
