from .base import BaseCrawler
from bs4 import BeautifulSoup
import re

class SukebeiCrawler(BaseCrawler):
    BASE_URL = "https://sukebei.nyaa.si"

    def search(self, query, type='all', page=1):
        # Category Mapping
        cat = "2_0" # All
        if type == 'censored':
            cat = "2_2"
        elif type == 'uncensored':
            cat = "2_3"

        if not query:
            # Popular/Hot (Sort by Seeders)
            search_url = f"{self.BASE_URL}/?f=0&c={cat}&s=seeders&o=desc&p={page}"
        else:
            search_url = f"{self.BASE_URL}/?f=0&c={cat}&q={query}&p={page}"
            
        soup = self.fetch_page(search_url)

        results = []
        rows = soup.select("tr.success, tr.default, tr.danger")
        for row in rows:
            cols = row.select("td")
            if len(cols) < 6: continue
            
            # Category
            category = cols[0].select_one("a")['title']
            if "Art - Censored" not in category and "Art - Uncensored" not in category:
                # Actually JAV is 2_2 (Censored) or 2_3 (Uncensored)
                # But our filter c=2_2 should handle it.
                pass
            
            # Title & Link
            title_tag = cols[1].select_one("a:not(.comments)")
            title = title_tag.text.strip()
            detail_url = self.BASE_URL + title_tag['href']
            
            # Magnet
            magnet = cols[2].select("a")[1]['href'] # Usually the second link is magnet
            
            # Size
            size = cols[3].text.strip()
            
            # Date
            date = cols[4].text.strip()
            
            # Seeders & Leechers (Hotness indicators)
            seeders = cols[5].text.strip()
            leechers = cols[6].text.strip()
            downloads = cols[7].text.strip()
            
            # Try to extract code from title
            code_match = re.search(r'([A-Z]{2,10}-\d{2,10})', title, re.I)
            code = code_match.group(1).upper() if code_match else "Unknown"
            
            is_chinese = "字幕" in title or "中文字幕" in title or "-C" in title.upper() or "CN" in title.upper()
            
            results.append({
                'source': 'Sukebei',
                'title': title,
                'cover': '', # Use empty to trigger frontend code-based placeholder
                'code': code,
                'date': date,
                'magnet': magnet,
                'size': size,
                'is_chinese': is_chinese,
                'seeders': seeders,
                'leechers': leechers,
                'downloads': downloads,
                'detail_url': detail_url
            })
            
        return results
