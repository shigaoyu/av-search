from flask import Flask, request, jsonify, render_template, Response
from config import Config
from engine import get_crawlers
from engine.manager import MetadataManager
import re
import requests
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
    
    proxy = Config.PROXY if hasattr(Config, 'PROXY') and Config.PROXY else None
    
    def fetch_with_requests(target_url):
        referer = "https://www.google.com/"
        if "javbus" in target_url or "pics" in target_url: 
            referer = "https://www.javbus.com/"
        elif "javdb" in target_url: 
            referer = "https://javdb.com/"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer,
        }
        
        proxies = {"http": proxy, "https": proxy} if proxy else None
        return requests.get(target_url, headers=headers, proxies=proxies, timeout=15, verify=False)

    try:
        resp = fetch_with_requests(url)
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
            return crawler.search(query, type=movie_type, page=page)
        except Exception as e:
            print(f"Crawler error ({crawler.__class__.__name__}): {e}")
            return []

    with ThreadPoolExecutor(max_workers=len(crawlers) + 1) as executor:
        c_results = list(executor.map(fetch_results, crawlers))
        for res in c_results:
            results.extend(res)
    
    # Deduplication
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
    val = float(m.group(1))
    unit = m.group(2).upper()
    if unit in ['GB', 'GIB']: return val * 1024
    if unit in ['KB']: return val / 1024
    return val

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
