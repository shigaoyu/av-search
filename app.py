from flask import Flask, request, jsonify, render_template, Response
from config import Config
from engine import get_crawlers
from engine.manager import MetadataManager
import re
import httpx
import asyncio

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
    
    # Use global proxy config if available
    proxy = Config.PROXY if hasattr(Config, 'PROXY') and Config.PROXY else None
    
    def fetch_with_referer(target_url):
        # Determine the best referer based on the target URL
        # Logic inspired by "Download Team" for maximum stability
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(target_url).netloc
        except: pass
        
        # Default referer is the domain itself or google
        referer = f"https://{domain}/" if domain else "https://www.google.com/"
        
        # Specific overrides for known strict hosts
        if any(x in target_url for x in ["javbus", "buscdn", "busun", "pics.javbus.com"]):
            referer = "https://www.javbus.com/"
        elif any(x in target_url for x in ["javdb", "jdbimgs.com"]):
            referer = "https://javdb.com/"
        elif "nyaa" in target_url or "sukebei" in target_url:
            referer = "https://sukebei.nyaa.si/"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": referer,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        # HTTP/1.1 is more stable for some proxies; verify=False avoids SSL handshake issues
        with httpx.Client(proxy=proxy, follow_redirects=True, verify=False, timeout=15.0, http1=True) as client:
            print(f"Proxying: {target_url} (Referer: {referer})")
            return client.get(target_url, headers=headers)

    try:
        resp = fetch_with_referer(url)
        
        # If JavBus high-res (_b.jpg) fails, try thumbnail as fallback
        if resp.status_code == 404 and "_b.jpg" in url:
            fallback_url = url.replace("_b.jpg", ".jpg").replace("/cover/", "/thumb/")
            print(f"Proxy: 404 for high-res, trying fallback: {fallback_url}")
            resp = fetch_with_referer(fallback_url)
            
        # Return the content with appropriate headers
        headers = {
            "Content-Type": resp.headers.get("Content-Type", "image/jpeg"), 
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*"
        }
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        print(f"Proxy Image Error: {e}")
        return "Error", 500

@app.route('/api/search')
def search():
    query = request.args.get('q', '').upper()
    sort_type = request.args.get('sort', 'default')
    movie_type = request.args.get('type', 'all') # censored, uncensored, all
    chinese_only = request.args.get('chinese', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    
    results = []
    print(f"Searching for: '{query}' on crawlers...")
    for crawler in crawlers:
        try:
            res = crawler.search(query, type=movie_type, page=page)
            print(f"Crawler {crawler.__class__.__name__} found {len(res)} results.")
            results.extend(res)
        except Exception as e:
            print(f"Crawler error ({crawler.__class__.__name__}): {e}")
    
    # Simple deduplication by magnet
    seen_magnets = set()
    unique_results = []
    for r in results:
        if r['magnet'] not in seen_magnets:
            seen_magnets.add(r['magnet'])
            if chinese_only and not r['is_chinese']:
                continue
            unique_results.append(r)

    # Sorting logic
    def sort_key(item):
        size_val = parse_size(item['size'])
        if sort_type == 'size':
            return (size_val,)
        elif sort_type == 'date':
            d = item['date']
            return (d if '-' in d else '0000-00-00',)
        elif sort_type == 'seeders':
            return (int(item.get('seeders', 0)),)
        else: # default: Chinese subtitle > File size (desc)
            return (1 if item['is_chinese'] else 0, size_val)

    unique_results.sort(key=sort_key, reverse=True)
    
    # Pagination
    start_idx = (page - 1) * 20
    end_idx = start_idx + 20
    paginated_results = unique_results[start_idx:end_idx]
    
    # Metadata Enrichment (Async)
    from concurrent.futures import ThreadPoolExecutor
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
        
        # Guarantee fields exist
        if 'cover' not in item: item['cover'] = ""
        item['image'] = item.get('cover', "")
        item['img_url'] = item.get('cover', "")
        if 'thumb' not in item: item['thumb'] = ""
        
        # Fallback to placeholder if still empty
        if not item['cover']:
            placeholder = f"https://via.placeholder.com/800x1200?text={code}"
            item['cover'] = placeholder
            item['image'] = placeholder
            item['img_url'] = placeholder
            item['thumb'] = placeholder.replace("800x1200", "300x450")
            
        return item

    with ThreadPoolExecutor(max_workers=10) as executor:
        paginated_results = list(executor.map(fill_metadata, paginated_results))
    
    return jsonify(paginated_results)

def parse_size(size_str):
    match = re.search(r"(\d+\.?\d*)\s*(GB|MB|GiB|MiB)", size_str, re.I)
    if not match: return 0
    val = float(match.group(1))
    unit = match.group(2).upper()
    if unit in ['GB', 'GIB']: return val * 1024
    return val

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
