from bs4 import BeautifulSoup
from .base import BaseCrawler
import re
import urllib.parse

class JavDbCrawler(BaseCrawler):
    BASE_URL = "https://javdb.com"

    def search(self, query, type='all', page=1):
        if not query:
            # For empty query, maybe show trending or just return empty
            url = f"{self.BASE_URL}/?page={page}"
        else:
            # f=all means all categories, including uncensored
            url = f"{self.BASE_URL}/search?q={urllib.parse.quote(query)}&f=all&page={page}"
        
        try:
            # JavDB often requires a User-Agent and handles cookies
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            response = self.session.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"JavDB search failed with status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            movie_items = soup.select(".movie-list .item")
            
            results = []
            for item in movie_items:
                try:
                    link_tag = item.select_one("a")
                    if not link_tag: continue
                    
                    href = link_tag['href']
                    detail_url = self.BASE_URL + href if href.startswith('/') else href
                    
                    cover_tag = item.select_one("img")
                    # JavDB often uses data-src for lazy loading
                    cover = cover_tag.get('data-src') or cover_tag.get('src') or ""
                    if cover.startswith('//'):
                        cover = 'https:' + cover
                    
                    title_tag = item.select_one(".video-title")
                    title = title_tag.text.strip() if title_tag else "No Title"
                    
                    meta_tag = item.select_one(".meta")
                    meta_text = meta_tag.text.strip() if meta_tag else ""
                    # Meta usually looks like "SSIS-123 2024-03-20"
                    parts = meta_text.split()
                    code = parts[0] if parts else "Unknown"
                    date = parts[1] if len(parts) > 1 else "Unknown"
                    
                    # JavDB search results don't have magnets in the list
                    # We would need to go to the detail page.
                    # But since this is a search engine, we'll return the metadata
                    # and let MetadataManager use it to enrich other sources.
                    # If we really want magnets from JavDB, we'd fetch detail_url.
                    
                    results.append({
                        'source': 'JavDB',
                        'title': title,
                        'cover': cover,
                        'thumb': cover, # Use same for now
                        'code': code,
                        'date': date,
                        'magnet': '', # JavDB requires login/detail fetch for magnets usually
                        'size': 'Unknown',
                        'is_chinese': '字幕' in title or '中文字幕' in title,
                        'detail_url': detail_url
                    })
                except Exception as e:
                    print(f"JavDB item parse error: {e}")
                    
            return results
        except Exception as e:
            print(f"JavDB search error: {e}")
            return []

    def get_metadata(self, code):
        """Specifically fetch metadata for a code."""
        results = self.search(code)
        # Find the best match
        target = code.upper().replace('-', '')
        for r in results:
            clean_r = r['code'].upper().replace('-', '')
            if target in clean_r or clean_r in target:
                return r
        return None
