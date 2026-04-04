import httpx
from bs4 import BeautifulSoup

class BaseCrawler:
    def __init__(self, config):
        self.config = config
        proxy = config.get('PROXY')
        self.client = httpx.Client(
            proxy=proxy if proxy else None,
            follow_redirects=True,
            verify=False,
            timeout=15.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        )

    def fetch_page(self, url, retry=2):
        for i in range(retry + 1):
            try:
                print(f"Fetching: {url} (Attempt {i+1})")
                response = self.client.get(url)
                
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
