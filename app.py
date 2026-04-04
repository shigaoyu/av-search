from flask import Flask, request, jsonify, render_template, Response
from config import Config
from engine import get_crawlers
from engine.manager import MetadataManager
import re
import httpx
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.config.from_object(Config)
crawlers = get_crawlers(app.config)
metadata_mgr = MetadataManager(app.config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/proxy_image')
def proxy_image():
    url = request.args.get('url')
    if not url: return "No URL", 400
    
    # Use global proxy config if available (Borrowed from Download Team)
    proxy = Config.PROXY if hasattr(Config, 'PROXY') and Config.PROXY else None
    
    def fetch_with_requests(target_url):
        # Determine the best referer based on the target URL
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(target_url).netloc
        except: pass
        
        referer = f"https://{domain}/" if domain else "https://www.google.com/"
        if any(x in target_url for x in ["javbus", "buscdn", "busun", "pics.javbus.com"]):
            referer = "https://www.javbus.com/"
        elif any(x in target_url for x in ["javdb", "jdbimgs.com"]):
            referer = "https://javdb.com/"
        elif "nyaa" in target_url or "sukebei" in target_url:
            referer = "https://sukebei.nyaa.si/"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        
        proxies = {"http": proxy, "https": proxy} if proxy else None
        # requests is often more stable for low-level proxying than httpx in certain environments
        return requests.get(target_url, headers=headers, proxies=proxies, timeout=15, verify=False)

    try:
        # Initial fetch
        resp = fetch_with_requests(url)
        
        # Fallback for JavBus high-res if 404
        if resp.status_code == 404 and "_b.jpg" in url:
            fallback = url.replace("_b.jpg", ".jpg").replace("/cover/", "/thumb/")
            resp = fetch_with_requests(fallback)
            
        return Response(resp.content, resp.status_code, {
            "Content-Type": resp.headers.get("Content-Type", "image/jpeg"), 
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        print(f"Proxy Image Error: {e}")
        return "Error", 500

@app.route('/api/search')
def search():
    query = request.args.get('q', '').upper()
    sort_type = request.args.get('sort', 'default')
    movie_type = request.args.get('type', 'all')
    chinese_only = request.args.get('chinese', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    
    results = []
    print(f"Searching: '{query}' (Type: {movie_type}, Page: {page})")
    # Task: Parallel search across all crawlers for speed
    def fetch_results(crawler):
        try:
            # Set a timeout per crawler to prevent one slow source from blocking everything
            return crawler.search(query, type=movie_type, page=page)
        except Exception as e:
            print(f"Crawler error ({crawler.__class__.__name__}): {e}")
            return []

    # Use a larger thread pool for the initial search to maximize concurrency
    with ThreadPoolExecutor(max_workers=15) as executor:
        c_results = list(executor.map(fetch_results, crawlers))
        for res in c_results:
            results.extend(res)
    
    # Simple deduplication
    seen = set()
    unique = []
    for r in results:
        if r['magnet'] not in seen:
            seen.add(r['magnet'])
            if chinese_only and not r['is_chinese']: continue
            unique.append(r)

    # Sort
    def sort_key(item):
        size = parse_size(item['size'])
        if sort_type == 'size': return (size,)
        elif sort_type == 'date': return (item['date'] if '-' in item['date'] else '0000-00-00',)
        elif sort_type == 'seeders': return (int(item.get('seeders', 0) or 0),)
        elif sort_type == 'downloads': return (int(item.get('downloads', 0) or 0),)
        else: return (1 if item['is_chinese'] else 0, size)

    unique.sort(key=sort_key, reverse=True)
    
    # Pagination
    paginated = unique[(page-1)*20 : page*20]
    
    # Enrichment
    def fill_metadata(item):
        code = item.get('code', 'Unknown')
        if not item.get('cover') or 'placeholder' in item.get('cover', ''):
            meta = metadata_mgr.get_metadata(code)
            if meta:
                item['cover'] = meta.get('cover', '')
                item['thumb'] = meta.get('thumb', '')
                if not item.get('title') or item.get('title') == 'No Title':
                    item['title'] = meta.get('title', 'Unknown')
                if not item.get('date') or item.get('date') == 'Unknown':
                    item['date'] = meta.get('date', 'Unknown')
        
        # Ensure image fields
        item['cover'] = item.get('cover') or f"https://via.placeholder.com/800x1200?text={code}"
        item['thumb'] = item.get('thumb') or item['cover'].replace("800x1200", "300x450")
        item['image'] = item['cover']
        item['img_url'] = item['cover']
        return item

    with ThreadPoolExecutor(max_workers=10) as executor:
        paginated = list(executor.map(fill_metadata, paginated))
    
    return jsonify(paginated)

def parse_size(s):
    m = re.search(r"(\d+\.?\d*)\s*(GB|MB|GiB|MiB|KB)", s, re.I)
    if not m: return 0
    v = float(m.group(1))
    u = m.group(2).upper()
    if u in ['GB', 'GIB']: return v * 1024
    if u in ['KB']: return v / 1024
    return v

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
