deny_domains = [
    "arts.units.it",
    "openstarts.units.it",
    "moodle.units.it",
    "moodle2.units.it",
    "wmail1.units.it",
    "cargo.units.it",
    "cspn.units.it",
    "www-amm.units.it",
    "inside.units.it",
    "flux.units.it",
    "centracon.units.it",
    "smats.units.it",
    "docenti.units.it",
    "orari.units.it",
    "pregresso.sba.units.it",
    "dryades.units.it",
    "stream.dia.units.it",
    "esse3.units.it",
    "esse3web.units.it",
    "biblio.units.it",
    "apply.units.it",
    "docu.units.it",
    "100anni.units.it",
    "70annisslmit.units.it"
    "rendiconti.dmi.units.it",
    "dmi.units.it",
    "wireless.units.it",
    "byzantine.units.it",
    "voip.units.it",
    "eut.units.it",
    "webmail.sp.units.it",
    "cloudmail.units.it",
    "cloudmail.studenti.units.it",
    "mail.scfor.units.it",
    "wmail2.units.it",
    "suggerimenti.units.it",
    "sebina.units.it",
    "onlineforms.units.it",
    "helpdesk.units.it",
    # not secure
    "pat.units.it",
    "ciamician.dia.units.it"  # centro interdipartimentale per l'energia l'ambiente e i trasporti (Giacomo Ciamician))
]

deny_regex = [
    r".*feedback.*",
    r".*search.*",
    r".*eventi-passati.*",
    r".*openstarts.*",
    r".*moodle.units.*",
    r".*moodle2.units.*",
    r".*wmail1.*",
    r".*cargo.*",
    r".*wmail3.*",
    r".*wmail4.*",
    r".*@.*",
    r".*facebook.*",
    r".*instagram.*",
    r".*notizie.*",
    r".*ricerca/progetti.*", # there are a lot of research projects, maybe useful

# --- Login & User Management ---
    # Captures both clean URLs and language-prefixed URLs (/it/user, /en/user)
    r'.*/user/login.*',
    r'.*/user/register.*',
    r'.*/user/password.*',
    r'.*user\?destination=.*',  # Most important: blocks login redirects
    r'.*/(it|en)/user.*',       # Language-specific user paths

    # --- Internal Drupal System Paths ---
    r'.*\?q=user.*',
    r'.*\?q=admin.*',
    r'.*\?q=comment/reply/.*',
    r'.*\?q=filter/tips/.*',
    r'.*/node/add/.*',          # Block content creation pages
    r'.*/node/\d+/(edit|delete).*', # Block editing/deleting interface

    # --- Search, Sorting & Filters (Infinite Loop Traps) ---
    r'.*/search/.*',
    r'.*[\?&]sort_by=.*',       # View sorting
    r'.*[\?&]sort_order=.*',    # View ordering
    r'.*[\?&]order=.*',         # Generic ordering parameter
    r'.*[\?&]items_per_page=.*',# Pagination variations
    r'.*[\?&]check_logged_in=.*',# Drupal session check parameters

    # --- Tracking & Feeds ---
    r'.*/rss\.xml$',            # RSS Feeds
    r'.*/aggregator.*',         # News aggregators
    r'.*[\?&]utm_.*',           # Marketing tracking parameters

    # --- Static Files & Media (Saves bandwidth) ---
    # Added common document/archive formats
    r'.*\.(pdf|zip|gz|tar|exe|mp4|mp3|docx|xlsx|pptx|jpg|jpeg|png|gif|svg)$',


    # --- At the moment not included ---
        r".*eventi.*",
        r".*events.*",
        r".*news.*",
        r".*consigli-di-corso-di-studio.*",

        # AVVISI (thousends of pages, often with little content, maybe a filter for node in future)
        r".*avvisi.*",
        # r".*avvisi-dipartimento.*",
        # r".*avvisi-dipartimento-archivio.*",


        r".*riunta-di-dipartimento",
        r".*consiglio-di-direzione",
]
