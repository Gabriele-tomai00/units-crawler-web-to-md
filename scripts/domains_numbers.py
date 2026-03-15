import argparse
from urllib.parse import urlparse
from collections import Counter, defaultdict
import re
import os

def count_links_per_domain(file_name):
    counter = Counter()

    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            url = line.strip()
            if url:  # ignore empty lines
                domain = urlparse(url).netloc
                if domain:
                    # Remove 'www.' prefix if present
                    if domain.startswith("www."):
                        domain = domain[4:]
                    counter[domain] += 1

    return counter


def normalize_url(url):
    """Removes the language prefix from the URL, only if it is the first segment of the path"""
    return re.sub(r'^(https?://[^/]+)/(it|en|de|fr)(/|$)', r'\1\3', url.strip())

def extract_lang(url):
    """Extracts the language prefix from the URL, None if absent"""
    match = re.match(r'https?://[^/]+/(it|en|de|fr)(/|$)', url)
    return match.group(1) if match else None

def analyze_duplications(filepath):
    with open(filepath, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    total = len(urls)
    unique_urls = list(dict.fromkeys(urls))  # removes exact duplicates keeping order
    exact_duplicates = total - len(unique_urls)

    # Group by normalized URL using set (ignores identical URLs)
    groups = defaultdict(set)
    for url in unique_urls:
        normalized = normalize_url(url)
        lang = extract_lang(url)
        groups[normalized].add((url, lang))

    # Find only groups with DIFFERENT languages (true language duplicates)
    lang_duplicates = {}
    for normalized, entries in groups.items():
        langs = set(lang for _, lang in entries if lang is not None)
        if len(langs) > 1:
            lang_duplicates[normalized] = entries

    # Build the report
    report = []
    report.append("\n" + "="*40)
    report.append("DUPLICATION ANALYSIS")
    report.append("="*40)
    report.append(f"Total processed URLs: {total}")
    report.append(f"Exact duplicates removed: {exact_duplicates}")
    report.append(f"Remaining unique URLs: {len(unique_urls)}")
    report.append("-" * 40)
    
    report.append(f"Language duplicate groups found: {len(lang_duplicates)}")
    
    if lang_duplicates:
        report.append("\nLanguage duplicates detail:")
        for normalized, entries in lang_duplicates.items():
            report.append(f"\nBase URL: {normalized}")
            for url, lang in entries:
                report.append(f"  - [{lang}] {url}")
                
    return "\n".join(report)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--depth", type=int, required=True, help="Depth limit")
    parser.add_argument("--dir", type=str, help="Output dir", default="../results_scrapy/")
    args = parser.parse_args()

    base_dir = os.path.abspath(args.dir)
    
    input_file_name = os.path.join(base_dir, f"links_list_{args.depth}.txt")
    output_file_name = os.path.join(base_dir, f"summary_domains_numbers_{args.depth}.txt")

    if not os.path.exists(input_file_name):
        print(f"Error: File not found -> {input_file_name}")
        exit(1)

    domains = count_links_per_domain(input_file_name)
    duplication_report = analyze_duplications(input_file_name)

    # Writes (overwriting each time) the result to the output file
    with open(output_file_name, 'w', encoding='utf-8') as f:
        for domain, count in domains.most_common():
            f.write(f"{domain}: {count}\n")
        
        f.write(duplication_report)

    print(f"Analysis complete. Report updated in: {output_file_name}")