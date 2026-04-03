import sys
import os
sys.path.append(os.getcwd())

from config import Config
from engine.sukebei import SukebeiCrawler
import json

class MockConfig:
    def get(self, key, default=None):
        data = {
            'PROXY': 'http://127.0.0.1:7890',
            'HEADERS': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
        }
        return data.get(key, default)

def test():
    config = MockConfig()
    crawler = SukebeiCrawler(config)
    print("Testing Sukebei search for 'SSIS-123'...")
    results = crawler.search("SSIS-123")
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"- {r['title']} ({r['size']})")
    
    print("\nTesting Sukebei Popular...")
    results = crawler.search("")
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"- {r['title']} ({r['size']})")

if __name__ == "__main__":
    test()
