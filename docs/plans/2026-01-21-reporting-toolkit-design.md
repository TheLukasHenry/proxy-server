# Reporting Toolkit Design - Open WebUI Community Tools

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan after design approval.

**Date:** January 21, 2026
**Status:** Approved
**Owner:** Dev Team
**For:** Lukas

---

## Executive Summary

Lukas needs Open WebUI to output professional reports for executives:
- Excel files with working formulas (not just data dumps)
- Interactive charts and graphs
- Executive dashboards with KPIs
- PowerPoint presentations

**Solution:** Build a Reporting Toolkit - 2 new tools + 2 existing community tools.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REPORTING TOOLKIT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  NEW TOOLS (We Build):                                           │
│  ─────────────────────                                           │
│  1. Excel Creator Tool                                           │
│     ├── Creates .xlsx with formulas (=SUM, =AVERAGE, =IF)       │
│     ├── Multiple sheets, formatting, auto-column-width          │
│     └── Library: openpyxl                                        │
│                                                                  │
│  2. Executive Dashboard Tool                                     │
│     ├── Multi-chart HTML page with KPI cards                    │
│     ├── Bar, Pie, Line charts in one view                       │
│     └── Library: Plotly.js + custom HTML/CSS                    │
│                                                                  │
│  EXISTING TOOLS (Just Install):                                  │
│  ──────────────────────────────                                  │
│  3. Visualize Data R3 Function                                   │
│     └── URL: openwebui.com/f/saulcutter/visualize               │
│                                                                  │
│  4. Generate Presentations Tool                                  │
│     └── URL: openwebui.com/t/timbo989/generate_presentations    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool 1: Excel Creator (NEW)

### Purpose
Create Excel files with **working formulas** that executives can modify and recalculate.

### Why openpyxl (not pandas)?
| Library | Formula Support | Formatting | Verdict |
|---------|-----------------|------------|---------|
| pandas + xlsxwriter | Limited (static formulas) | Basic | ❌ |
| openpyxl | Full (dynamic formulas) | Advanced | ✅ |

### Capabilities

| Feature | Example |
|---------|---------|
| **Cell Formulas** | `=B2+C2`, `=SUM(B2:B10)`, `=AVERAGE(C:C)` |
| **Conditional Formulas** | `=IF(B2>100,"High","Low")` |
| **Lookup Formulas** | `=VLOOKUP(A2,Sheet2!A:B,2,FALSE)` |
| **Multiple Sheets** | "Summary", "Details", "Raw Data" |
| **Formatting** | Bold headers, currency format, percentages |
| **Auto-fit Columns** | Columns resize to fit content |
| **Freeze Panes** | Header row stays visible when scrolling |

### Input Format (JSON from LLM)

```json
{
  "filename": "Q1_Sales_Report",
  "sheets": [
    {
      "name": "Sales Summary",
      "headers": ["Product", "Jan", "Feb", "Mar", "Q1 Total"],
      "data": [
        ["Widget", 100, 120, 140, "=SUM(B2:D2)"],
        ["Gadget", 150, 140, 160, "=SUM(B3:D3)"],
        ["Gizmo", 200, 180, 220, "=SUM(B4:D4)"]
      ],
      "totals_row": ["TOTAL", "=SUM(B2:B4)", "=SUM(C2:C4)", "=SUM(D2:D4)", "=SUM(E2:E4)"],
      "format": {
        "currency_columns": ["B", "C", "D", "E"],
        "bold_headers": true,
        "freeze_row": 1
      }
    }
  ]
}
```

### Output
- Downloads `.xlsx` file to browser
- File has working formulas (user can edit values, formulas recalculate)

### Technical Implementation

```python
# Key libraries
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, PatternFill
from openpyxl.utils import get_column_letter

# Formula handling - openpyxl preserves formulas as-is
cell.value = "=SUM(B2:B10)"  # Stored as formula, not calculated value

# Formatting
cell.font = Font(bold=True)
cell.number_format = '$#,##0.00'  # Currency
cell.number_format = '0.00%'      # Percentage
```

---

## Tool 2: Executive Dashboard (NEW)

### Purpose
Generate a single HTML page with multiple charts and KPIs that executives love.

### Layout Design

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 EXECUTIVE DASHBOARD - Q1 2026                               │
│  Generated: 2026-01-21 14:30                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  KPI CARDS (Top Row):                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Revenue  │  │ Users    │  │ Growth   │  │ NPS      │        │
│  │ $1.2M    │  │ 45,000   │  │ +23%     │  │ 72       │        │
│  │ ▲ 15%    │  │ ▲ 8%     │  │ ▲ 5pts   │  │ ▲ 3pts   │        │
│  │ vs LY    │  │ vs LY    │  │ vs LY    │  │ vs LY    │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  CHARTS (Middle Row):                                            │
│  ┌─────────────────────────┐  ┌─────────────────────────┐      │
│  │  Revenue Trend          │  │  Sales by Region        │      │
│  │  (Line Chart)           │  │  (Pie Chart)            │      │
│  │       📈                │  │        🥧               │      │
│  └─────────────────────────┘  └─────────────────────────┘      │
│                                                                  │
│  COMPARISON (Bottom Row):                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Monthly Performance vs Target (Bar Chart)          │        │
│  │  ████████ Actual  ░░░░░░░░ Target                   │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                  │
│  [Download HTML] [Download PNG]                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Input Format (JSON from LLM)

```json
{
  "title": "Q1 2026 Executive Dashboard",
  "kpis": [
    {"label": "Revenue", "value": "$1.2M", "change": "+15%", "trend": "up"},
    {"label": "Users", "value": "45,000", "change": "+8%", "trend": "up"},
    {"label": "Growth", "value": "+23%", "change": "+5pts", "trend": "up"},
    {"label": "NPS", "value": "72", "change": "+3pts", "trend": "up"}
  ],
  "charts": [
    {
      "type": "line",
      "title": "Revenue Trend",
      "labels": ["Jan", "Feb", "Mar"],
      "datasets": [
        {"label": "2026", "data": [350000, 420000, 480000]},
        {"label": "2025", "data": [300000, 350000, 400000]}
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
      "title": "Monthly Performance vs Target",
      "labels": ["Jan", "Feb", "Mar"],
      "datasets": [
        {"label": "Actual", "data": [105, 98, 112]},
        {"label": "Target", "data": [100, 100, 100]}
      ]
    }
  ]
}
```

### Technical Implementation

```html
<!-- Plotly.js for interactive charts -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<!-- KPI Cards with CSS Grid -->
<div class="kpi-grid">
  <div class="kpi-card positive">
    <div class="kpi-label">Revenue</div>
    <div class="kpi-value">$1.2M</div>
    <div class="kpi-change">▲ 15% vs LY</div>
  </div>
  <!-- More cards... -->
</div>

<!-- Charts -->
<div class="chart-grid">
  <div id="chart1"></div>
  <div id="chart2"></div>
</div>

<script>
  Plotly.newPlot('chart1', data, layout);
</script>
```

### Output Options
1. **View in chat** - Rendered HTML in Open WebUI
2. **Download HTML** - Standalone file, works offline
3. **Download PNG** - Screenshot for emails/presentations

---

## Tool 3: Visualize Data R3 (EXISTING)

### Source
**URL:** https://openwebui.com/f/saulcutter/visualize

### What It Does
- Analyzes data in conversation
- Automatically selects chart type (bar, pie, line)
- Renders interactive Plotly.js chart in chat

### Installation
1. Go to Open WebUI → Admin → Functions
2. Click "Import from Community"
3. Search "Visualize Data R3"
4. Click Install

### Usage Example
```
User: "Show me a pie chart of our Q1 expenses:
       Marketing: $50,000
       Engineering: $120,000
       Sales: $80,000
       Operations: $40,000"

Bot: [Renders interactive pie chart]
```

---

## Tool 4: Generate Presentations (EXISTING)

### Source
**URL:** https://openwebui.com/t/timbo989/generate_presentations_from_template

### What It Does
- Creates PowerPoint .pptx files from templates
- Uses python-pptx library
- Replaces placeholders with content

### Installation
1. Go to Open WebUI → Admin → Tools
2. Click "Import from Community"
3. Search "Generate presentations"
4. Click Install
5. Upload PowerPoint template with placeholders

### Usage Example
```
User: "Create a Q1 presentation with:
       Title: Q1 2026 Results
       Subtitle: Record-breaking quarter
       Section 1: Revenue grew 23%
       Section 2: User base expanded to 45,000"

Bot: [Downloads Q1_presentation_2026-01-21.pptx]
```

---

## File Structure

```
open-webui-functions/
├── reporting/
│   ├── excel_creator.py           # NEW - Excel with formulas
│   ├── executive_dashboard.py     # NEW - Multi-chart dashboards
│   └── __init__.py
├── mcp_entra_token_auth.py        # Existing
└── README.md                       # Update with new tools

docs/
└── REPORTING-TOOLKIT-GUIDE.md     # User guide for Lukas
```

---

## Dependencies

### For Excel Creator
```python
# requirements.txt additions
openpyxl>=3.1.0
```

### For Executive Dashboard
```python
# No additional Python deps - uses Plotly.js via CDN
# HTML/CSS/JS generated inline
```

---

## Success Criteria

| Requirement | How We Meet It |
|-------------|----------------|
| Excel with formulas | openpyxl preserves `=SUM()`, `=IF()`, etc. |
| Charts/Graphs | Visualize Data R3 (existing) + Dashboard tool |
| Executive dashboards | Custom Dashboard tool with KPIs + multi-chart |
| PowerPoint | Generate Presentations (existing) |
| Easy to use | LLM understands natural language, outputs JSON |
| Downloads work | Base64 encoding triggers browser download |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| openpyxl not installed on Open WebUI | Add to Docker image or use pip install at runtime |
| Large Excel files slow | Limit to 10,000 rows, paginate if needed |
| Dashboard HTML too complex | Use tested Plotly.js patterns |
| LLM outputs bad JSON | Validate JSON, provide clear error messages |

---

## Next Steps

1. **Create implementation plan** using superpowers:writing-plans
2. **Build Excel Creator Tool** (~2 hours)
3. **Build Executive Dashboard Tool** (~2 hours)
4. **Install existing tools** (10 min)
5. **Test end-to-end** (1 hour)
6. **Document for Lukas** (30 min)

---

*Design approved: January 21, 2026*
