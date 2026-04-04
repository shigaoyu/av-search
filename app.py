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
        # Determine the best referer based on the target URL (Simplified like Download Team)
        referer = "https://www.javbus.com/" if "javbus" in target_url or "pics" in target_url else "https://javdb.com/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer,
        }
        
        # Simple client like Download Team
        with httpx.Client(proxy=proxy, follow_redirects=True, timeout=15.0) as client:
            print(f"Proxying: {target_url}")
            resp = client.get(target_url, headers=headers)
            return resp

    try:
        resp = fetch_with_referer(url)
        
        # If JavBus high-res (_b.jpg) fails, try thumbnail as fallback
        if resp.status_code == 404 and "_b.jpg" in url:
            fallback_url = url.replace("_b.jpg", ".jpg").replace("/cover/", "/thumb/")
            print(f"Proxy: 404 for high-res, trying fallback: {fallback_url}")
            resp = fetch_with_referer(fallback_url)
            
        return Response(resp.content, resp.status_code, {
            "Content-Type": resp.headers.get("Content-Type", "image/jpeg"), 
            "Cache-Control": "max-age=86400"
        })
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
    
    # Enrichment: If no cover, try to find one using MetadataManager
    # results = metadata_mgr.enrich_results(results) # We will do this in parallel below
    
    # Simple deduplication by magnet
    seen_magnets = set()
    unique_results = []
    for r in results:
        if r['magnet'] not in seen_magnets:
            seen_magnets.add(r['magnet'])
            # Apply Chinese filter if requested
            if chinese_only and not r['is_chinese']:
                continue
            unique_results.append(r)

    # Sorting logic
    def sort_key(item):
        size_val = parse_size(item['size'])
        if sort_type == 'size':
            return (size_val,)
        elif sort_type == 'date':
            # Handle non-date formats gracefully
            d = item['date']
            return (d if '-' in d else '0000-00-00',)
        elif sort_type == 'seeders':
            return (int(item.get('seeders', 0)),)
        else: # default: Chinese subtitle > File size (desc)
            return (1 if item['is_chinese'] else 0, size_val)

    unique_results.sort(key=sort_key, reverse=True)
    
    # Pagination logic
    start_idx = (page - 1) * 20
    end_idx = start_idx + 20
    paginated_results = unique_results[start_idx:end_idx]
    
    # Task #18: Metadata auto-completion (Async) for CURRENT PAGE ONLY
    # If some items (like Sukebei) lack covers, try to fill them from JavBus/JavDB
    from concurrent.futures import ThreadPoolExecutor
    def fill_metadata(item):
        code = item.get('code', 'Unknown')
        # Always try to fetch metadata if cover is empty or looks like a placeholder
        if not item.get('cover') or 'placeholder' in item.get('cover', ''):
            meta = metadata_mgr.get_metadata(code)
            if meta:
                # Add multiple alias fields for compatibility
                item['cover'] = meta.get('cover', '')
                item['image'] = item['cover']
                item['img_url'] = item['cover']
                item['thumb'] = meta.get('thumb', '')
                if not item.get('title') or item.get('title') == 'No Title':
                    item['title'] = meta.get('title', 'Unknown')
                if not item.get('date') or item.get('date') == 'Unknown':
                    item['date'] = meta.get('date', 'Unknown')
        
        # Ensure image url related fields are ALWAYS present (Aliases for safety)
        if 'cover' not in item: item['cover'] = ""
        item['image'] = item.get('cover', "")
        item['img_url'] = item.get('cover', "")
        if 'thumb' not in item: item['thumb'] = ""
        
        # Final fallback for empty covers (Smart dynamic placeholder)
        if not item['cover'] or item['cover'] == "":
            # Generate a more varied placeholder or use a stable one
            placeholder = f"https://via.placeholder.com/800x1200?text={code}"
            item['cover'] = placeholder
            item['image'] = placeholder
            item['img_url'] = placeholder
            item['thumb'] = placeholder.replace("800x1200", "300x450")
            
        return item

    # Enrich only the items being returned
    with ThreadPoolExecutor(max_workers=10) as executor:
        paginated_results = list(executor.map(fill_metadata, paginated_results))
    
    return jsonify(paginated_results)

def parse_size(size_str):
    # e.g., "5.43GB", "800MB", "4.0 GiB"
    match = re.search(r"(\d+\.?\d*)\s*(GB|MB|GiB|MiB)", size_str, re.I)
    if not match: return 0
    val = float(match.group(1))
    unit = match.group(2).upper()
    if unit in ['GB', 'GIB']: return val * 1024
    return val

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
