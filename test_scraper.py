from engine.javbus import JavBusCrawler
from engine.sukebei import SukebeiCrawler
import json

def test():
    query = "SSIS-123"
    config = {'PROXY': 'http://127.0.0.1:7890'}
    print(f"Testing JavBus for query: {query} with proxy {config['PROXY']}")
    javbus = JavBusCrawler(config)
    results = javbus.search(query)
    if results:
        print(f"JavBus found {len(results)} results")
        print(f"First result cover: {results[0].get('cover')}")
        print(f"First result code: {results[0].get('code')}")
    else:
        print("JavBus found 0 results")

    print("\nTesting Sukebei for query: SSIS")
    sukebei = SukebeiCrawler({})
    results = sukebei.search("SSIS")
    if results:
        print(f"Sukebei found {len(results)} results")
        print(f"First result cover: {results[0].get('cover')}")
        print(f"First result code: {results[0].get('code')}")

if __name__ == "__main__":
    test()
