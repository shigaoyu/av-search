from flask import Flask, request, jsonify, render_template, Response
from config import Config
from engine import get_crawlers
from engine.manager import MetadataManager
import re
import httpx
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import time

app = Flask(__name__)
app.config.from_object(Config)
crawlers = get_crawlers(app.config)
metadata_mgr = MetadataManager(app.config)

# Global Search Cache: { "query_type_page": { "data": results, "time": timestamp } }
SEARCH_CACHE = {}
CACHE_EXPIRY = 3600 # 1 hour

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
    
    # 1. Check Cache for Speed
    cache_key = f"{query}_{movie_type}_{page}"
    if cache_key in SEARCH_CACHE:
        entry = SEARCH_CACHE[cache_key]
        if time.time() - entry['time'] < CACHE_EXPIRY:
            print(f"Cache Hit for: {cache_key}")
            return jsonify(self_sort(entry['data'], sort_type, chinese_only))
    
    results = []
    print(f"Searching: '{query}' (Type: {movie_type}, Page: {page})")
    
    # Task: Parallel search with HARD TIMEOUT (10s)
    def fetch_results(crawler):
        try:
            # Add internal timeout check if crawler supports it, 
            # or just rely on the ThreadPool wait
            return crawler.search(query, type=movie_type, page=page)
        except Exception as e:
            print(f"Crawler error ({crawler.__class__.__name__}): {e}")
            return []

    with ThreadPoolExecutor(max_workers=15) as executor:
        # Submit all tasks
        future_to_crawler = {executor.submit(fetch_results, c): c for c in crawlers}
        
        # Wait for all futures with a timeout of 12 seconds total
        done, not_done = wait(future_to_crawler.keys(), timeout=12)
        
        for future in done:
            try:
                results.extend(future.result())
            except Exception as e:
                print(f"Future result error: {e}")
                
        for future in not_done:
            crawler = future_to_crawler[future]
            print(f"Crawler timed out: {crawler.__class__.__name__}")
            # We don't cancel because ThreadPoolExecutor.submit futures aren't easily cancelable if running
    
    # Store in cache BEFORE enrichment to keep cache clean
    SEARCH_CACHE[cache_key] = {'data': results, 'time': time.time()}
    
    return jsonify(self_sort(results, sort_type, chinese_only))

def self_sort(results, sort_type, chinese_only):
    # Simple deduplication
    seen = set()
    unique = []
    for r in results:
        # Use magnet as unique ID
        mag = r.get('magnet', '')
        if mag not in seen:
            seen.add(mag)
            if chinese_only and not r.get('is_chinese'): continue
            unique.append(r)

    # Sort
    def sort_key(item):
        size = parse_size(item.get('size', '0'))
        if sort_type == 'size': return (size,)
        elif sort_type == 'date': return (item.get('date', '0000-00-00') if '-' in item.get('date', '') else '0000-00-00',)
        elif sort_type == 'seeders': return (int(item.get('seeders', 0) or 0),)
        elif sort_type == 'downloads': return (int(item.get('downloads', 0) or 0),)
        else: return (1 if item.get('is_chinese') else 0, size)

    unique.sort(key=sort_key, reverse=True)
    
    # Limit to current page (20 results)
    paginated = unique[:20] 
    
    # Enrichment - Optimized Parallel Enrichment from MetadataManager
    paginated = metadata_mgr.enrich_results_parallel(paginated)
    
    return paginated

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
