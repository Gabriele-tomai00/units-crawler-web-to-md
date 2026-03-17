import json
import os
import re
from urllib.parse import urlparse
import hashlib
from lxml import html as lxml_html
import html2text
import argparse
import glob

# -------------------------------
# Filters
# -------------------------------

REMOVE_IDS = ["footer"]
# REMOVE_CLASSES = ["sidebar", "breadcrumb", "menu"]

# -------------------------------
# Helper functions
# -------------------------------

def sanitize_filename(url: str) -> str:
    """Transform URL into a safe filename."""
    parsed = urlparse(url)
    name = parsed.netloc + parsed.path
    name = re.sub(r"[\\/?:*\"<>|]", "_", name).strip("_")
    if len(name) > 150:
        digest = hashlib.sha1(name.encode()).hexdigest()[:8]
        name = name[:150] + "_" + digest
    return name + ".md"

def clean_html(html_content: str) -> str:
    """Remove tags by id/class using lxml and return cleaned HTML."""
    try:
        tree = lxml_html.fromstring(html_content)
    except Exception:
        return html_content  # fallback: return raw HTML

    # Remove by ID
    for id_val in REMOVE_IDS:
        for el in tree.xpath(f'//*[@id="{id_val}"]'):
            el.drop_tree()

    # Remove by class (uncomment if needed)
    # for cls in REMOVE_CLASSES:
    #     for el in tree.xpath(f'//*[contains(concat(" ", normalize-space(@class), " "), " {cls} ")]'):
    #         el.drop_tree()

    return lxml_html.tostring(tree, encoding="unicode")

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown using html2text."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_content)

def collect_jsonl_files(input_folder: str) -> list[str]:
    """Recursively collect all .jsonl files inside the input folder."""
    pattern = os.path.join(input_folder, "**", "*.jsonl")
    files = glob.glob(pattern, recursive=True)
    # Also match files directly in the root of the folder
    root_pattern = os.path.join(input_folder, "*.jsonl")
    root_files = glob.glob(root_pattern)
    # Merge and deduplicate while preserving order
    all_files = list(dict.fromkeys(root_files + files))
    return sorted(all_files)

# -------------------------------
# Main processing
# -------------------------------

def process_folder(input_folder: str, output_file: str):
    """
    Parse all .jsonl files inside input_folder,
    process each record, and write everything to a single output .jsonl file.
    """
    if not os.path.isdir(input_folder):
        raise ValueError(f"Input path is not a directory: {input_folder}")

    jsonl_files = collect_jsonl_files(input_folder)
    if not jsonl_files:
        print(f"No .jsonl files found in: {input_folder}")
        return

    print(f"Found {len(jsonl_files)} JSONL file(s) to process:")
    for f in jsonl_files:
        print(f"  - {f}")

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    saved = 0
    skipped = 0

    with open(output_file, "w", encoding="utf-8") as fout:
        for jsonl_path in jsonl_files:
            print(f"\nProcessing: {jsonl_path}")
            file_count = 0

            with open(jsonl_path, "r", encoding="utf-8") as fin:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        skipped += 1
                        continue

                    html_content = item.get("content", "")
                    url = item.get("url", "unknown")

                    cleaned_html = clean_html(html_content)
                    md_text = html_to_markdown(cleaned_html)
                    item["content"] = md_text

                    fout.write(json.dumps(item, ensure_ascii=False) + "\n")
                    saved += 1
                    file_count += 1

            print(f"  -> {file_count} records processed")

    print(f"\nDone: {saved} records saved, {skipped} skipped.")
    print(f"Output JSONL: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean HTML content from JSONL files in a folder and merge into a single JSONL output."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input folder containing one or more .jsonl files"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .jsonl file path (single merged file)"
    )
    args = parser.parse_args()

    process_folder(args.input, args.output)