#!/usr/bin/env python3
"""
Flatten DeHashed results JSON into a single-sheet xlsx report.

Input format expected (from dehashed_query.py):
  {"balance": ..., "total": ..., "collected": ..., "query": ..., "entries": [...]}

Or a bare list of entry dicts (from a pruning subagent that emitted just the kept rows).

Behavior:
  - List-valued fields (email, username, password, etc.) are joined with ", "
    so the sheet reads flat.
  - Only columns that are populated in at least one row are included.
  - A "query" column is prepended if the input carried the original query string,
    so the xlsx is self-documenting for later reference.

Dependencies: openpyxl (install with `pip install openpyxl`).
"""
import argparse
import json
import sys
from pathlib import Path

from openpyxl import Workbook


STANDARD_COLUMN_ORDER = [
    "id",
    "email",
    "username",
    "password",
    "hashed_password",
    "hash_type",
    "name",
    "phone",
    "address",
    "dob",
    "ip_address",
    "url",
    "domain",
    "company",
    "social",
    "cryptocurrency_address",
    "license_plate",
    "vin",
    "database_name",
    "raw_record",
]


def load_entries(path: Path) -> tuple[list[dict], str | None]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict) and "entries" in data:
        return data["entries"], data.get("query")
    raise SystemExit(f"[!] Unrecognized input shape in {path}; expected a list or an object with 'entries'.")


def flatten_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None and v != "")
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def discover_columns(entries: list[dict]) -> list[str]:
    seen: set[str] = set()
    for entry in entries:
        for key, value in entry.items():
            if value in (None, "", [], {}):
                continue
            seen.add(key)
    ordered = [c for c in STANDARD_COLUMN_ORDER if c in seen]
    extras = sorted(seen - set(ordered))
    return ordered + extras


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert DeHashed results JSON to a flat xlsx.")
    parser.add_argument("--input", required=True, help="Path to results JSON (from dehashed_query.py or a pruning subagent).")
    parser.add_argument("--output", required=True, help="Path to write the xlsx.")
    parser.add_argument("--sheet-name", default="DeHashed", help="Worksheet name. Default: DeHashed.")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.is_file():
        raise SystemExit(f"[!] Input not found: {src}")

    entries, query = load_entries(src)
    if not entries:
        print("[!] No entries in input; nothing to write.", file=sys.stderr)
        return

    columns = discover_columns(entries)
    if query:
        columns = ["_query"] + columns

    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet_name[:31]
    ws.append(columns)

    for entry in entries:
        row = []
        for col in columns:
            if col == "_query":
                row.append(query or "")
            else:
                row.append(flatten_value(entry.get(col)))
        ws.append(row)

    for idx, col in enumerate(columns, start=1):
        letter = ws.cell(row=1, column=idx).column_letter
        sample_len = max((len(str(ws.cell(row=r, column=idx).value or "")) for r in range(1, min(ws.max_row, 50) + 1)), default=10)
        ws.column_dimensions[letter].width = min(max(sample_len + 2, 10), 60)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"[+] Wrote {len(entries)} rows × {len(columns)} columns to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
