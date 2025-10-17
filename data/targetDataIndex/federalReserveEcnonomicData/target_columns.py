"""Create a flattened CSV of FRED search results for downstream Ollama analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
CONSOLIDATED_RESULTS = BASE_DIR / "search_results_consolidated.json"
RAW_RESULTS_DIR = BASE_DIR / "search_results"
OUTPUT_DIR = BASE_DIR / "ollama_pickup"
OUTPUT_PATH = OUTPUT_DIR / "target_columns.csv"


def load_search_results() -> dict:
    """Load consolidated search results; fallback to individual JSON files."""
    if CONSOLIDATED_RESULTS.exists():
        return json.loads(CONSOLIDATED_RESULTS.read_text(encoding="utf-8"))

    data = {}

    if RAW_RESULTS_DIR.exists():
        for json_file in sorted(RAW_RESULTS_DIR.glob("*.json")):
            content = json.loads(json_file.read_text(encoding="utf-8"))
            query_key = content.get("query") or json_file.stem

            # Ensure a consistent list of result dictionaries.
            results = content.get("results")
            if not results:
                series_entries = content.get("series", [])
                results = [
                    {
                        "series_id": entry.get("series_id") or entry.get("id"),
                        "title": entry.get("title", ""),
                        "frequency": entry.get("frequency", ""),
                        "units": entry.get("units", ""),
                        "last_updated": entry.get("last_updated", ""),
                        "notes": entry.get("notes", ""),
                    }
                    for entry in series_entries
                    if entry
                ]

            data[query_key] = {
                "query": query_key,
                "results": results or [],
            }

    if data:
        return data

    raise FileNotFoundError(
        "No search results found. Expected "
        f"{CONSOLIDATED_RESULTS} or JSON files in {RAW_RESULTS_DIR}."
    )


def build_dataframe(search_data: dict) -> pd.DataFrame:
    """Flatten search result records into a DataFrame."""
    records = []

    for query, payload in search_data.items():
        query_name = payload.get("query", query)
        for result in payload.get("results", []) or []:
            series_id = result.get("series_id") or result.get("id")
            title = result.get("title", "").strip()
            if not series_id and not title:
                continue

            notes = (result.get("notes") or "").strip()
            record = {
                "task_name": f"FRED series {series_id}: {title}".strip()
                if series_id
                else title,
                "query": query_name,
                "series_id": series_id or "",
                "title": title,
                "frequency": (result.get("frequency") or "").strip(),
                "units": (result.get("units") or "").strip(),
                "last_updated": (result.get("last_updated") or "").strip(),
                "notes": notes,
            }
            records.append(record)

    df = pd.DataFrame.from_records(records)
    if not df.empty:
        # Ensure a consistent column order for downstream tooling.
        df = df[
            [
                "task_name",
                "query",
                "series_id",
                "title",
                "frequency",
                "units",
                "last_updated",
                "notes",
            ]
        ]
    return df


def main() -> None:
    search_data = load_search_results()
    df = build_dataframe(search_data)

    if df.empty:
        raise ValueError("No search result records to write to CSV.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
