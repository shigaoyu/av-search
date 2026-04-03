import requests
from bs4 import BeautifulSoup

class BaseCrawler:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '\"macOS\"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        # Add basic cookies to bypass some checks
        self.session.cookies.set('existmag', 'mag')
        self.session.cookies.set('age', '18')
        
        if config.get('PROXY'):
            self.session.proxies = {
                'http': config.get('PROXY'),
                'https': config.get('PROXY'),
            }

    def fetch_page(self, url):
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=15)
            if 'driver-verify' in response.url:
                print(f"Warning: JAVBus verification triggered at {url}")
                return None
            response.raise_for_status()
            # Use html.parser as fallback if lxml is missing
            try:
                return BeautifulSoup(response.text, 'lxml')
            except Exception:
                return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def search(self, query):
        raise NotImplementedError
