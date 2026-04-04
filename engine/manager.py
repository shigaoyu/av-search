from .javbus import JavBusCrawler
from .javdb import JavDbCrawler
import time

class MetadataManager:
    def __init__(self, config):
        self.config = config
        self.javbus = JavBusCrawler(config)
        self.javdb = JavDbCrawler(config)
        self.cache = {}

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
                    # Success!
                    self.cache[code] = meta
                    return meta
            except Exception as e:
                print(f"Metadata fetch (JavBus) failed: {e}")
            
        # Try JavDB
        try:
            metadata = self.javdb.get_metadata(code)
            if metadata and metadata.get('cover'):
                self.cache[code] = metadata
                return metadata
        except Exception as e:
            print(f"Metadata fetch (JavDB) failed: {e}")
            
        # Last resort: Placeholder but with the code
        return self._get_placeholder(code)

    def _get_placeholder(self, code):
        """Return a structured placeholder metadata."""
        # Using a more robust placeholder service or just a text-based one
        return {
            'title': f'Resource: {code}',
            'cover': f'https://via.placeholder.com/800x1200?text={code}',
            'thumb': f'https://via.placeholder.com/300x450?text={code}',
            'code': code,
            'date': 'Unknown'
        }

    def enrich_results(self, results):
        """Enrich results that are missing covers or other metadata."""
        # Find unique codes from results that need enrichment
        to_enrich = []
        for r in results:
            # If cover is a placeholder or empty, we enrich it
            if not r.get('cover') or 'placeholder' in r.get('cover', ''):
                if r['code'] not in to_enrich:
                    to_enrich.append(r['code'])
                    
        # Batch fetch metadata (in parallel would be better but let's keep it simple for now)
        # We only enrich the first 20 unique codes (full page) to avoid long response times
        meta_map = {}
        for code in to_enrich[:20]:
            meta = self.get_metadata(code)
            if meta:
                meta_map[code] = meta
                
        # Apply enrichment
        for r in results:
            code = r['code']
            if code in meta_map:
                meta = meta_map[code]
                if not r.get('cover') or 'placeholder' in r.get('cover', ''):
                    r['cover'] = meta['cover']
                if not r.get('title') or r.get('title') == 'No Title':
                    r['title'] = meta['title']
                if not r.get('date') or r.get('date') == 'Unknown':
                    r['date'] = meta['date']
                    
        return results
