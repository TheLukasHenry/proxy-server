# Reporting Toolkit Guide

**For:** Lukas and Open WebUI Users
**Version:** 1.1 (Updated)
**Date:** January 23, 2026

---

## Current Status - What's Actually Installed

| Tool | Version | Status | How to Use |
|------|---------|--------|------------|
| **Export to Excel** | v0.1.1 | ✅ Working | Action button on messages |
| **Visualize Data** | v0.2.1 | ✅ Working | Action button on messages |
| **Visualize Data R3** | v0.0.2r3 | ⚠️ Needs API | Action button (needs config) |

### Quick Explanation for Lukas

**What works RIGHT NOW (no setup needed):**
- **Export to Excel** - Click button → downloads .xlsx file
- **Visualize Data** - Click button → shows chart in chat

**What needs extra setup:**
- **Visualize Data R3** - Smarter AI-powered charts, but needs OpenAI API key

---

## Overview

The Reporting Toolkit gives Open WebUI the ability to create professional reports for executives:

| Tool | What It Does | Source |
|------|--------------|--------|
| **Export to Excel** | Extracts tables → downloads .xlsx file | Community (modified) |
| **Visualize Data** | Extracts tables → renders Plotly charts | Custom (we built) |
| **Visualize Data R3** | AI analyzes data → creates smart charts | Community |
| **Generate Presentations** | Creates PowerPoint .pptx files | Community (not installed) |

---

## Quick Start

### 1. Excel Files with Formulas

Just ask naturally:

```
"Create an Excel file with our Q1 sales data:
- Products: Widget ($100), Gadget ($150), Gizmo ($200)
- Add columns for January, February, March
- Add a Total column that sums the months
- Add a totals row at the bottom"
```

**Result:** Downloads an Excel file where the formulas actually work!

---

### 2. Executive Dashboards

```
"Create an executive dashboard for Q1 2026:
- KPIs: Revenue $1.2M (up 15%), Users 45K (up 8%), NPS 72 (up 3 points)
- Line chart showing revenue trend from Jan to April
- Pie chart showing sales by region (North 35%, South 25%, East 22%, West 18%)
- Bar chart comparing actual vs target by quarter"
```

**Result:** Beautiful interactive dashboard with download button!

---

### 3. Quick Charts

```
"Show me a pie chart of our expenses:
- Marketing: $50,000
- Engineering: $120,000
- Sales: $80,000
- Operations: $40,000"
```

**Result:** Interactive chart rendered right in chat!

---

### 4. PowerPoint Presentations

```
"Create a Q1 presentation with:
- Title: Q1 2026 Results
- Subtitle: Record-breaking quarter
- Bullet 1: Revenue grew 23%
- Bullet 2: User base expanded to 45,000
- Bullet 3: NPS improved to 72"
```

**Result:** Downloads .pptx file!

---

## Installation Guide

### Install Custom Tools (Excel Creator & Executive Dashboard)

1. **Go to:** Open WebUI → Admin Panel → Functions
2. **Click:** "Create New Function"
3. **Copy-paste** the code from:
   - `open-webui-functions/reporting/excel_creator.py`
   - `open-webui-functions/reporting/executive_dashboard.py`
4. **Save** each function

### Install Community Tools

#### Visualize Data R3 (Charts)

1. **Go to:** Open WebUI → Admin Panel → Functions
2. **Click:** "Import from Community"
3. **Search:** "Visualize Data R3"
4. **Click:** Install
5. **URL:** https://openwebui.com/f/saulcutter/visualize

#### Generate Presentations (PowerPoint)

1. **Go to:** Open WebUI → Admin Panel → Tools
2. **Click:** "Import from Community"
3. **Search:** "Generate presentations from template"
4. **Click:** Install
5. **URL:** https://openwebui.com/t/timbo989/generate_presentations_from_template

**Note:** PowerPoint tool requires a template file. Upload a .pptx template with placeholders like `{Title}`, `{Bullet 1}`, etc.

---

## Excel Creator - Detailed Guide

### Supported Formulas

| Formula | Example | Description |
|---------|---------|-------------|
| SUM | `=SUM(B2:B10)` | Add range of cells |
| AVERAGE | `=AVERAGE(C:C)` | Average of column |
| IF | `=IF(B2>100,"High","Low")` | Conditional logic |
| VLOOKUP | `=VLOOKUP(A2,Data!A:B,2,FALSE)` | Lookup from another sheet |
| COUNT | `=COUNT(B:B)` | Count numbers |
| MAX/MIN | `=MAX(B2:B10)` | Maximum value |
| Cell refs | `=B2+C2` | Add two cells |

### Formatting Options

| Format | Description |
|--------|-------------|
| Bold headers | First row is bold with gray background |
| Currency | Columns display as $1,234.56 |
| Percentage | Columns display as 12.34% |
| Auto-fit | Columns resize to fit content |
| Freeze panes | Header row stays visible when scrolling |

### Example: Budget Report

```
"Create a budget Excel file:

Sheet 1 - Summary:
| Department | Budget | Actual | Variance |
| Marketing | 50000 | 48000 | =B2-C2 |
| Engineering | 120000 | 125000 | =B3-C3 |
| Sales | 80000 | 82000 | =B4-C4 |
| TOTAL | =SUM(B2:B4) | =SUM(C2:C4) | =SUM(D2:D4) |

Format as currency, bold headers, freeze first row."
```

---

## Executive Dashboard - Detailed Guide

### KPI Cards

KPIs appear at the top with:
- Label (e.g., "Revenue")
- Value (e.g., "$1.2M")
- Change indicator (e.g., "+15%")
- Trend arrow (▲ green for up, ▼ red for down)

### Chart Types

| Type | Best For | Example |
|------|----------|---------|
| **Bar** | Comparisons | Actual vs Target |
| **Line** | Trends over time | Monthly revenue |
| **Pie** | Parts of whole | Sales by region |
| **Scatter** | Correlations | Price vs Sales |

### Example: Sales Dashboard

```
"Create a sales dashboard:

Title: Q1 2026 Sales Performance

KPIs:
- Total Sales: $2.4M (up 18%)
- New Customers: 1,250 (up 12%)
- Avg Deal Size: $15,000 (up 8%)
- Win Rate: 32% (up 4 points)

Charts:
1. Line chart: Monthly sales trend (Jan $700K, Feb $800K, Mar $900K)
2. Pie chart: Sales by product (Enterprise 45%, Pro 35%, Starter 20%)
3. Bar chart: Sales by rep (Alice 450K, Bob 380K, Charlie 520K, Diana 410K)"
```

---

## Tips for Best Results

### Be Specific with Numbers

```
Good: "Revenue: $1,234,567"
Bad: "Revenue: about a million"
```

### Specify Formula Columns

```
Good: "Column D should have formula =B+C"
Bad: "Add a total column"
```

### Name Your Sheets

```
Good: "Sheet 1: Summary, Sheet 2: Details"
Bad: "Put everything in Excel"
```

### Include Trend Direction

```
Good: "Revenue $1.2M, up 15% vs last year"
Bad: "Revenue $1.2M, 15%"
```

---

## Troubleshooting

### Excel Won't Download

1. Check if pop-ups are blocked
2. Try a different browser
3. Check console for JavaScript errors

### Charts Not Rendering

1. Check internet connection (Plotly.js loads from CDN)
2. Try refreshing the page
3. Check if chart data is numeric

### Formulas Show as Text

Make sure formulas start with `=`:
- Correct: `=SUM(B2:B10)`
- Wrong: `SUM(B2:B10)`

---

## File Locations

```
open-webui-functions/
├── reporting/
│   ├── __init__.py
│   ├── excel_creator.py        # Excel with formulas
│   └── executive_dashboard.py  # Interactive dashboards
└── mcp_entra_token_auth.py     # Existing auth function

docs/
├── REPORTING-TOOLKIT-GUIDE.md  # This file
└── plans/
    ├── 2026-01-21-reporting-toolkit-design.md
    └── 2026-01-21-reporting-toolkit-implementation.md
```

---

## Requirements

### Python Libraries

```python
# For Excel Creator
openpyxl>=3.1.0

# For Executive Dashboard
# No additional deps - uses Plotly.js via CDN
```

### Add to Dockerfile if needed:

```dockerfile
RUN pip install openpyxl
```

---

## Community Tool Links

| Tool | URL | Downloads |
|------|-----|-----------|
| Visualize Data R3 | https://openwebui.com/f/saulcutter/visualize | 16K+ |
| Export to Excel | https://openwebui.com/f/brunthas/export_to_excel | 500+ |
| Generate Presentations | https://openwebui.com/t/timbo989/generate_presentations_from_template | - |
| FileWriter | https://openwebui.com/t/leocpx4000/filewriter | 500+ |

---

## Summary

| Need | Solution | Status |
|------|----------|--------|
| Excel with formulas | Excel Creator (custom) | ✅ Built |
| Interactive charts | Visualize Data R3 (community) | ✅ Install |
| Executive dashboards | Executive Dashboard (custom) | ✅ Built |
| PowerPoint | Generate Presentations (community) | ✅ Install |

**Lukas can now tell executives:** "Yes, we can generate Excel reports with real formulas and beautiful dashboards automatically!"

---

*Guide created: January 21, 2026*
