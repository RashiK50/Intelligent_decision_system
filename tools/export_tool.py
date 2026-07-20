"""Export Tool — writes result rows to a downloadable file (CSV, optionally Excel).

Returns the file path and metadata; serving/downloading is the API layer's
concern. Excel export activates automatically when openpyxl is installed.
"""

import csv
import os
import re
from datetime import datetime
from typing import Any, Dict

from tools.common import ToolContext, clean_rows

EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")


def _safe_slug(text: str, default: str = "report") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip())[:40].strip("_").lower()
    return slug or default


def export_results(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    if not rows:
        return {"status": "error", "error": "No data rows available to export."}

    requested = str(context.entities.get("export_format", "csv")).lower()
    os.makedirs(EXPORT_DIR, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{_safe_slug(context.user_query)}_{stamp}"
    columns = list(rows[0].keys())

    if requested in ("xlsx", "excel"):
        try:
            from openpyxl import Workbook

            path = os.path.join(EXPORT_DIR, f"{base}.xlsx")
            wb = Workbook()
            ws = wb.active
            ws.title = "Results"
            ws.append(columns)
            for r in rows:
                ws.append([str(r.get(c, "")) for c in columns])
            wb.save(path)
            return {"status": "success", "format": "xlsx", "path": path, "rows": len(rows), "columns": columns}
        except ImportError:
            requested = "csv"  # graceful fallback when openpyxl is absent

    path = os.path.join(EXPORT_DIR, f"{base}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})

    return {"status": "success", "format": "csv", "path": path, "rows": len(rows), "columns": columns}
