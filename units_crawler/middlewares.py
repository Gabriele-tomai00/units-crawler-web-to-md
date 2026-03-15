# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from w3lib.util import to_unicode
import base64
import random


class SelectiveProxyMiddleware:
    def __init__(self, proxy_url, proxy_user, proxy_pass, proxy_rate, use_proxy):
        self.proxy_url = proxy_url
        self.proxy_user = proxy_user
        self.proxy_pass = proxy_pass
        self.proxy_rate = float(proxy_rate or 0.0)
        self.use_proxy = use_proxy

        # Prepare proxy auth header if credentials exist
        if proxy_user and proxy_pass:
            creds = f"{proxy_user}:{proxy_pass}"
            token = base64.b64encode(creds.encode()).decode()
            self.proxy_auth_header = f"Basic {token}"
        else:
            self.proxy_auth_header = None

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        proxy_url = settings.get("PROXY_URL")
        proxy_user = settings.get("PROXY_USER")
        proxy_pass = settings.get("PROXY_PASS")
        proxy_rate = settings.getfloat("PROXY_RATE", 0.0)
        use_proxy = settings.getbool("USE_PROXY", True)
        return cls(proxy_url, proxy_user, proxy_pass, proxy_rate, use_proxy)

    def process_request(self, request, spider):
        stats = spider.crawler.stats

        # Proxy is globally disabled
        if not self.use_proxy:
            request.meta.pop("proxy", None)
            request.headers.pop("Proxy-Authorization", None)
            stats.inc_value("proxy/disabled")
            return

        # Force direct request
        if request.meta.get("force_direct"):
            request.meta.pop("proxy", None)
            request.headers.pop("Proxy-Authorization", None)
            stats.inc_value("proxy/skipped")
            return

        # Decide randomly if proxy is used
        use_proxy = request.meta.get("force_proxy") or (self.proxy_rate > 0 and random.random() < self.proxy_rate)

        if use_proxy:
            request.meta["proxy"] = self.proxy_url
            if self.proxy_auth_header:
                request.headers["Proxy-Authorization"] = self.proxy_auth_header
            stats.inc_value("proxy/used")
        else:
            request.meta.pop("proxy", None)
            request.headers.pop("Proxy-Authorization", None)
            stats.inc_value("proxy/not_used")

class UARotatorMiddleware:
    def __init__(self, user_agents, rotate=True):
        self.user_agents = user_agents
        self.rotate = rotate

    @classmethod
    def from_crawler(cls, crawler):
        rotate = crawler.settings.getbool("ROTARY_USER_AGENT", False)
        user_agents = crawler.settings.get('USER_AGENTS', [])
        return cls(user_agents, rotate)

    def process_request(self, request, spider):
        if self.rotate and self.user_agents:
            user_agent = random.choice(self.user_agents)
            request.headers['User-Agent'] = user_agent

