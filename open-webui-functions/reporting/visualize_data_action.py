"""
title: Visualize Data
author: MCP Team
description: Extract data from the last assistant message and render interactive charts in the chat using Plotly.js
version: 0.2.1
requirements: pandas
"""

import re
import json
import random
from typing import Optional, Callable, Awaitable, Any


class Action:
    """
    Visualize Data Action for Open WebUI

    This action extracts markdown tables from the assistant's last message
    and renders them as interactive Plotly.js charts directly in the chat.

    Supports:
    - Bar charts (default for categorical data)
    - Line charts (for time-series data)
    - Pie charts (for percentage/proportion data)
    """

    class UserValves:
        def __init__(self, show_status=True, default_chart_type="bar"):
            self.show_status = show_status
            self.default_chart_type = default_chart_type

    def __init__(self):
        pass

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """
        Extract tables from the last assistant message and render as interactive charts.
        """
        user_valves = __user__.get("valves") if __user__ else None
        if not user_valves:
            user_valves = self.UserValves()

        if __event_emitter__:
            last_assistant_message = body["messages"][-1]

            if user_valves.show_status:
                await __event_emitter__(
                    {"type": "status", "data": {"description": "Analyzing data...", "done": False}}
                )

            try:
                message_content = last_assistant_message["content"]
                tables = self.extract_tables_from_message(message_content)

                if not tables:
                    if user_valves.show_status:
                        await __event_emitter__(
                            {"type": "status", "data": {"description": "No tables found", "done": True}}
                        )
                    return {"message": "No tables found in message"}

                # Generate chart JavaScript for each table and execute it
                if __event_call__:
                    for i, table in enumerate(tables):
                        chart_js = self.generate_chart_js(table, i, user_valves.default_chart_type)
                        await __event_call__(
                            {
                                "type": "execute",
                                "data": {"code": chart_js}
                            }
                        )

                if user_valves.show_status:
                    await __event_emitter__(
                        {"type": "status", "data": {"description": f"Created {len(tables)} chart(s)", "done": True}}
                    )

                return {"message": f"Visualized {len(tables)} table(s)"}

            except Exception as e:
                if user_valves.show_status:
                    await __event_emitter__(
                        {"type": "status", "data": {"description": f"Error: {str(e)}", "done": True}}
                    )
                return {"message": f"Error: {str(e)}"}

    def extract_tables_from_message(self, message: str) -> list:
        """Extract markdown tables from message content."""
        rows = message.split("\n")
        tables = []
        current_table = []

        for row in rows:
            if "|" in row:
                # Split by | and filter out empty cells from leading/trailing pipes
                cells = [cell.strip() for cell in row.split("|")]
                # Remove empty strings from the list (from leading/trailing |)
                cells = [cell for cell in cells if cell]

                # Skip separator rows (----, :---:, etc.)
                if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    continue

                # Only add rows that have content
                if cells:
                    current_table.append(cells)
            elif current_table:
                # End of table - validate and add
                if len(current_table) >= 2:  # Need at least header + 1 data row
                    tables.append(current_table)
                current_table = []

        # Don't forget the last table if message doesn't end with empty line
        if current_table and len(current_table) >= 2:
            tables.append(current_table)

        return tables

    def generate_chart_js(self, table: list, chart_index: int, default_type: str = "bar") -> str:
        """Generate JavaScript code to inject a Plotly.js chart into the DOM."""
        if not table or len(table) < 2:
            return ""

        headers = table[0]
        data_rows = table[1:]

        # Determine chart type based on data
        chart_type = self.detect_chart_type(headers, data_rows, default_type)

        # Extract labels and data
        labels = [row[0] for row in data_rows if row]

        # Build datasets for each numeric column
        datasets = []
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

        for col_idx in range(1, len(headers)):
            col_data = []
            for row in data_rows:
                if col_idx < len(row):
                    val = row[col_idx]
                    # Try to convert to number
                    try:
                        # Remove currency symbols and commas
                        clean_val = re.sub(r'[$,€£%]', '', str(val))
                        col_data.append(float(clean_val))
                    except ValueError:
                        col_data.append(0)
                else:
                    col_data.append(0)

            datasets.append({
                "label": headers[col_idx] if col_idx < len(headers) else f"Series {col_idx}",
                "data": col_data,
                "color": colors[(col_idx - 1) % len(colors)]
            })

        # Generate unique chart ID
        chart_id = f"chart_{chart_index}_{random.randint(100000, 999999)}"

        # Build Plotly traces based on chart type
        if chart_type == "pie":
            traces = [{
                "labels": labels,
                "values": datasets[0]['data'] if datasets else [],
                "type": "pie",
                "hole": 0.4,
                "marker": {"colors": colors[:len(labels)]},
                "textinfo": "label+percent"
            }]
        elif chart_type == "line":
            traces = []
            for ds in datasets:
                traces.append({
                    "x": labels,
                    "y": ds['data'],
                    "name": ds['label'],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": ds['color'], "width": 3},
                    "marker": {"size": 8}
                })
        else:  # bar
            traces = []
            for ds in datasets:
                traces.append({
                    "x": labels,
                    "y": ds['data'],
                    "name": ds['label'],
                    "type": "bar",
                    "marker": {"color": ds['color']}
                })

        # Title from first header
        title = headers[0] if headers else "Data Visualization"

        # Convert traces to JSON
        traces_json = json.dumps(traces)

        layout = {
            "title": {"text": title, "font": {"size": 18}},
            "barmode": "group",
            "margin": {"t": 50, "r": 30, "b": 60, "l": 60},
            "legend": {"orientation": "h", "y": -0.15},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "xaxis": {"showgrid": True, "gridcolor": "#e5e7eb"},
            "yaxis": {"showgrid": True, "gridcolor": "#e5e7eb"}
        }
        layout_json = json.dumps(layout)

        # JavaScript to inject the chart
        js_code = f'''
(function() {{
    // Create chart container
    var container = document.createElement('div');
    container.style.cssText = 'background: #1e293b; border-radius: 12px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.3);';

    var chartDiv = document.createElement('div');
    chartDiv.id = '{chart_id}';
    chartDiv.style.cssText = 'width: 100%; height: 400px;';
    container.appendChild(chartDiv);

    // Find the chat messages area and append chart
    var messagesArea = document.querySelector('[aria-label="Chat Conversation"]');
    var inserted = false;
    if (messagesArea) {{
        var lastMessage = messagesArea.querySelector('li:last-child');
        if (lastMessage) {{
            lastMessage.appendChild(container);
            inserted = true;
        }}
    }}

    // Fallback: append to body if chat area not found
    if (!inserted) {{
        document.body.appendChild(container);
    }}

    // Load Plotly if not already loaded
    function renderChart() {{
        // Wait for DOM to update before rendering
        requestAnimationFrame(function() {{
            setTimeout(function() {{
                var targetDiv = document.getElementById('{chart_id}');
                if (targetDiv) {{
                    var data = {traces_json};
                    var layout = {layout_json};
                    layout.paper_bgcolor = '#1e293b';
                    layout.plot_bgcolor = '#1e293b';
                    layout.font = {{ color: '#e5e7eb' }};
                    layout.xaxis.gridcolor = '#374151';
                    layout.yaxis.gridcolor = '#374151';
                    var config = {{ responsive: true, displayModeBar: true }};
                    Plotly.newPlot('{chart_id}', data, layout, config);
                }} else {{
                    console.error('Chart div not found: {chart_id}');
                }}
            }}, 100);
        }});
    }}

    if (typeof Plotly === 'undefined') {{
        var script = document.createElement('script');
        script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
        script.onload = renderChart;
        document.head.appendChild(script);
    }} else {{
        renderChart();
    }}
}})();
'''
        return js_code

    def detect_chart_type(self, headers: list, data_rows: list, default: str) -> str:
        """Detect the best chart type based on data characteristics."""
        if not headers or not data_rows:
            return default

        # Check for time-series indicators
        first_col_lower = headers[0].lower() if headers else ""
        if any(term in first_col_lower for term in ['date', 'time', 'month', 'year', 'quarter', 'week', 'day']):
            return "line"

        # Check for percentage/proportion data
        if len(headers) == 2:  # Two columns often indicates pie chart data
            second_col = headers[1].lower() if len(headers) > 1 else ""
            if any(term in second_col for term in ['percent', '%', 'share', 'portion', 'proportion']):
                return "pie"

        # Check first column values for time patterns
        if data_rows:
            first_vals = [row[0].lower() if row else "" for row in data_rows[:3]]
            time_patterns = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                           'q1', 'q2', 'q3', 'q4', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            if any(any(pattern in val for pattern in time_patterns) for val in first_vals):
                return "line"

        return default
