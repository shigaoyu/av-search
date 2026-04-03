from flask import Flask, request, jsonify, render_template
from config import Config
from engine import get_crawlers
from engine.manager import MetadataManager
import re

app = Flask(__name__)
app.config.from_object(Config)
crawlers = get_crawlers(app.config)
metadata_mgr = MetadataManager(app.config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    query = request.args.get('q', '').upper()
    sort_type = request.args.get('sort', 'default')
    movie_type = request.args.get('type', 'all') # censored, uncensored, all
    chinese_only = request.args.get('chinese', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    
    results = []
    for crawler in crawlers:
        try:
            # Pass type and page to crawler search
            results.extend(crawler.search(query, type=movie_type, page=page))
        except Exception as e:
            print(f"Crawler error: {e}")
    
    # Enrichment: If no cover, try to find one using MetadataManager
    results = metadata_mgr.enrich_results(results)
    
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
    
    # Task #18: Metadata auto-completion (Async)
    # If some items (like Sukebei) lack covers, try to fill them from JavBus/JavDB
    from concurrent.futures import ThreadPoolExecutor
    def fill_metadata(item):
        if not item.get('cover') or item['cover'] == '':
            # Try to get from metadata-rich sources
            for crawler in crawlers:
                if hasattr(crawler, 'get_metadata'):
                    meta = crawler.get_metadata(item['code'])
                    if meta and meta.get('cover'):
                        item['cover'] = meta['cover']
                        if meta.get('title'): item['title'] = meta['title']
                        if meta.get('date'): item['date'] = meta['date']
                        break
        return item

    # Limit to top 20 for completion to keep it fast
    with ThreadPoolExecutor(max_workers=5) as executor:
        unique_results[:20] = list(executor.map(fill_metadata, unique_results[:20]))

    # Pagination logic
    paginated_results = unique_results[:20]
    
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
