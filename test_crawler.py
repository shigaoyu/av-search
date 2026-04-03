import sys
import os
sys.path.append(os.getcwd())

from config import Config
from engine.javbus import JavBusCrawler
import json

class MockConfig:
    def get(self, key, default=None):
        data = {
            'PROXY': 'http://127.0.0.1:7890',
            'HEADERS': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        return data.get(key, default)

def test():
    config = MockConfig()
    crawler = JavBusCrawler(config)
    print("Testing search for 'SSIS-123'...")
    results = crawler.search("SSIS-123")
    print(f"Found {len(results)} results")
    if results:
        print(json.dumps(results[0], indent=2, ensure_ascii=False))
    
    print("\nTesting Popular/Recent...")
    results = crawler.search("")
    print(f"Found {len(results)} results")
    if results:
        print(json.dumps(results[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test()
