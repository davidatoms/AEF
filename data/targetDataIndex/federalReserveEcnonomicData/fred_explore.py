import argparse
import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime

def search_fred_series(api_key, query, limit=20):
    url = "https://api.stlouisfed.org/fred/series/search"
    params = {
        "api_key": api_key,
        "search_text": query,
        "limit": limit,
        "file_type": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    series = data.get("seriess", [])
    return series

def save_results(query, series, selected_series=None):
    """Save search results to search_results/ directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ensure search_results directory exists
    os.makedirs("search_results", exist_ok=True)
    
    # Save JSON results
    json_filename = f"search_results/{query.lower().replace(' ', '_')}_{timestamp}.json"
    json_data = {
        "query": query,
        "timestamp": timestamp,
        "total_results": len(series),
        "series": series,
        "selected_series": selected_series
    }
    
    with open(json_filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    # Save human-readable text results
    txt_filename = f"search_results/{query.lower().replace(' ', '_')}_{timestamp}.txt"
    with open(txt_filename, 'w') as f:
        f.write(f"FRED Series Search Results\n")
        f.write(f"Query: {query}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Total Results: {len(series)}\n\n")
        
        for idx, s in enumerate(series):
            f.write(f"{idx+1}. {s['id']} - {s['title']}\n")
            f.write(f"   Notes: {s.get('notes', 'No description available')}\n")
            f.write(f"   Units: {s.get('units', 'N/A')}\n")
            f.write(f"   Frequency: {s.get('frequency', 'N/A')}\n")
            f.write(f"   Last Updated: {s.get('last_updated', 'N/A')}\n\n")
        
        if selected_series:
            f.write("\n" + "="*50 + "\n")
            f.write("SELECTED SERIES:\n")
            f.write(f"ID: {selected_series['id']}\n")
            f.write(f"Title: {selected_series['title']}\n")
            f.write(f"Description: {selected_series.get('notes', 'No description available')}\n")
    
    print(f"\n✅ Results saved to:")
    print(f"   📄 {txt_filename}")
    print(f"   📊 {json_filename}")
    return json_filename, txt_filename

def select_series(series):
    if not series:
        print("No series found.")
        return None
    print("\nAvailable FRED Series:\n")
    for idx, s in enumerate(series):
        print(f"{idx+1}. {s['id']} - {s['title']}")
        print(f"   {s.get('notes', '')}\n")
    while True:
        try:
            choice = int(input(f"Select a series by number (1-{len(series)}), or 0 to exit: "))
            if choice == 0:
                return None
            if 1 <= choice <= len(series):
                return series[choice-1]
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Search FRED data series by description.")
    parser.add_argument("query", help="Search query for series descriptions")
    parser.add_argument("--api-key", help="Your FRED API key (if not set in .env)")
    parser.add_argument("--limit", type=int, default=20, help="Number of results to show")
    parser.add_argument("--auto-save", action="store_true", default=True, help="Automatically save results (default: True)")
    parser.add_argument("--no-select", action="store_true", help="Skip series selection, just save search results")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("FRED_API_KEY")
    if not api_key:
        print("Error: FRED API key not provided. Set FRED_API_KEY in .env or use --api-key.")
        exit(1)

    print(f"🔍 Searching FRED for: '{args.query}'...")
    series = search_fred_series(api_key, args.query, args.limit)
    
    if not series:
        print("❌ No series found for your query.")
        exit(0)
    
    print(f"📈 Found {len(series)} series matching your query.")
    
    # Always save the search results first
    save_results(args.query, series)
    
    # Skip selection if --no-select flag is used
    if args.no_select:
        print("\n✅ Search complete! Results saved without selection.")
    else:
        # Allow user to select a series
        selected = select_series(series)
        if selected:
            print("\n🎯 You selected:")
            print(f"   ID: {selected['id']}")
            print(f"   Title: {selected['title']}")
            print(f"   Description: {selected.get('notes', '')}")
            
            # Save updated results with selection
            save_results(args.query, series, selected)
        else:
            print("\n👋 No series selected. Results still saved!")
