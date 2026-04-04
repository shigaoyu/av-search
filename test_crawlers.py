from engine.javbus import JavBusCrawler
from engine.sukebei import SukebeiCrawler
from engine.javdb import JavDbCrawler
from config import Config

class MockConfig:
    def get(self, key, default=None):
        return getattr(Config, key, default)

config = MockConfig()
bus = JavBusCrawler(config)
suke = SukebeiCrawler(config)
db = JavDbCrawler(config)

print("Testing Sukebei...")
results = suke.search("SSIS-123")
print(f"Sukebei found {len(results)} items")
if results:
    print(f"First item keys: {results[0].keys()}")
    print(f"First item cover: '{results[0].get('cover')}'")

print("\nTesting JavBus...")
results = bus.search("SSIS-123")
print(f"JavBus found {len(results)} items")
if results:
    print(f"First item keys: {results[0].keys()}")
    print(f"First item cover: '{results[0].get('cover')}'")

print("\nTesting JavDB...")
results = db.search("SSIS-123")
print(f"JavDB found {len(results)} items")
if results:
    print(f"First item keys: {results[0].keys()}")
    print(f"First item cover: '{results[0].get('cover')}'")
