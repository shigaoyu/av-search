import os
import json
from .javbus import JavBusCrawler
from .javdb import JavDbCrawler
from concurrent.futures import ThreadPoolExecutor

class MetadataManager:
    def __init__(self, config):
        self.config = config
        self.javbus = JavBusCrawler(config)
        self.javdb = JavDbCrawler(config)
        self.cache_file = os.path.join(os.path.dirname(__file__), 'metadata_cache.json')
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except: pass

    def get_metadata(self, code):
        """Fetch metadata for a given code (ID). Try multiple sources."""
        if not code or code == 'Unknown':
            return self._get_placeholder(code)
            
        if code in self.cache:
            return self.cache[code]
            
        # Try JavBus first
        if hasattr(self.javbus, 'get_metadata'):
            try:
                meta = self.javbus.get_metadata(code)
                if meta and meta.get('cover'):
                    self.cache[code] = meta
                    self._save_cache()
                    return meta
            except Exception as e:
                print(f"Metadata fetch (JavBus) failed: {e}")
            
        # Try JavDB
        try:
            metadata = self.javdb.get_metadata(code)
            if metadata and metadata.get('cover'):
                self.cache[code] = metadata
                self._save_cache()
                return metadata
        except Exception as e:
            print(f"Metadata fetch (JavDB) failed: {e}")
            
        return self._get_placeholder(code)

    def _get_placeholder(self, code):
        return {
            'title': f'Resource: {code}',
            'cover': f'https://via.placeholder.com/800x1200?text={code}',
            'thumb': f'https://via.placeholder.com/300x450?text={code}',
            'code': code,
            'date': 'Unknown'
        }

    def enrich_results_parallel(self, results):
        """Enrich results in parallel, optimized for unique codes."""
        # Deduplicate codes to fetch
        codes_to_fetch = list(set(r['code'] for r in results if not r.get('cover') or 'placeholder' in r.get('cover', '')))
        
        if not codes_to_fetch:
            return results
            
        # Parallel fetch for unique codes
        meta_map = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_code = {executor.submit(self.get_metadata, c): c for c in codes_to_fetch}
            for future in future_to_code:
                code = future_to_code[future]
                try:
                    meta = future.result()
                    if meta: meta_map[code] = meta
                except: pass
                
        # Apply metadata to all matching results
        for r in results:
            c = r['code']
            if c in meta_map:
                m = meta_map[c]
                r['cover'] = m.get('cover', '')
                r['thumb'] = m.get('thumb', '')
                if not r.get('title') or r.get('title') == 'No Title':
                    r['title'] = m.get('title', 'Unknown')
                if not r.get('date') or r.get('date') == 'Unknown':
                    r['date'] = m.get('date', 'Unknown')
                r['image'] = r['cover']
                r['img_url'] = r['cover']
                
        return results
