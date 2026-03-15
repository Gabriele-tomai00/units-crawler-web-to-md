import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Resolve paths relative to this script's location, not cwd
SCRIPT_DIR  = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR.parent / "results_scrapy"


def sanitize_filename(url):
    """Create a safe filename from a URL."""
    parsed = urlparse(url)
    filename = parsed.netloc + parsed.path
    # Replace unsafe characters
    filename = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in filename)
    # Remove leading/trailing underscores and limit length
    filename = filename.strip('_')[:100]
    if not filename:
        filename = "unknown_url"
    return filename


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract markdown content from a JSONL file based on URL.")
    parser.add_argument("-d", "--depth", type=int, required=True, help="Depth value to identify the input file (e.g., 2 for results_scrapy/filtered_items_2.jsonl)")
    parser.add_argument("-u", "--url",   type=str, required=True, help="The URL to search for.")

    args = parser.parse_args()

    input_file = RESULTS_DIR / f"filtered_items_{args.depth}.jsonl"

    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)

    found      = False
    target_url = args.url.strip()

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data        = json.loads(line)
                    current_url = data.get("url", "").strip()

                    if current_url == target_url:
                        content = data.get("content", "")
                        if not content:
                            print("Warning: URL found but content is empty.")

                        output_file = RESULTS_DIR / f"{sanitize_filename(target_url)}.md"
                        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

                        with open(output_file, "w", encoding="utf-8") as out_f:
                            out_f.write(content)

                        print(f"Success! Content for URL '{target_url}' saved to:\n{output_file}")
                        found = True
                        break

                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON on line {line_num}")
                    continue

        if not found:
            print(f"URL '{target_url}' not found in '{input_file}'.")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


# example:
# python display_md.py -d 1 -u "https://pat.units.it"