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
        if not soup: return []

        results = []
        rows = soup.select("tr.success, tr.default, tr.danger, tr")
        for row in rows:
            cols = row.select("td")
            # Nyaa tables have specific structures: Category, Name, Comments, Link, Size, Date, Seeders, Leechers, Downloads
            if len(cols) < 9: continue
            
            title_tag = row.select_one("a[href^='/view/']")
            if not title_tag: continue
            
            title = title_tag.text.strip()
            detail_url = self.BASE_URL + title_tag['href']
            
            magnet_tag = row.select_one("a[href^='magnet:?']")
            if not magnet_tag: continue
            magnet = magnet_tag['href']
            
            size = cols[4].text.strip() # Size
            date = cols[5].text.strip() # Date
            
            def clean_num(text):
                return re.sub(r'[^\d]', '', text) or '0'
                
            seeders = clean_num(cols[6].text.strip())   # Seeders
            leechers = clean_num(cols[7].text.strip())  # Leechers
            downloads = clean_num(cols[8].text.strip()) # Completed downloads (Downloads)
            
            # Try to extract code from title
            code_match = re.search(r'([A-Z]{2,10}-\d{2,10})', title, re.I)
            if not code_match:
                code_match = re.search(r'([A-Z\d]{3,10}-\d{2,10})', title, re.I)
            
            code = code_match.group(1).upper() if code_match else "Unknown"
            is_chinese = any(x in title for x in ["字幕", "中文字幕", "CN", "SUB"]) or "-C" in title.upper()
            
            results.append({
                'source': 'Sukebei',
                'title': title,
                'cover': '', 
                'thumb': '', 
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
