import re
from scrapy.dupefilters import RFPDupeFilter

import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from scrapy.dupefilters import RFPDupeFilter

class UnitsLinguisticDupeFilter(RFPDupeFilter):
    """
    Custom Scrapy DupeFilter to unify multilingual URLs into a single canonical fingerprint.
    Specifically designed for university portals with subdomains, subdirectories, or query parameters.
    """
    def request_fingerprint(self, request):
        parsed = urlparse(request.url)

        LANG_QUERY_KEYS = {'lang', 'hl', 'language', 'locale', 'l', 'ln', 'lingua'}
        # LANG_CODE_PATTERN = re.compile(r'^(it|en|de|fr|es)$', re.IGNORECASE)
        # something stronger
        LANG_CODE_PATTERN = re.compile(r'^(it|en|de|fr|es|uk)$', re.IGNORECASE)
        lang_codes = LANG_CODE_PATTERN.pattern.strip('^$()')

        # ── 1. Subdomain ──────────────────────────────────────────────────────────
        host = parsed.netloc.lower()
        host = re.sub(r':443$', '', host)
        host = re.sub(r':80$',  '', host)
        parts = host.split('.')
        if LANG_CODE_PATTERN.match(parts[0]):
            host = '.'.join(parts[1:])

        # ── 2. Path segments ──────────────────────────────────────────────────────
        segments = parsed.path.split('/')
        segments = [s for s in segments if s and not LANG_CODE_PATTERN.match(s)]
        path = '/' + '/'.join(segments) if segments else '/'

        # ── 3. File extension / underscore language suffix ────────────────────────
        path = re.sub(rf'\.({lang_codes})(\.[a-zA-Z]+)$', r'\2', path, flags=re.IGNORECASE)
        path = re.sub(rf'_({lang_codes})(\.[a-zA-Z]+)$',  r'\2', path, flags=re.IGNORECASE)

        # ── 4. Query parameters ───────────────────────────────────────────────────
        q_params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in q_params if k.lower() not in LANG_QUERY_KEYS]
        new_query = urlencode(sorted(filtered))

        # ── 5. Fragment / hash ────────────────────────────────────────────────────
        fragment = parsed.fragment
        fragment = re.sub(rf'[#!]*\/?({lang_codes})\/?$',                         '',    fragment, flags=re.IGNORECASE)
        fragment = re.sub(rf'(lang|hl|language|locale|l|ln)=({lang_codes})(&|$)', r'\3', fragment, flags=re.IGNORECASE)
        fragment = re.sub(r'(lang|hl|language|locale|l|ln)=\s*(&|$)',             '',    fragment, flags=re.IGNORECASE)
        fragment = fragment.strip('&#/!')

        canonical_url = urlunparse((parsed.scheme, host, path, parsed.params, new_query, fragment))

        new_request = request.replace(url=canonical_url)
        fp_bytes = self.fingerprinter.fingerprint(new_request)
        return fp_bytes.hex()


#### Cases covered ####

# GROUP 1 — units.it (no subdomain)

# ("https://en.units.it/ateneo",          "Subdomain"),
# ("https://units.it/ateneo?lang=it",     "Query param: lang"),
# ("https://units.it:443/ateneo?hl=es",   "Port + Query param: hl"),
# ("https://units.it/en/ateneo/",         "Trailing slash + Subdirectory"),

# GROUP 2 — portale.units.it

# ("https://en.portale.units.it/ateneo",              "Subdomain"),
# ("https://portale.units.it/ateneo?lang=it",         "Query param: lang"),
# ("https://portale.units.it:443/ateneo?hl=es",       "Port + Query param: hl"),
# ("https://portale.units.it/en/ateneo/",             "Trailing slash + Subdirectory"),
# ("https://portale.units.it/ateneo?language=fr",     "Query param: language"),
# ("https://portale.units.it/ateneo?locale=de",       "Query param: locale"),
# ("https://portale.units.it/ateneo?l=it",            "Query param: l"),
# ("https://portale.units.it/ateneo?ln=en",           "Query param: ln"),
# ("https://portale.units.it/ateneo/en/",             "Lang at end of path"),
# ("https://portale.units.it/ateneo#lang=it",         "Fragment: lang param"),
# ("https://portale.units.it/ateneo#!/it/",           "Fragment: hash-bang path"),
# ("https://portale.units.it/ateneo?id=5&lang=it",    "Lang mixed with real params — expects ?id=5")

# GROUP 3 — file suffix

# ("https://portale.units.it/pagina.en.html",  "File extension suffix"),
# ("https://portale.units.it/document_fr.pdf", "Filename underscore suffix"),
