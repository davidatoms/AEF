#!/usr/bin/env python3
"""
Analyze task descriptions using Ollama to extract role, goal, and location/context
"""

import pandas as pd
import json
import subprocess
from tqdm import tqdm
import sys

def query_ollama(task_description, model="llama3.2"):
    """
    Query Ollama to analyze a task description

    Args:
        task_description: The task description to analyze
        model: The Ollama model to use (default: llama3.2)

    Returns:
        dict with role, goal, and location keys
    """
    prompt = f"""Analyze this task description and extract the following information in JSON format:

Task: "{task_description}"

Please provide:
1. "role": What job role or occupation is performing this task?
2. "goal": What is the person trying to accomplish?
3. "location": Where or in what context is this task being performed (e.g., office, hospital, school, factory, etc.)?
4. "company_level": What level in the organizational hierarchy is this role (e.g., entry-level, mid-level, senior, executive, specialist, etc.)?
5. "fred_category": Which FRED (Federal Reserve Economic Data) economic category would this role fall under? Choose from: Agriculture, Mining, Construction, Manufacturing, Wholesale Trade, Retail Trade, Transportation, Utilities, Information, Financial Activities, Professional Services, Education and Health Services, Leisure and Hospitality, Other Services, Government, or Other.
6. "user_intent": Write a single clear sentence describing what the user was trying to accomplish with this task.
7. "difficulty": Rate the difficulty level of this task. Choose from: Very Easy, Easy, Moderate, Hard, Very Hard, Expert.

Respond ONLY with valid JSON in this exact format:
{{"role": "...", "goal": "...", "location": "...", "company_level": "...", "fred_category": "...", "user_intent": "...", "difficulty": "..."}}"""

    try:
        # Call Ollama via subprocess
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"Error calling Ollama: {result.stderr}", file=sys.stderr)
            return {"role": "ERROR", "goal": "ERROR", "location": "ERROR", "company_level": "ERROR", "fred_category": "ERROR", "user_intent": "ERROR", "difficulty": "ERROR"}

        # Parse the JSON response
        response_text = result.stdout.strip()

        # Try to find JSON in the response
        # Sometimes the model adds extra text, so we look for the JSON object
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            return parsed
        else:
            print(f"Could not find JSON in response: {response_text}", file=sys.stderr)
            return {"role": "PARSE_ERROR", "goal": "PARSE_ERROR", "location": "PARSE_ERROR", "company_level": "PARSE_ERROR", "fred_category": "PARSE_ERROR", "user_intent": "PARSE_ERROR", "difficulty": "PARSE_ERROR"}

    except subprocess.TimeoutExpired:
        print(f"Timeout querying Ollama for task: {task_description[:50]}...", file=sys.stderr)
        return {"role": "TIMEOUT", "goal": "TIMEOUT", "location": "TIMEOUT", "company_level": "TIMEOUT", "fred_category": "TIMEOUT", "user_intent": "TIMEOUT", "difficulty": "TIMEOUT"}
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        print(f"Response was: {response_text}", file=sys.stderr)
        return {"role": "JSON_ERROR", "goal": "JSON_ERROR", "location": "JSON_ERROR", "company_level": "JSON_ERROR", "fred_category": "JSON_ERROR", "user_intent": "JSON_ERROR", "difficulty": "JSON_ERROR"}
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return {"role": "ERROR", "goal": "ERROR", "location": "ERROR", "company_level": "ERROR", "fred_category": "ERROR", "user_intent": "ERROR", "difficulty": "ERROR"}


def process_csv_file(input_file, output_file, model="llama3.2", limit=None):
    """
    Process a CSV file with task descriptions

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        model: Ollama model to use
        limit: Optional limit on number of rows to process (for testing)
    """
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)

    if limit:
        df = df.head(limit)
        print(f"Processing first {limit} rows only")

    print(f"Total tasks to process: {len(df)}")

    # Initialize new columns
    df['role'] = ''
    df['goal'] = ''
    df['location'] = ''
    df['company_level'] = ''
    df['fred_category'] = ''
    df['user_intent'] = ''
    df['difficulty'] = ''

    # Process each task
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing tasks"):
        task_name = row['task_name']

        # Query Ollama
        result = query_ollama(task_name, model=model)

        # Store results
        df.at[idx, 'role'] = result.get('role', 'ERROR')
        df.at[idx, 'goal'] = result.get('goal', 'ERROR')
        df.at[idx, 'location'] = result.get('location', 'ERROR')
        df.at[idx, 'company_level'] = result.get('company_level', 'ERROR')
        df.at[idx, 'fred_category'] = result.get('fred_category', 'ERROR')
        df.at[idx, 'user_intent'] = result.get('user_intent', 'ERROR')
        df.at[idx, 'difficulty'] = result.get('difficulty', 'ERROR')

        # Save intermediate results every 10 rows
        if (idx + 1) % 10 == 0:
            df.to_csv(output_file, index=False)

    # Final save
    print(f"\nSaving results to {output_file}...")
    df.to_csv(output_file, index=False)
    print("Done!")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze task descriptions using Ollama')
    parser.add_argument('--model', default='llama3.2', help='Ollama model to use')
    parser.add_argument('--limit', type=int, help='Limit number of rows to process (for testing)')
    parser.add_argument('--v1', action='store_true', help='Process task_names_v1.csv')
    parser.add_argument('--v2', action='store_true', help='Process task_names_v2.csv')
    parser.add_argument('--both', action='store_true', help='Process both v1 and v2')

    args = parser.parse_args()

    if args.both or args.v1:
        print("\n" + "="*60)
        print("Processing task_names_v1.csv")
        print("="*60)
        process_csv_file(
            'task_names_v1.csv',
            'task_names_v1_analyzed.csv',
            model=args.model,
            limit=args.limit
        )

    if args.both or args.v2:
        print("\n" + "="*60)
        print("Processing task_names_v2.csv")
        print("="*60)
        process_csv_file(
            'task_names_v2.csv',
            'task_names_v2_analyzed.csv',
            model=args.model,
            limit=args.limit
        )

    if not (args.v1 or args.v2 or args.both):
        parser.print_help()
        print("\nPlease specify --v1, --v2, or --both to process files")


if __name__ == '__main__':
    main()
