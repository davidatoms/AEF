#!/usr/bin/env python3
"""Convert search_results/*.txt files to structured JSON format."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


def parse_search_result_file(file_path: Path) -> Dict[str, object]:
    """Parse a single search result .txt file into structured data.

    Args:
        file_path: Path to the .txt file

    Returns:
        Dictionary with query and results list
    """
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    if not lines:
        return {"query": file_path.stem, "results": []}

    # Extract query from "Query: X" line
    query = file_path.stem  # default fallback
    for line in lines[:10]:  # check first few lines
        if line.startswith("Query: "):
            query = line.replace("Query: ", "").strip()
            break

    results: List[Dict[str, str]] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and headers
        if not line or line.startswith(("FRED Series", "Query:", "Timestamp:", "Total Results:")):
            i += 1
            continue

        # Parse series line: "1. SERIES_ID - Title"
        match = re.match(r"\d+\. ([A-Z0-9]+) - (.+)", line)
        if match:
            series_id = match.group(1).strip()
            title = match.group(2).strip()

            # Parse metadata from following lines
            metadata = {
                "frequency": "",
                "units": "",
                "last_updated": "",
                "notes": ""
            }
            
            # Look ahead for metadata lines
            j = i + 1
            notes_lines = []
            
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Stop if we hit the next series or empty line followed by number
                if not next_line:
                    if j + 1 < len(lines) and re.match(r"\d+\.", lines[j + 1].strip()):
                        break
                    j += 1
                    continue
                
                if re.match(r"\d+\.", next_line):
                    break
                    
                # Parse specific metadata lines
                if next_line.startswith("Units: "):
                    metadata["units"] = next_line.replace("Units: ", "").strip()
                elif next_line.startswith("Frequency: "):
                    metadata["frequency"] = next_line.replace("Frequency: ", "").strip()
                elif next_line.startswith("Last Updated: "):
                    metadata["last_updated"] = next_line.replace("Last Updated: ", "").strip()
                elif next_line.startswith("Notes: "):
                    # Start collecting notes
                    note_text = next_line.replace("Notes: ", "").strip()
                    if note_text != "No description available":
                        notes_lines.append(note_text)
                else:
                    # Continue collecting notes if we're in notes section
                    if notes_lines or (j > i + 1 and "Notes:" in lines[j-1]):
                        notes_lines.append(next_line)
                
                j += 1
            
            # Join notes
            if notes_lines:
                metadata["notes"] = " ".join(notes_lines).strip()

            results.append({
                "series_id": series_id,
                "title": title,
                **metadata,
            })

            i = j  # Skip to next series
            continue

        i += 1

    return {
        "query": query,
        "result_count": len(results),
        "results": results,
    }


def convert_all_search_results(
    input_dir: Path,
    output_file: Path,
    individual_json: bool = False,
) -> None:
    """Convert all .txt files in input_dir to JSON.

    Args:
        input_dir: Directory containing .txt search result files
        output_file: Path for consolidated JSON output
        individual_json: If True, also create individual JSON files for each query
    """
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        return

    txt_files = sorted(input_dir.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    all_data = {}

    for txt_file in txt_files:
        print(f"Processing {txt_file.name}...")
        data = parse_search_result_file(txt_file)
        query = data["query"]
        all_data[query] = data

        # Optionally save individual JSON files
        if individual_json:
            json_file = txt_file.with_suffix(".json")
            json_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  → Created {json_file.name}")

    # Save consolidated JSON
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(all_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nConsolidated data written to {output_file}")
    print(f"Total queries: {len(all_data)}")
    print(f"Total series: {sum(len(d['results']) for d in all_data.values())}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert search_results/*.txt to structured JSON"
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
        default=Path(__file__).parent / "search_results_consolidated.json",
        help="Output path for consolidated JSON (default: ./search_results_consolidated.json)",
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="Also create individual JSON files alongside each .txt file",
    )

    args = parser.parse_args()

    convert_all_search_results(
        input_dir=args.input_dir,
        output_file=args.output,
        individual_json=args.individual,
    )


if __name__ == "__main__":
    main()
