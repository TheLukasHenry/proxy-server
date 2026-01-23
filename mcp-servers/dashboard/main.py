"""
Executive Dashboard MCP Server
Creates professional HTML dashboards with KPI cards and interactive charts.
Exposes tools via OpenAPI for the MCP proxy.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

app = FastAPI(
    title="Executive Dashboard MCP",
    description="Create professional executive dashboards with KPI cards and charts",
    version="1.0.0"
)

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.27.0.min.js"


class SimpleDashboardRequest(BaseModel):
    """Request for creating a simple dashboard."""
    title: str = Field(..., description="Dashboard title")
    kpis: str = Field(
        default="",
        description="KPIs in format 'Label:Value:Change:trend|...' (e.g., 'Revenue:$1.2M:+15%:up|Users:45K:+8%:up')"
    )
    chart_type: str = Field(default="bar", description="Chart type: bar, line, or pie")
    chart_title: str = Field(default="Chart", description="Title for the chart")
    chart_labels: str = Field(default="", description="Comma-separated labels (e.g., 'Jan,Feb,Mar,Apr')")
    chart_data: str = Field(default="", description="Comma-separated data values (e.g., '100,120,140,160')")
    theme: str = Field(default="light", description="Theme: light or dark")


class AdvancedDashboardRequest(BaseModel):
    """Request for creating an advanced dashboard with full JSON specification."""
    specification: str = Field(
        ...,
        description="""JSON specification for the dashboard. Format:
{
    "title": "Q1 2026 Executive Dashboard",
    "subtitle": "Performance Overview",
    "kpis": [
        {"label": "Revenue", "value": "$1.2M", "change": "+15%", "trend": "up"},
        {"label": "Users", "value": "45,000", "change": "+8%", "trend": "up"}
    ],
    "charts": [
        {
            "type": "line",
            "title": "Revenue Trend",
            "labels": ["Jan", "Feb", "Mar"],
            "datasets": [{"label": "2026", "data": [350000, 420000, 480000]}]
        },
        {
            "type": "pie",
            "title": "Sales by Region",
            "labels": ["North", "South", "East"],
            "data": [35, 25, 40]
        }
    ],
    "theme": "light"
}"""
    )


class DashboardResponse(BaseModel):
    """Response containing the dashboard."""
    success: bool
    filename: str
    download_html: str
    message: str
    kpi_count: int
    chart_count: int


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dashboard"}


def generate_kpi_cards(kpis: List[Dict]) -> str:
    """Generate HTML for KPI cards."""
    cards_html = ""
    for kpi in kpis:
        label = kpi.get("label", "KPI")
        value = kpi.get("value", "0")
        change = kpi.get("change", "")
        trend = kpi.get("trend", "neutral")

        if trend == "up":
            trend_class = "positive"
            trend_arrow = "&#9650;"
        elif trend == "down":
            trend_class = "negative"
            trend_arrow = "&#9660;"
        else:
            trend_class = "neutral"
            trend_arrow = "&#9644;"

        cards_html += f'''
        <div class="kpi-card {trend_class}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {f'<div class="kpi-change"><span class="trend-arrow">{trend_arrow}</span> {change}</div>' if change else ''}
        </div>'''
    return cards_html


def generate_chart_js(chart: Dict, chart_id: str) -> tuple:
    """Generate HTML div and Plotly.js code for a chart."""
    chart_type = chart.get("type", "bar")
    title = chart.get("title", "Chart")

    div_html = f'''
    <div class="chart-container">
        <div class="chart-title">{title}</div>
        <div id="{chart_id}" class="chart"></div>
    </div>'''

    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

    if chart_type == "pie":
        labels = chart.get("labels", [])
        data = chart.get("data", [])
        trace = {
            "labels": labels,
            "values": data,
            "type": "pie",
            "hole": 0.4,
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
        js_code = f'Plotly.newPlot("{chart_id}", [{json.dumps(trace)}], {json.dumps(layout)}, {{responsive: true, displayModeBar: false}});'

    elif chart_type == "line":
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])
        traces = []
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
        js_code = f'Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {json.dumps(layout)}, {{responsive: true, displayModeBar: false}});'

    else:  # bar
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])
        traces = []
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
        js_code = f'Plotly.newPlot("{chart_id}", {json.dumps(traces)}, {json.dumps(layout)}, {{responsive: true, displayModeBar: false}});'

    return div_html, js_code


def get_dashboard_css(theme: str = "light") -> str:
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
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: {bg_color};
        color: {text_color};
        line-height: 1.6;
    }}
    .dashboard {{ max-width: 1400px; margin: 0 auto; padding: 30px; }}
    .dashboard-header {{ text-align: center; margin-bottom: 40px; }}
    .dashboard-title {{ font-size: 32px; font-weight: 700; color: {text_color}; margin-bottom: 8px; }}
    .dashboard-subtitle {{ font-size: 18px; color: #6b7280; margin-bottom: 8px; }}
    .dashboard-timestamp {{ font-size: 14px; color: #9ca3af; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px; margin-bottom: 40px; }}
    .kpi-card {{
        background: {card_bg}; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .kpi-card:hover {{ transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
    .kpi-label {{ font-size: 14px; font-weight: 500; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 36px; font-weight: 700; color: {text_color}; margin-bottom: 8px; }}
    .kpi-change {{ font-size: 14px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 4px; }}
    .kpi-card.positive .kpi-change {{ color: #10b981; }}
    .kpi-card.negative .kpi-change {{ color: #ef4444; }}
    .kpi-card.neutral .kpi-change {{ color: #6b7280; }}
    .trend-arrow {{ font-size: 12px; }}
    .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px; margin-bottom: 40px; }}
    .chart-container {{ background: {card_bg}; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
    .chart-title {{ font-size: 18px; font-weight: 600; color: {text_color}; margin-bottom: 16px; text-align: center; }}
    .chart {{ min-height: 300px; width: 100%; }}
    .download-bar {{ text-align: center; margin: 40px 0; }}
    .download-btn {{
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white; border: none; padding: 14px 28px; border-radius: 12px;
        font-size: 16px; font-weight: 600; cursor: pointer;
        display: inline-flex; align-items: center; gap: 8px;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .download-btn:hover {{ transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(59,130,246,0.3); }}
    .btn-icon {{ font-size: 18px; }}
    .footer {{ text-align: center; padding: 20px; color: #9ca3af; font-size: 12px; border-top: 1px solid {border_color}; margin-top: 40px; }}
    @media (max-width: 768px) {{
        .dashboard {{ padding: 16px; }}
        .dashboard-title {{ font-size: 24px; }}
        .kpi-value {{ font-size: 28px; }}
        .chart-grid {{ grid-template-columns: 1fr; }}
    }}
</style>'''


def build_dashboard_html(title: str, subtitle: str, kpis: List[Dict], charts: List[Dict], theme: str) -> str:
    """Build complete dashboard HTML."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    download_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    kpi_html = generate_kpi_cards(kpis)

    charts_html = ""
    charts_js = ""
    for i, chart in enumerate(charts):
        chart_id = f"chart_{i}"
        div_html, js_code = generate_chart_js(chart, chart_id)
        charts_html += div_html
        charts_js += js_code

    css = get_dashboard_css(theme)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="{PLOTLY_CDN}"></script>
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
        document.addEventListener('DOMContentLoaded', function() {{
            {charts_js}
        }});

        function downloadHTML() {{
            const html = document.documentElement.outerHTML;
            const blob = new Blob([html], {{type: "text/html"}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "dashboard_{download_timestamp}.html";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>'''
    return html


@app.post("/create_simple_dashboard", response_model=DashboardResponse)
async def create_simple_dashboard(request: SimpleDashboardRequest):
    """
    Create a simple dashboard from basic inputs.

    Example:
        title: "Q1 Dashboard"
        kpis: "Revenue:$1.2M:+15%:up|Users:45K:+8%:up|NPS:72:+3 pts:up"
        chart_type: "bar"
        chart_title: "Monthly Sales"
        chart_labels: "Jan,Feb,Mar,Apr"
        chart_data: "100,120,140,160"
    """
    try:
        # Parse KPIs
        kpi_list = []
        if request.kpis:
            for kpi_str in request.kpis.split("|"):
                parts = kpi_str.split(":")
                if len(parts) >= 2:
                    kpi_list.append({
                        "label": parts[0].strip(),
                        "value": parts[1].strip(),
                        "change": parts[2].strip() if len(parts) > 2 else "",
                        "trend": parts[3].strip() if len(parts) > 3 else "neutral"
                    })

        # Parse chart
        labels = [l.strip() for l in request.chart_labels.split(",")] if request.chart_labels else []
        data = []
        if request.chart_data:
            for val in request.chart_data.split(","):
                try:
                    data.append(float(val.strip()))
                except ValueError:
                    data.append(0)

        # Build charts
        charts = []
        if labels and data:
            if request.chart_type == "pie":
                charts.append({
                    "type": "pie",
                    "title": request.chart_title,
                    "labels": labels,
                    "data": data
                })
            else:
                charts.append({
                    "type": request.chart_type,
                    "title": request.chart_title,
                    "labels": labels,
                    "datasets": [{"label": "Value", "data": data}]
                })

        # Build HTML
        html = build_dashboard_html(request.title, "", kpi_list, charts, request.theme)

        # Create download wrapper
        fname = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        import base64
        b64 = base64.b64encode(html.encode()).decode()

        download_html = f'''<div style="padding:20px;background:linear-gradient(135deg,#1e3a5f,#2d5a87);border-radius:12px;color:white;margin:10px 0;">
<h3 style="margin:0 0 10px 0;">Executive Dashboard Created: {request.title}</h3>
<p style="margin:0 0 15px 0;opacity:0.9;">Contains {len(kpi_list)} KPIs and {len(charts)} chart(s)</p>
<a href="data:text/html;base64,{b64}" download="{fname}" style="display:inline-block;padding:12px 24px;background:#4CAF50;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">Download Dashboard</a>
</div>'''

        return DashboardResponse(
            success=True,
            filename=fname,
            download_html=download_html,
            message=f"Created dashboard with {len(kpi_list)} KPIs and {len(charts)} charts",
            kpi_count=len(kpi_list),
            chart_count=len(charts)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_dashboard", response_model=DashboardResponse)
async def create_dashboard(request: AdvancedDashboardRequest):
    """
    Create an advanced dashboard from full JSON specification.

    Supports multiple charts, custom KPIs, and themes.
    """
    try:
        spec = json.loads(request.specification)

        title = spec.get("title", "Executive Dashboard")
        subtitle = spec.get("subtitle", "")
        kpis = spec.get("kpis", [])
        charts = spec.get("charts", [])
        theme = spec.get("theme", "light")

        html = build_dashboard_html(title, subtitle, kpis, charts, theme)

        fname = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        import base64
        b64 = base64.b64encode(html.encode()).decode()

        download_html = f'''<div style="padding:20px;background:linear-gradient(135deg,#1e3a5f,#2d5a87);border-radius:12px;color:white;margin:10px 0;">
<h3 style="margin:0 0 10px 0;">Executive Dashboard Created: {title}</h3>
<p style="margin:0 0 15px 0;opacity:0.9;">Contains {len(kpis)} KPIs and {len(charts)} chart(s)</p>
<a href="data:text/html;base64,{b64}" download="{fname}" style="display:inline-block;padding:12px 24px;background:#4CAF50;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">Download Dashboard</a>
</div>'''

        return DashboardResponse(
            success=True,
            filename=fname,
            download_html=download_html,
            message=f"Created dashboard with {len(kpis)} KPIs and {len(charts)} charts",
            kpi_count=len(kpis),
            chart_count=len(charts)
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
