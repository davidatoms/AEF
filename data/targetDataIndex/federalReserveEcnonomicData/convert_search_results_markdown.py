#!/usr/bin/env python3
"""Convert search_results/*.txt files to Markdown summaries."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List


def parse_search_result_file(file_path: Path) -> Dict[str, object]:
    """Parse a single search result .txt file into structured data."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    if not lines:
        return {"query": file_path.stem, "results": []}

    query = file_path.stem
    for line in lines[:10]:
        if line.startswith("Query: "):
            query = line.replace("Query: ", "").strip()
            break

    results: List[Dict[str, str]] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line or line.startswith(("FRED Series", "Query:", "Timestamp:", "Total Results:")):
            i += 1
            continue

        match = re.match(r"\d+\. ([A-Z0-9]+) - (.+)", line)
        if match:
            series_id = match.group(1).strip()
            title = match.group(2).strip()

            metadata = {
                "frequency": "",
                "units": "",
                "last_updated": "",
                "notes": "",
            }

            j = i + 1
            notes_lines = []

            while j < len(lines):
                next_line = lines[j].strip()

                if not next_line:
                    if j + 1 < len(lines) and re.match(r"\d+\.", lines[j + 1].strip()):
                        break
                    j += 1
                    continue

                if re.match(r"\d+\.", next_line):
                    break

                if next_line.startswith("Units: "):
                    metadata["units"] = next_line.replace("Units: ", "").strip()
                elif next_line.startswith("Frequency: "):
                    metadata["frequency"] = next_line.replace("Frequency: ", "").strip()
                elif next_line.startswith("Last Updated: "):
                    metadata["last_updated"] = next_line.replace("Last Updated: ", "").strip()
                elif next_line.startswith("Notes: "):
                    note_text = next_line.replace("Notes: ", "").strip()
                    if note_text != "No description available":
                        notes_lines.append(note_text)
                else:
                    if notes_lines or (j > i + 1 and "Notes:" in lines[j - 1]):
                        notes_lines.append(next_line)

                j += 1

            if notes_lines:
                metadata["notes"] = " ".join(notes_lines).strip()

            results.append(
                {
                    "series_id": series_id,
                    "title": title,
                    **metadata,
                }
            )

            i = j
            continue

        i += 1

    return {
        "query": query,
        "result_count": len(results),
        "results": results,
    }


def _escape_markdown(text: str) -> str:
    """Escape pipe characters so Markdown tables render correctly."""
    return text.replace("|", "\\|")


def _render_query_markdown(query: str, data: Dict[str, object]) -> str:
    """Render a single query's data to Markdown."""
    lines = []
    lines.append(f"## {query}")
    lines.append(f"Total results: {data['result_count']}")
    lines.append("")

    if not data["results"]:
        lines.append("_No series found._")
        lines.append("")
        return "\n".join(lines)

    lines.append("| ID | Title | Frequency | Units | Last Updated | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- |")

    for item in data["results"]:
        series_id = _escape_markdown(item.get("series_id", ""))
        title = _escape_markdown(item.get("title", ""))
        frequency = _escape_markdown(item.get("frequency", ""))
        units = _escape_markdown(item.get("units", ""))
        last_updated = _escape_markdown(item.get("last_updated", ""))
        notes = _escape_markdown(item.get("notes", "") or "")

        lines.append(
            f"| {series_id} | {title} | {frequency} | {units} | {last_updated} | {notes} |"
        )

    lines.append("")
    return "\n".join(lines)


def convert_all_search_results(
    input_dir: Path,
    output_file: Path,
    individual_markdown: bool = False,
) -> None:
    """Convert all .txt files in input_dir to Markdown."""
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        return

    txt_files = sorted(input_dir.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    consolidated_sections = ["# FRED Search Results"]
    all_data = {}

    for txt_file in txt_files:
        print(f"Processing {txt_file.name}...")
        data = parse_search_result_file(txt_file)
        query = data["query"]
        all_data[query] = data
        consolidated_sections.append(_render_query_markdown(query, data))

        if individual_markdown:
            md_file = txt_file.with_suffix(".md")
            md_content = "\n".join(
                [
                    f"# FRED Search Results: {query}",
                    "",
                    _render_query_markdown(query, data),
                ]
            )
            md_file.write_text(md_content, encoding="utf-8")
            print(f"  → Created {md_file.name}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(consolidated_sections), encoding="utf-8")

    print(f"\nConsolidated markdown written to {output_file}")
    print(f"Total queries: {len(all_data)}")
    print(f"Total series: {sum(len(d['results']) for d in all_data.values())}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert search_results/*.txt files to Markdown summaries"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).parent / "search_results",
        help="Directory containing .txt files (default: ./search_results)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "search_results_consolidated.md",
        help="Output path for consolidated Markdown (default: ./search_results_consolidated.md)",
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="Also create individual Markdown files alongside each .txt file",
    )

    args = parser.parse_args()

    convert_all_search_results(
        input_dir=args.input_dir,
        output_file=args.output,
        individual_markdown=args.individual,
    )


if __name__ == "__main__":
    main()
