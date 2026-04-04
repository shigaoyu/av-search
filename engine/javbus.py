from bs4 import BeautifulSoup
from .base import BaseCrawler
import re
from concurrent.futures import ThreadPoolExecutor

class JavBusCrawler(BaseCrawler):
    BASE_URL = "https://www.buscdn.me"

    def search(self, query, type='all', page=1, fetch_magnets=True):
        # Mirror rotation for stability
        mirrors = ["https://www.buscdn.me", "https://www.javbus.com", "https://www.busun.me"]
        if type == 'uncensored':
            mirrors = ["https://www.busun.me", "https://www.buscdn.me"]
        
        for base in mirrors:
            if not query:
                search_url = f"{base}/page/{page}" if page > 1 else base
            else:
                search_url = f"{base}/search/{query}/{page}"
                
            # Set cookies for each mirror
            domain = base.split('//')[1]
            self.client.cookies.set('existmag', 'mag', domain=domain)
            self.client.cookies.set('age', '18', domain=domain)
            
            soup = self.fetch_page(search_url)
            if not soup:
                continue
                
            # Check if we are on a list page or detail page
            # Waterfall exists on search results and index pages
            if soup.select("#waterfall .item"):
                results = self.parse_list_page(soup, base, fetch_magnets)
                if results: return results
            elif soup.select(".container h3"): # Likely a detail page redirect
                results = self.parse_detail_page(soup, search_url, base, fetch_magnets)
                if results: return results
                
        return []

    def get_metadata(self, code):
        """Standard interface for MetadataManager."""
        # Try search with magnets disabled for speed
        results = self.search(code, fetch_magnets=False)
        if results:
            # Prefer exact match if possible
            for r in results:
                if code.upper() in r['code'].upper() or r['code'].upper() in code.upper():
                    return r
            return results[0]
        return None

    def parse_list_page(self, soup, base, fetch_magnets=True):
        results = []
        movie_items = soup.select("#waterfall .item")
        if not movie_items:
            return []
            
        def process_item(item):
            try:
                link_tag = item.select_one("a.movie-box")
                if not link_tag: return []
                
                href = link_tag['href']
                detail_url = href if href.startswith('http') else (base.rstrip('/') + '/' + href.lstrip('/'))
                
                cover_tag = link_tag.select_one("img")
                title = cover_tag['title'] if cover_tag else "No Title"
                src = ""
                if cover_tag:
                    src = cover_tag.get('data-original') or cover_tag.get('src') or ""
                
                # Robust URL handling
                if src.startswith('//'):
                    cover = 'https:' + src
                elif src.startswith('http'):
                    cover = src
                elif src:
                    cover = base.rstrip('/') + '/' + src.lstrip('/')
                else:
                    cover = ""
                
                # Create cover and thumb
                thumb = ""
                if cover:
                    if '/pics/thumb/' in cover:
                        path = cover.split('/pics/thumb/')[1]
                        thumb = f"https://pics.javbus.com/pics/thumb/{path}"
                        # JAVBus cover usually has _b suffix
                        if '.' in path:
                            name, ext = path.rsplit('.', 1)
                            cover = f"https://pics.javbus.com/pics/cover/{name}_b.{ext}"
                        else:
                            cover = f"https://pics.javbus.com/pics/cover/{path}"
                    elif '/pics/cover/' in cover:
                        path = cover.split('/pics/cover/')[1]
                        cover = f"https://pics.javbus.com/pics/cover/{path}"
                        # Reverse to get thumb
                        if '_b.' in path:
                            thumb_path = path.replace('_b.', '.')
                            thumb = f"https://pics.javbus.com/pics/thumb/{thumb_path}"
                        else:
                            thumb = f"https://pics.javbus.com/pics/thumb/{path}"
                    else:
                        thumb = cover
                
                code_tags = item.select("date")
                code = code_tags[0].text.strip() if len(code_tags) > 0 else "Unknown"
                date = code_tags[1].text.strip() if len(code_tags) > 1 else "Unknown"
                
                magnets = []
                if fetch_magnets:
                    magnets = self.fetch_magnets(detail_url, base)
                
                if not magnets:
                    magnets = [{'link': '', 'size': 'Unknown', 'is_chinese': False, 'name': title}]
                    
                item_results = []
                for mag in magnets:
                    item_results.append({
                        'source': 'JAVBus',
                        'title': title,
                        'cover': cover,
                        'thumb': thumb,
                        'code': code,
                        'date': date,
                        'magnet': mag['link'],
                        'size': mag['size'],
                        'is_chinese': mag.get('is_chinese', False),
                        'detail_url': detail_url
                    })
                return item_results
            except Exception as e:
                print(f"Item parse error: {e}")
                return []

        with ThreadPoolExecutor(max_workers=5) as executor:
            task_results = executor.map(process_item, movie_items)
            for res in task_results:
                results.extend(res)
                
        return results

    def parse_detail_page(self, soup, detail_url, base, fetch_magnets=True):
        try:
            title_tag = soup.select_one(".container h3")
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            cover_tag = soup.select_one(".bigImage img")
            src = cover_tag.get('src') if cover_tag else ""
            
            if src.startswith('//'): cover = 'https:' + src
            elif src.startswith('http'): cover = src
            elif src: cover = base.rstrip('/') + '/' + src.lstrip('/')
            else: cover = ""
                
            thumb = ""
            if cover:
                if '/pics/cover/' in cover:
                    path = cover.split('/pics/cover/')[1]
                    cover = f"https://pics.javbus.com/pics/cover/{path}"
                    thumb = f"https://pics.javbus.com/pics/thumb/{path}"
                else:
                    thumb = cover
            
            info_ps = soup.select(".info p")
            code, date = "Unknown", "Unknown"
            for p in info_ps:
                if "識別碼:" in p.text:
                    spans = p.select("span")
                    code = spans[-1].text.strip() if spans else "Unknown"
                if "發行日期:" in p.text:
                    date = p.text.split("發行日期:")[1].strip()

            magnets = self.fetch_magnets(detail_url, base) if fetch_magnets else []
            if not magnets:
                magnets = [{'link': '', 'size': 'Unknown', 'is_chinese': False, 'name': title}]
                
            results = []
            for mag in magnets:
                results.append({
                    'source': 'JAVBus',
                    'title': title,
                    'cover': cover,
                    'thumb': thumb,
                    'code': code,
                    'date': date,
                    'magnet': mag['link'],
                    'size': mag['size'],
                    'is_chinese': mag.get('is_chinese', False),
                    'detail_url': detail_url
                })
            return results
        except Exception as e:
            print(f"Detail parse error: {e}")
            return []

    def fetch_magnets(self, detail_url, base):
        try:
            domain = base
            if 'javbus.com' in detail_url: domain = "https://www.javbus.com"
            elif 'buscdn.me' in detail_url: domain = "https://www.buscdn.me"
            elif 'busun.me' in detail_url: domain = "https://www.busun.me"

            response = self.client.get(detail_url)
            if not response or response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_text = ""
            for s in soup.find_all('script'):
                if s.string and 'var gid' in s.string:
                    script_text = s.string
                    break
            
            if not script_text: return []
                
            gid = re.search(r'var gid = (\d+);', script_text).group(1)
            uc = re.search(r'var uc = (\d+);', script_text).group(1)
            img = re.search(r"var img = '(.+?)';", script_text).group(1)
            
            ajax_url = f"{domain}/ajax/uncensored-search.php?gid={gid}&lang=zh&img={img}&uc={uc}&floor={100}"
            ajax_res = self.client.get(ajax_url)
            if not ajax_res or ajax_res.status_code != 200:
                return []
                
            ajax_soup = BeautifulSoup(ajax_res.text, 'html.parser')
            magnets = []
            for row in ajax_soup.select("tr"):
                cols = row.select("td")
                if len(cols) < 3: continue
                link_tag = cols[0].select_one("a")
                if not link_tag: continue
                
                name = link_tag.text.strip()
                link = link_tag['href']
                size = cols[1].text.strip()
                is_chinese = any(x in name.lower() for x in ["字幕", "中文字幕", "-c", "cn"])
                magnets.append({'name': name, 'link': link, 'size': size, 'is_chinese': is_chinese})
            return magnets
        except Exception as e:
            print(f"Magnet fetch error: {e}")
            return []
