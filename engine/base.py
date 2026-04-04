import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure request warnings if we disable verify
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BaseCrawler:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        # Modern headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        
        proxy = config.get('PROXY')
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy,
            }

    def fetch_page(self, url, retry=2):
        for i in range(retry + 1):
            try:
                print(f"Fetching: {url} (Attempt {i+1})")
                # Sometimes verify=False helps with SSL issues in restricted environments
                response = self.session.get(url, timeout=15, verify=False)
                
                if response.status_code == 403:
                    print(f"403 Forbidden for {url}")
                    continue
                    
                if 'driver-verify' in response.url:
                    print(f"Verification triggered at {url}")
                    continue
                    
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                print(f"Attempt {i+1} failed for {url}: {e}")
                if i == retry:
                    return None
        return None

    def search(self, query):
        raise NotImplementedError
