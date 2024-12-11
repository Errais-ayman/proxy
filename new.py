import argparse
import asyncio
import platform
import re
import sys
import time

import httpx
from bs4 import BeautifulSoup


class Scraper:

    def __init__(self, method, _url):
        self.method = method
        self._url = _url

    def get_url(self, **kwargs):
        return self._url.format(**kwargs, method=self.method)

    async def get_response(self, client):
        return await client.get(self.get_url())

    async def handle(self, response):
        return response.text

    async def scrape(self, client):
        response = await self.get_response(client)
        proxies = await self.handle(response)
        pattern = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?")
        return re.findall(pattern, proxies)


# From spys.me
class SpysMeScraper(Scraper):

    def __init__(self, method):
        if method == "http":
            super().__init__(method, "https://spys.me/proxy.txt")
        elif method == "socks":
            super().__init__(method, "https://spys.me/socks.txt")
        else:
            raise NotImplementedError


# From proxyscrape.com
class ProxyScrapeScraper(Scraper):

    def __init__(self, method, timeout=1000, country="All"):
        self.timeout = timeout
        self.country = country
        super().__init__(method,
                         "https://api.proxyscrape.com/?request=getproxies"
                         "&proxytype={method}"
                         "&timeout={timeout}"
                         "&country={country}")

    def get_url(self, **kwargs):
        return super().get_url(timeout=self.timeout, country=self.country, **kwargs)

# From geonode.com - A little dirty, grab http(s) and socks but use just for socks
class GeoNodeScraper(Scraper):

    def __init__(self, method, limit="500", page="1", sort_by="lastChecked", sort_type="desc"):
        self.limit = limit
        self.page = page
        self.sort_by = sort_by
        self.sort_type = sort_type
        super().__init__(method,
                         "https://proxylist.geonode.com/api/proxy-list?"
                         "&limit={limit}"
                         "&page={page}"
                         "&sort_by={sort_by}"
                         "&sort_type={sort_type}")

    def get_url(self, **kwargs):
        return super().get_url(limit=self.limit, page=self.page, sort_by=self.sort_by, sort_type=self.sort_type, **kwargs)

# From proxy-list.download
class ProxyListDownloadScraper(Scraper):

    def __init__(self, method, anon):
        self.anon = anon
        super().__init__(method, "https://www.proxy-list.download/api/v1/get?type={method}&anon={anon}")

    def get_url(self, **kwargs):
        return super().get_url(anon=self.anon, **kwargs)


# For websites using table in html
class GeneralTableScraper(Scraper):

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table", attrs={"class": "table table-striped table-bordered"})
        for row in table.findAll("tr"):
            count = 0
            proxy = ""
            for cell in row.findAll("td"):
                if count == 1:
                    proxy += ":" + cell.text.replace("&nbsp;", "")
                    proxies.add(proxy)
                    break
                proxy += cell.text.replace("&nbsp;", "")
                count += 1
        return "\n".join(proxies)


# For websites using div in html
class GeneralDivScraper(Scraper):

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("div", attrs={"class": "list"})
        for row in table.findAll("div"):
            count = 0
            proxy = ""
            for cell in row.findAll("div", attrs={"class": "td"}):
                if count == 2:
                    break
                proxy += cell.text+":"
                count += 1
            proxy = proxy.rstrip(":")
            proxies.add(proxy)
        return "\n".join(proxies)
    
# For scraping live proxylist from github
class GitHubScraper(Scraper):
        
    async def handle(self, response):
        tempproxies = response.text.split("\n")
        proxies = set()
        for prxy in tempproxies:
            if self.method in prxy:
                proxies.add(prxy.split("//")[-1])

        return "\n".join(proxies)

# From proxydb.net
class ProxyDBScraper(Scraper):

    def __init__(self, method, limit=15):
        self.limit = limit
        super().__init__(method, "http://proxydb.net/?protocol={method}&offset={offset}")

    def get_url(self, offset=0, **kwargs):
        return super().get_url(offset=offset, **kwargs)

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for offset in range(0, self.limit, 15):
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From GitHub: https://raw.githubusercontent.com/sunny9577/proxy-scraper/refs/heads/master/proxies.txt
class Sunny9577GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/sunny9577/proxy-scraper/refs/heads/master/proxies.txt")

# From GitHub: https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/all.txt
class MonosansGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/all.txt")

# From GitHub: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/http.txt
class TheSpeedXGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/http.txt")

# From GitHub: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks4.txt
class TheSpeedXSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks4.txt")

# From GitHub: https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks5.txt
class TheSpeedXSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks5.txt")

# From GitHub: https://raw.githubusercontent.com/gitrecon1455/ProxyScraper/refs/heads/main/proxies.txt
class Gitrecon1455GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/gitrecon1455/ProxyScraper/refs/heads/main/proxies.txt")

# From GitHub: https://raw.githubusercontent.com/zebbern/Proxy-Scraper/refs/heads/main/proxies.txt
class ZebbernGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/zebbern/Proxy-Scraper/refs/heads/main/proxies.txt")

# From GitHub: https://raw.githubusercontent.com/Isloka/proxyscraper/refs/heads/main/proxies/http.txt
class IslokaHttpGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/Isloka/proxyscraper/refs/heads/main/proxies/http.txt")

# From GitHub: https://raw.githubusercontent.com/Isloka/proxyscraper/refs/heads/main/proxies/socks.txt
class IslokaSocksGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/Isloka/proxyscraper/refs/heads/main/proxies/socks.txt")

# From GitHub: https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/http.txt
class ProxyScraperHttpGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/http.txt")

# From GitHub: https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/socks4.txt
class ProxyScraperSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/socks4.txt")

# From GitHub: https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/socks5.txt
class ProxyScraperSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/refs/heads/main/socks5.txt")

# From GitHub: https://raw.githubusercontent.com/lalifeier/proxy-scraper/refs/heads/main/proxies/https.txt
class LalifeierHttpsGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/lalifeier/proxy-scraper/refs/heads/main/proxies/https.txt")

# From GitHub: https://raw.githubusercontent.com/lalifeier/proxy-scraper/refs/heads/main/proxies/socks4.txt
class LalifeierSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/lalifeier/proxy-scraper/refs/heads/main/proxies/socks4.txt")

# From GitHub: https://raw.githubusercontent.com/gingteam/proxy-scraper/refs/heads/main/proxies.txt
class GingteamGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/gingteam/proxy-scraper/refs/heads/main/proxies.txt")

# From GitHub: https://raw.githubusercontent.com/CNMengHan/ProxyPool/refs/heads/main/proxy.txt
class CNMengHanGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/CNMengHan/ProxyPool/refs/heads/main/proxy.txt")

# From GitHub: https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks4.txt
class R00teeSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks4.txt")

# From GitHub: https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks5.txt
class R00teeSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks5.txt")

# From GitHub: https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Https.txt
class R00teeHttpsGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Https.txt")

# From GitHub: https://raw.githubusercontent.com/hookzof/socks5_list/refs/heads/master/proxy.txt
class HookzofSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/hookzof/socks5_list/refs/heads/master/proxy.txt")

# From GitHub: https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks5.txt
class ErcinDedeogluSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks5.txt")

# From GitHub: https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks4.txt
class ErcinDedeogluSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks4.txt")

# From GitHub: https://raw.githubusercontent.com/SevenworksDev/proxy-list/refs/heads/main/proxies/socks5.txt
class SevenworksDevSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/SevenworksDev/proxy-list/refs/heads/main/proxies/socks5.txt")

# From GitHub: https://raw.githubusercontent.com/TuanMinPay/live-proxy/refs/heads/master/all.txt
class TuanMinPayGitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/TuanMinPay/live-proxy/refs/heads/master/all.txt")

# From GitHub: https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/SOCKS5_RAW.txt
class RoosterkidSocks5GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/SOCKS5_RAW.txt")

# From GitHub: https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/SOCKS4_RAW.txt
class RoosterkidSocks4GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/SOCKS4_RAW.txt")

# From GitHub: https://raw.githubusercontent.com/gitrecon1455/ProxyScraper/refs/heads/main/proxies.txt
class Gitrecon1455GitHubScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://raw.githubusercontent.com/gitrecon1455/ProxyScraper/refs/heads/main/proxies.txt")

# From proxy-spider.com
class ProxySpiderScraper(Scraper):

    def __init__(self, method, location):
        self.location = location
        super().__init__(method, f"https://proxy-spider.com/proxies/locations/{location}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From advanced.name
class AdvancedNameScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://advanced.name/freeproxy?page={page}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 6):
            self._url = f"https://advanced.name/freeproxy?page={page}"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From premiumproxy.net
class PremiumProxyScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://premiumproxy.net/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From free-proxy-list.net/web-proxy.html
class FreeProxyListWebProxyScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://free-proxy-list.net/web-proxy.html")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From www.socks-proxy.net
class SocksProxyNetScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://www.socks-proxy.net/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From www.sslproxies.org
class SSLProxiesScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://www.sslproxies.org/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From premproxy.com
class PremProxyScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://premproxy.com/list/type-0{page}.htm")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 8):
            self._url = f"https://premproxy.com/list/type-0{page}.htm"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From plainproxies.com
class PlainProxiesScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://plainproxies.com/resources/free-proxy-list?page={page}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 6):
            self._url = f"https://plainproxies.com/resources/free-proxy-list?page={page}"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From proxy-list.org
class ProxyListOrgScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://proxy-list.org/english/index.php?p={page}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 11):
            self._url = f"https://proxy-list.org/english/index.php?p={page}"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From hasdata.com
class HasDataScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://hasdata.com/free-proxy-list")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

# From proxybros.com
class ProxyBrosScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://proxybros.com/free-proxy-list/speed-1500/{page}/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                proxy = cells[0].text.strip()
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 31):
            self._url = f"https://proxybros.com/free-proxy-list/speed-1500/{page}/"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From www.freeproxy.world
class FreeProxyWorldScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://www.freeproxy.world/?type=&anonymity=&country=&speed=&port=&page={page}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 140):  # تعديل هنا لجمع من 1 إلى 139
            self._url = f"https://www.freeproxy.world/?type=&anonymity=&country=&speed=&port=&page={page}"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From iproyal.com
class IPRoyalScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://iproyal.com/free-proxy-list/?page={page}&entries=100")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 61):  # تعديل هنا لجمع من 1 إلى 60
            self._url = f"https://iproyal.com/free-proxy-list/?page={page}&entries=100"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From hidemy.name
class HideMyNameScraper(Scraper):

    def __init__(self, method, page=1):
        self.page = page
        super().__init__(method, f"https://hidemy.name/en/proxy-list/?type={method}&start={page*64}")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

    async def scrape(self, client):
        proxies = []
        for page in range(1, 6):
            self._url = f"https://hidemy.name/en/proxy-list/?type={self.method}&start={page*64}"
            response = await self.get_response(client)
            proxies.extend(await self.handle(response))
        return proxies

# From proxylist.geonode.com
class GeoNodeProxyListScraper(Scraper):

    def __init__(self, method, limit="500", page="1", sort_by="lastChecked", sort_type="desc"):
        self.limit = limit
        self.page = page
        self.sort_by = sort_by
        self.sort_type = sort_type
        super().__init__(method,
                         "https://proxylist.geonode.com/api/proxy-list?"
                         "&limit={limit}"
                         "&page={page}"
                         "&sort_by={sort_by}"
                         "&sort_type={sort_type}")

    def get_url(self, **kwargs):
        return super().get_url(limit=self.limit, page=self.page, sort_by=self.sort_by, sort_type=self.sort_type, **kwargs)

# From free-proxy-list.net
class FreeProxyListNetScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://free-proxy-list.net/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

# From us-proxy.org
class USProxyOrgScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://us-proxy.org/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

# From socks-proxy.net
class SocksProxyNetScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://www.socks-proxy.net/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

# From sslproxies.org
class SSLProxiesOrgScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://www.sslproxies.org/")

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table")
        for row in table.findAll("tr"):
            cells = row.findAll("td")
            if len(cells) > 0:
                ip = cells[0].text.strip()
                port = cells[1].text.strip()
                proxy = f"{ip}:{port}"
                proxies.add(proxy)
        return "\n".join(proxies)

scrapers = [
    SpysMeScraper("http"),
    SpysMeScraper("socks"),
    ProxyScrapeScraper("http"),
    ProxyScrapeScraper("socks4"),
    ProxyScrapeScraper("socks5"),
    GeoNodeScraper("socks"),
    ProxyListDownloadScraper("https", "elite"),
    ProxyListDownloadScraper("http", "elite"),
    ProxyListDownloadScraper("http", "transparent"),
    ProxyListDownloadScraper("http", "anonymous"),
    GeneralTableScraper("https", "http://sslproxies.org"),
    GeneralTableScraper("http", "http://free-proxy-list.net"),
    GeneralTableScraper("http", "http://us-proxy.org"),
    GeneralTableScraper("socks", "http://socks-proxy.net"),
    GeneralDivScraper("http", "https://freeproxy.lunaproxy.com/"),
    GitHubScraper("http", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("socks4", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("socks5", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("http", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"),
    GitHubScraper("socks", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"),
    GitHubScraper("https", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt"),
    GitHubScraper("http", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt"),
    GitHubScraper("socks4", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks4.txt"),
    GitHubScraper("socks5", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt"),
    ProxyDBScraper("http"),
    ProxyDBScraper("socks4"),
    ProxyDBScraper("socks5"),
    Sunny9577GitHubScraper("http"),
    MonosansGitHubScraper("http"),
    TheSpeedXGitHubScraper("http"),
    TheSpeedXSocks4GitHubScraper("socks4"),
    TheSpeedXSocks5GitHubScraper("socks5"),
    Gitrecon1455GitHubScraper("http"),
    ZebbernGitHubScraper("http"),
    IslokaHttpGitHubScraper("http"),
    IslokaSocksGitHubScraper("socks"),
    ProxyScraperHttpGitHubScraper("http"),
    ProxyScraperSocks4GitHubScraper("socks4"),
    ProxyScraperSocks5GitHubScraper("socks5"),
    LalifeierHttpsGitHubScraper("https"),
    LalifeierSocks4GitHubScraper("socks4"),
    GingteamGitHubScraper("http"),
    CNMengHanGitHubScraper("http"),
    R00teeSocks4GitHubScraper("socks4"),
    R00teeSocks5GitHubScraper("socks5"),
    R00teeHttpsGitHubScraper("https"),
    HookzofSocks5GitHubScraper("socks5"),
    ErcinDedeogluSocks5GitHubScraper("socks5"),
    ErcinDedeogluSocks4GitHubScraper("socks4"),
    SevenworksDevSocks5GitHubScraper("socks5"),
    TuanMinPayGitHubScraper("http"),
    RoosterkidSocks5GitHubScraper("socks5"),
    RoosterkidSocks4GitHubScraper("socks4"),
    Gitrecon1455GitHubScraper("http"),
    ProxySpiderScraper("http", "us-united-states"),
    ProxySpiderScraper("http", "cn-china"),
    ProxySpiderScraper("http", "retrusion"),
    ProxySpiderScraper("http", "au-australia"),
    ProxySpiderScraper("http", "de-germany"),
    ProxySpiderScraper("http", "id-indonesia"),
    ProxySpiderScraper("http", "ca-canada"),
    ProxySpiderScraper("http", "ir-iran"),
    ProxySpiderScraper("http", "in-india"),
    AdvancedNameScraper("http"),
    AdvancedNameScraper("https"),
    AdvancedNameScraper("socks4"),
    AdvancedNameScraper("socks5"),
    PremiumProxyScraper("http"),
    PremiumProxyScraper("https"),
    PremiumProxyScraper("socks4"),
    PremiumProxyScraper("socks5"),
    FreeProxyListWebProxyScraper("http"),
    FreeProxyListWebProxyScraper("https"),
    FreeProxyListWebProxyScraper("socks4"),
    FreeProxyListWebProxyScraper("socks5"),
    SocksProxyNetScraper("socks"),
    SSLProxiesScraper("https"),
    PremProxyScraper("http"),
    PremProxyScraper("https"),
    PremProxyScraper("socks4"),
    PremProxyScraper("socks5"),
    PlainProxiesScraper("http"),
    PlainProxiesScraper("https"),
    PlainProxiesScraper("socks4"),
    PlainProxiesScraper("socks5"),
    ProxyListOrgScraper("http"),
    ProxyListOrgScraper("https"),
    ProxyListOrgScraper("socks4"),
    ProxyListOrgScraper("socks5"),
    HasDataScraper("http"),
    HasDataScraper("https"),
    HasDataScraper("socks4"),
    HasDataScraper("socks5"),
    ProxyBrosScraper("http"),
    ProxyBrosScraper("https"),
    ProxyBrosScraper("socks4"),
    ProxyBrosScraper("socks5"),
    FreeProxyWorldScraper("http"),
    FreeProxyWorldScraper("https"),
    FreeProxyWorldScraper("socks4"),
    FreeProxyWorldScraper("socks5"),
    IPRoyalScraper("http"),
    IPRoyalScraper("https"),
    IPRoyalScraper("socks4"),
    IPRoyalScraper("socks5"),
    HideMyNameScraper("http"),
    HideMyNameScraper("https"),
    HideMyNameScraper("socks4"),
    HideMyNameScraper("socks5"),
    GeoNodeProxyListScraper("http"),
    GeoNodeProxyListScraper("https"),
    GeoNodeProxyListScraper("socks4"),
    GeoNodeProxyListScraper("socks5"),
    FreeProxyListNetScraper("http"),
    FreeProxyListNetScraper("https"),
    USProxyOrgScraper("http"),
    USProxyOrgScraper("https"),
    SocksProxyNetScraper("socks"),
    SSLProxiesOrgScraper("https")
]

def verbose_print(verbose, message):
    if verbose:
        print(message)

async def scrape(method, output, verbose):
    now = time.time()
    methods = [method]
    if method == "all":
        methods = ["http", "https", "socks4", "socks5"]
    elif method == "socks":
        methods += ["socks4", "socks5"]
    proxy_scrapers = [s for s in scrapers if s.method in methods]
    if not proxy_scrapers:
        raise ValueError("Method not supported")
    verbose_print(verbose, "Scraping proxies...")
    proxies = []

    tasks = []
    client = httpx.AsyncClient(follow_redirects=True)

    async def scrape_scraper(scraper):
        try:
            verbose_print(verbose, f"Looking {scraper.get_url()}...")
            proxies.extend(await scraper.scrape(client))
        except Exception:
            pass

    for scraper in proxy_scrapers:
        tasks.append(asyncio.ensure_future(scrape_scraper(scraper)))

    await asyncio.gather(*tasks)
    await client.aclose()

    proxies = set(proxies)
    verbose_print(verbose, f"Writing {len(proxies)} proxies to file...")
    with open(output, "w") as f:
        f.write("\n".join(proxies))
    verbose_print(verbose, "Done!")
    verbose_print(verbose, f"Took {time.time() - now} seconds")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--proxy",
        help="Supported proxy type: " + ", ".join(sorted(set([s.method for s in scrapers]))),
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file name to save .txt file",
        default="output.txt",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase output verbosity",
        action="store_true",
    )
    args = parser.parse_args()

    if sys.version_info >= (3, 7) and platform.system() == 'Windows':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape(args.proxy, args.output, args.verbose))
        loop.close()
    elif sys.version_info >= (3, 7):
        asyncio.run(scrape(args.proxy, args.output, args.verbose))
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(scrape(args.proxy, args.output, args.verbose))
        loop.close()

if __name__ == "__main__":
    main()