# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import os
from dotenv import load_dotenv

BOT_NAME = "units_crawler"

SPIDER_MODULES = ["units_crawler.spiders"]
NEWSPIDER_MODULE = "units_crawler.spiders"

DUPEFILTER_CLASS = 'units_crawler.multilingual_page_filtering.UnitsLinguisticDupeFilter'
# JOBDIR = 'crawls/myspider-1'  # Enables disk-based duplicate filtering

ADDONS = {}
DEPTH_LIMIT = 1

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "units_crawler (network lab)"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
]
# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 20
CONCURRENT_REQUESTS_PER_DOMAIN = 20
# Configure a delay (in seconds) for requests for the same website
DOWNLOAD_DELAY = 0.4

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
USE_PROXY = False
try:
    load_dotenv()
    PROXY_URL = os.getenv("SCRAPY_PROXY_URL")
    PROXY_USER = os.getenv("SCRAPY_PROXY_USER")
    PROXY_PASS = os.getenv("SCRAPY_PROXY_PASS")
    PROXY_RATE = float(os.getenv("SCRAPY_PROXY_RATE", 0))  # di default 0 se mancante

except Exception as e:
    print(f"[WARN] Impossible loading .env: {e}")
    PROXY_URL = PROXY_USER = PROXY_PASS = None
    PROXY_RATE = 0

# Imposta i middleware in base all’uso o meno del proxy
if USE_PROXY:
    DOWNLOADER_MIDDLEWARES = {
        'units_crawler.middlewares.SelectiveProxyMiddleware': 100,
        'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        'units_crawler.middlewares.UARotatorMiddleware': 400,
    }
else:
    DOWNLOADER_MIDDLEWARES = {
        'units_crawler.middlewares.UARotatorMiddleware': 400,
    }


# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "units_crawler.pipelines.saveLinksPipeline": 100,
    'units_crawler.pipelines.MultiFileJsonPipeline': 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 0
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 20
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 5
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

LOG_ENABLED = True
LOG_LEVEL = "ERROR"


DOWNLOAD_TIMEOUT = 20  
RETRY_TIMES = 2 
RETRY_ENABLED = True
DNS_TIMEOUT = 5
REACTOR_THREADPOOL_MAXSIZE = 20
