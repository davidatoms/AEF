#!/usr/bin/env python3
"""
Generate target-alignment notes for FRED series using an Ollama model.

Reads the consolidated FRED metadata in
`data/targetDataIndex/federalReserveEcnonomicData/ollama_pickup/target_columns.csv`,
queries an Ollama LLM for each row, and writes the augmented CSV back to disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm
import subprocess

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = (
    BASE_DIR
    / "targetDataIndex"
    / "federalReserveEcnonomicData"
    / "ollama_pickup"
    / "target_columns.csv"
)

DEFAULT_OUTPUT = BASE_DIR / "aiThroughPut2" / "target_columns_with_notes.csv"
DEFAULT_MODEL = "llama3.2"
DEFAULT_COLUMNS = ["recommendedFredSeries", "reasonsForRecommendation"]
DEFAULT_INSTRUCTION = (
    "Provide thoughtful, well-structured values for each requested field so analysts "
    "can compare workforce task demand against macroeconomic indicators."
)


def load_instruction(arg_instruction: str | None, prompt_path: Path | None) -> str:
    if prompt_path:
        try:
            return prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise SystemExit(f"Failed to read prompt file {prompt_path}: {exc}") from exc

    instruction = (arg_instruction or "").strip()
    return instruction if instruction else DEFAULT_INSTRUCTION


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value)
    return text.strip()


def build_prompt(row: pd.Series, column_names: list[str], instruction: str) -> str:
    details = []
    for field in ["query", "series_id", "title", "frequency", "units", "last_updated"]:
        value = normalize_cell(row.get(field))
        if value:
            details.append(f"- {field}: {value}")

    notes = normalize_cell(row.get("notes"))
    if notes:
        details.append(f"- notes: {notes}")

    details_block = "\n".join(details) if details else "- No additional metadata supplied."

    columns_block = "\n".join(f'- "{name}"' for name in column_names)
    json_example = ", ".join(f'"{name}": "..."' for name in column_names)

    return f"""You are assisting with economic labor analytics.

We maintain a crosswalk between job tasks and FRED economic indicators.

Series metadata:
{details_block}

Instruction: {instruction}

Requested output fields:
{columns_block}

Respond ONLY with valid JSON of the form:
{{{json_example}}}
"""


def query_ollama(prompt: str, model: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": "TIMEOUT"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": f"UNEXPECTED_ERROR: {exc}"}

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return {"error": f"OLLAMA_ERROR: {stderr}"}

    response_text = (result.stdout or "").strip()
    start = response_text.find("{")
    end = response_text.rfind("}") + 1
    if start == -1 or end <= start:
        return {"error": f"PARSE_ERROR: {response_text}"}

    try:
        return json.loads(response_text[start:end])
    except json.JSONDecodeError as exc:
        return {"error": f"JSON_ERROR: {exc}: {response_text}"}


def process_dataframe(
    df: pd.DataFrame,
    column_names: list[str],
    instruction: str,
    model: str,
    limit: int | None,
    overwrite: bool,
) -> pd.DataFrame:
    for name in column_names:
        if name not in df.columns:
            df[name] = ""

    rows = df.head(limit) if limit else df

    for idx, row in tqdm(rows.iterrows(), total=len(rows), desc="Querying Ollama"):
        existing_values = [normalize_cell(row.get(col)) for col in column_names]
        if not overwrite and all(existing_values):
            continue

        prompt = build_prompt(row, column_names, instruction)
        response = query_ollama(prompt, model=model)

        if "error" in response:
            for name in column_names:
                df.at[idx, name] = response["error"]
            continue

        for name in column_names:
            value = response.get(name)
            if isinstance(value, str) and value.strip():
                df.at[idx, name] = value.strip()
            else:
                df.at[idx, name] = f"PARSE_ERROR: {response}"

    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Augment FRED target columns with Ollama-generated notes."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input CSV path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--column",
        help=(
            "Populate a single column (overrides default list; ignored if --columns is set). "
            f"Default columns: {', '.join(DEFAULT_COLUMNS)}."
        ),
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        help="Populate all listed columns from a single Ollama response (overrides --column).",
    )
    parser.add_argument(
        "--instruction",
        help="Custom instruction text for the model (overrides default).",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a text file containing the instruction payload.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of rows processed (for testing).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-query rows where the target column already has content.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruction = load_instruction(args.instruction, args.prompt_file)

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    try:
        df = pd.read_csv(args.input)
    except Exception as exc:
        raise SystemExit(f"Failed to read {args.input}: {exc}") from exc

    if args.columns:
        column_names = args.columns
    elif args.column:
        column_names = [args.column]
    else:
        column_names = list(DEFAULT_COLUMNS)

    processed_df = process_dataframe(
        df=df,
        column_names=column_names,
        instruction=instruction,
        model=args.model,
        limit=args.limit,
        overwrite=args.overwrite,
    )

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        processed_df.to_csv(output_path, index=False)
    except Exception as exc:
        raise SystemExit(f"Failed to write {output_path}: {exc}") from exc

    print(f"Wrote {len(processed_df)} rows to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
