from bs4 import BeautifulSoup
from .base import BaseCrawler
import re
from concurrent.futures import ThreadPoolExecutor

class JavBusCrawler(BaseCrawler):
    BASE_URL = "https://www.buscdn.me" # Censored default mirror

    def get_metadata(self, code):
        """Metadata completion interface for Manager."""
        results = self.search(code, fetch_magnets=False)
        if results:
            # Match the code exactly if possible
            for r in results:
                if r['code'].upper() == code.upper():
                    return r
            return results[0]
        return None

    def search(self, query, type='all', page=1, fetch_magnets=True):
        # Mirror rotation for stability
        mirrors = ["https://www.buscdn.me", "https://www.javbus.com", "https://www.busun.me"]
        if type == 'uncensored':
            mirrors = ["https://www.busun.me", "https://www.buscdn.me"]
        
        last_error = None
        for base in mirrors:
            if not query:
                search_url = f"{base}/page/{page}" if page > 1 else base
            else:
                search_url = f"{base}/search/{query}/{page}"
                
            try:
                # Set cookies for age verification
                self.session.cookies.set('existmag', 'mag', domain='www.buscdn.me')
                self.session.cookies.set('existmag', 'mag', domain='www.busun.me')
                self.session.cookies.set('existmag', 'mag', domain='www.javbus.com')
                
                response = self.session.get(search_url, timeout=10, allow_redirects=True)
                if not response or response.status_code != 200:
                    continue
                    
                if 'driver-verify' in response.url:
                    print(f"JAVBus Verification triggered at {response.url}")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # If search results are empty, Waterfall won't exist
                if not query or '/search/' in response.url:
                    results = self.parse_list_page(soup, base, fetch_magnets)
                    if results: return results
                else:
                    results = self.parse_detail_page(soup, response.url, base, fetch_magnets)
                    if results: return results
            except Exception as e:
                last_error = e
                print(f"JavBus mirror {base} failed: {e}")
                continue
        
        if last_error:
            print(f"JavBus search all mirrors failed. Last error: {last_error}")
        return []

    def get_metadata(self, code):
        """Standard interface for MetadataManager."""
        results = self.search(code, fetch_magnets=False)
        if results:
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
                # Handle lazy loading (data-original or data-src)
                src = ""
                if cover_tag:
                    src = cover_tag.get('src') or cover_tag.get('data-original') or cover_tag.get('data-src') or ""
                
                # Robust URL handling
                if src.startswith('//'):
                    cover = 'https:' + src
                elif src.startswith('http'):
                    cover = src
                elif src:
                    cover = base.rstrip('/') + '/' + src.lstrip('/')
                else:
                    cover = ""
                
                # Normalize cover URL to use the most stable image server (pics.javbus.com)
                if cover:
                    if '/pics/thumb/' in cover:
                        path = cover.split('/pics/thumb/')[1]
                        cover = f"https://pics.javbus.com/pics/thumb/{path}"
                    elif '/pics/cover/' in cover:
                        path = cover.split('/pics/cover/')[1]
                        cover = f"https://pics.javbus.com/pics/cover/{path}"
                
                code_tags = item.select("date")
                code = code_tags[0].text.strip() if len(code_tags) > 0 else "Unknown"
                date = code_tags[1].text.strip() if len(code_tags) > 1 else "Unknown"
                
                if fetch_magnets:
                    magnets = self.fetch_magnets(detail_url, base)
                else:
                    magnets = [{'link': '', 'size': '', 'is_chinese': False}]
                    
                item_results = []
                for mag in magnets:
                    item_results.append({
                        'source': 'JAVBus',
                        'title': title,
                        'cover': cover,
                        'code': code,
                        'date': date,
                        'magnet': mag['link'],
                        'size': mag['size'],
                        'is_chinese': mag['is_chinese'],
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
            src = ""
            if cover_tag:
                src = cover_tag.get('src') or cover_tag.get('data-original') or cover_tag.get('data-src') or ""
            
            # Robust URL handling
            if src.startswith('//'):
                cover = 'https:' + src
            elif src.startswith('http'):
                cover = src
            elif src:
                cover = base.rstrip('/') + '/' + src.lstrip('/')
            else:
                cover = ""
                
            # Normalize cover URL to use pics.javbus.com for stability
            if cover:
                if '/pics/cover/' in cover:
                    path = cover.split('/pics/cover/')[1]
                    cover = f"https://pics.javbus.com/pics/cover/{path}"
                elif '/pics/thumb/' in cover:
                    path = cover.split('/pics/thumb/')[1]
                    cover = f"https://pics.javbus.com/pics/thumb/{path}"
            
            info_ps = soup.select(".info p")
            code = "Unknown"
            date = "Unknown"
            for p in info_ps:
                text = p.text
                if "識別碼:" in text:
                    spans = p.select("span")
                    code = spans[-1].text.strip() if spans else "Unknown"
                if "發行日期:" in text:
                    date = text.split("發行日期:")[1].strip()

            if fetch_magnets:
                magnets = self.fetch_magnets(detail_url, base)
            else:
                magnets = [{'link': '', 'size': '', 'is_chinese': False}]
                
            results = []
            for mag in magnets:
                results.append({
                    'source': 'JAVBus',
                    'title': title,
                    'cover': cover,
                    'code': code,
                    'date': date,
                    'magnet': mag['link'],
                    'size': mag['size'],
                    'is_chinese': mag['is_chinese'],
                    'detail_url': detail_url
                })
            return results
        except Exception as e:
            print(f"Detail parse error: {e}")
            return []

    def fetch_magnets(self, detail_url, base):
        try:
            # We must use the same base for magnets as the detail page
            # because the AJAX call depends on the domain
            domain = base
            if 'javbus.com' in detail_url: domain = "https://www.javbus.com"
            elif 'buscdn.me' in detail_url: domain = "https://www.buscdn.me"
            elif 'busun.me' in detail_url: domain = "https://www.busun.me"

            response = self.session.get(detail_url, timeout=10)
            if not response or response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_text = ""
            for s in soup.find_all('script'):
                if s.string and 'var gid' in s.string:
                    script_text = s.string
                    break
            
            if not script_text: return []
                
            gid_match = re.search(r'var gid = (\d+);', script_text)
            uc_match = re.search(r'var uc = (\d+);', script_text)
            img_match = re.search(r"var img = '(.+?)';", script_text)
            
            if not (gid_match and uc_match and img_match): return []
                
            gid = gid_match.group(1)
            uc = uc_match.group(1)
            img = img_match.group(1)
            
            ajax_url = f"{domain}/ajax/uncensored-search.php?gid={gid}&lang=zh&img={img}&uc={uc}&floor={100}"
            ajax_response = self.session.get(ajax_url, timeout=10)
            if not ajax_response or ajax_response.status_code != 200:
                return []
                
            ajax_soup = BeautifulSoup(ajax_response.text, 'html.parser')
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
