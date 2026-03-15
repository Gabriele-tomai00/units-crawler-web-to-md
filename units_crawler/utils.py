
import datetime
import json
import os
import re
import unicodedata
import json
from datetime import datetime
from shutil import rmtree
from os import path

def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_size_of_result_file(path: str) -> str:
    """
    Returns the size of a file or a folder.
    - For a file: returns its size.
    - For a folder: returns the total size of all files inside (recursively).
    The returned value is a human-readable string (B, KB, MB, GB).
    """
    if not os.path.exists(path):
        return "File or folder not found"

    total_size = 0

    if os.path.isfile(path):
        total_size = os.path.getsize(path)
    elif os.path.isdir(path):
        # Walk through all files in the directory
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)

    # Convert to human-readable format
    if total_size >= 1024**3:
        return f"{total_size / (1024**3):.2f} GB"
    elif total_size >= 1024**2:
        return f"{total_size / (1024**2):.2f} MB"
    elif total_size >= 1024:
        return f"{total_size / 1024:.2f} KB"
    else:
        return f"{total_size} B"


def print_scraping_summary(stats: dict, settings, pdf_count, output_dir, summary_file_name):
    print(json.dumps(stats, indent=4, default=str))

    start_time = stats.get("start_time", datetime.now())
    end_time = stats.get("finish_time", datetime.now())
    elapsed = stats.get("elapsed_time_seconds", (end_time - start_time).total_seconds())
    request_depth_max = stats.get("request_depth_max", 0)
    item_scraped_count = stats.get("item_scraped_count", 0)
    responses_per_minute = int(float(stats.get("responses_per_minute") or 0))

    proxy_used = stats.get("proxy/used", 0)
    proxy_not_used = stats.get("proxy/not_used", 0)
    proxy_disabled = stats.get("proxy/disabled", 0)
    proxy_total = proxy_used + proxy_not_used + proxy_disabled

    exception_count = stats.get("downloader/exception_count", 0)
    retry_count = stats.get("retry/count", 0)
    retry_max_reached = stats.get("retry/max_reached", 0)
    
    status_codes_summary = []
    for key, value in stats.items():
        if key.startswith("downloader/response_status_count/"):
            code = key.split("/")[-1]
            status_codes_summary.append(f"{code}: {value}")
    status_codes_str = ", ".join(status_codes_summary) if status_codes_summary else "None"

    if proxy_total > 0:
        if proxy_disabled > 0 and proxy_used == 0:
            proxy_summary = "Proxy disabled for this run"
        else:
            proxy_percent = (proxy_used / proxy_total) * 100
            proxy_summary = f"Proxy usage: {proxy_percent:.1f}% ({proxy_used}/{proxy_total})"
    else:
        proxy_summary = "Proxy usage: No data"

    summary_lines = [
        f"\n====== SCRAPING SESSION {start_time.strftime('%d-%m-%Y %H:%M')} ======",
        f"Elapsed time: {format_time(elapsed)}",
        f"End time: {end_time.strftime('%d-%m-%Y %H:%M')}",
        f"Total items scraped: {item_scraped_count}",
        f"Responses per minute: {responses_per_minute}",
        f"Max request depth: {request_depth_max}",
        f"Exceptions: {exception_count}",
        f"Retries: {retry_count}",
        f"Max retries reached: {retry_max_reached}",
        f"Status codes: {status_codes_str}",
        f"Use of multiple user agents: {settings.getbool('ROTARY_USER_AGENT', False)}",
        f"{proxy_summary}",
        f"Output: {output_dir}",
        f"Output size: {get_size_of_result_file(output_dir)}",
        "==============================================="
    ]

    if pdf_count > 0:
        summary_lines.insert(4, f"Total unique PDF links found: {pdf_count}")

    for line in summary_lines:
        print(line)

    with open(summary_file_name, "a", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")
    print(f"'{summary_file_name}' updated")


def remove_output_directory(dir_path):
    if path.exists(dir_path) and path.isdir(dir_path):
        rmtree(dir_path)
        print(f"Output directory '{dir_path}' removed.")


def save_webpage_to_file(html_content, url, counter, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    original_path = os.path.join(output_dir, f"{counter}_original.html")
    with open(original_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def save_pdf_list(links_set, file_path):
    os.makedirs(file_path, exist_ok=True)

    # Define the full path for the output file
    output_file = os.path.join(file_path, "pdf_links.txt")

    # Open the file in append mode to add new links without overwriting
    with open(output_file, "a", encoding="utf-8") as f:
        for link in links_set:
            f.write(link + "\n")


def get_article_date(response):
    modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
    published = response.xpath('//meta[@property="article:published_time"]/@content').get()

    modified_date = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', modified) if modified else None
    published_date = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', published) if published else None

    if modified_date:
        date = modified_date.group(1)
    elif published_date:
        date = published_date.group(1)
    else:
        date = ""

    return date

def get_metadata(response) -> dict:
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        if not title:
            title = response.xpath('//title/text()').get()

        # --- DESCRIPTION ---
        description = response.xpath('//meta[@name="description"]/@content').get()
        if not description:
            description = response.xpath('//meta[@property="og:description"]/@content').get()
        date = get_article_date(response)
        return {
            "title": title,
            "description": description,
            "date": date
        }



def normalize_markdown(text: str) -> str:
    """Avoid problems in JSON line (in markdown) about special unicode characters."""
    if not text:
        return text

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "\u00A0": " ",  # space not-breaking
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)


def is_informative_markdown(text: str) -> bool:
    # remove markdown titles
    cleaned = re.sub(r'#+\s*.*', '', text)
    # remove common footer/header phrases
    cleaned = re.sub(r'\b(Tutti gli avvisi|Link utili|Contatti|Servizi|Servizi digitali|Servizi di segreteria|Dipartimenti|Vai alla pagina)\b',
                     '', cleaned, flags=re.IGNORECASE) 
    # divide into lines and remove non-meaningful ones (less than 2 words)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    meaningful_lines = [line for line in lines if len(line.split()) >= 2]
    # calculate word count
    cleaned_text = " ".join(meaningful_lines)
    word_count = len(cleaned_text.split())
    # criteria: at least 20 words total and at least 2 meaningful lines
    return word_count > 20 and len(meaningful_lines) > 1

def print_log(response, counter, settings):
    log = str(counter) + " " + response.url
    rotate = settings.getbool("ROTARY_USER_AGENT", False)
    proxy = settings.getbool("USE_PROXY", False)
    if proxy:
        current_proxy = response.meta.get("proxy")
        if current_proxy:
            log = log + "   PROXY: " + current_proxy
        else:
            log = log + "   direct (no proxy) " 
    if rotate:
        user_agent = response.request.headers.get("User-Agent", b"").decode("utf-8")
        ua_preview = user_agent[:20] + ("..." if len(user_agent) > 50 else "")
        log = log + " | UA: " + ua_preview
    print(log)


# def get_page_id(response):
#     """
#     Generates a unique identifier for the page to detect linguistic duplicates.
#     It prioritizes the canonical tag and removes non-semantic URL parts.
#     """
#     # 1. Extract canonical link if present
#     canonical = response.xpath('//link[@rel="canonical"]/@href').get()
#     base_url = canonical if canonical else response.url
    
#     # 2. Normalize the URL string
#     # Remove explicit port 443
#     normalized = base_url.replace(':443', '')
    
#     # Remove /it/ or /en/ language prefixes from the path
#     # This matches /it/ at the start of path or mid-path
#     normalized = re.sub(r'/(it|en)(/|$)', '/', normalized)
    
#     # Remove trailing slash for consistency
#     return normalized.rstrip('/')