import lxml.html as html
from lxml import etree
from bs4 import BeautifulSoup
import re
import html2text
import unicodedata
import json
import argparse
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
import os
from urllib.parse import urlparse, unquote
import hashlib
import multiprocessing
import copy
from functools import partial

# Set to True only if you want to inspect intermediate files
SAVE_DEBUG_FILES = False

# ---------------------------------------------------------------------------
# Drupal whitelist extraction
# ---------------------------------------------------------------------------
# XPath chain: first match wins.
DRUPAL_CONTENT_XPATHS = [
    # Drupal 10
    '//article[contains(@class,"node")]//div[contains(@class,"node__content")]',
    '//*[@id="block-units-base-content"]//div[contains(@class,"content")]',
    # Drupal 7
    '//*[@id="inner_contentcolumn"]',
    '//*[@id="contentcolumn"]',
    # Drupal 10
    '//main[@id="content" or @role="main"]',
    '//*[@id="main-wrapper"]',
    '//*[@id="main"]',
]

# Residual Drupal chrome that leaks inside node__content.
CONTENT_NOISE_CLASSES = [
    "layout-builder__add-block",
    "layout-builder__add-section",
    "contextual-region",
    "rsbtn", "rs_skip", "open-readspeaker-webreader",
    "cookiesjsr", "cookies-block",
    "media--blazy", "media--video", "media--youtube",
    "ti-interessa",
    "view-ultimo-aggiornamento",
    "breadcrumb",
    "field__label",
    "language-switcher",
    "menu-servizio", "hamburger--footer",
    "modal-search",
    "menu-spalla",      
    "menu--main"                  
    "paragraph--contenuto-correlati",
    # Drupal 7 departmental portals
    "rightcolumn",               # right sidebar with notices and links
    "leftcolumn",                # left sidebar with section navigation
    "box-sub-menu",              # section sub-navigation menu
    "box-left-bottom",           # bottom sidebar links (Contacts/Login)
]

# IDs of top-level structural elements stripped in the non-Drupal fallback.
STRUCTURAL_IDS = [
    "header", "navbar-top", "navbar-main",
    "site-footer", "footer", "CollapsingNavbar",
    "block-menutarget", "block-menutarget-2",
    "block-menusocial-2", "block-menusocial-3",
    "block-menucontatti-2", "block-menuorganizzazione-2",
    "block-menuriferimenti-2", "block-menuportale-2",
    "block-quicklinks-2", "block-modalsearch",
    "block-units-base-cookiesui",
    # Drupal 7 departmental portals
    "menu", "header", "leftcolumn", "rightcolumn",
    "footer", "link-utili-mobile", "nav-search",
]

# ---------------------------------------------------------------------------
# Original blacklist (restored from first version of the script)
# "block-layout-builder" intentionally EXCLUDED — it matched the main content
# block on Drupal pages and caused the page body to be silently dropped.
# ---------------------------------------------------------------------------
ORIGINAL_CLASSES_AND_IDS_TO_REMOVE = [
    "open-readspeaker-ui", "banner", "cookie", "nav-item dropdown",
    "sidebar", "breadcrumb", "btn dropdown-toggle", "main-header",
    "footer-container", "links",
    "clearfix navnavbar-nav", "clearfix menu menu-level-0",
    "views-field views-field-link__uri",
    # "block-layout-builder",  <-- REMOVED: matched main content on Drupal
    "block-field-blocknodeeventofield-documenti-allegati",
    "visually-hidden-focusable", "clearfix dropdown-menu", "nav-link",
    "field__label visually-hidden", "visually-hidden",
    "field field--name-field-media-image field--type-image field--label-visually_hidden",
    "clearfix nav", "modal modal-search fade",
    "block block-menu navigation menu--menu-target", "view-content row",
    "rsbtn", "rs_skip",
    "block block-menu navigation menu--main"
]

# Tags always removed (carry no textual information).
NOISE_TAGS = ["footer", "script", "style", "meta", "link", "img"]


# ---------------------------------------------------------------------------
# lxml helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str, max_length: int = 150) -> str:
    name = unquote(name)
    parsed = urlparse(name)
    basename = parsed.netloc + parsed.path
    basename = re.sub(r'[\\/?:*"<>|]', '_', basename).strip('_')
    if len(basename) > max_length:
        digest = hashlib.sha1(basename.encode()).hexdigest()[:8]
        basename = basename[:max_length] + "_" + digest
    return basename


def _drop_tags(tree, tags):
    for tag in tags:
        for el in tree.xpath(f"//{tag}"):
            try:
                el.drop_tree()
            except Exception:
                pass


def _drop_by_class_contains(tree, names):
    """
    Drop elements whose @class *contains* any of the given strings
    (case-insensitive).  Mirrors the original filter_response logic.
    """
    for name in names:
        name_lower = name.lower()
        for el in tree.xpath(
            f'//*[contains('
            f'translate(@class,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),'
            f'"{name_lower}")]'
        ):
            try:
                el.drop_tree()
            except Exception:
                pass
        for el in tree.xpath(
            f'//*[contains('
            f'translate(@id,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),'
            f'"{name_lower}")]'
        ):
            try:
                el.drop_tree()
            except Exception:
                pass


def _drop_by_id(tree, ids):
    for id_val in ids:
        for el in tree.xpath(f'//*[@id="{id_val}"]'):
            try:
                el.drop_tree()
            except Exception:
                pass


def _is_drupal_page(tree) -> bool:
    for el in tree.xpath('//meta[@name="Generator" or @name="generator"]'):
        content = (el.get("content") or "").lower()
        if "drupal" in content:
            return True
    for el in tree.xpath("//body"):
        cls = (el.get("class") or "").lower()
        if "path-node" in cls or "node--type" in cls:
            return True
    return False


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def _drupal_extract(tree):
    """
    Whitelist extraction for Drupal pages.
    Returns the serialised HTML of the content region, or None if not found.
    """
    _drop_by_id(tree, STRUCTURAL_IDS)
    
    for xpath in DRUPAL_CONTENT_XPATHS:
        nodes = tree.xpath(xpath)
        if nodes:
            wrapper = etree.Element("div")
            for node in nodes:
                wrapper.append(copy.deepcopy(node))
            _drop_by_class_contains(wrapper, CONTENT_NOISE_CLASSES)
            _drop_tags(wrapper, NOISE_TAGS)
            return etree.tostring(wrapper, encoding="unicode")
    return None


def _generic_extract(tree):
    """
    Fallback for non-Drupal pages (and Drupal pages where whitelist fails).
    Applies the original blacklist strategy, minus "block-layout-builder".
    Additionally removes known structural IDs (header, footer, navbar, …).
    """
    # 1. Remove known structural IDs (header, nav, footer, …)
    _drop_by_id(tree, STRUCTURAL_IDS)

    # 2. Original blacklist (restored, minus the problematic entry)
    _drop_by_class_contains(tree, ORIGINAL_CLASSES_AND_IDS_TO_REMOVE)

    return html.tostring(tree, encoding="unicode")


def filter_response(html_content: str) -> str:
    """
    Main HTML cleaner.

    For Drupal pages  → whitelist extraction (node__content region).
    For non-Drupal    → original blacklist strategy (restored + improved).
    In both cases     → NOISE_TAGS are removed first, then BeautifulSoup
                        post-processes for empty elements.
    """
    try:
        tree = html.fromstring(html_content)
    except Exception:
        return ""

    # Pass 1: always remove noise tags
    _drop_tags(tree, NOISE_TAGS)

    # Pass 2: choose extraction strategy
    if _is_drupal_page(tree):
        serialised = _drupal_extract(tree)
        if serialised is None:
            # Drupal page but no recognised content region → generic fallback
            serialised = _generic_extract(tree)
    else:
        serialised = _generic_extract(tree)

    # Pass 3: BeautifulSoup final cleanup
    soup = BeautifulSoup(serialised, "lxml")

    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return str(soup)


# ---------------------------------------------------------------------------
# Text utilities (unchanged from original)
# ---------------------------------------------------------------------------

def normalize_markdown(text: str) -> str:
    if not text:
        return text
    replacements = {
        "'": "'", "'": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00A0": " "
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)


def has_meaningful_content(text: str) -> bool:
    """Discard only pages that produce zero textual content."""
    if not text or not text.strip():
        return False
    return any(line.strip() for line in text.splitlines())


def parse_html_content_html2text(html_content: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return normalize_markdown(h.handle(html_content))


# ---------------------------------------------------------------------------
# Processing pipeline (unchanged from original)
# ---------------------------------------------------------------------------

def process_line(line, debug_dirs=None):
    line = line.strip()
    if not line:
        return None, "skipped"
    try:
        item = json.loads(line)
    except Exception:
        return None, "skipped"

    html_content = item.get("content", "")
    url = item.get("url", "")
    if not html_content:
        return None, "skipped"

    try:
        cleaned_html = filter_response(html_content)
        md = parse_html_content_html2text(cleaned_html)

        if not has_meaningful_content(md):
            return None, "skipped"

        item["content"] = md

        if SAVE_DEBUG_FILES and debug_dirs:
            fn = sanitize_filename(url)
            with open(os.path.join(debug_dirs['html'], fn + ".html"),
                      "w", encoding="utf-8") as f:
                f.write(cleaned_html)
            with open(os.path.join(debug_dirs['md'], fn + ".md"),
                      "w", encoding="utf-8") as f:
                f.write(md)

        return item, "saved"
    except Exception:
        return None, "skipped"


def process_file_logic(input_file_path, output_file_handle, verbose,
                       debug_dirs):
    max_workers = min(8, multiprocessing.cpu_count())
    saved, skipped = 0, 0
    worker_func = partial(process_line, debug_dirs=debug_dirs)

    with open(input_file_path, "r", encoding="utf-8") as fin:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for result in tqdm(
                executor.map(worker_func, fin, chunksize=200),
                desc=f"Processing {os.path.basename(input_file_path)}",
                leave=False,
            ):
                if not result:
                    skipped += 1
                    continue
                item, status = result
                if status == "saved" and item:
                    output_file_handle.write(
                        json.dumps(item, ensure_ascii=False) + "\n"
                    )
                    saved += 1
                    if verbose:
                        tqdm.write(f"SAVED: {item.get('url', '')}")
                else:
                    skipped += 1
    return saved, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",   type=str, required=True)
    parser.add_argument("--output",  type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    input_path  = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    base_output_dir = os.path.dirname(output_path)
    if base_output_dir and not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir, exist_ok=True)

    debug_dirs = None
    if SAVE_DEBUG_FILES:
        debug_dirs = {
            'html': os.path.join(base_output_dir, "debug_filtered_html"),
            'md':   os.path.join(base_output_dir, "debug_cleaned_md"),
        }
        for d in debug_dirs.values():
            os.makedirs(d, exist_ok=True)

    if os.path.isfile(input_path):
        with open(output_path, "w", encoding="utf-8") as fout:
            process_file_logic(input_path, fout, args.verbose, debug_dirs)
    elif os.path.isdir(input_path):
        jsonl_files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.endswith(".jsonl")
        ]
        with open(output_path, "w", encoding="utf-8") as fout:
            for f in jsonl_files:
                process_file_logic(f, fout, args.verbose, debug_dirs)

    print(f"\nProcessing complete. Output: {output_path}")


if __name__ == "__main__":
    main()